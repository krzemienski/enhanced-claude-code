"""Configuration settings for Claude Code Builder."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import os
from datetime import timedelta


@dataclass
class AIConfig:
    """Configuration for AI planning and execution."""
    
    model: str = "claude-3-opus-20240229"
    temperature: float = 0.7
    max_tokens: int = 4096
    planning_prompt_template: Optional[str] = None
    phase_optimization: bool = True
    dependency_resolution: bool = True
    risk_assessment: bool = True
    adaptive_planning: bool = True
    context_window_size: int = 200000
    
    def __post_init__(self):
        """Validate AI configuration."""
        if not 0 <= self.temperature <= 1:
            raise ValueError("Temperature must be between 0 and 1")
        if self.max_tokens < 1:
            raise ValueError("Max tokens must be positive")


@dataclass
class ExecutionConfig:
    """Configuration for project execution."""
    
    max_retries: int = 3
    retry_delay: timedelta = timedelta(seconds=5)
    checkpoint_interval: timedelta = timedelta(minutes=5)
    parallel_tasks: bool = True
    max_parallel_workers: int = 4
    timeout_per_phase: timedelta = timedelta(minutes=10)
    error_recovery: bool = True
    state_persistence: bool = True
    state_file: str = ".claude-state.json"
    verbose: bool = True
    debug: bool = False
    
    def __post_init__(self):
        """Validate execution configuration."""
        if self.max_retries < 0:
            raise ValueError("Max retries must be non-negative")
        if self.max_parallel_workers < 1:
            raise ValueError("Max parallel workers must be at least 1")


@dataclass
class TestingConfig:
    """Configuration for functional testing."""
    
    run_tests: bool = True
    test_timeout: timedelta = timedelta(minutes=30)
    performance_benchmarks: bool = True
    security_scan: bool = True
    code_coverage_target: float = 0.8
    test_stages: List[str] = field(default_factory=lambda: [
        "installation",
        "cli",
        "functional",
        "performance",
        "recovery"
    ])
    generate_report: bool = True
    report_format: str = "json"
    fail_fast: bool = False
    
    def __post_init__(self):
        """Validate testing configuration."""
        if not 0 <= self.code_coverage_target <= 1:
            raise ValueError("Code coverage target must be between 0 and 1")
        if self.report_format not in ["json", "html", "markdown"]:
            raise ValueError(f"Invalid report format: {self.report_format}")


@dataclass
class MCPConfig:
    """Configuration for Model Context Protocol."""
    
    auto_discover: bool = True
    complexity_threshold: int = 5
    verify_installation: bool = True
    recommend_servers: bool = True
    server_timeout: timedelta = timedelta(seconds=30)
    max_servers: int = 10
    cache_discoveries: bool = True
    cache_duration: timedelta = timedelta(hours=24)


@dataclass
class ResearchConfig:
    """Configuration for research agents."""
    
    enabled: bool = True
    agents: List[str] = field(default_factory=lambda: [
        "TechnologyAnalyst",
        "SecuritySpecialist",
        "PerformanceEngineer",
        "SolutionsArchitect",
        "BestPracticesAdvisor",
        "QualityAssuranceExpert",
        "DevOpsSpecialist"
    ])
    max_research_time: timedelta = timedelta(minutes=5)
    cache_results: bool = True
    parallel_research: bool = True
    synthesis_strategy: str = "weighted_consensus"
    min_confidence_score: float = 0.7


@dataclass
class MonitoringConfig:
    """Configuration for real-time monitoring."""
    
    enabled: bool = True
    log_streaming: bool = True
    progress_tracking: bool = True
    cost_monitoring: bool = True
    performance_metrics: bool = True
    error_tracking: bool = True
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "error_rate": 0.1,
        "cost_overrun": 1.5,
        "time_overrun": 2.0,
        "memory_usage": 0.8
    })
    update_interval: timedelta = timedelta(seconds=1)
    dashboard: bool = True


@dataclass
class BuilderConfig:
    """Main configuration for Claude Code Builder."""
    
    ai: AIConfig = field(default_factory=AIConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    testing: TestingConfig = field(default_factory=TestingConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    research: ResearchConfig = field(default_factory=ResearchConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    # General settings
    output_dir: Path = Path("./output")
    temp_dir: Path = Path("/tmp/claude-code-builder")
    log_level: str = "INFO"
    dry_run: bool = False
    force: bool = False
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "BuilderConfig":
        """Create BuilderConfig from dictionary."""
        ai_config = AIConfig(**config_dict.get("ai", {}))
        execution_config = ExecutionConfig(**config_dict.get("execution", {}))
        testing_config = TestingConfig(**config_dict.get("testing", {}))
        mcp_config = MCPConfig(**config_dict.get("mcp", {}))
        research_config = ResearchConfig(**config_dict.get("research", {}))
        monitoring_config = MonitoringConfig(**config_dict.get("monitoring", {}))
        
        return cls(
            ai=ai_config,
            execution=execution_config,
            testing=testing_config,
            mcp=mcp_config,
            research=research_config,
            monitoring=monitoring_config,
            output_dir=Path(config_dict.get("output_dir", "./output")),
            temp_dir=Path(config_dict.get("temp_dir", "/tmp/claude-code-builder")),
            log_level=config_dict.get("log_level", "INFO"),
            dry_run=config_dict.get("dry_run", False),
            force=config_dict.get("force", False)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert BuilderConfig to dictionary."""
        return {
            "ai": self.ai.__dict__,
            "execution": self.execution.__dict__,
            "testing": self.testing.__dict__,
            "mcp": self.mcp.__dict__,
            "research": self.research.__dict__,
            "monitoring": self.monitoring.__dict__,
            "output_dir": str(self.output_dir),
            "temp_dir": str(self.temp_dir),
            "log_level": self.log_level,
            "dry_run": self.dry_run,
            "force": self.force
        }
    
    def validate(self) -> None:
        """Validate the complete configuration."""
        # Validate output directory
        if not self.force and self.output_dir.exists() and any(self.output_dir.iterdir()):
            raise ValueError(f"Output directory {self.output_dir} is not empty. Use --force to overwrite.")
        
        # Validate log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_levels:
            raise ValueError(f"Invalid log level: {self.log_level}. Must be one of {valid_levels}")
        
        # Ensure temp directory is writable
        try:
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            test_file = self.temp_dir / "test_write"
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            raise ValueError(f"Cannot write to temp directory {self.temp_dir}: {e}")


