"""Validator for custom instructions with regex pattern support."""

import logging
import re
from typing import Dict, Any, List, Optional, Pattern, Union, Tuple
from datetime import datetime
from collections import defaultdict

from ..models.custom_instructions import (
    InstructionRule, InstructionSet, ValidationResult,
    InstructionContext, Priority
)

logger = logging.getLogger(__name__)


class PatternValidator:
    """Validates patterns and provides pattern matching capabilities."""
    
    def __init__(self):
        """Initialize the pattern validator."""
        self.compiled_patterns: Dict[str, Pattern] = {}
        self.pattern_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "compile_time": 0,
            "match_count": 0,
            "fail_count": 0,
            "avg_match_time": 0
        })
        
        # Common pattern templates
        self.pattern_templates = {
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "url": r"https?://[^\s]+",
            "ip_address": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
            "phone": r"[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{4,6}",
            "date": r"\d{4}-\d{2}-\d{2}",
            "time": r"\d{2}:\d{2}(:\d{2})?",
            "uuid": r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
            "version": r"\d+\.\d+(\.\d+)?",
            "camelCase": r"[a-z]+(?:[A-Z][a-z]+)*",
            "snake_case": r"[a-z]+(?:_[a-z]+)*",
            "kebab-case": r"[a-z]+(?:-[a-z]+)*"
        }
        
        # Pattern complexity analyzer
        self.complexity_indicators = {
            "lookahead": r"\(\?=",
            "lookbehind": r"\(\?<=",
            "negative_lookahead": r"\(\?!",
            "negative_lookbehind": r"\(\?<!",
            "backreference": r"\\[0-9]+",
            "named_group": r"\(\?P<\w+>",
            "conditional": r"\(\?\(",
            "recursive": r"\(\?R\)"
        }
    
    def compile_pattern(
        self,
        pattern: str,
        flags: int = re.IGNORECASE | re.MULTILINE
    ) -> Tuple[bool, Optional[Pattern], Optional[str]]:
        """Compile a regex pattern with validation."""
        start_time = datetime.now()
        
        try:
            # Check cache first
            cache_key = f"{pattern}:{flags}"
            if cache_key in self.compiled_patterns:
                return True, self.compiled_patterns[cache_key], None
            
            # Compile pattern
            compiled = re.compile(pattern, flags)
            self.compiled_patterns[cache_key] = compiled
            
            # Update stats
            compile_time = (datetime.now() - start_time).total_seconds()
            self.pattern_stats[pattern]["compile_time"] = compile_time
            
            return True, compiled, None
            
        except re.error as e:
            error_msg = f"Invalid regex pattern: {e}"
            logger.error(f"{error_msg} - Pattern: {pattern}")
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error compiling pattern: {e}"
            logger.error(f"{error_msg} - Pattern: {pattern}")
            return False, None, error_msg
    
    def validate_pattern(self, pattern: str) -> ValidationResult:
        """Validate a regex pattern."""
        errors = []
        warnings = []
        metadata = {}
        
        # Try to compile
        success, compiled, error = self.compile_pattern(pattern)
        if not success:
            errors.append(error)
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )
        
        # Analyze pattern complexity
        complexity = self._analyze_pattern_complexity(pattern)
        metadata["complexity"] = complexity
        
        if complexity["score"] > 0.8:
            warnings.append(
                f"High complexity pattern (score: {complexity['score']:.2f})"
            )
        
        # Check for common issues
        issues = self._check_pattern_issues(pattern)
        warnings.extend(issues)
        
        # Analyze pattern efficiency
        efficiency = self._analyze_pattern_efficiency(pattern)
        metadata["efficiency"] = efficiency
        
        if efficiency["potential_issues"]:
            warnings.extend(efficiency["potential_issues"])
        
        return ValidationResult(
            is_valid=True,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )
    
    def match_pattern(
        self,
        pattern: str,
        text: str,
        match_type: str = "search"
    ) -> Tuple[bool, Optional[List[str]], Dict[str, Any]]:
        """Match pattern against text."""
        start_time = datetime.now()
        
        # Compile pattern
        success, compiled, error = self.compile_pattern(pattern)
        if not success:
            return False, None, {"error": error}
        
        try:
            # Perform matching based on type
            if match_type == "match":
                match = compiled.match(text)
                matches = [match.group(0)] if match else None
            elif match_type == "fullmatch":
                match = compiled.fullmatch(text)
                matches = [match.group(0)] if match else None
            elif match_type == "findall":
                matches = compiled.findall(text)
                matches = matches if matches else None
            else:  # search
                match = compiled.search(text)
                matches = [match.group(0)] if match else None
            
            # Update statistics
            match_time = (datetime.now() - start_time).total_seconds()
            stats = self.pattern_stats[pattern]
            
            if matches:
                stats["match_count"] += 1
            else:
                stats["fail_count"] += 1
            
            # Update average match time
            total_matches = stats["match_count"] + stats["fail_count"]
            stats["avg_match_time"] = (
                (stats["avg_match_time"] * (total_matches - 1) + match_time) / 
                total_matches
            )
            
            metadata = {
                "match_type": match_type,
                "match_time": match_time,
                "matches_found": len(matches) if matches else 0
            }
            
            return bool(matches), matches, metadata
            
        except Exception as e:
            logger.error(f"Error matching pattern: {e}")
            return False, None, {"error": str(e)}
    
    def extract_groups(
        self,
        pattern: str,
        text: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], Dict[str, Any]]:
        """Extract named and numbered groups from pattern match."""
        success, compiled, error = self.compile_pattern(pattern)
        if not success:
            return False, None, {"error": error}
        
        try:
            match = compiled.search(text)
            if not match:
                return False, None, {"error": "No match found"}
            
            # Extract groups
            groups = {
                "full_match": match.group(0),
                "numbered_groups": match.groups(),
                "named_groups": match.groupdict()
            }
            
            metadata = {
                "pattern": pattern,
                "text_length": len(text),
                "match_start": match.start(),
                "match_end": match.end()
            }
            
            return True, groups, metadata
            
        except Exception as e:
            logger.error(f"Error extracting groups: {e}")
            return False, None, {"error": str(e)}
    
    def suggest_pattern(
        self,
        examples: List[str],
        negative_examples: Optional[List[str]] = None
    ) -> Tuple[str, float]:
        """Suggest a pattern based on examples."""
        if not examples:
            return "", 0.0
        
        # Analyze common characteristics
        characteristics = self._analyze_text_characteristics(examples)
        
        # Generate pattern based on characteristics
        pattern_parts = []
        
        # Length constraints
        if characteristics["length"]["consistent"]:
            avg_len = characteristics["length"]["average"]
            pattern_parts.append(f".{{{int(avg_len)}}}")
        else:
            min_len = characteristics["length"]["min"]
            max_len = characteristics["length"]["max"]
            pattern_parts.append(f".{{{min_len},{max_len}}}")
        
        # Character types
        if characteristics["has_digits"] and not characteristics["has_letters"]:
            pattern_parts = [r"\d" + p[1:] for p in pattern_parts]
        elif characteristics["has_letters"] and not characteristics["has_digits"]:
            pattern_parts = [r"[a-zA-Z]" + p[1:] for p in pattern_parts]
        
        # Common prefixes/suffixes
        if characteristics["common_prefix"]:
            pattern_parts.insert(0, re.escape(characteristics["common_prefix"]))
        if characteristics["common_suffix"]:
            pattern_parts.append(re.escape(characteristics["common_suffix"]))
        
        pattern = "".join(pattern_parts) if pattern_parts else ".*"
        
        # Test pattern against examples
        confidence = self._test_pattern_accuracy(
            pattern, examples, negative_examples
        )
        
        return pattern, confidence
    
    def _analyze_pattern_complexity(self, pattern: str) -> Dict[str, Any]:
        """Analyze pattern complexity."""
        complexity_score = 0.0
        features_used = []
        
        # Check for complexity indicators
        for feature, indicator in self.complexity_indicators.items():
            if re.search(indicator, pattern):
                features_used.append(feature)
                complexity_score += 0.15
        
        # Check pattern length
        if len(pattern) > 100:
            complexity_score += 0.2
        elif len(pattern) > 50:
            complexity_score += 0.1
        
        # Check nesting depth
        nesting_depth = self._calculate_nesting_depth(pattern)
        complexity_score += nesting_depth * 0.1
        
        # Check quantifier usage
        quantifiers = len(re.findall(r"[*+?{]", pattern))
        complexity_score += quantifiers * 0.05
        
        return {
            "score": min(complexity_score, 1.0),
            "features": features_used,
            "nesting_depth": nesting_depth,
            "length": len(pattern),
            "quantifiers": quantifiers
        }
    
    def _check_pattern_issues(self, pattern: str) -> List[str]:
        """Check for common pattern issues."""
        issues = []
        
        # Check for catastrophic backtracking
        if re.search(r"(.*)*", pattern) or re.search(r"(.+)+", pattern):
            issues.append("Potential catastrophic backtracking detected")
        
        # Check for unescaped special characters
        special_chars = r".^$*+?{}[]|()"
        for char in special_chars:
            if f"{char}" in pattern and f"\\{char}" not in pattern:
                # More sophisticated check needed, this is simplified
                pass
        
        # Check for unnecessary capturing groups
        capturing_groups = len(re.findall(r"\([^?]", pattern))
        non_capturing = len(re.findall(r"\(\?:", pattern))
        if capturing_groups > 5 and non_capturing == 0:
            issues.append(
                f"Consider using non-capturing groups (?:) - found {capturing_groups} capturing groups"
            )
        
        # Check for greedy quantifiers that could be lazy
        if re.search(r".*[^?]", pattern) or re.search(r".+[^?]", pattern):
            issues.append("Consider using lazy quantifiers (*?, +?) for better performance")
        
        return issues
    
    def _analyze_pattern_efficiency(self, pattern: str) -> Dict[str, Any]:
        """Analyze pattern efficiency."""
        potential_issues = []
        efficiency_score = 1.0
        
        # Check for anchors
        has_start_anchor = pattern.startswith("^")
        has_end_anchor = pattern.endswith("$")
        
        if not has_start_anchor and len(pattern) > 10:
            potential_issues.append("Consider adding ^ anchor for better performance")
            efficiency_score -= 0.1
        
        # Check for alternation at start
        if pattern.startswith("(") and "|" in pattern.split(")")[0]:
            potential_issues.append("Alternation at start may impact performance")
            efficiency_score -= 0.2
        
        # Check for redundant quantifiers
        if re.search(r"{1}", pattern):
            potential_issues.append("Redundant {1} quantifier found")
            efficiency_score -= 0.05
        
        # Check for character class optimization
        char_classes = re.findall(r"\[[^\]]+\]", pattern)
        for char_class in char_classes:
            if len(char_class) > 20 and "-" not in char_class:
                potential_issues.append(
                    f"Large character class without ranges: {char_class}"
                )
                efficiency_score -= 0.1
        
        return {
            "score": max(efficiency_score, 0.0),
            "has_anchors": {"start": has_start_anchor, "end": has_end_anchor},
            "potential_issues": potential_issues
        }
    
    def _calculate_nesting_depth(self, pattern: str) -> int:
        """Calculate maximum nesting depth of pattern."""
        max_depth = 0
        current_depth = 0
        
        for char in pattern:
            if char == "(" and not pattern[pattern.index(char)-1:pattern.index(char)] == "\\":
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == ")" and not pattern[pattern.index(char)-1:pattern.index(char)] == "\\":
                current_depth = max(0, current_depth - 1)
        
        return max_depth
    
    def _analyze_text_characteristics(
        self,
        examples: List[str]
    ) -> Dict[str, Any]:
        """Analyze characteristics of example texts."""
        if not examples:
            return {}
        
        lengths = [len(ex) for ex in examples]
        
        characteristics = {
            "length": {
                "min": min(lengths),
                "max": max(lengths),
                "average": sum(lengths) / len(lengths),
                "consistent": max(lengths) - min(lengths) <= 2
            },
            "has_digits": any(any(c.isdigit() for c in ex) for ex in examples),
            "has_letters": any(any(c.isalpha() for c in ex) for ex in examples),
            "has_special": any(
                any(not c.isalnum() for c in ex) for ex in examples
            ),
            "common_prefix": self._find_common_prefix(examples),
            "common_suffix": self._find_common_suffix(examples)
        }
        
        return characteristics
    
    def _find_common_prefix(self, strings: List[str]) -> str:
        """Find common prefix among strings."""
        if not strings:
            return ""
        
        prefix = strings[0]
        for s in strings[1:]:
            while not s.startswith(prefix):
                prefix = prefix[:-1]
                if not prefix:
                    return ""
        
        return prefix
    
    def _find_common_suffix(self, strings: List[str]) -> str:
        """Find common suffix among strings."""
        if not strings:
            return ""
        
        suffix = strings[0]
        for s in strings[1:]:
            while not s.endswith(suffix):
                suffix = suffix[1:]
                if not suffix:
                    return ""
        
        return suffix
    
    def _test_pattern_accuracy(
        self,
        pattern: str,
        positive_examples: List[str],
        negative_examples: Optional[List[str]] = None
    ) -> float:
        """Test pattern accuracy against examples."""
        if not positive_examples:
            return 0.0
        
        # Test positive examples
        positive_matches = 0
        for example in positive_examples:
            success, matches, _ = self.match_pattern(pattern, example)
            if success:
                positive_matches += 1
        
        positive_accuracy = positive_matches / len(positive_examples)
        
        # Test negative examples if provided
        if negative_examples:
            negative_matches = 0
            for example in negative_examples:
                success, matches, _ = self.match_pattern(pattern, example)
                if not success:  # Should NOT match
                    negative_matches += 1
            
            negative_accuracy = negative_matches / len(negative_examples)
            
            # Combined accuracy
            return (positive_accuracy + negative_accuracy) / 2
        
        return positive_accuracy


