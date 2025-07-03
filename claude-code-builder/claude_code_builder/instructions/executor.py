"""Executor for custom instruction rules."""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict
import time

from ..models.custom_instructions import (
    InstructionRule, InstructionSet, InstructionContext,
    Priority, ValidationResult
)
from .engine import RulesEngine, RuleMatch
from .priority import PriorityExecutor, ExecutionPlan, ExecutionResult
from .filter import ContextFilter
from .validator import InstructionValidator

logger = logging.getLogger(__name__)


@dataclass
class ExecutionConfig:
    """Configuration for rule execution."""
    max_concurrent: int = 10
    timeout_seconds: int = 300
    retry_attempts: int = 3
    retry_delay: float = 1.0
    fail_fast: bool = False
    track_metrics: bool = True
    enable_caching: bool = True
    debug_mode: bool = False


@dataclass
class ExecutionMetrics:
    """Metrics for rule execution."""
    start_time: datetime
    end_time: Optional[datetime] = None
    rules_processed: int = 0
    rules_succeeded: int = 0
    rules_failed: int = 0
    rules_skipped: int = 0
    total_execution_time: float = 0.0
    avg_rule_time: float = 0.0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class RuleExecutor:
    """Executes custom instruction rules with advanced features."""
    
    def __init__(self, config: Optional[ExecutionConfig] = None):
        """Initialize the rule executor."""
        self.config = config or ExecutionConfig()
        self.engine = RulesEngine()
        self.priority_executor = PriorityExecutor()
        self.context_filter = ContextFilter()
        self.validator = InstructionValidator()
        
        # Execution state
        self.current_execution: Optional[str] = None
        self.execution_history: Dict[str, ExecutionMetrics] = {}
        
        # Custom action handlers
        self.action_handlers: Dict[str, Callable] = {}
        self.pre_processors: List[Callable] = []
        self.post_processors: List[Callable] = []
        
        # Result cache
        self.result_cache: Dict[str, Any] = {}
        
        # Initialize default handlers
        self._register_default_handlers()
        
        logger.info("Rule Executor initialized")
    
    async def execute(
        self,
        input_data: Dict[str, Any],
        instruction_set: InstructionSet,
        context: Optional[InstructionContext] = None,
        execution_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute an instruction set on input data."""
        execution_id = execution_id or self._generate_execution_id()
        self.current_execution = execution_id
        
        # Initialize metrics
        metrics = ExecutionMetrics(start_time=datetime.now())
        self.execution_history[execution_id] = metrics
        
        try:
            # Pre-process input
            processed_input = await self._pre_process(input_data, context)
            
            # Load instruction set into engine
            self.engine.load_instruction_set(instruction_set)
            
            # Filter rules based on context
            filtered_rules = self.context_filter.filter_rules(
                instruction_set.rules,
                context or InstructionContext()
            )
            
            metrics.rules_processed = len(filtered_rules)
            
            # Create execution plan
            plan = self.priority_executor.create_execution_plan(
                filtered_rules,
                context
            )
            
            # Execute plan
            results = await self.priority_executor.execute_plan(
                plan,
                processed_input,
                context,
                self._execute_rule_action
            )
            
            # Aggregate results
            final_result = await self._aggregate_results(
                results, processed_input, context
            )
            
            # Post-process results
            final_result = await self._post_process(final_result, context)
            
            # Update metrics
            self._update_metrics(metrics, results)
            
            # Cache results if enabled
            if self.config.enable_caching:
                cache_key = self._generate_cache_key(
                    input_data, instruction_set, context
                )
                self.result_cache[cache_key] = final_result
            
            return final_result
            
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            metrics.errors.append({
                "type": "execution_error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            
            if self.config.fail_fast:
                raise
            
            return {
                "status": "error",
                "error": str(e),
                "execution_id": execution_id,
                "partial_results": []
            }
        
        finally:
            metrics.end_time = datetime.now()
            metrics.total_execution_time = (
                metrics.end_time - metrics.start_time
            ).total_seconds()
            self.current_execution = None
    
    async def execute_batch(
        self,
        batch_data: List[Dict[str, Any]],
        instruction_set: InstructionSet,
        context: Optional[InstructionContext] = None,
        batch_size: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Execute rules on a batch of data."""
        batch_size = batch_size or self.config.max_concurrent
        results = []
        
        # Process in chunks
        for i in range(0, len(batch_data), batch_size):
            chunk = batch_data[i:i + batch_size]
            
            # Execute chunk concurrently
            chunk_tasks = [
                self.execute(data, instruction_set, context)
                for data in chunk
            ]
            
            chunk_results = await asyncio.gather(
                *chunk_tasks,
                return_exceptions=True
            )
            
            # Handle results
            for result in chunk_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch item failed: {result}")
                    if self.config.fail_fast:
                        raise result
                    results.append({
                        "status": "error",
                        "error": str(result)
                    })
                else:
                    results.append(result)
        
        return results
    
    def register_action_handler(
        self,
        action_type: str,
        handler: Callable
    ) -> None:
        """Register a custom action handler."""
        self.action_handlers[action_type] = handler
        logger.info(f"Registered action handler for: {action_type}")
    
    def add_pre_processor(self, processor: Callable) -> None:
        """Add a pre-processor function."""
        self.pre_processors.append(processor)
    
    def add_post_processor(self, processor: Callable) -> None:
        """Add a post-processor function."""
        self.post_processors.append(processor)
    
    async def validate_execution(
        self,
        input_data: Dict[str, Any],
        instruction_set: InstructionSet,
        context: Optional[InstructionContext] = None
    ) -> ValidationResult:
        """Validate execution before running."""
        errors = []
        warnings = []
        
        # Validate instruction set
        set_validation = self.validator.validate_instruction_set(instruction_set)
        if not set_validation.is_valid:
            errors.extend(set_validation.errors)
        warnings.extend(set_validation.warnings)
        
        # Validate input data structure
        input_validation = await self._validate_input(
            input_data, instruction_set
        )
        if not input_validation.is_valid:
            errors.extend(input_validation.errors)
        warnings.extend(input_validation.warnings)
        
        # Validate context if provided
        if context:
            context_validation = self._validate_context(context, instruction_set)
            if not context_validation.is_valid:
                errors.extend(context_validation.errors)
            warnings.extend(context_validation.warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata={
                "instruction_set": instruction_set.name,
                "rule_count": len(instruction_set.rules)
            }
        )
    
    def get_execution_metrics(
        self,
        execution_id: Optional[str] = None
    ) -> Union[ExecutionMetrics, Dict[str, ExecutionMetrics]]:
        """Get execution metrics."""
        if execution_id:
            return self.execution_history.get(execution_id)
        return dict(self.execution_history)
    
    def clear_cache(self) -> None:
        """Clear the result cache."""
        self.result_cache.clear()
        self.engine.clear_cache()
        logger.info("Execution cache cleared")
    
    async def _execute_rule_action(
        self,
        rule: InstructionRule,
        input_data: Dict[str, Any],
        context: Optional[InstructionContext]
    ) -> Dict[str, Any]:
        """Execute a single rule action."""
        start_time = time.time()
        
        try:
            # Parse action
            action_parts = rule.action.split(":", 1)
            action_type = action_parts[0]
            action_params = action_parts[1] if len(action_parts) > 1 else ""
            
            # Get handler
            handler = self.action_handlers.get(action_type)
            
            if handler:
                # Execute custom handler
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(
                        rule, input_data, action_params, context
                    )
                else:
                    result = handler(
                        rule, input_data, action_params, context
                    )
            else:
                # Use default engine execution
                match = RuleMatch(
                    rule=rule,
                    match_score=1.0,
                    matched_patterns=[],
                    context_match=True
                )
                result = self.engine._execute_action(
                    rule.action, input_data, match, context
                )
            
            # Add execution metadata
            result["_metadata"] = {
                "rule": rule.name,
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing rule '{rule.name}': {e}")
            
            # Retry logic
            if self.config.retry_attempts > 0:
                for attempt in range(self.config.retry_attempts):
                    await asyncio.sleep(self.config.retry_delay)
                    try:
                        return await self._execute_rule_action(
                            rule, input_data, context
                        )
                    except:
                        continue
            
            # Return error result
            return {
                "status": "error",
                "error": str(e),
                "rule": rule.name,
                "_metadata": {
                    "execution_time": time.time() - start_time,
                    "timestamp": datetime.now().isoformat()
                }
            }
    
    async def _pre_process(
        self,
        input_data: Dict[str, Any],
        context: Optional[InstructionContext]
    ) -> Dict[str, Any]:
        """Pre-process input data."""
        processed = input_data.copy()
        
        for processor in self.pre_processors:
            if asyncio.iscoroutinefunction(processor):
                processed = await processor(processed, context)
            else:
                processed = processor(processed, context)
        
        return processed
    
    async def _post_process(
        self,
        result: Dict[str, Any],
        context: Optional[InstructionContext]
    ) -> Dict[str, Any]:
        """Post-process results."""
        processed = result.copy()
        
        for processor in self.post_processors:
            if asyncio.iscoroutinefunction(processor):
                processed = await processor(processed, context)
            else:
                processed = processor(processed, context)
        
        return processed
    
    async def _aggregate_results(
        self,
        results: List[ExecutionResult],
        input_data: Dict[str, Any],
        context: Optional[InstructionContext]
    ) -> Dict[str, Any]:
        """Aggregate execution results."""
        aggregated = {
            "status": "completed",
            "execution_id": self.current_execution,
            "input_summary": self._summarize_input(input_data),
            "context": context.to_dict() if context else None,
            "results": [],
            "transformations": {},
            "validations": [],
            "enrichments": {},
            "metadata": {
                "total_rules": len(results),
                "successful_rules": sum(1 for r in results if r.success),
                "failed_rules": sum(1 for r in results if not r.success),
                "execution_time": sum(
                    r.metadata.get("execution_time", 0) for r in results
                )
            }
        }
        
        # Process each result
        for result in results:
            if result.success and result.output:
                # Add to results
                aggregated["results"].append({
                    "rule": result.rule_name,
                    "priority": result.priority.name,
                    "output": result.output
                })
                
                # Extract specific outputs
                if isinstance(result.output, dict):
                    if "transform" in result.output:
                        aggregated["transformations"].update(
                            result.output["transform"]
                        )
                    
                    if "valid" in result.output:
                        aggregated["validations"].append({
                            "rule": result.rule_name,
                            "valid": result.output["valid"],
                            "errors": result.output.get("errors", [])
                        })
                    
                    if "enrichments" in result.output:
                        aggregated["enrichments"].update(
                            result.output["enrichments"]
                        )
        
        return aggregated
    
    def _register_default_handlers(self) -> None:
        """Register default action handlers."""
        # Transform handler
        self.register_action_handler("transform", self._handle_transform)
        
        # Validate handler
        self.register_action_handler("validate", self._handle_validate)
        
        # Filter handler
        self.register_action_handler("filter", self._handle_filter)
        
        # Aggregate handler
        self.register_action_handler("aggregate", self._handle_aggregate)
        
        # Compute handler
        self.register_action_handler("compute", self._handle_compute)
    
    def _handle_transform(
        self,
        rule: InstructionRule,
        input_data: Dict[str, Any],
        params: str,
        context: Optional[InstructionContext]
    ) -> Dict[str, Any]:
        """Handle transform actions."""
        transformations = {}
        
        # Parse transformation expressions
        for expr in params.split(";"):
            if "=" in expr:
                target, source = expr.split("=", 1)
                target = target.strip()
                source = source.strip()
                
                # Evaluate transformation
                try:
                    # Simple evaluation (can be enhanced)
                    if source.startswith("$"):
                        # Reference to input field
                        field = source[1:]
                        transformations[target] = input_data.get(field)
                    else:
                        # Literal value
                        transformations[target] = source
                except Exception as e:
                    logger.error(f"Transform error: {e}")
        
        return {
            "status": "transformed",
            "transform": transformations
        }
    
    def _handle_validate(
        self,
        rule: InstructionRule,
        input_data: Dict[str, Any],
        params: str,
        context: Optional[InstructionContext]
    ) -> Dict[str, Any]:
        """Handle validate actions."""
        errors = []
        
        # Parse validation rules
        for validation in params.split(";"):
            if ":" in validation:
                field, constraint = validation.split(":", 1)
                field = field.strip()
                constraint = constraint.strip()
                
                value = input_data.get(field)
                
                # Apply constraint
                if constraint == "required" and not value:
                    errors.append(f"{field} is required")
                elif constraint.startswith("type:"):
                    expected_type = constraint[5:]
                    if not self._check_type(value, expected_type):
                        errors.append(
                            f"{field} must be of type {expected_type}"
                        )
        
        return {
            "status": "validated",
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def _handle_filter(
        self,
        rule: InstructionRule,
        input_data: Dict[str, Any],
        params: str,
        context: Optional[InstructionContext]
    ) -> Dict[str, Any]:
        """Handle filter actions."""
        if params.startswith("fields:"):
            # Filter specific fields
            fields = [f.strip() for f in params[7:].split(",")]
            filtered = {
                k: v for k, v in input_data.items()
                if k in fields
            }
        else:
            filtered = input_data
        
        return {
            "status": "filtered",
            "data": filtered
        }
    
    def _handle_aggregate(
        self,
        rule: InstructionRule,
        input_data: Dict[str, Any],
        params: str,
        context: Optional[InstructionContext]
    ) -> Dict[str, Any]:
        """Handle aggregate actions."""
        aggregations = {}
        
        # Simple aggregation (can be enhanced)
        if params == "count":
            aggregations["count"] = len(input_data)
        elif params == "sum":
            aggregations["sum"] = sum(
                v for v in input_data.values()
                if isinstance(v, (int, float))
            )
        
        return {
            "status": "aggregated",
            "aggregations": aggregations
        }
    
    def _handle_compute(
        self,
        rule: InstructionRule,
        input_data: Dict[str, Any],
        params: str,
        context: Optional[InstructionContext]
    ) -> Dict[str, Any]:
        """Handle compute actions."""
        computations = {}
        
        # Parse computation expressions
        for expr in params.split(";"):
            if "=" in expr:
                target, formula = expr.split("=", 1)
                target = target.strip()
                formula = formula.strip()
                
                # Evaluate formula (simplified)
                try:
                    # Replace field references
                    for field, value in input_data.items():
                        if isinstance(value, (int, float)):
                            formula = formula.replace(f"${field}", str(value))
                    
                    # Evaluate (UNSAFE - should use safe evaluation)
                    result = eval(formula)
                    computations[target] = result
                except Exception as e:
                    logger.error(f"Computation error: {e}")
        
        return {
            "status": "computed",
            "computations": computations
        }
    
    async def _validate_input(
        self,
        input_data: Dict[str, Any],
        instruction_set: InstructionSet
    ) -> ValidationResult:
        """Validate input data against instruction set requirements."""
        errors = []
        warnings = []
        
        # Check required fields from rules
        required_fields = set()
        for rule in instruction_set.rules:
            if rule.conditions:
                required_fields.update(rule.conditions.keys())
        
        # Check if required fields exist
        missing_fields = required_fields - set(input_data.keys())
        if missing_fields:
            warnings.append(
                f"Input missing fields referenced in rules: {missing_fields}"
            )
        
        return ValidationResult(
            is_valid=True,  # Non-blocking for now
            errors=errors,
            warnings=warnings
        )
    
    def _validate_context(
        self,
        context: InstructionContext,
        instruction_set: InstructionSet
    ) -> ValidationResult:
        """Validate context against instruction set requirements."""
        errors = []
        warnings = []
        
        # Check if context matches any rule requirements
        context_matched = False
        for rule in instruction_set.rules:
            if "context" in rule.metadata:
                # Check if this rule's context requirements are met
                rule_context = rule.metadata["context"]
                if self._context_matches(context, rule_context):
                    context_matched = True
                    break
        
        if not context_matched and len(instruction_set.rules) > 0:
            warnings.append(
                "Context may not match any rule requirements"
            )
        
        return ValidationResult(
            is_valid=True,
            errors=errors,
            warnings=warnings
        )
    
    def _context_matches(
        self,
        context: InstructionContext,
        requirements: Dict[str, Any]
    ) -> bool:
        """Check if context matches requirements."""
        if "environment" in requirements:
            if context.environment not in requirements["environment"]:
                return False
        
        if "phase" in requirements:
            if context.phase not in requirements["phase"]:
                return False
        
        return True
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "float": float,
            "boolean": bool,
            "list": list,
            "dict": dict
        }
        
        expected = type_map.get(expected_type.lower())
        if expected:
            return isinstance(value, expected)
        
        return True
    
    def _summarize_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create summary of input data."""
        return {
            "keys": list(input_data.keys())[:10],  # First 10 keys
            "size": len(input_data),
            "types": {
                k: type(v).__name__ 
                for k, v in list(input_data.items())[:5]
            }
        }
    
    def _generate_execution_id(self) -> str:
        """Generate unique execution ID."""
        import uuid
        return f"exec_{uuid.uuid4().hex[:12]}"
    
    def _generate_cache_key(
        self,
        input_data: Dict[str, Any],
        instruction_set: InstructionSet,
        context: Optional[InstructionContext]
    ) -> str:
        """Generate cache key for results."""
        import hashlib
        
        # Create hash from key components
        components = [
            str(sorted(input_data.items())),
            instruction_set.name,
            instruction_set.version,
            str(context.to_dict()) if context else "no_context"
        ]
        
        content = ":".join(components)
        return hashlib.md5(content.encode()).hexdigest()
    
    def _update_metrics(
        self,
        metrics: ExecutionMetrics,
        results: List[ExecutionResult]
    ) -> None:
        """Update execution metrics."""
        for result in results:
            if result.success:
                metrics.rules_succeeded += 1
            else:
                metrics.rules_failed += 1
                if result.error:
                    metrics.errors.append({
                        "rule": result.rule_name,
                        "error": result.error,
                        "timestamp": result.end_time.isoformat()
                    })
        
        if metrics.rules_processed > 0:
            metrics.avg_rule_time = (
                metrics.total_execution_time / metrics.rules_processed
            )