# Create a default configuration instance
DEFAULT_CONFIG = BuilderConfig()


class Settings(BuilderConfig):
    """Settings class for backward compatibility."""
    
    def __init__(self, **kwargs):
        """Initialize settings.
        
        Args:
            **kwargs: Configuration values
        """
        super().__init__(**kwargs)
        
        # Additional dynamic attributes
        self._dynamic_attrs = {}
        
        # Common attributes for compatibility
        self.api_key = kwargs.get('api_key', os.environ.get('ANTHROPIC_API_KEY', ''))
        self.model = self.ai.model
        self.max_tokens = self.ai.max_tokens
    
    def update(self, config: Dict[str, Any]) -> None:
        """Update settings from dictionary.
        
        Args:
            config: Configuration dictionary
        """
        for key, value in config.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self._dynamic_attrs[key] = value
    
    def __getattr__(self, name: str) -> Any:
        """Get dynamic attribute.
        
        Args:
            name: Attribute name
            
        Returns:
            Attribute value
        """
        if name in self._dynamic_attrs:
            return self._dynamic_attrs[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def load_from_file(self, file_path: Path) -> None:
        """Load settings from file.
        
        Args:
            file_path: Path to settings file
        """
        import json
        
        if file_path.suffix == '.json':
            with open(file_path, 'r') as f:
                config = json.load(f)
        elif file_path.suffix in ['.yaml', '.yml']:
            import yaml
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported config file format: {file_path.suffix}")
        
        self.update(config)
    
    def save_to_file(self, file_path: Path) -> None:
        """Save settings to file.
        
        Args:
            file_path: Path to save settings
        """
        import json
        
        config = self.to_dict()
        config['api_key'] = self.api_key
        
        if file_path.suffix == '.json':
            with open(file_path, 'w') as f:
                json.dump(config, f, indent=2, default=str)
        elif file_path.suffix in ['.yaml', '.yml']:
            import yaml
            with open(file_path, 'w') as f:
                yaml.safe_dump(config, f, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported config file format: {file_path.suffix}")