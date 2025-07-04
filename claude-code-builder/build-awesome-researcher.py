#!/usr/bin/env python3
"""
Build script for Awesome Researcher using Claude Code Builder v3.0
This script demonstrates how to use the Claude Code Builder to build a complex project.
"""

import os
import sys
import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime

# Add the claude_code_builder to Python path
sys.path.insert(0, str(Path(__file__).parent))

from claude_code_builder.models.project import ProjectSpec
from claude_code_builder.execution.orchestrator import ExecutionOrchestrator, OrchestrationConfig
from claude_code_builder.config.settings import Settings
from claude_code_builder.logging.logger import setup_logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BuildMonitor:
    """Monitor build progress with detailed logging."""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.phases_completed = 0
        self.total_phases = 0
        self.current_phase = None
        self.files_created = []
        
    def on_phase_start(self, phase_name: str, phase_data: dict):
        """Called when a phase starts."""
        self.current_phase = phase_name
        logger.info(f"{'='*80}")
        logger.info(f"Starting Phase: {phase_name}")
        logger.info(f"Description: {phase_data.get('description', 'N/A')}")
        logger.info(f"Tasks: {len(phase_data.get('tasks', []))}")
        
    def on_phase_complete(self, phase_name: str, result: dict):
        """Called when a phase completes."""
        self.phases_completed += 1
        duration = result.get('duration', 0)
        logger.info(f"Phase '{phase_name}' completed in {duration:.2f}s")
        
        # Log any files created
        if 'files_created' in result:
            self.files_created.extend(result['files_created'])
            logger.info(f"Files created in this phase: {len(result['files_created'])}")
            
    def on_phase_error(self, phase_name: str, error: str):
        """Called when a phase fails."""
        logger.error(f"Phase '{phase_name}' failed: {error}")
        
    def on_task_complete(self, task_name: str, result: dict):
        """Called when a task completes."""
        logger.debug(f"  ✓ {task_name}")
        
    def get_summary(self) -> dict:
        """Get build summary."""
        total_time = (datetime.now() - self.start_time).total_seconds()
        return {
            'duration': total_time,
            'phases_completed': self.phases_completed,
            'total_phases': self.total_phases,
            'files_created': len(self.files_created),
            'success': self.phases_completed == self.total_phases
        }


async def build_awesome_researcher():
    """Build the Awesome Researcher project."""
    
    # Check for API key
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable not set!")
        logger.error("Please set it with: export ANTHROPIC_API_KEY='your-key-here'")
        return False
        
    # Load the specification
    spec_path = Path(__file__).parent / "awesome-researcher-complete-spec.md"
    if not spec_path.exists():
        logger.error(f"Specification file not found: {spec_path}")
        return False
        
    logger.info(f"Loading specification from: {spec_path}")
    spec_content = spec_path.read_text()
    
    # Parse the specification
    try:
        project_spec = ProjectSpec.from_markdown(spec_content)
        logger.info(f"Parsed project: {project_spec.name}")
        logger.info(f"Description: {project_spec.description[:100]}...")
    except Exception as e:
        logger.error(f"Failed to parse specification: {e}")
        return False
    
    # Setup output directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path(__file__).parent / f"awesome-researcher-build-{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")
    
    # Initialize settings
    settings = Settings()
    settings.api_key = api_key
    settings.output_dir = str(output_dir)
    
    # Create orchestration config
    config = OrchestrationConfig(
        max_concurrent_phases=1,  # Execute phases sequentially
        max_concurrent_tasks=5,   # But allow parallel tasks within phases
        checkpoint_interval=300,  # Every 5 minutes
        enable_recovery=True,
        enable_monitoring=True
    )
    
    # Initialize the orchestrator
    orchestrator = ExecutionOrchestrator(config=config)
    
    # Create monitor
    monitor = BuildMonitor()
    
    # Register event handlers
    orchestrator.register_event_handler('phase_start', monitor.on_phase_start)
    orchestrator.register_event_handler('phase_complete', monitor.on_phase_complete)
    orchestrator.register_event_handler('phase_error', monitor.on_phase_error)
    orchestrator.register_event_handler('task_complete', monitor.on_task_complete)
    
    # Build context
    context = {
        'output_dir': str(output_dir),
        'api_key': api_key,
        'settings': settings.to_dict(),
        'monitoring': {
            'log_level': 'INFO',
            'progress_tracking': True,
            'cost_tracking': True
        }
    }
    
    logger.info("Starting build process...")
    logger.info(f"Using Claude Code Builder v3.0")
    
    try:
        # Execute the project build
        result = await orchestrator.execute_project(
            project=project_spec,
            context=context
        )
        
        # Get summary
        summary = monitor.get_summary()
        
        # Log results
        logger.info(f"{'='*80}")
        logger.info("Build Summary:")
        logger.info(f"  Status: {'SUCCESS' if summary['success'] else 'FAILED'}")
        logger.info(f"  Duration: {summary['duration']:.2f}s")
        logger.info(f"  Phases: {summary['phases_completed']}/{summary['total_phases']}")
        logger.info(f"  Files Created: {summary['files_created']}")
        logger.info(f"  Output: {output_dir}")
        
        if 'cost' in result:
            logger.info(f"  Total Cost: ${result['cost']:.4f}")
            
        # Save build report
        report_path = output_dir / "build_report.json"
        with open(report_path, 'w') as f:
            json.dump({
                'project': project_spec.name,
                'timestamp': timestamp,
                'summary': summary,
                'result': result if isinstance(result, dict) else {'status': str(result)}
            }, f, indent=2)
            
        logger.info(f"Build report saved to: {report_path}")
        
        return summary['success']
        
    except KeyboardInterrupt:
        logger.warning("Build interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Build failed with error: {e}", exc_info=True)
        return False


def main():
    """Main entry point."""
    logger.info("Awesome Researcher Build Script")
    logger.info("Using Claude Code Builder v3.0")
    
    # Run the async build
    success = asyncio.run(build_awesome_researcher())
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()