"""Rules Engine for custom instructions processing."""

import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import re
from collections import defaultdict

from ..models.custom_instructions import (
    InstructionRule, InstructionSet, ValidationResult,
    InstructionContext, Priority
)

logger = logging.getLogger(__name__)


@dataclass
class RuleMatch:
    """Represents a matched rule."""
    rule: InstructionRule
    match_score: float
    matched_patterns: List[str]
    context_match: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class RulesEngine:
    """Engine for processing and executing custom instruction rules."""
    
    def __init__(self):
        """Initialize the Rules Engine."""
        self.rule_sets: Dict[str, InstructionSet] = {}
        self.global_rules: List[InstructionRule] = []
        self.rule_cache: Dict[str, List[RuleMatch]] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.context_stack: List[InstructionContext] = []
        
        # Pattern compilation cache
        self._compiled_patterns: Dict[str, re.Pattern] = {}
        
        # Rule statistics
        self.statistics = {
            "rules_loaded": 0,
            "rules_executed": 0,
            "rules_matched": 0,
            "cache_hits": 0,
            "validation_errors": 0
        }
        
        logger.info("Rules Engine initialized")
    
    def load_instruction_set(self, instruction_set: InstructionSet) -> None:
        """Load an instruction set into the engine."""
        set_id = instruction_set.metadata.get("id", f"set_{len(self.rule_sets)}")
        
        # Validate instruction set
        validation = self._validate_instruction_set(instruction_set)
        if not validation.is_valid:
            logger.error(f"Invalid instruction set: {validation.errors}")
            raise ValueError(f"Invalid instruction set: {validation.errors}")
        
        self.rule_sets[set_id] = instruction_set
        
        # Extract global rules
        for rule in instruction_set.rules:
            if rule.metadata.get("global", False):
                self.global_rules.append(rule)
        
        self.statistics["rules_loaded"] += len(instruction_set.rules)
        logger.info(f"Loaded instruction set '{set_id}' with {len(instruction_set.rules)} rules")
    
    def process(
        self,
        input_data: Dict[str, Any],
        context: Optional[InstructionContext] = None,
        rule_set_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Process input data through the rules engine."""
        start_time = datetime.now()
        
        # Set up context
        if context:
            self.context_stack.append(context)
        
        try:
            # Get applicable rules
            applicable_rules = self._get_applicable_rules(input_data, context, rule_set_ids)
            
            # Match rules
            matched_rules = self._match_rules(applicable_rules, input_data, context)
            
            # Sort by priority
            matched_rules.sort(key=lambda m: m.rule.priority.value, reverse=True)
            
            # Execute rules
            results = self._execute_rules(matched_rules, input_data, context)
            
            # Record execution
            execution_record = {
                "timestamp": start_time,
                "duration": (datetime.now() - start_time).total_seconds(),
                "input_summary": self._summarize_input(input_data),
                "rules_matched": len(matched_rules),
                "rules_executed": len(results["executed_rules"]),
                "context": context.to_dict() if context else None
            }
            self.execution_history.append(execution_record)
            
            return results
            
        finally:
            # Clean up context
            if context and self.context_stack:
                self.context_stack.pop()
    
    def validate_rules(
        self,
        rule_set_id: Optional[str] = None
    ) -> List[ValidationResult]:
        """Validate rules for conflicts and issues."""
        results = []
        
        if rule_set_id:
            rule_sets = [self.rule_sets.get(rule_set_id)]
            if not rule_sets[0]:
                return [ValidationResult(
                    is_valid=False,
                    errors=[f"Rule set '{rule_set_id}' not found"]
                )]
        else:
            rule_sets = list(self.rule_sets.values())
        
        for rule_set in rule_sets:
            if rule_set:
                # Check for pattern conflicts
                conflicts = self._check_pattern_conflicts(rule_set.rules)
                
                # Check for circular dependencies
                circular_deps = self._check_circular_dependencies(rule_set.rules)
                
                # Check for unreachable rules
                unreachable = self._check_unreachable_rules(rule_set.rules)
                
                errors = []
                warnings = []
                
                if conflicts:
                    warnings.extend([f"Pattern conflict: {c}" for c in conflicts])
                if circular_deps:
                    errors.extend([f"Circular dependency: {c}" for c in circular_deps])
                if unreachable:
                    warnings.extend([f"Unreachable rule: {r}" for r in unreachable])
                
                results.append(ValidationResult(
                    is_valid=len(errors) == 0,
                    errors=errors,
                    warnings=warnings,
                    metadata={
                        "rule_set": rule_set.name,
                        "rule_count": len(rule_set.rules)
                    }
                ))
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            **self.statistics,
            "cache_size": len(self.rule_cache),
            "execution_count": len(self.execution_history),
            "active_rule_sets": len(self.rule_sets),
            "global_rules": len(self.global_rules)
        }
    
    def clear_cache(self) -> None:
        """Clear the rule matching cache."""
        self.rule_cache.clear()
        logger.info("Rule cache cleared")
    
    def _validate_instruction_set(
        self,
        instruction_set: InstructionSet
    ) -> ValidationResult:
        """Validate an instruction set."""
        errors = []
        warnings = []
        
        # Check for empty rule set
        if not instruction_set.rules:
            errors.append("Instruction set contains no rules")
        
        # Validate individual rules
        for i, rule in enumerate(instruction_set.rules):
            # Check pattern validity
            if rule.pattern:
                try:
                    re.compile(rule.pattern)
                except re.error as e:
                    errors.append(f"Rule {i}: Invalid regex pattern: {e}")
            
            # Check for required fields
            if not rule.name:
                errors.append(f"Rule {i}: Missing rule name")
            
            if not rule.action:
                errors.append(f"Rule {i}: Missing rule action")
            
            # Check for duplicate rule names
            rule_names = [r.name for r in instruction_set.rules]
            if len(rule_names) != len(set(rule_names)):
                warnings.append("Duplicate rule names detected")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _get_applicable_rules(
        self,
        input_data: Dict[str, Any],
        context: Optional[InstructionContext],
        rule_set_ids: Optional[List[str]]
    ) -> List[InstructionRule]:
        """Get rules applicable to the current processing."""
        rules = []
        
        # Add global rules
        rules.extend(self.global_rules)
        
        # Add rules from specified sets
        if rule_set_ids:
            for set_id in rule_set_ids:
                if set_id in self.rule_sets:
                    rules.extend(self.rule_sets[set_id].rules)
        else:
            # Add all non-global rules
            for rule_set in self.rule_sets.values():
                rules.extend([
                    r for r in rule_set.rules
                    if not r.metadata.get("global", False)
                ])
        
        # Filter by context if provided
        if context:
            rules = [
                r for r in rules
                if self._matches_context(r, context)
            ]
        
        # Filter disabled rules
        rules = [r for r in rules if not r.metadata.get("disabled", False)]
        
        return rules
    
    def _match_rules(
        self,
        rules: List[InstructionRule],
        input_data: Dict[str, Any],
        context: Optional[InstructionContext]
    ) -> List[RuleMatch]:
        """Match rules against input data."""
        matches = []
        
        # Check cache
        cache_key = self._generate_cache_key(input_data, context)
        if cache_key in self.rule_cache:
            self.statistics["cache_hits"] += 1
            return self.rule_cache[cache_key]
        
        for rule in rules:
            match = self._match_single_rule(rule, input_data, context)
            if match:
                matches.append(match)
                self.statistics["rules_matched"] += 1
        
        # Cache results
        self.rule_cache[cache_key] = matches
        
        return matches
    
    def _match_single_rule(
        self,
        rule: InstructionRule,
        input_data: Dict[str, Any],
        context: Optional[InstructionContext]
    ) -> Optional[RuleMatch]:
        """Match a single rule against input data."""
        matched_patterns = []
        match_score = 0.0
        
        # Pattern matching
        if rule.pattern:
            pattern_match = self._match_pattern(rule.pattern, input_data)
            if pattern_match:
                matched_patterns.extend(pattern_match)
                match_score += 0.5
            elif rule.metadata.get("require_pattern_match", True):
                return None
        
        # Condition evaluation
        if rule.conditions:
            condition_match = self._evaluate_conditions(rule.conditions, input_data)
            if condition_match:
                match_score += 0.3
            else:
                return None
        
        # Context matching
        context_match = True
        if context and rule.metadata.get("context_required"):
            context_match = self._matches_context(rule, context)
            if context_match:
                match_score += 0.2
            else:
                return None
        
        # Create match if score > 0
        if match_score > 0:
            return RuleMatch(
                rule=rule,
                match_score=match_score,
                matched_patterns=matched_patterns,
                context_match=context_match,
                metadata={
                    "input_type": type(input_data).__name__,
                    "timestamp": datetime.now()
                }
            )
        
        return None
    
    def _match_pattern(
        self,
        pattern: str,
        input_data: Dict[str, Any]
    ) -> Optional[List[str]]:
        """Match pattern against input data."""
        matches = []
        
        # Compile pattern if not cached
        if pattern not in self._compiled_patterns:
            try:
                self._compiled_patterns[pattern] = re.compile(pattern, re.IGNORECASE)
            except re.error:
                logger.error(f"Invalid pattern: {pattern}")
                return None
        
        compiled = self._compiled_patterns[pattern]
        
        # Search in string representation of input
        input_str = str(input_data)
        pattern_matches = compiled.findall(input_str)
        if pattern_matches:
            matches.extend(pattern_matches)
        
        # Search in specific fields
        for key, value in input_data.items():
            if isinstance(value, str):
                field_matches = compiled.findall(value)
                if field_matches:
                    matches.extend(field_matches)
        
        return matches if matches else None
    
    def _evaluate_conditions(
        self,
        conditions: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> bool:
        """Evaluate rule conditions."""
        for field, expected in conditions.items():
            actual = input_data.get(field)
            
            # Handle different condition types
            if isinstance(expected, dict):
                # Complex condition
                if not self._evaluate_complex_condition(expected, actual):
                    return False
            elif callable(expected):
                # Lambda condition
                if not expected(actual):
                    return False
            else:
                # Simple equality
                if actual != expected:
                    return False
        
        return True
    
    def _evaluate_complex_condition(
        self,
        condition: Dict[str, Any],
        value: Any
    ) -> bool:
        """Evaluate complex conditions."""
        operator = condition.get("operator", "eq")
        expected = condition.get("value")
        
        if operator == "eq":
            return value == expected
        elif operator == "ne":
            return value != expected
        elif operator == "gt":
            return value > expected
        elif operator == "gte":
            return value >= expected
        elif operator == "lt":
            return value < expected
        elif operator == "lte":
            return value <= expected
        elif operator == "in":
            return value in expected
        elif operator == "not_in":
            return value not in expected
        elif operator == "contains":
            return expected in str(value)
        elif operator == "regex":
            return bool(re.search(expected, str(value)))
        else:
            logger.warning(f"Unknown operator: {operator}")
            return False
    
    def _matches_context(
        self,
        rule: InstructionRule,
        context: InstructionContext
    ) -> bool:
        """Check if rule matches the current context."""
        rule_context = rule.metadata.get("context", {})
        
        # Check environment
        if "environment" in rule_context:
            if context.environment not in rule_context["environment"]:
                return False
        
        # Check phase
        if "phase" in rule_context:
            if context.phase not in rule_context["phase"]:
                return False
        
        # Check feature flags
        if "features" in rule_context:
            required_features = set(rule_context["features"])
            if not required_features.issubset(context.active_features):
                return False
        
        # Check custom context
        if "custom" in rule_context:
            for key, value in rule_context["custom"].items():
                if context.metadata.get(key) != value:
                    return False
        
        return True
    
    def _execute_rules(
        self,
        matched_rules: List[RuleMatch],
        input_data: Dict[str, Any],
        context: Optional[InstructionContext]
    ) -> Dict[str, Any]:
        """Execute matched rules."""
        results = {
            "executed_rules": [],
            "outputs": [],
            "errors": [],
            "transformations": {},
            "metadata": {}
        }
        
        # Track rule execution
        executed_rule_names = set()
        
        for match in matched_rules:
            rule = match.rule
            
            # Check dependencies
            if rule.metadata.get("depends_on"):
                dependencies = rule.metadata["depends_on"]
                if not all(dep in executed_rule_names for dep in dependencies):
                    logger.debug(f"Skipping rule '{rule.name}' due to unmet dependencies")
                    continue
            
            # Check exclusions
            if rule.metadata.get("excludes"):
                exclusions = rule.metadata["excludes"]
                if any(exc in executed_rule_names for exc in exclusions):
                    logger.debug(f"Skipping rule '{rule.name}' due to exclusion")
                    continue
            
            try:
                # Execute rule action
                output = self._execute_action(rule.action, input_data, match, context)
                
                results["executed_rules"].append({
                    "name": rule.name,
                    "priority": rule.priority.value,
                    "match_score": match.match_score,
                    "output": output
                })
                
                results["outputs"].append(output)
                executed_rule_names.add(rule.name)
                self.statistics["rules_executed"] += 1
                
                # Apply transformations if any
                if "transform" in output:
                    results["transformations"].update(output["transform"])
                
            except Exception as e:
                logger.error(f"Error executing rule '{rule.name}': {e}")
                results["errors"].append({
                    "rule": rule.name,
                    "error": str(e)
                })
        
        return results
    
    def _execute_action(
        self,
        action: str,
        input_data: Dict[str, Any],
        match: RuleMatch,
        context: Optional[InstructionContext]
    ) -> Dict[str, Any]:
        """Execute a rule action."""
        # Parse action type
        action_parts = action.split(":", 1)
        action_type = action_parts[0]
        action_params = action_parts[1] if len(action_parts) > 1 else ""
        
        if action_type == "transform":
            return self._action_transform(action_params, input_data, match)
        elif action_type == "validate":
            return self._action_validate(action_params, input_data, match)
        elif action_type == "filter":
            return self._action_filter(action_params, input_data, match)
        elif action_type == "enrich":
            return self._action_enrich(action_params, input_data, match, context)
        elif action_type == "notify":
            return self._action_notify(action_params, match)
        elif action_type == "custom":
            return self._action_custom(action_params, input_data, match, context)
        else:
            logger.warning(f"Unknown action type: {action_type}")
            return {"status": "unknown_action", "action": action}
    
    def _action_transform(
        self,
        params: str,
        input_data: Dict[str, Any],
        match: RuleMatch
    ) -> Dict[str, Any]:
        """Transform action implementation."""
        transformations = {}
        
        # Parse transformation rules
        for transform in params.split(";"):
            if "=" in transform:
                field, expr = transform.split("=", 1)
                field = field.strip()
                expr = expr.strip()
                
                # Evaluate expression
                try:
                    # Simple expression evaluation (could be enhanced)
                    if expr.startswith("upper("):
                        source_field = expr[6:-1]
                        transformations[field] = input_data.get(source_field, "").upper()
                    elif expr.startswith("lower("):
                        source_field = expr[6:-1]
                        transformations[field] = input_data.get(source_field, "").lower()
                    elif expr.startswith("concat("):
                        fields = expr[7:-1].split(",")
                        transformations[field] = "".join(
                            str(input_data.get(f.strip(), "")) for f in fields
                        )
                    else:
                        # Direct assignment
                        transformations[field] = expr
                except Exception as e:
                    logger.error(f"Transform error: {e}")
        
        return {
            "status": "transformed",
            "transform": transformations,
            "rule": match.rule.name
        }
    
    def _action_validate(
        self,
        params: str,
        input_data: Dict[str, Any],
        match: RuleMatch
    ) -> Dict[str, Any]:
        """Validate action implementation."""
        validation_errors = []
        
        # Parse validation rules
        for validation in params.split(";"):
            if ":" in validation:
                field, rule = validation.split(":", 1)
                field = field.strip()
                rule = rule.strip()
                
                value = input_data.get(field)
                
                # Apply validation rule
                if rule == "required" and not value:
                    validation_errors.append(f"{field} is required")
                elif rule.startswith("min_length:"):
                    min_len = int(rule.split(":")[1])
                    if len(str(value or "")) < min_len:
                        validation_errors.append(
                            f"{field} must be at least {min_len} characters"
                        )
                elif rule.startswith("max_length:"):
                    max_len = int(rule.split(":")[1])
                    if len(str(value or "")) > max_len:
                        validation_errors.append(
                            f"{field} must not exceed {max_len} characters"
                        )
                elif rule.startswith("pattern:"):
                    pattern = rule.split(":", 1)[1]
                    if not re.match(pattern, str(value or "")):
                        validation_errors.append(f"{field} does not match required pattern")
        
        return {
            "status": "validated",
            "valid": len(validation_errors) == 0,
            "errors": validation_errors,
            "rule": match.rule.name
        }
    
    def _action_filter(
        self,
        params: str,
        input_data: Dict[str, Any],
        match: RuleMatch
    ) -> Dict[str, Any]:
        """Filter action implementation."""
        filtered_data = {}
        
        # Parse filter rules
        if params.startswith("include:"):
            # Include only specified fields
            fields = [f.strip() for f in params[8:].split(",")]
            for field in fields:
                if field in input_data:
                    filtered_data[field] = input_data[field]
        elif params.startswith("exclude:"):
            # Exclude specified fields
            excluded = set(f.strip() for f in params[8:].split(","))
            filtered_data = {
                k: v for k, v in input_data.items()
                if k not in excluded
            }
        
        return {
            "status": "filtered",
            "data": filtered_data,
            "rule": match.rule.name
        }
    
    def _action_enrich(
        self,
        params: str,
        input_data: Dict[str, Any],
        match: RuleMatch,
        context: Optional[InstructionContext]
    ) -> Dict[str, Any]:
        """Enrich action implementation."""
        enrichments = {}
        
        # Add metadata
        enrichments["_metadata"] = {
            "rule": match.rule.name,
            "timestamp": datetime.now().isoformat(),
            "match_score": match.match_score
        }
        
        # Add context if available
        if context:
            enrichments["_context"] = {
                "environment": context.environment,
                "phase": context.phase,
                "user": context.user
            }
        
        # Parse enrichment rules
        for enrichment in params.split(";"):
            if "=" in enrichment:
                field, value = enrichment.split("=", 1)
                enrichments[field.strip()] = value.strip()
        
        return {
            "status": "enriched",
            "enrichments": enrichments,
            "rule": match.rule.name
        }
    
    def _action_notify(
        self,
        params: str,
        match: RuleMatch
    ) -> Dict[str, Any]:
        """Notify action implementation."""
        # In a real implementation, this would send notifications
        logger.info(f"Notification from rule '{match.rule.name}': {params}")
        
        return {
            "status": "notified",
            "message": params,
            "rule": match.rule.name
        }
    
    def _action_custom(
        self,
        params: str,
        input_data: Dict[str, Any],
        match: RuleMatch,
        context: Optional[InstructionContext]
    ) -> Dict[str, Any]:
        """Custom action implementation."""
        # This would call custom handlers in a real implementation
        return {
            "status": "custom_executed",
            "params": params,
            "rule": match.rule.name,
            "input_summary": self._summarize_input(input_data)
        }
    
    def _check_pattern_conflicts(
        self,
        rules: List[InstructionRule]
    ) -> List[str]:
        """Check for conflicting patterns in rules."""
        conflicts = []
        
        for i, rule1 in enumerate(rules):
            if not rule1.pattern:
                continue
                
            for rule2 in rules[i+1:]:
                if not rule2.pattern:
                    continue
                
                # Simple conflict detection - could be enhanced
                if rule1.pattern == rule2.pattern and rule1.priority == rule2.priority:
                    conflicts.append(
                        f"Rules '{rule1.name}' and '{rule2.name}' have identical patterns and priority"
                    )
        
        return conflicts
    
    def _check_circular_dependencies(
        self,
        rules: List[InstructionRule]
    ) -> List[str]:
        """Check for circular dependencies in rules."""
        circular = []
        
        # Build dependency graph
        deps = {}
        for rule in rules:
            if rule.metadata.get("depends_on"):
                deps[rule.name] = rule.metadata["depends_on"]
        
        # Check for cycles
        for rule_name in deps:
            visited = set()
            if self._has_cycle(rule_name, deps, visited, []):
                circular.append(f"Circular dependency detected involving '{rule_name}'")
        
        return circular
    
    def _has_cycle(
        self,
        node: str,
        graph: Dict[str, List[str]],
        visited: Set[str],
        path: List[str]
    ) -> bool:
        """Check if there's a cycle in the dependency graph."""
        if node in path:
            return True
        
        if node in visited:
            return False
        
        visited.add(node)
        path.append(node)
        
        if node in graph:
            for neighbor in graph[node]:
                if self._has_cycle(neighbor, graph, visited, path):
                    return True
        
        path.pop()
        return False
    
    def _check_unreachable_rules(
        self,
        rules: List[InstructionRule]
    ) -> List[str]:
        """Check for rules that can never be executed."""
        unreachable = []
        
        # Group rules by priority
        priority_groups = defaultdict(list)
        for rule in rules:
            priority_groups[rule.priority].append(rule)
        
        # Check for shadowed rules
        for priority in sorted(priority_groups.keys(), reverse=True):
            group = priority_groups[priority]
            for i, rule1 in enumerate(group):
                for rule2 in group[i+1:]:
                    if self._rule_shadows(rule1, rule2):
                        unreachable.append(
                            f"Rule '{rule2.name}' is shadowed by '{rule1.name}'"
                        )
        
        return unreachable
    
    def _rule_shadows(
        self,
        rule1: InstructionRule,
        rule2: InstructionRule
    ) -> bool:
        """Check if rule1 shadows rule2."""
        # Simple implementation - could be enhanced
        if rule1.pattern and rule2.pattern:
            # Check if patterns overlap
            if rule1.pattern == rule2.pattern:
                return True
        
        return False
    
    def _generate_cache_key(
        self,
        input_data: Dict[str, Any],
        context: Optional[InstructionContext]
    ) -> str:
        """Generate cache key for rule matching."""
        # Simple hash-based key
        key_parts = [
            str(hash(frozenset(input_data.items()))),
            str(context.to_dict()) if context else "no_context"
        ]
        return ":".join(key_parts)
    
    def _summarize_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of input data."""
        return {
            "keys": list(input_data.keys()),
            "size": len(str(input_data)),
            "types": {k: type(v).__name__ for k, v in input_data.items()}
        }