"""Task Runner for executing individual build tasks."""

import logging
import asyncio
import time
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import json
import os

from ..models.phase import Task, TaskStatus, TaskResult
from ..exceptions import ValidationError
from ..sdk.session import SessionManager
from ..sdk.tools import ToolManager

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of tasks that can be executed."""
    CODE_GENERATION = "code_generation"
    FILE_OPERATION = "file_operation"
    COMMAND_EXECUTION = "command_execution"
    API_CALL = "api_call"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    ANALYSIS = "analysis"
    CUSTOM = "custom"


@dataclass
class TaskRunnerConfig:
    """Configuration for task runner."""
    timeout: int = 600  # seconds
    retry_attempts: int = 3
    retry_delay: float = 1.0
    capture_output: bool = True
    working_directory: Optional[str] = None
    environment_vars: Dict[str, str] = field(default_factory=dict)
    tool_restrictions: List[str] = field(default_factory=list)
    enable_sandboxing: bool = False


@dataclass
class TaskExecutionContext:
    """Context for task execution."""
    task: Task
    global_context: Dict[str, Any]
    session_id: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    attempts: int = 0
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


class TaskRunner:
    """Runs individual build tasks with proper isolation and error handling."""
    
    def __init__(self, config: Optional[TaskRunnerConfig] = None):
        """Initialize the task runner."""
        self.config = config or TaskRunnerConfig()
        
        # Session and tool management
        self.session_manager = SessionManager()
        self.tool_manager = ToolManager()
        
        # Task type handlers
        self.task_handlers: Dict[TaskType, Callable] = {
            TaskType.CODE_GENERATION: self._run_code_generation,
            TaskType.FILE_OPERATION: self._run_file_operation,
            TaskType.COMMAND_EXECUTION: self._run_command_execution,
            TaskType.API_CALL: self._run_api_call,
            TaskType.VALIDATION: self._run_validation,
            TaskType.TRANSFORMATION: self._run_transformation,
            TaskType.ANALYSIS: self._run_analysis,
            TaskType.CUSTOM: self._run_custom
        }
        
        # Custom handlers
        self.custom_handlers: Dict[str, Callable] = {}
        
        # Execution hooks
        self.pre_execution_hooks: List[Callable] = []
        self.post_execution_hooks: List[Callable] = []
        
        logger.info("Task Runner initialized")
    
    async def run_task(
        self,
        task: Task,
        context: Dict[str, Any]
    ) -> TaskResult:
        """Run a single task."""
        logger.info(f"Running task: {task.name} (type: {task.type})")
        
        # Create execution context
        exec_context = TaskExecutionContext(
            task=task,
            global_context=context
        )
        
        try:
            # Run pre-execution hooks
            await self._run_hooks(self.pre_execution_hooks, exec_context)
            
            # Determine task type
            task_type = self._determine_task_type(task)
            
            # Get handler
            handler = self.task_handlers.get(task_type)
            if not handler:
                raise ValidationError(
                    f"No handler for task type: {task_type}"
                )
            
            # Execute with timeout
            result = await asyncio.wait_for(
                handler(exec_context),
                timeout=self.config.timeout
            )
            
            # Run post-execution hooks
            await self._run_hooks(self.post_execution_hooks, exec_context)
            
            # Create task result
            return self._create_task_result(exec_context, result, TaskStatus.COMPLETED)
            
        except asyncio.TimeoutError:
            logger.error(f"Task timed out: {task.name}")
            return self._create_task_result(
                exec_context,
                {"error": "Task execution timed out"},
                TaskStatus.FAILED
            )
            
        except Exception as e:
            logger.error(f"Task execution failed: {task.name} - {e}")
            
            # Retry if configured
            if exec_context.attempts < self.config.retry_attempts:
                return await self._retry_task(exec_context, context)
            
            return self._create_task_result(
                exec_context,
                {"error": str(e)},
                TaskStatus.FAILED
            )
    
    def register_custom_handler(
        self,
        handler_name: str,
        handler: Callable
    ) -> None:
        """Register a custom task handler."""
        self.custom_handlers[handler_name] = handler
        logger.info(f"Registered custom handler: {handler_name}")
    
    def add_pre_execution_hook(self, hook: Callable) -> None:
        """Add a pre-execution hook."""
        self.pre_execution_hooks.append(hook)
    
    def add_post_execution_hook(self, hook: Callable) -> None:
        """Add a post-execution hook."""
        self.post_execution_hooks.append(hook)
    
    async def _run_code_generation(
        self,
        context: TaskExecutionContext
    ) -> Dict[str, Any]:
        """Run a code generation task."""
        task = context.task
        
        # Create or get session
        if not context.session_id:
            session = await self.session_manager.create_session(
                project_id=context.global_context.project_id
            )
            context.session_id = session.id
        
        # Prepare tools
        tools = await self._prepare_tools(task)
        
        # Prepare prompt
        prompt = self._prepare_prompt(task, context.global_context)
        
        # Execute code generation
        start_time = time.time()
        
        # This would integrate with Claude Code SDK
        # For now, it's a placeholder
        result = {
            "status": "generated",
            "files_created": [],
            "files_modified": [],
            "code_blocks": []
        }
        
        # Record metrics
        context.metrics["generation_time"] = time.time() - start_time
        context.metrics["tokens_used"] = 0  # Would come from actual API
        
        return result
    
    async def _run_file_operation(
        self,
        context: TaskExecutionContext
    ) -> Dict[str, Any]:
        """Run a file operation task."""
        task = context.task
        operation = task.metadata.get("operation", "create")
        
        result = {
            "status": "completed",
            "operations": []
        }
        
        if operation == "create":
            files = task.metadata.get("files", [])
            for file_info in files:
                path = file_info.get("path")
                content = file_info.get("content", "")
                
                # Create file
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w') as f:
                    f.write(content)
                
                result["operations"].append({
                    "type": "create",
                    "path": path,
                    "size": len(content)
                })
                
        elif operation == "copy":
            source = task.metadata.get("source")
            destination = task.metadata.get("destination")
            
            # Copy operation
            import shutil
            shutil.copy2(source, destination)
            
            result["operations"].append({
                "type": "copy",
                "source": source,
                "destination": destination
            })
            
        elif operation == "delete":
            paths = task.metadata.get("paths", [])
            for path in paths:
                if os.path.exists(path):
                    if os.path.isdir(path):
                        import shutil
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                    
                    result["operations"].append({
                        "type": "delete",
                        "path": path
                    })
        
        return result
    
    async def _run_command_execution(
        self,
        context: TaskExecutionContext
    ) -> Dict[str, Any]:
        """Run a command execution task."""
        task = context.task
        command = task.metadata.get("command")
        
        if not command:
            raise ValidationError("No command specified")
        
        # Prepare environment
        env = os.environ.copy()
        env.update(self.config.environment_vars)
        env.update(task.metadata.get("env", {}))
        
        # Determine working directory
        cwd = (
            task.metadata.get("working_directory") or
            self.config.working_directory or
            os.getcwd()
        )
        
        # Execute command
        start_time = time.time()
        
        try:
            if isinstance(command, list):
                cmd = command
            else:
                cmd = command.split()
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE if self.config.capture_output else None,
                stderr=asyncio.subprocess.PIPE if self.config.capture_output else None,
                cwd=cwd,
                env=env
            )
            
            stdout, stderr = await process.communicate()
            
            result = {
                "status": "completed",
                "exit_code": process.returncode,
                "command": command,
                "duration": time.time() - start_time
            }
            
            if self.config.capture_output:
                result["stdout"] = stdout.decode() if stdout else ""
                result["stderr"] = stderr.decode() if stderr else ""
            
            if process.returncode != 0:
                result["status"] = "failed"
                context.errors.append(
                    f"Command failed with exit code {process.returncode}"
                )
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "command": command
            }
    
    async def _run_api_call(
        self,
        context: TaskExecutionContext
    ) -> Dict[str, Any]:
        """Run an API call task."""
        task = context.task
        
        # Extract API details
        endpoint = task.metadata.get("endpoint")
        method = task.metadata.get("method", "GET")
        headers = task.metadata.get("headers", {})
        body = task.metadata.get("body")
        
        if not endpoint:
            raise ValidationError("No API endpoint specified")
        
        # Make API call (using aiohttp)
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            
            async with session.request(
                method=method,
                url=endpoint,
                headers=headers,
                json=body if body and method != "GET" else None
            ) as response:
                response_data = await response.text()
                
                try:
                    response_json = json.loads(response_data)
                except:
                    response_json = None
                
                result = {
                    "status": "completed",
                    "status_code": response.status,
                    "duration": time.time() - start_time,
                    "response": response_json or response_data,
                    "headers": dict(response.headers)
                }
                
                if response.status >= 400:
                    result["status"] = "error"
                    context.errors.append(
                        f"API call failed with status {response.status}"
                    )
                
                return result
    
    async def _run_validation(
        self,
        context: TaskExecutionContext
    ) -> Dict[str, Any]:
        """Run a validation task."""
        task = context.task
        validation_type = task.metadata.get("validation_type", "general")
        target = task.metadata.get("target")
        
        result = {
            "status": "completed",
            "validation_type": validation_type,
            "errors": [],
            "warnings": []
        }
        
        if validation_type == "file_exists":
            paths = task.metadata.get("paths", [])
            for path in paths:
                if not os.path.exists(path):
                    result["errors"].append(f"File not found: {path}")
                    
        elif validation_type == "json_schema":
            schema = task.metadata.get("schema")
            data = task.metadata.get("data")
            
            # Validate against schema
            import jsonschema
            try:
                jsonschema.validate(data, schema)
            except jsonschema.ValidationError as e:
                result["errors"].append(str(e))
                
        elif validation_type == "custom":
            validator_name = task.metadata.get("validator")
            if validator_name in self.custom_handlers:
                validation_result = await self.custom_handlers[validator_name](
                    context
                )
                result.update(validation_result)
        
        result["valid"] = len(result["errors"]) == 0
        
        return result
    
    async def _run_transformation(
        self,
        context: TaskExecutionContext
    ) -> Dict[str, Any]:
        """Run a transformation task."""
        task = context.task
        transform_type = task.metadata.get("transform_type", "general")
        
        result = {
            "status": "completed",
            "transform_type": transform_type,
            "outputs": {}
        }
        
        if transform_type == "template":
            template = task.metadata.get("template")
            variables = task.metadata.get("variables", {})
            
            # Simple template rendering
            import string
            template_obj = string.Template(template)
            result["outputs"]["rendered"] = template_obj.substitute(variables)
            
        elif transform_type == "json":
            source = task.metadata.get("source")
            transformations = task.metadata.get("transformations", [])
            
            # Apply JSON transformations
            data = source
            for transform in transformations:
                # Apply transformation (simplified)
                pass
            
            result["outputs"]["transformed"] = data
            
        elif transform_type == "custom":
            transformer_name = task.metadata.get("transformer")
            if transformer_name in self.custom_handlers:
                transform_result = await self.custom_handlers[transformer_name](
                    context
                )
                result["outputs"] = transform_result
        
        return result
    
    async def _run_analysis(
        self,
        context: TaskExecutionContext
    ) -> Dict[str, Any]:
        """Run an analysis task."""
        task = context.task
        analysis_type = task.metadata.get("analysis_type", "general")
        
        result = {
            "status": "completed",
            "analysis_type": analysis_type,
            "findings": []
        }
        
        if analysis_type == "code_complexity":
            files = task.metadata.get("files", [])
            # Analyze code complexity (placeholder)
            result["findings"] = [
                {
                    "file": f,
                    "complexity": "low",
                    "metrics": {}
                }
                for f in files
            ]
            
        elif analysis_type == "dependencies":
            # Analyze dependencies
            result["findings"] = {
                "direct": [],
                "transitive": [],
                "conflicts": []
            }
            
        elif analysis_type == "custom":
            analyzer_name = task.metadata.get("analyzer")
            if analyzer_name in self.custom_handlers:
                analysis_result = await self.custom_handlers[analyzer_name](
                    context
                )
                result["findings"] = analysis_result
        
        return result
    
    async def _run_custom(
        self,
        context: TaskExecutionContext
    ) -> Dict[str, Any]:
        """Run a custom task."""
        task = context.task
        handler_name = task.metadata.get("handler")
        
        if not handler_name:
            raise ValidationError("No custom handler specified")
        
        if handler_name not in self.custom_handlers:
            raise ValidationError(
                f"Custom handler not found: {handler_name}"
            )
        
        handler = self.custom_handlers[handler_name]
        
        if asyncio.iscoroutinefunction(handler):
            return await handler(context)
        else:
            return handler(context)
    
    async def _retry_task(
        self,
        context: TaskExecutionContext,
        global_context: Dict[str, Any]
    ) -> TaskResult:
        """Retry a failed task."""
        context.attempts += 1
        logger.info(
            f"Retrying task {context.task.name} "
            f"(attempt {context.attempts}/{self.config.retry_attempts})"
        )
        
        # Wait before retry
        await asyncio.sleep(
            self.config.retry_delay * (2 ** (context.attempts - 1))
        )
        
        # Retry execution
        return await self.run_task(context.task, global_context)
    
    async def _prepare_tools(
        self,
        task: Task
    ) -> List[Dict[str, Any]]:
        """Prepare tools for task execution."""
        # Get required tools
        required_tools = task.metadata.get("tools", [])
        
        # Apply restrictions
        if self.config.tool_restrictions:
            required_tools = [
                t for t in required_tools
                if t not in self.config.tool_restrictions
            ]
        
        # Configure tools
        return await self.tool_manager.configure_tools(required_tools)
    
    def _prepare_prompt(
        self,
        task: Task,
        context: Dict[str, Any]
    ) -> str:
        """Prepare prompt for code generation."""
        prompt_parts = [
            f"Task: {task.name}",
            f"Type: {task.type}",
            f"Description: {task.description}",
            ""
        ]
        
        # Add requirements
        if task.requirements:
            prompt_parts.extend([
                "Requirements:",
                *[f"- {req}" for req in task.requirements]
            ])
        
        # Add context
        if context.previous_outputs:
            prompt_parts.extend([
                "",
                "Available Context:",
                *[f"- {k}: {type(v).__name__}" 
                  for k, v in context.previous_outputs.items()]
            ])
        
        # Add specific instructions
        if task.metadata.get("instructions"):
            prompt_parts.extend([
                "",
                "Instructions:",
                task.metadata["instructions"]
            ])
        
        return "\n".join(prompt_parts)
    
    def _determine_task_type(self, task: Task) -> TaskType:
        """Determine the task type from task metadata."""
        # Check explicit type
        if task.metadata.get("runner_type"):
            try:
                return TaskType(task.metadata["runner_type"])
            except ValueError:
                pass
        
        # Infer from task type
        type_mapping = {
            "code": TaskType.CODE_GENERATION,
            "file": TaskType.FILE_OPERATION,
            "command": TaskType.COMMAND_EXECUTION,
            "api": TaskType.API_CALL,
            "validate": TaskType.VALIDATION,
            "transform": TaskType.TRANSFORMATION,
            "analyze": TaskType.ANALYSIS
        }
        
        for key, task_type in type_mapping.items():
            if key in task.type.lower():
                return task_type
        
        return TaskType.CUSTOM
    
    def _create_task_result(
        self,
        context: TaskExecutionContext,
        outputs: Dict[str, Any],
        status: TaskStatus
    ) -> TaskResult:
        """Create a task result from execution context."""
        end_time = datetime.now()
        duration = (end_time - context.start_time).total_seconds()
        
        return TaskResult(
            task_id=context.task.id,
            status=status,
            start_time=context.start_time,
            end_time=end_time,
            outputs=outputs,
            artifacts=context.outputs.get("artifacts", {}),
            metrics={
                **context.metrics,
                "duration": duration,
                "attempts": context.attempts
            },
            error="; ".join(context.errors) if context.errors else None
        )
    
    async def _run_hooks(
        self,
        hooks: List[Callable],
        context: TaskExecutionContext
    ) -> None:
        """Run a list of hooks."""
        for hook in hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(context)
                else:
                    hook(context)
            except Exception as e:
                logger.error(f"Hook execution error: {e}")