# Claude Code Builder v3.0 - API Reference

## Table of Contents

1. [Core Classes](#core-classes)
2. [Models](#models)
3. [AI System](#ai-system)
4. [Execution System](#execution-system)
5. [Memory System](#memory-system)
6. [MCP Integration](#mcp-integration)
7. [Research Agents](#research-agents)
8. [Validation System](#validation-system)
9. [CLI Interface](#cli-interface)
10. [Utilities](#utilities)

## Core Classes

### ProjectSpec

The main project specification class that represents a project to be built.

```python
from claude_code_builder.models.project import ProjectSpec, ProjectMetadata, Feature, Technology

# Create project metadata
metadata = ProjectMetadata(
    name="My API Project",
    version="1.0.0",
    author="John Doe",
    description="A REST API for task management"
)

# Define features
features = [
    Feature(
        name="User Authentication",
        description="JWT-based authentication system",
        priority=Priority.HIGH,
        requirements=["User registration", "Login/logout", "Token refresh"]
    ),
    Feature(
        name="Task Management",
        description="CRUD operations for tasks",
        priority=Priority.HIGH,
        requirements=["Create tasks", "Update tasks", "Delete tasks", "List tasks"]
    )
]

# Define technologies
technologies = [
    Technology(
        name="Python",
        version="3.9+",
        category=TechnologyCategory.LANGUAGE,
        required=True,
        dependencies=["pip", "venv"]
    ),
    Technology(
        name="FastAPI",
        version="0.100+",
        category=TechnologyCategory.FRAMEWORK,
        required=True,
        dependencies=["uvicorn", "pydantic"]
    )
]

# Create project specification
project_spec = ProjectSpec(
    metadata=metadata,
    description="A comprehensive task management API",
    features=features,
    technologies=technologies,
    requirements={
        "performance": ["Response time < 100ms", "Support 1000 concurrent users"],
        "security": ["HTTPS only", "Rate limiting", "Input validation"]
    }
)

# Validate specification
validation_result = project_spec.validate()
if not validation_result.is_valid:
    print(f"Validation errors: {validation_result.errors}")

# Convert to/from markdown
markdown_content = project_spec.to_markdown()
loaded_spec = ProjectSpec.from_markdown(markdown_content)
```

### ExecutionOrchestrator

Main orchestrator for project execution.

```python
from claude_code_builder.execution import ExecutionOrchestrator, OrchestrationConfig
from claude_code_builder.execution import ExecutionMode

# Configure orchestrator
config = OrchestrationConfig(
    mode=ExecutionMode.ADAPTIVE,
    max_concurrent_phases=3,
    max_concurrent_tasks=10,
    enable_checkpoints=True,
    checkpoint_interval=300,  # 5 minutes
    enable_monitoring=True,
    enable_recovery=True,
    max_retry_attempts=3,
    retry_delay=5.0
)

# Initialize orchestrator with dependencies
orchestrator = ExecutionOrchestrator(
    config=config,
    planner=ai_planner,
    memory_store=memory_store,
    event_bus=event_bus
)

# Set up event handlers
@orchestrator.on("phase.start")
async def handle_phase_start(event):
    print(f"Starting phase: {event.phase_id}")

@orchestrator.on("phase.complete")
async def handle_phase_complete(event):
    print(f"Completed phase: {event.phase_id}")

# Execute project
result = await orchestrator.execute_project(
    project=project_spec,
    context={
        "output_dir": "/path/to/output",
        "api_key": "your-api-key",
        "dry_run": False
    }
)

# Check results
print(f"Status: {result.status}")
print(f"Phases completed: {result.phases_completed}")
print(f"Files created: {result.files_created}")
print(f"Total duration: {result.duration}s")
```

## Models

### Base Models

All models inherit from a hierarchy of base classes:

```python
from claude_code_builder.models.base import (
    SerializableModel,
    TimestampedModel,
    IdentifiedModel,
    VersionedModel
)

# Example custom model
@dataclass
class CustomModel(VersionedModel):
    """Custom model with all base features."""
    name: str
    value: int
    tags: List[str] = field(default_factory=list)
    
    def validate(self) -> bool:
        """Validate model data."""
        return len(self.name) > 0 and self.value >= 0
```

### Phase Models

```python
from claude_code_builder.models.phase import Phase, Task, TaskType, TaskStatus

# Create a phase
phase = Phase(
    id="implementation",
    name="Core Implementation",
    description="Implement main application logic",
    dependencies=["setup", "planning"],
    tasks=[]
)

# Create tasks
task1 = Task(
    id="create-api",
    name="Create API endpoints",
    description="Implement REST API endpoints",
    type=TaskType.CODE_GENERATION,
    estimated_tokens=5000,
    estimated_time=120,  # seconds
    output_files=["src/api/routes.py", "src/api/handlers.py"]
)

task2 = Task(
    id="create-models",
    name="Create data models",
    description="Define database models",
    type=TaskType.CODE_GENERATION,
    dependencies=["create-api"],
    estimated_tokens=3000,
    estimated_time=90,
    output_files=["src/models/user.py", "src/models/task.py"]
)

# Add tasks to phase
phase.add_task(task1)
phase.add_task(task2)

# Execute task
task_result = await execute_task(task1)
task1.status = TaskStatus.COMPLETED
task1.result = task_result
```

### Monitoring Models

```python
from claude_code_builder.models.monitoring import (
    ExecutionMetrics,
    PhaseMetrics,
    PerformanceMetrics,
    HealthStatus
)

# Track execution metrics
metrics = ExecutionMetrics()
metrics.start_phase("phase-1")
metrics.increment_tasks_completed()
metrics.add_file_created("src/main.py")
metrics.add_api_call(tokens=1500, cost=0.03)
phase_metrics = metrics.end_phase("phase-1")

# Monitor performance
perf_metrics = PerformanceMetrics()
perf_metrics.record_latency("api_call", 250.5)  # ms
perf_metrics.record_throughput("files_generated", 5.2)  # per second
perf_metrics.record_resource_usage(memory_mb=512, cpu_percent=45.3)

# Check health status
health = HealthStatus(
    status="healthy",
    api_connected=True,
    memory_available=True,
    disk_space_ok=True,
    error_rate=0.02,
    latency_p99=450.0
)
```

## AI System

### AIPlanner

The core AI planning system.

```python
from claude_code_builder.ai import AIPlanner, AIConfig
from claude_code_builder.ai.prompts import PlanningPromptTemplate

# Configure AI
ai_config = AIConfig(
    model="claude-3-opus-20240229",
    temperature=0.7,
    max_tokens=100000,
    top_p=0.9,
    retry_attempts=3,
    retry_delay=5.0,
    timeout=60.0
)

# Initialize planner
planner = AIPlanner(
    ai_config=ai_config,
    memory_store=memory_store,
    cost_tracker=cost_tracker
)

# Create custom prompt template
custom_template = PlanningPromptTemplate(
    system_prompt="You are an expert software architect...",
    planning_prompt="Analyze the following specification and create a detailed plan...",
    variables=["project_name", "features", "technologies"]
)

# Set custom template
planner.set_prompt_template(custom_template)

# Create build plan
build_plan = await planner.create_plan(project_spec)

# Access plan details
print(f"Total phases: {len(build_plan.phases)}")
print(f"Estimated cost: ${build_plan.cost_estimate.total_cost:.2f}")
print(f"Risk level: {build_plan.risks.overall_risk_level}")

# Get specific analysis
spec_analysis = await planner.analyze_specification(project_spec)
risk_assessment = await planner.assess_risks(project_spec)
dependencies = await planner.resolve_dependencies(build_plan.phases)
```

### Cost Tracking

```python
from claude_code_builder.models.cost import CostTracker, CostEstimate

# Initialize cost tracker
cost_tracker = CostTracker(
    cost_per_1k_tokens={
        "claude-3-opus-20240229": 0.015,
        "claude-3-sonnet-20240229": 0.003,
        "claude-3-haiku-20240307": 0.00025
    }
)

# Track operation
with cost_tracker.track_operation("generate_code"):
    # Perform AI operation
    response = await ai_client.generate(prompt, tokens=5000)

# Get cost breakdown
breakdown = cost_tracker.get_breakdown()
print(f"Total cost: ${breakdown.total_cost:.4f}")
print(f"By operation: {breakdown.by_operation}")
print(f"By model: {breakdown.by_model}")

# Estimate project cost
estimate = cost_tracker.estimate_project_cost(project_spec)
print(f"Estimated cost: ${estimate.total:.2f}")
print(f"Breakdown: {estimate.breakdown}")
```

## Execution System

### Phase Executor

```python
from claude_code_builder.execution import PhaseExecutor, ExecutionContext

# Create execution context
context = ExecutionContext(
    project_spec=project_spec,
    output_directory=Path("/output"),
    api_client=claude_client,
    memory_store=memory_store,
    event_bus=event_bus
)

# Initialize executor
executor = PhaseExecutor(context)

# Execute phase
phase_result = await executor.execute_phase(phase)

# Check results
print(f"Status: {phase_result.status}")
print(f"Tasks completed: {phase_result.tasks_completed}")
print(f"Files created: {phase_result.files_created}")
print(f"Errors: {phase_result.errors}")
```

### Task Runner

```python
from claude_code_builder.execution import TaskRunner, TaskContext

# Create task context
task_context = TaskContext(
    task=task,
    phase=phase,
    project_spec=project_spec,
    previous_results={},
    output_directory=Path("/output")
)

# Initialize runner
runner = TaskRunner(
    api_client=claude_client,
    file_handler=file_handler
)

# Execute task
result = await runner.execute_task(task_context)

# Handle different task types
if task.type == TaskType.CODE_GENERATION:
    print(f"Generated files: {result.files_created}")
elif task.type == TaskType.VALIDATION:
    print(f"Validation passed: {result.validation_passed}")
elif task.type == TaskType.DOCUMENTATION:
    print(f"Docs generated: {result.documentation_files}")
```

### State Manager

```python
from claude_code_builder.execution import StateManager, ExecutionState

# Initialize state manager
state_manager = StateManager(
    checkpoint_dir=Path(".checkpoints"),
    enable_compression=True
)

# Save checkpoint
state = ExecutionState(
    project_id=project_spec.metadata.id,
    current_phase="implementation",
    completed_phases=["setup", "planning"],
    completed_tasks=["task-1", "task-2"],
    context={"files_created": 10}
)

checkpoint_id = await state_manager.save_checkpoint(state)

# Load checkpoint
loaded_state = await state_manager.load_checkpoint(checkpoint_id)

# List checkpoints
checkpoints = await state_manager.list_checkpoints(project_id)
for cp in checkpoints:
    print(f"Checkpoint: {cp.id} at {cp.timestamp}")

# Clean old checkpoints
await state_manager.cleanup_old_checkpoints(max_age_days=7)
```

## Memory System

### MemoryStore

```python
from claude_code_builder.memory import MemoryStore, MemoryEntry, MemoryType

# Initialize memory store
memory_store = MemoryStore(
    db_path="builder_memory.db",
    cache_size=1000,
    ttl_days=7,
    compression_threshold=1024
)

# Store memory
entry = MemoryEntry(
    type=MemoryType.PATTERN,
    content="API endpoint pattern for FastAPI",
    tags=["api", "fastapi", "pattern"],
    metadata={
        "language": "python",
        "framework": "fastapi",
        "usage_count": 0
    },
    priority=0.8
)

await memory_store.store(entry)

# Search memories
from claude_code_builder.memory import SearchFilters

filters = SearchFilters(
    types=[MemoryType.PATTERN, MemoryType.SOLUTION],
    tags=["api"],
    min_priority=0.5,
    max_age_days=30
)

results = await memory_store.search("fastapi endpoint", filters)
for result in results:
    print(f"Found: {result.content[:100]}...")
    print(f"Relevance: {result.relevance_score}")

# Update memory
entry.metadata["usage_count"] += 1
await memory_store.update(entry)

# Get statistics
stats = await memory_store.get_statistics()
print(f"Total entries: {stats.total_entries}")
print(f"Cache hit rate: {stats.cache_hit_rate:.2%}")
print(f"Average query time: {stats.avg_query_time_ms}ms")
```

### Context Accumulator

```python
from claude_code_builder.memory import ContextAccumulator

# Initialize accumulator
accumulator = ContextAccumulator(max_size=50000)  # tokens

# Add context
accumulator.add_context(
    key="project_spec",
    content=project_spec.to_dict(),
    priority=1.0
)

accumulator.add_context(
    key="previous_code",
    content=generated_code,
    priority=0.8
)

# Get accumulated context
context = accumulator.get_context(max_tokens=10000)
print(f"Context size: {context.token_count} tokens")
print(f"Included keys: {context.included_keys}")

# Clear specific context
accumulator.clear_context("previous_code")
```

## MCP Integration

### MCP Discovery

```python
from claude_code_builder.mcp import MCPDiscovery, MCPServer

# Initialize discovery
discovery = MCPDiscovery()

# Discover available servers
servers = await discovery.discover_servers()
for server in servers:
    print(f"Found: {server.name} - {server.description}")
    print(f"  Command: {server.command}")
    print(f"  Capabilities: {server.capabilities}")

# Check if server is installed
is_installed = await discovery.is_server_installed("filesystem")
if not is_installed:
    print("Filesystem server not installed")

# Get server by name
fs_server = await discovery.get_server("filesystem")
if fs_server:
    print(f"Server command: {fs_server.get_command()}")
```

### MCP Installation

```python
from claude_code_builder.mcp import MCPInstaller

# Initialize installer
installer = MCPInstaller()

# Install server
result = await installer.install_server("filesystem")
if result.success:
    print(f"Installed: {result.server_name}")
    print(f"Version: {result.version}")
else:
    print(f"Installation failed: {result.error}")

# Install multiple servers
servers_to_install = ["filesystem", "github", "postgres"]
results = await installer.install_multiple(servers_to_install)
for server, result in results.items():
    print(f"{server}: {'✓' if result.success else '✗'}")

# Update server
update_result = await installer.update_server("filesystem")
```

### MCP Configuration

```python
from claude_code_builder.mcp import MCPConfig, MCPManager

# Create MCP configuration
mcp_config = MCPConfig()
mcp_config.add_server(
    name="filesystem",
    command="npx",
    args=["@modelcontextprotocol/server-filesystem"],
    env={"ALLOWED_DIRECTORIES": "/tmp,/home/user/projects"}
)

mcp_config.add_server(
    name="custom",
    command="python",
    args=["-m", "my_custom_mcp_server"],
    env={"API_KEY": "secret"}
)

# Save configuration
mcp_config.save(".mcp.json")

# Initialize manager
manager = MCPManager(mcp_config)

# Start servers
await manager.start_all()

# Use specific server
async with manager.use_server("filesystem") as server:
    # Server is available here
    response = await server.call_tool("read_file", {"path": "/tmp/test.txt"})
```

## Research Agents

### Research Coordinator

```python
from claude_code_builder.research import ResearchCoordinator, ResearchQuery
from claude_code_builder.research import ResearchMode, ResearchPriority

# Initialize coordinator with agents
coordinator = ResearchCoordinator(
    agents=[
        TechnologyAnalyst(ai_config, memory_store),
        SecuritySpecialist(ai_config, memory_store),
        PerformanceExpert(ai_config, memory_store),
        ArchitectureAdvisor(ai_config, memory_store)
    ]
)

# Create research query
query = ResearchQuery(
    question="What's the best architecture for a real-time chat application?",
    context={
        "project_type": "web",
        "expected_users": 10000,
        "technologies": ["Python", "WebSockets"]
    },
    mode=ResearchMode.PARALLEL,
    priority=ResearchPriority.HIGH,
    required_capabilities=["architecture", "performance", "scalability"]
)

# Perform research
result = await coordinator.research(query)

# Access results
print(f"Confidence: {result.confidence}")
print(f"Synthesis: {result.synthesis}")
for agent_result in result.agent_results:
    print(f"\n{agent_result.agent_name}:")
    print(f"  Finding: {agent_result.finding}")
    print(f"  Recommendations: {agent_result.recommendations}")
```

### Custom Research Agent

```python
from claude_code_builder.research import BaseAgent, AgentCapability

class CustomAgent(BaseAgent):
    """Custom research agent for specific domain."""
    
    name = "CustomDomainExpert"
    specialization = "Custom Domain"
    capabilities = [
        AgentCapability.ARCHITECTURE,
        AgentCapability.BEST_PRACTICES
    ]
    
    async def analyze(self, project_spec: ProjectSpec, context: Dict) -> Any:
        """Perform custom analysis."""
        # Implement domain-specific analysis
        prompt = self._build_analysis_prompt(project_spec, context)
        response = await self._query_ai(prompt)
        return self._parse_analysis(response)
    
    async def recommend(self, analysis_result: Any) -> List[str]:
        """Provide recommendations based on analysis."""
        recommendations = []
        # Generate recommendations based on analysis
        if self._needs_optimization(analysis_result):
            recommendations.append("Consider implementing caching layer")
        return recommendations
    
    async def validate(self, solution: Any) -> ValidationResult:
        """Validate proposed solution."""
        # Implement validation logic
        issues = self._check_for_issues(solution)
        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues
        )
```

## Validation System

### Syntax Validator

```python
from claude_code_builder.validation import SyntaxValidator, ValidationConfig

# Configure validator
config = ValidationConfig(
    strict_mode=True,
    check_imports=True,
    check_types=True,
    max_line_length=100,
    allowed_languages=["python", "javascript", "typescript"]
)

# Initialize validator
validator = SyntaxValidator(config)

# Validate single file
result = await validator.validate_file(Path("src/main.py"))
if not result.is_valid:
    for error in result.errors:
        print(f"Error at {error.line}:{error.column} - {error.message}")

# Validate directory
results = await validator.validate_directory(
    Path("src"),
    exclude_patterns=["*.test.js", "__pycache__"]
)

for file_path, result in results.items():
    if not result.is_valid:
        print(f"\n{file_path}:")
        for error in result.errors:
            print(f"  Line {error.line}: {error.message}")
```

### Security Scanner

```python
from claude_code_builder.validation import SecurityScanner, SecurityConfig

# Configure scanner
security_config = SecurityConfig(
    check_secrets=True,
    check_vulnerabilities=True,
    check_dependencies=True,
    secret_patterns=[
        r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]",
        r"password\s*=\s*['\"][^'\"]+['\"]"
    ]
)

# Initialize scanner
scanner = SecurityScanner(security_config)

# Scan project
scan_result = await scanner.scan_project(Path("output"))

# Check results
if scan_result.has_issues():
    print(f"Found {len(scan_result.vulnerabilities)} vulnerabilities")
    print(f"Found {len(scan_result.secrets)} potential secrets")
    
    for vuln in scan_result.vulnerabilities:
        print(f"\nVulnerability: {vuln.title}")
        print(f"  Severity: {vuln.severity}")
        print(f"  File: {vuln.file_path}")
        print(f"  Line: {vuln.line}")
        print(f"  Fix: {vuln.recommendation}")
```

### Quality Analyzer

```python
from claude_code_builder.validation import QualityAnalyzer, QualityMetrics

# Initialize analyzer
analyzer = QualityAnalyzer()

# Analyze code quality
metrics = await analyzer.analyze_project(Path("output"))

# Display metrics
print(f"Code Quality Score: {metrics.overall_score}/100")
print(f"\nBreakdown:")
print(f"  Maintainability: {metrics.maintainability_score}")
print(f"  Complexity: {metrics.complexity_score}")
print(f"  Documentation: {metrics.documentation_score}")
print(f"  Test Coverage: {metrics.test_coverage:.1%}")

# Get specific recommendations
recommendations = analyzer.get_recommendations(metrics)
for rec in recommendations:
    print(f"\n{rec.category}: {rec.message}")
    print(f"  Impact: {rec.impact}")
    print(f"  Effort: {rec.effort}")
```

## CLI Interface

### CLI Class

```python
from claude_code_builder.cli import CLI, CLIConfig

# Configure CLI
cli_config = CLIConfig(
    colored_output=True,
    show_progress=True,
    log_level="INFO",
    config_file=".claude-code-builder.yaml"
)

# Initialize CLI
cli = CLI(cli_config)

# Run CLI
result = cli.run(["build", "project.md", "--output", "my-project"])

# Programmatic usage
async def custom_command():
    """Custom CLI command."""
    # Parse specification
    spec = await cli.parse_specification("project.md")
    
    # Validate
    validation = await cli.validate_specification(spec)
    if not validation.is_valid:
        cli.display_errors(validation.errors)
        return
    
    # Build
    result = await cli.build_project(spec, output_dir="output")
    cli.display_result(result)
```

### Command Handlers

```python
from claude_code_builder.cli.commands import CommandHandler
import argparse

class CustomCommandHandler(CommandHandler):
    """Custom command handler."""
    
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add command arguments."""
        parser.add_argument("spec", help="Project specification file")
        parser.add_argument("--custom", help="Custom option")
    
    async def execute(self, args: argparse.Namespace) -> int:
        """Execute command."""
        # Load specification
        spec = await self.load_specification(args.spec)
        
        # Custom logic
        if args.custom:
            await self.process_custom_option(args.custom)
        
        # Display progress
        with self.progress_bar(total=100) as progress:
            for i in range(100):
                await asyncio.sleep(0.1)
                progress.update(1)
        
        # Display result
        self.display_success("Command completed successfully")
        return 0

# Register handler
cli.register_command("custom", CustomCommandHandler())
```

## Utilities

### File Handler

```python
from claude_code_builder.utils import FileHandler, FileOperation

# Initialize handler
file_handler = FileHandler()

# Write file with backup
await file_handler.write_file(
    path=Path("src/main.py"),
    content=code_content,
    create_backup=True,
    encoding="utf-8"
)

# Read file safely
content = await file_handler.read_file(
    path=Path("src/main.py"),
    encoding="utf-8",
    default=""
)

# Batch operations
operations = [
    FileOperation(
        type="write",
        path=Path("src/api.py"),
        content=api_code
    ),
    FileOperation(
        type="write",
        path=Path("src/models.py"),
        content=model_code
    ),
    FileOperation(
        type="mkdir",
        path=Path("tests")
    )
]

results = await file_handler.batch_operations(operations)
```

### Logger Setup

```python
from claude_code_builder.utils import setup_logger, LogConfig

# Configure logging
log_config = LogConfig(
    level="DEBUG",
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    file_path="builder.log",
    max_file_size="10MB",
    backup_count=5,
    console_output=True,
    colored_console=True
)

# Setup logger
logger = setup_logger("claude_code_builder", log_config)

# Use logger
logger.info("Starting build process")
logger.debug("Debug information", extra={"context": {"phase": "planning"}})
logger.error("Error occurred", exc_info=True)

# Structured logging
from claude_code_builder.utils import StructuredLogger

struct_logger = StructuredLogger("builder")
struct_logger.log(
    level="info",
    message="Phase completed",
    phase_id="implementation",
    duration=45.3,
    tasks_completed=10
)
```

### Performance Utilities

```python
from claude_code_builder.utils import Timer, measure_performance

# Using Timer context manager
async with Timer() as timer:
    await expensive_operation()
print(f"Operation took: {timer.elapsed:.2f}s")

# Using decorator
@measure_performance
async def process_data(data):
    """Process data with performance measurement."""
    await asyncio.sleep(1)
    return len(data)

# Manual timing
from claude_code_builder.utils import PerformanceTracker

tracker = PerformanceTracker()
tracker.start("data_processing")
# ... do work ...
tracker.end("data_processing")

# Get statistics
stats = tracker.get_statistics("data_processing")
print(f"Average time: {stats.average:.2f}s")
print(f"Min/Max: {stats.min:.2f}s / {stats.max:.2f}s")
print(f"Total calls: {stats.count}")
```

## Error Handling

### Custom Exceptions

```python
from claude_code_builder.exceptions import (
    BuildError,
    ValidationError,
    ExecutionError,
    ConfigurationError,
    DependencyError
)

# Handling build errors
try:
    result = await builder.build(project_spec)
except ValidationError as e:
    print(f"Validation failed: {e}")
    for error in e.errors:
        print(f"  - {error}")
except ExecutionError as e:
    print(f"Execution failed: {e}")
    print(f"Phase: {e.phase_id}")
    print(f"Task: {e.task_id}")
except BuildError as e:
    print(f"Build failed: {e}")
    if e.recovery_possible:
        print("Recovery possible - run with --resume")
```

### Error Recovery

```python
from claude_code_builder.exceptions import RecoverableError, RecoveryStrategy

class CustomRecoveryStrategy(RecoveryStrategy):
    """Custom recovery strategy."""
    
    async def can_recover(self, error: Exception) -> bool:
        """Check if recovery is possible."""
        return isinstance(error, RecoverableError)
    
    async def recover(self, error: Exception, context: Dict) -> Any:
        """Attempt recovery."""
        if error.error_code == "API_RATE_LIMIT":
            await asyncio.sleep(60)  # Wait for rate limit
            return True
        elif error.error_code == "NETWORK_ERROR":
            return await self.retry_with_backoff(context)
        return False

# Register recovery strategy
orchestrator.register_recovery_strategy(CustomRecoveryStrategy())
```

## Complete Example

Here's a complete example that ties everything together:

```python
import asyncio
from pathlib import Path
from claude_code_builder import (
    ProjectSpec,
    ExecutionOrchestrator,
    AIPlanner,
    MemoryStore,
    MCPManager,
    ResearchCoordinator,
    CLI
)

async def build_project():
    """Complete project build example."""
    
    # 1. Load and parse specification
    with open("my-project.md", "r") as f:
        markdown_content = f.read()
    
    project_spec = ProjectSpec.from_markdown(markdown_content)
    
    # 2. Validate specification
    validation = project_spec.validate()
    if not validation.is_valid:
        print(f"Validation errors: {validation.errors}")
        return
    
    # 3. Initialize components
    memory_store = MemoryStore("builder_memory.db")
    cost_tracker = CostTracker()
    
    ai_config = AIConfig(
        model="claude-3-opus-20240229",
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )
    
    planner = AIPlanner(ai_config, memory_store, cost_tracker)
    
    # 4. Setup research agents
    research_coordinator = ResearchCoordinator([
        TechnologyAnalyst(ai_config, memory_store),
        SecuritySpecialist(ai_config, memory_store),
        ArchitectureAdvisor(ai_config, memory_store)
    ])
    
    # 5. Configure orchestrator
    config = OrchestrationConfig(
        mode=ExecutionMode.ADAPTIVE,
        enable_monitoring=True
    )
    
    orchestrator = ExecutionOrchestrator(
        config=config,
        planner=planner,
        memory_store=memory_store
    )
    
    # 6. Setup MCP servers
    mcp_manager = MCPManager()
    await mcp_manager.start_all()
    
    # 7. Execute project
    try:
        result = await orchestrator.execute_project(
            project=project_spec,
            context={
                "output_dir": Path("output"),
                "research_coordinator": research_coordinator,
                "mcp_manager": mcp_manager
            }
        )
        
        # 8. Display results
        print(f"\nBuild completed successfully!")
        print(f"Status: {result.status}")
        print(f"Duration: {result.duration:.1f}s")
        print(f"Files created: {result.files_created}")
        print(f"Total cost: ${result.total_cost:.2f}")
        
    except Exception as e:
        print(f"Build failed: {e}")
    finally:
        # 9. Cleanup
        await mcp_manager.stop_all()
        await memory_store.close()

# Run the build
if __name__ == "__main__":
    asyncio.run(build_project())
```

This comprehensive API reference covers all major components and their usage patterns in Claude Code Builder v3.0.