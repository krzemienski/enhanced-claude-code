"""Checkpoint management for execution state persistence."""

import logging
import json
import pickle
import gzip
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
import hashlib
import shutil

from ..models.project import Project, BuildPhase, BuildTask
from ..models.context import ExecutionContext, PhaseResult, TaskResult
from ..models.errors import CheckpointError

logger = logging.getLogger(__name__)


@dataclass
class CheckpointMetadata:
    """Metadata for a checkpoint."""
    id: str
    project_id: str
    execution_id: str
    timestamp: datetime
    phase_id: Optional[str] = None
    task_id: Optional[str] = None
    description: str = ""
    size_bytes: int = 0
    compression_ratio: float = 0.0
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)


@dataclass
class CheckpointData:
    """Data stored in a checkpoint."""
    metadata: CheckpointMetadata
    project_state: Dict[str, Any]
    execution_state: Dict[str, Any]
    phase_states: Dict[str, Dict[str, Any]]
    task_states: Dict[str, Dict[str, Any]]
    artifacts: Dict[str, Any]
    context: Dict[str, Any]
    custom_data: Dict[str, Any] = field(default_factory=dict)


class CheckpointManager:
    """Manages checkpoint creation, storage, and restoration."""
    
    def __init__(self, checkpoint_dir: Optional[Path] = None):
        """Initialize the checkpoint manager."""
        self.checkpoint_dir = checkpoint_dir or Path.home() / ".claude_code_builder" / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Checkpoint index
        self.index_file = self.checkpoint_dir / "checkpoint_index.json"
        self.index = self._load_index()
        
        # Checkpoint cache
        self.cache: Dict[str, CheckpointData] = {}
        self.max_cache_size = 10
        
        # Retention policy
        self.max_checkpoints_per_project = 50
        self.retention_days = 30
        
        logger.info(f"Checkpoint Manager initialized at {self.checkpoint_dir}")
    
    def create_checkpoint(
        self,
        project: Project,
        execution_id: str,
        execution_state: Dict[str, Any],
        phase_results: Optional[Dict[str, PhaseResult]] = None,
        task_results: Optional[Dict[str, TaskResult]] = None,
        context: Optional[ExecutionContext] = None,
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> CheckpointMetadata:
        """Create a new checkpoint."""
        checkpoint_id = self._generate_checkpoint_id(project.config.id, execution_id)
        
        # Prepare checkpoint data
        checkpoint_data = CheckpointData(
            metadata=CheckpointMetadata(
                id=checkpoint_id,
                project_id=project.config.id,
                execution_id=execution_id,
                timestamp=datetime.now(),
                description=description,
                tags=tags or []
            ),
            project_state=self._serialize_project(project),
            execution_state=execution_state,
            phase_states=self._serialize_phase_results(phase_results or {}),
            task_states=self._serialize_task_results(task_results or {}),
            artifacts=self._collect_artifacts(project, phase_results, task_results),
            context=context.to_dict() if context else {}
        )
        
        # Save checkpoint
        checkpoint_path = self._save_checkpoint(checkpoint_data)
        
        # Update metadata with file info
        checkpoint_data.metadata.size_bytes = checkpoint_path.stat().st_size
        
        # Update index
        self._update_index(checkpoint_data.metadata)
        
        # Clean up old checkpoints
        self._cleanup_old_checkpoints(project.config.id)
        
        logger.info(f"Created checkpoint: {checkpoint_id}")
        
        return checkpoint_data.metadata
    
    def restore_checkpoint(
        self,
        checkpoint_id: str
    ) -> CheckpointData:
        """Restore a checkpoint."""
        # Check cache
        if checkpoint_id in self.cache:
            logger.info(f"Restored checkpoint from cache: {checkpoint_id}")
            return self.cache[checkpoint_id]
        
        # Load from disk
        checkpoint_path = self._get_checkpoint_path(checkpoint_id)
        
        if not checkpoint_path.exists():
            raise CheckpointError(f"Checkpoint not found: {checkpoint_id}")
        
        checkpoint_data = self._load_checkpoint(checkpoint_path)
        
        # Update cache
        self._update_cache(checkpoint_id, checkpoint_data)
        
        logger.info(f"Restored checkpoint: {checkpoint_id}")
        
        return checkpoint_data
    
    def list_checkpoints(
        self,
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[CheckpointMetadata]:
        """List available checkpoints."""
        checkpoints = list(self.index.values())
        
        # Filter by project
        if project_id:
            checkpoints = [
                cp for cp in checkpoints
                if cp["project_id"] == project_id
            ]
        
        # Filter by execution
        if execution_id:
            checkpoints = [
                cp for cp in checkpoints
                if cp["execution_id"] == execution_id
            ]
        
        # Filter by tags
        if tags:
            tag_set = set(tags)
            checkpoints = [
                cp for cp in checkpoints
                if tag_set.intersection(set(cp.get("tags", [])))
            ]
        
        # Convert to metadata objects
        return [
            self._dict_to_metadata(cp) for cp in checkpoints
        ]
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint."""
        checkpoint_path = self._get_checkpoint_path(checkpoint_id)
        
        if checkpoint_path.exists():
            checkpoint_path.unlink()
            
            # Remove from index
            if checkpoint_id in self.index:
                del self.index[checkpoint_id]
                self._save_index()
            
            # Remove from cache
            if checkpoint_id in self.cache:
                del self.cache[checkpoint_id]
            
            logger.info(f"Deleted checkpoint: {checkpoint_id}")
            return True
        
        return False
    
    def create_phase_checkpoint(
        self,
        project: Project,
        execution_id: str,
        phase: BuildPhase,
        phase_result: PhaseResult,
        context: ExecutionContext
    ) -> CheckpointMetadata:
        """Create a checkpoint for a completed phase."""
        description = f"Phase completed: {phase.name}"
        tags = ["phase_checkpoint", f"phase_{phase.id}"]
        
        # Include phase-specific state
        execution_state = {
            "current_phase": phase.id,
            "completed_phases": [phase.id],  # Would be accumulated in real implementation
            "phase_result": phase_result.to_dict() if hasattr(phase_result, 'to_dict') else {}
        }
        
        metadata = self.create_checkpoint(
            project=project,
            execution_id=execution_id,
            execution_state=execution_state,
            phase_results={phase.id: phase_result},
            context=context,
            description=description,
            tags=tags
        )
        
        metadata.phase_id = phase.id
        
        return metadata
    
    def create_task_checkpoint(
        self,
        project: Project,
        execution_id: str,
        phase: BuildPhase,
        task: BuildTask,
        task_result: TaskResult,
        context: ExecutionContext
    ) -> CheckpointMetadata:
        """Create a checkpoint for a completed task."""
        description = f"Task completed: {task.name}"
        tags = ["task_checkpoint", f"phase_{phase.id}", f"task_{task.id}"]
        
        # Include task-specific state
        execution_state = {
            "current_phase": phase.id,
            "current_task": task.id,
            "task_result": task_result.to_dict() if hasattr(task_result, 'to_dict') else {}
        }
        
        metadata = self.create_checkpoint(
            project=project,
            execution_id=execution_id,
            execution_state=execution_state,
            task_results={task.id: task_result},
            context=context,
            description=description,
            tags=tags
        )
        
        metadata.phase_id = phase.id
        metadata.task_id = task.id
        
        return metadata
    
    def get_latest_checkpoint(
        self,
        project_id: str,
        execution_id: Optional[str] = None
    ) -> Optional[CheckpointMetadata]:
        """Get the latest checkpoint for a project."""
        checkpoints = self.list_checkpoints(
            project_id=project_id,
            execution_id=execution_id
        )
        
        if not checkpoints:
            return None
        
        # Sort by timestamp
        checkpoints.sort(key=lambda cp: cp.timestamp, reverse=True)
        
        return checkpoints[0]
    
    def export_checkpoint(
        self,
        checkpoint_id: str,
        export_path: Path
    ) -> None:
        """Export a checkpoint to a file."""
        checkpoint_data = self.restore_checkpoint(checkpoint_id)
        
        # Save to export path
        export_path.parent.mkdir(parents=True, exist_ok=True)
        
        with gzip.open(export_path, 'wb') as f:
            pickle.dump(checkpoint_data, f)
        
        logger.info(f"Exported checkpoint to: {export_path}")
    
    def import_checkpoint(
        self,
        import_path: Path
    ) -> CheckpointMetadata:
        """Import a checkpoint from a file."""
        if not import_path.exists():
            raise CheckpointError(f"Import file not found: {import_path}")
        
        # Load checkpoint data
        with gzip.open(import_path, 'rb') as f:
            checkpoint_data = pickle.load(f)
        
        # Save to checkpoint directory
        checkpoint_path = self._save_checkpoint(checkpoint_data)
        
        # Update index
        self._update_index(checkpoint_data.metadata)
        
        logger.info(f"Imported checkpoint: {checkpoint_data.metadata.id}")
        
        return checkpoint_data.metadata
    
    def _generate_checkpoint_id(
        self,
        project_id: str,
        execution_id: str
    ) -> str:
        """Generate a unique checkpoint ID."""
        timestamp = datetime.now().isoformat()
        content = f"{project_id}:{execution_id}:{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _get_checkpoint_path(self, checkpoint_id: str) -> Path:
        """Get the file path for a checkpoint."""
        return self.checkpoint_dir / f"{checkpoint_id}.checkpoint.gz"
    
    def _save_checkpoint(self, checkpoint_data: CheckpointData) -> Path:
        """Save checkpoint data to disk."""
        checkpoint_path = self._get_checkpoint_path(checkpoint_data.metadata.id)
        
        # Serialize and compress
        with gzip.open(checkpoint_path, 'wb') as f:
            pickle.dump(checkpoint_data, f)
        
        # Calculate compression ratio
        uncompressed_size = len(pickle.dumps(checkpoint_data))
        compressed_size = checkpoint_path.stat().st_size
        checkpoint_data.metadata.compression_ratio = (
            1 - (compressed_size / uncompressed_size)
        )
        
        return checkpoint_path
    
    def _load_checkpoint(self, checkpoint_path: Path) -> CheckpointData:
        """Load checkpoint data from disk."""
        with gzip.open(checkpoint_path, 'rb') as f:
            return pickle.load(f)
    
    def _serialize_project(self, project: Project) -> Dict[str, Any]:
        """Serialize project state."""
        return {
            "config": project.config.to_dict() if hasattr(project.config, 'to_dict') else {},
            "phases": [
                phase.to_dict() if hasattr(phase, 'to_dict') else {}
                for phase in project.phases
            ],
            "status": project.status.value if hasattr(project.status, 'value') else str(project.status),
            "metadata": project.metadata
        }
    
    def _serialize_phase_results(
        self,
        phase_results: Dict[str, PhaseResult]
    ) -> Dict[str, Dict[str, Any]]:
        """Serialize phase results."""
        return {
            phase_id: result.to_dict() if hasattr(result, 'to_dict') else {}
            for phase_id, result in phase_results.items()
        }
    
    def _serialize_task_results(
        self,
        task_results: Dict[str, TaskResult]
    ) -> Dict[str, Dict[str, Any]]:
        """Serialize task results."""
        return {
            task_id: result.to_dict() if hasattr(result, 'to_dict') else {}
            for task_id, result in task_results.items()
        }
    
    def _collect_artifacts(
        self,
        project: Project,
        phase_results: Dict[str, PhaseResult],
        task_results: Dict[str, TaskResult]
    ) -> Dict[str, Any]:
        """Collect artifacts from results."""
        artifacts = {}
        
        # Project artifacts
        artifacts["project"] = project.metadata.get("artifacts", {})
        
        # Phase artifacts
        artifacts["phases"] = {}
        for phase_id, result in phase_results.items():
            if hasattr(result, 'artifacts'):
                artifacts["phases"][phase_id] = result.artifacts
        
        # Task artifacts
        artifacts["tasks"] = {}
        for task_id, result in task_results.items():
            if hasattr(result, 'artifacts'):
                artifacts["tasks"][task_id] = result.artifacts
        
        return artifacts
    
    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """Load checkpoint index."""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_index(self) -> None:
        """Save checkpoint index."""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2, default=str)
    
    def _update_index(self, metadata: CheckpointMetadata) -> None:
        """Update checkpoint index."""
        self.index[metadata.id] = asdict(metadata)
        self._save_index()
    
    def _update_cache(
        self,
        checkpoint_id: str,
        checkpoint_data: CheckpointData
    ) -> None:
        """Update checkpoint cache."""
        # Add to cache
        self.cache[checkpoint_id] = checkpoint_data
        
        # Evict oldest if cache is full
        if len(self.cache) > self.max_cache_size:
            # Get oldest checkpoint
            oldest_id = min(
                self.cache.keys(),
                key=lambda cid: self.cache[cid].metadata.timestamp
            )
            del self.cache[oldest_id]
    
    def _cleanup_old_checkpoints(self, project_id: str) -> None:
        """Clean up old checkpoints for a project."""
        checkpoints = self.list_checkpoints(project_id=project_id)
        
        # Sort by timestamp
        checkpoints.sort(key=lambda cp: cp.timestamp, reverse=True)
        
        # Remove old checkpoints
        if len(checkpoints) > self.max_checkpoints_per_project:
            for checkpoint in checkpoints[self.max_checkpoints_per_project:]:
                self.delete_checkpoint(checkpoint.id)
        
        # Remove expired checkpoints
        cutoff_date = datetime.now().timestamp() - (self.retention_days * 86400)
        for checkpoint in checkpoints:
            if checkpoint.timestamp.timestamp() < cutoff_date:
                self.delete_checkpoint(checkpoint.id)
    
    def _dict_to_metadata(self, data: Dict[str, Any]) -> CheckpointMetadata:
        """Convert dictionary to CheckpointMetadata."""
        # Handle datetime conversion
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        
        return CheckpointMetadata(**data)
    
    def validate_checkpoint(self, checkpoint_id: str) -> bool:
        """Validate checkpoint integrity."""
        try:
            checkpoint_data = self.restore_checkpoint(checkpoint_id)
            
            # Check required fields
            required_fields = [
                "metadata", "project_state", "execution_state",
                "phase_states", "task_states", "artifacts", "context"
            ]
            
            for field in required_fields:
                if not hasattr(checkpoint_data, field):
                    logger.error(f"Checkpoint missing field: {field}")
                    return False
            
            # Validate metadata
            if not checkpoint_data.metadata.id == checkpoint_id:
                logger.error("Checkpoint ID mismatch")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Checkpoint validation failed: {e}")
            return False