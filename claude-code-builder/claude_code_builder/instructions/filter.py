"""Context-aware filter for custom instructions."""

import logging
from typing import Dict, Any, List, Optional, Set, Callable, Tuple
from datetime import datetime
from collections import defaultdict
import fnmatch

from ..models.custom_instructions import (
    InstructionRule, InstructionSet, InstructionContext,
    Priority
)

logger = logging.getLogger(__name__)


class ContextFilter:
    """Filters instructions based on context and conditions."""
    
    def __init__(self):
        """Initialize the context filter."""
        self.filter_cache: Dict[str, List[InstructionRule]] = {}
        self.context_matchers: Dict[str, Callable] = {
            "environment": self._match_environment,
            "phase": self._match_phase,
            "features": self._match_features,
            "tags": self._match_tags,
            "time": self._match_time_constraints,
            "user": self._match_user_constraints
        }
        
        # Filter statistics
        self.stats = defaultdict(lambda: {
            "total_filtered": 0,
            "rules_passed": 0,
            "rules_blocked": 0,
            "cache_hits": 0,
            "avg_filter_time": 0
        })
    
    def filter_rules(
        self,
        rules: List[InstructionRule],
        context: InstructionContext,
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> List[InstructionRule]:
        """Filter rules based on context."""
        start_time = datetime.now()
        
        # Generate cache key
        cache_key = self._generate_cache_key(rules, context, additional_filters)
        
        # Check cache
        if cache_key in self.filter_cache:
            self.stats[context.environment]["cache_hits"] += 1
            return self.filter_cache[cache_key]
        
        # Apply filters
        filtered_rules = []
        
        for rule in rules:
            if self._should_include_rule(rule, context, additional_filters):
                filtered_rules.append(rule)
                self.stats[context.environment]["rules_passed"] += 1
            else:
                self.stats[context.environment]["rules_blocked"] += 1
        
        # Update statistics
        filter_time = (datetime.now() - start_time).total_seconds()
        self._update_stats(context.environment, filter_time)
        
        # Cache results
        self.filter_cache[cache_key] = filtered_rules
        
        logger.info(
            f"Filtered {len(rules)} rules to {len(filtered_rules)} "
            f"for context {context.environment}/{context.phase}"
        )
        
        return filtered_rules
    
    def filter_by_priority(
        self,
        rules: List[InstructionRule],
        min_priority: Priority = Priority.LOW,
        max_priority: Priority = Priority.CRITICAL
    ) -> List[InstructionRule]:
        """Filter rules by priority range."""
        return [
            rule for rule in rules
            if min_priority.value <= rule.priority.value <= max_priority.value
        ]
    
    def filter_by_tags(
        self,
        rules: List[InstructionRule],
        required_tags: Optional[Set[str]] = None,
        excluded_tags: Optional[Set[str]] = None,
        match_all: bool = True
    ) -> List[InstructionRule]:
        """Filter rules by tags."""
        filtered_rules = []
        
        for rule in rules:
            rule_tags = set(rule.metadata.get("tags", []))
            
            # Check required tags
            if required_tags:
                if match_all:
                    if not required_tags.issubset(rule_tags):
                        continue
                else:
                    if not required_tags.intersection(rule_tags):
                        continue
            
            # Check excluded tags
            if excluded_tags:
                if excluded_tags.intersection(rule_tags):
                    continue
            
            filtered_rules.append(rule)
        
        return filtered_rules
    
    def filter_by_pattern(
        self,
        rules: List[InstructionRule],
        pattern_filter: str,
        use_glob: bool = True
    ) -> List[InstructionRule]:
        """Filter rules by pattern matching."""
        filtered_rules = []
        
        for rule in rules:
            if not rule.pattern:
                continue
            
            if use_glob:
                if fnmatch.fnmatch(rule.pattern, pattern_filter):
                    filtered_rules.append(rule)
            else:
                if pattern_filter in rule.pattern:
                    filtered_rules.append(rule)
        
        return filtered_rules
    
    def filter_by_capability(
        self,
        rules: List[InstructionRule],
        required_capabilities: Set[str],
        context: Optional[InstructionContext] = None
    ) -> List[InstructionRule]:
        """Filter rules by required capabilities."""
        filtered_rules = []
        
        for rule in rules:
            # Check if rule provides required capabilities
            rule_capabilities = set(rule.metadata.get("provides", []))
            
            if required_capabilities.issubset(rule_capabilities):
                # Additional context check if provided
                if context and not self._matches_context(rule, context):
                    continue
                
                filtered_rules.append(rule)
        
        return filtered_rules
    
    def create_context_filter(
        self,
        base_context: InstructionContext
    ) -> Callable[[InstructionRule], bool]:
        """Create a reusable context filter function."""
        def filter_func(rule: InstructionRule) -> bool:
            return self._matches_context(rule, base_context)
        
        return filter_func
    
    def _should_include_rule(
        self,
        rule: InstructionRule,
        context: InstructionContext,
        additional_filters: Optional[Dict[str, Any]]
    ) -> bool:
        """Determine if a rule should be included based on all filters."""
        # Check if rule is disabled
        if rule.metadata.get("disabled", False):
            return False
        
        # Check context match
        if not self._matches_context(rule, context):
            return False
        
        # Check additional filters
        if additional_filters:
            if not self._matches_additional_filters(rule, additional_filters):
                return False
        
        return True
    
    def _matches_context(
        self,
        rule: InstructionRule,
        context: InstructionContext
    ) -> bool:
        """Check if rule matches the given context."""
        rule_context = rule.metadata.get("context", {})
        
        if not rule_context:
            # No context requirements - always matches
            return True
        
        # Check each context dimension
        for dimension, matcher in self.context_matchers.items():
            if dimension in rule_context:
                if not matcher(rule_context[dimension], context):
                    return False
        
        return True
    
    def _match_environment(
        self,
        rule_env: Union[str, List[str]],
        context: InstructionContext
    ) -> bool:
        """Match environment constraint."""
        if isinstance(rule_env, str):
            rule_env = [rule_env]
        
        # Support wildcards
        for env in rule_env:
            if fnmatch.fnmatch(context.environment, env):
                return True
        
        return False
    
    def _match_phase(
        self,
        rule_phase: Union[str, List[str]],
        context: InstructionContext
    ) -> bool:
        """Match phase constraint."""
        if isinstance(rule_phase, str):
            rule_phase = [rule_phase]
        
        return context.phase in rule_phase
    
    def _match_features(
        self,
        rule_features: Dict[str, Any],
        context: InstructionContext
    ) -> bool:
        """Match feature constraints."""
        if "required" in rule_features:
            required = set(rule_features["required"])
            if not required.issubset(context.active_features):
                return False
        
        if "excluded" in rule_features:
            excluded = set(rule_features["excluded"])
            if excluded.intersection(context.active_features):
                return False
        
        if "any_of" in rule_features:
            any_of = set(rule_features["any_of"])
            if not any_of.intersection(context.active_features):
                return False
        
        return True
    
    def _match_tags(
        self,
        rule_tags: Dict[str, Any],
        context: InstructionContext
    ) -> bool:
        """Match tag constraints."""
        context_tags = set(context.metadata.get("tags", []))
        
        if "required" in rule_tags:
            required = set(rule_tags["required"])
            if not required.issubset(context_tags):
                return False
        
        if "excluded" in rule_tags:
            excluded = set(rule_tags["excluded"])
            if excluded.intersection(context_tags):
                return False
        
        return True
    
    def _match_time_constraints(
        self,
        time_constraints: Dict[str, Any],
        context: InstructionContext
    ) -> bool:
        """Match time-based constraints."""
        current_time = datetime.now()
        
        if "after" in time_constraints:
            after_time = datetime.fromisoformat(time_constraints["after"])
            if current_time < after_time:
                return False
        
        if "before" in time_constraints:
            before_time = datetime.fromisoformat(time_constraints["before"])
            if current_time > before_time:
                return False
        
        if "business_hours" in time_constraints:
            if time_constraints["business_hours"]:
                # Simple business hours check (9-5, Mon-Fri)
                if current_time.weekday() >= 5:  # Weekend
                    return False
                if current_time.hour < 9 or current_time.hour >= 17:
                    return False
        
        return True
    
    def _match_user_constraints(
        self,
        user_constraints: Dict[str, Any],
        context: InstructionContext
    ) -> bool:
        """Match user-based constraints."""
        if not context.user:
            return False
        
        if "roles" in user_constraints:
            required_roles = set(user_constraints["roles"])
            user_roles = set(context.metadata.get("user_roles", []))
            if not required_roles.intersection(user_roles):
                return False
        
        if "users" in user_constraints:
            allowed_users = user_constraints["users"]
            if context.user not in allowed_users:
                return False
        
        if "groups" in user_constraints:
            required_groups = set(user_constraints["groups"])
            user_groups = set(context.metadata.get("user_groups", []))
            if not required_groups.intersection(user_groups):
                return False
        
        return True
    
    def _matches_additional_filters(
        self,
        rule: InstructionRule,
        filters: Dict[str, Any]
    ) -> bool:
        """Match additional custom filters."""
        for key, value in filters.items():
            # Check in rule metadata
            if key in rule.metadata:
                rule_value = rule.metadata[key]
                
                # Handle different comparison types
                if isinstance(value, dict) and "operator" in value:
                    if not self._compare_values(
                        rule_value, value["operator"], value["value"]
                    ):
                        return False
                elif rule_value != value:
                    return False
            else:
                # Key not in metadata - doesn't match
                return False
        
        return True
    
    def _compare_values(
        self,
        actual: Any,
        operator: str,
        expected: Any
    ) -> bool:
        """Compare values with operator."""
        if operator == "eq":
            return actual == expected
        elif operator == "ne":
            return actual != expected
        elif operator == "gt":
            return actual > expected
        elif operator == "gte":
            return actual >= expected
        elif operator == "lt":
            return actual < expected
        elif operator == "lte":
            return actual <= expected
        elif operator == "in":
            return actual in expected
        elif operator == "not_in":
            return actual not in expected
        elif operator == "contains":
            return expected in str(actual)
        elif operator == "matches":
            return fnmatch.fnmatch(str(actual), expected)
        else:
            logger.warning(f"Unknown operator: {operator}")
            return False
    
    def _generate_cache_key(
        self,
        rules: List[InstructionRule],
        context: InstructionContext,
        additional_filters: Optional[Dict[str, Any]]
    ) -> str:
        """Generate cache key for filter results."""
        key_parts = [
            # Rules hash (simplified - could be improved)
            str(hash(tuple(r.name for r in rules))),
            # Context hash
            context.environment,
            context.phase,
            str(sorted(context.active_features)),
            # Additional filters
            str(additional_filters) if additional_filters else "no_filters"
        ]
        
        return ":".join(key_parts)
    
    def _update_stats(self, environment: str, filter_time: float) -> None:
        """Update filter statistics."""
        stats = self.stats[environment]
        stats["total_filtered"] += 1
        
        # Update average filter time
        total = stats["total_filtered"]
        stats["avg_filter_time"] = (
            (stats["avg_filter_time"] * (total - 1) + filter_time) / total
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get filter statistics."""
        return {
            "environments": dict(self.stats),
            "cache_size": len(self.filter_cache),
            "total_operations": sum(
                s["total_filtered"] for s in self.stats.values()
            )
        }
    
    def clear_cache(self) -> None:
        """Clear filter cache."""
        self.filter_cache.clear()
        logger.info("Filter cache cleared")
    
    def create_composite_filter(
        self,
        *filters: Callable[[InstructionRule], bool]
    ) -> Callable[[InstructionRule], bool]:
        """Create a composite filter from multiple filter functions."""
        def composite(rule: InstructionRule) -> bool:
            return all(f(rule) for f in filters)
        
        return composite
    
    def create_priority_gradient_filter(
        self,
        base_priority: Priority,
        context_modifiers: Dict[str, float]
    ) -> Callable[[InstructionRule], bool]:
        """Create a filter with dynamic priority based on context."""
        def gradient_filter(rule: InstructionRule) -> bool:
            # Calculate effective priority based on context
            effective_priority = base_priority.value
            
            for modifier_key, modifier_value in context_modifiers.items():
                if modifier_key in rule.metadata:
                    effective_priority += modifier_value
            
            # Check if rule priority meets effective threshold
            return rule.priority.value >= effective_priority
        
        return gradient_filter