class InstructionValidator:
    """Validates instruction rules and sets."""
    
    def __init__(self):
        """Initialize the instruction validator."""
        self.pattern_validator = PatternValidator()
        self.validation_cache: Dict[str, ValidationResult] = {}
        
        # Validation rules
        self.validation_rules = {
            "name_format": re.compile(r"^[a-zA-Z][a-zA-Z0-9_\-\s]{2,50}$"),
            "action_format": re.compile(r"^[a-zA-Z]+:[^:]*$"),
            "priority_values": set(Priority.__members__.values()),
            "reserved_metadata": {
                "global", "disabled", "depends_on", "excludes",
                "context", "tags", "version"
            }
        }
    
    def validate_rule(self, rule: InstructionRule) -> ValidationResult:
        """Validate a single instruction rule."""
        errors = []
        warnings = []
        metadata = {}
        
        # Validate name
        if not rule.name:
            errors.append("Rule name is required")
        elif not self.validation_rules["name_format"].match(rule.name):
            errors.append(
                f"Invalid rule name format: '{rule.name}'. "
                "Must start with letter and contain only alphanumeric, "
                "underscore, hyphen, or space"
            )
        
        # Validate pattern if present
        if rule.pattern:
            pattern_result = self.pattern_validator.validate_pattern(rule.pattern)
            if not pattern_result.is_valid:
                errors.extend([
                    f"Pattern error: {e}" for e in pattern_result.errors
                ])
            warnings.extend(pattern_result.warnings)
            metadata["pattern_analysis"] = pattern_result.metadata
        
        # Validate action
        if not rule.action:
            warnings.append("Rule has no action defined")
        elif not self.validation_rules["action_format"].match(rule.action):
            warnings.append(
                f"Action format should be 'type:parameters', got: '{rule.action}'"
            )
        
        # Validate priority
        if rule.priority not in self.validation_rules["priority_values"]:
            errors.append(f"Invalid priority: {rule.priority}")
        
        # Validate conditions
        if rule.conditions:
            condition_result = self._validate_conditions(rule.conditions)
            if not condition_result.is_valid:
                errors.extend(condition_result.errors)
            warnings.extend(condition_result.warnings)
        
        # Validate metadata
        if rule.metadata:
            metadata_result = self._validate_metadata(rule.metadata)
            if not metadata_result.is_valid:
                errors.extend(metadata_result.errors)
            warnings.extend(metadata_result.warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )
    
    def validate_instruction_set(
        self,
        instruction_set: InstructionSet
    ) -> ValidationResult:
        """Validate an entire instruction set."""
        errors = []
        warnings = []
        metadata = {
            "total_rules": len(instruction_set.rules),
            "rules_validated": 0,
            "rules_with_errors": 0,
            "rules_with_warnings": 0
        }
        
        # Check for cache
        cache_key = f"{instruction_set.name}:{instruction_set.version}"
        if cache_key in self.validation_cache:
            logger.info(f"Using cached validation for {cache_key}")
            return self.validation_cache[cache_key]
        
        # Validate set metadata
        if not instruction_set.name:
            errors.append("Instruction set name is required")
        
        if not instruction_set.version:
            warnings.append("Instruction set version is recommended")
        
        # Validate each rule
        rule_names = set()
        for i, rule in enumerate(instruction_set.rules):
            # Check for duplicate names
            if rule.name in rule_names:
                errors.append(f"Duplicate rule name: '{rule.name}'")
            rule_names.add(rule.name)
            
            # Validate individual rule
            rule_result = self.validate_rule(rule)
            metadata["rules_validated"] += 1
            
            if rule_result.errors:
                metadata["rules_with_errors"] += 1
                errors.extend([
                    f"Rule '{rule.name}': {e}" for e in rule_result.errors
                ])
            
            if rule_result.warnings:
                metadata["rules_with_warnings"] += 1
                warnings.extend([
                    f"Rule '{rule.name}': {w}" for w in rule_result.warnings
                ])
        
        # Check inter-rule validations
        inter_rule_result = self._validate_inter_rule_constraints(instruction_set)
        if not inter_rule_result.is_valid:
            errors.extend(inter_rule_result.errors)
        warnings.extend(inter_rule_result.warnings)
        
        result = ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )
        
        # Cache result
        self.validation_cache[cache_key] = result
        
        return result
    
    def _validate_conditions(
        self,
        conditions: Dict[str, Any]
    ) -> ValidationResult:
        """Validate rule conditions."""
        errors = []
        warnings = []
        
        for field, condition in conditions.items():
            if not field:
                errors.append("Empty field name in condition")
                continue
            
            if isinstance(condition, dict):
                # Complex condition
                if "operator" not in condition:
                    errors.append(f"Complex condition for '{field}' missing operator")
                elif "value" not in condition:
                    errors.append(f"Complex condition for '{field}' missing value")
                else:
                    # Validate operator
                    valid_operators = {
                        "eq", "ne", "gt", "gte", "lt", "lte",
                        "in", "not_in", "contains", "regex"
                    }
                    if condition["operator"] not in valid_operators:
                        warnings.append(
                            f"Unknown operator '{condition['operator']}' "
                            f"for field '{field}'"
                        )
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_metadata(
        self,
        metadata: Dict[str, Any]
    ) -> ValidationResult:
        """Validate rule metadata."""
        errors = []
        warnings = []
        
        # Check dependencies
        if "depends_on" in metadata:
            deps = metadata["depends_on"]
            if not isinstance(deps, list):
                errors.append("'depends_on' must be a list of rule names")
            elif not all(isinstance(d, str) for d in deps):
                errors.append("All dependencies must be rule name strings")
        
        # Check exclusions
        if "excludes" in metadata:
            excludes = metadata["excludes"]
            if not isinstance(excludes, list):
                errors.append("'excludes' must be a list of rule names")
            elif not all(isinstance(e, str) for e in excludes):
                errors.append("All exclusions must be rule name strings")
        
        # Check tags
        if "tags" in metadata:
            tags = metadata["tags"]
            if not isinstance(tags, list):
                warnings.append("'tags' should be a list")
            elif not all(isinstance(t, str) for t in tags):
                warnings.append("All tags should be strings")
        
        # Check context requirements
        if "context" in metadata:
            context = metadata["context"]
            if not isinstance(context, dict):
                errors.append("'context' must be a dictionary")
            else:
                valid_context_keys = {
                    "environment", "phase", "features", "custom"
                }
                unknown_keys = set(context.keys()) - valid_context_keys
                if unknown_keys:
                    warnings.append(
                        f"Unknown context keys: {', '.join(unknown_keys)}"
                    )
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_inter_rule_constraints(
        self,
        instruction_set: InstructionSet
    ) -> ValidationResult:
        """Validate constraints between rules."""
        errors = []
        warnings = []
        
        rule_names = {rule.name for rule in instruction_set.rules}
        rule_by_name = {rule.name: rule for rule in instruction_set.rules}
        
        for rule in instruction_set.rules:
            # Check dependencies exist
            if "depends_on" in rule.metadata:
                for dep in rule.metadata["depends_on"]:
                    if dep not in rule_names:
                        errors.append(
                            f"Rule '{rule.name}' depends on non-existent "
                            f"rule '{dep}'"
                        )
            
            # Check exclusions exist
            if "excludes" in rule.metadata:
                for excl in rule.metadata["excludes"]:
                    if excl not in rule_names:
                        warnings.append(
                            f"Rule '{rule.name}' excludes non-existent "
                            f"rule '{excl}'"
                        )
            
            # Check for circular dependencies
            if "depends_on" in rule.metadata:
                visited = set()
                if self._has_circular_dependency(
                    rule.name, rule_by_name, visited, []
                ):
                    errors.append(
                        f"Circular dependency detected for rule '{rule.name}'"
                    )
        
        # Check for conflicting patterns at same priority
        self._check_pattern_conflicts(instruction_set.rules, errors, warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _has_circular_dependency(
        self,
        rule_name: str,
        rule_by_name: Dict[str, InstructionRule],
        visited: set,
        path: List[str]
    ) -> bool:
        """Check for circular dependencies."""
        if rule_name in path:
            return True
        
        if rule_name in visited:
            return False
        
        visited.add(rule_name)
        path.append(rule_name)
        
        rule = rule_by_name.get(rule_name)
        if rule and "depends_on" in rule.metadata:
            for dep in rule.metadata["depends_on"]:
                if dep in rule_by_name:
                    if self._has_circular_dependency(
                        dep, rule_by_name, visited, path
                    ):
                        return True
        
        path.pop()
        return False
    
    def _check_pattern_conflicts(
        self,
        rules: List[InstructionRule],
        errors: List[str],
        warnings: List[str]
    ) -> None:
        """Check for conflicting patterns."""
        # Group rules by priority
        priority_groups = defaultdict(list)
        for rule in rules:
            if rule.pattern:
                priority_groups[rule.priority].append(rule)
        
        # Check within each priority group
        for priority, group in priority_groups.items():
            for i, rule1 in enumerate(group):
                for rule2 in group[i+1:]:
                    if self._patterns_conflict(rule1.pattern, rule2.pattern):
                        warnings.append(
                            f"Potential pattern conflict between "
                            f"'{rule1.name}' and '{rule2.name}' "
                            f"at priority {priority.value}"
                        )
    
    def _patterns_conflict(self, pattern1: str, pattern2: str) -> bool:
        """Check if two patterns might conflict."""
        # Simple check - could be enhanced
        if pattern1 == pattern2:
            return True
        
        # Check if one pattern is a subset of another
        try:
            # Test with sample strings
            test_strings = ["test", "Test123", "test@example.com", "123"]
            conflicts = 0
            
            for test in test_strings:
                match1, _, _ = self.pattern_validator.match_pattern(
                    pattern1, test
                )
                match2, _, _ = self.pattern_validator.match_pattern(
                    pattern2, test
                )
                
                if match1 and match2:
                    conflicts += 1
            
            # If multiple test strings match both patterns, likely conflict
            return conflicts >= 2
            
        except:
            return False