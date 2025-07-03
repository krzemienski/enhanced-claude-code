"""State management for execution persistence and recovery."""

import logging
import json
import sqlite3
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading
import pickle

from ..models.project import BuildStatus
from ..models.context import ExecutionContext

logger = logging.getLogger(__name__)


class StateType(Enum):
    """Types of state that can be persisted."""
    EXECUTION = "execution"
    PHASE = "phase"
    TASK = "task"
    ARTIFACT = "artifact"
    METRIC = "metric"
    CONFIG = "config"
    CHECKPOINT = "checkpoint"


@dataclass
class StateEntry:
    """Individual state entry."""
    id: str
    type: StateType
    key: str
    value: Any
    timestamp: datetime
    execution_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateSnapshot:
    """Complete state snapshot at a point in time."""
    snapshot_id: str
    execution_id: str
    timestamp: datetime
    entries: List[StateEntry]
    metadata: Dict[str, Any] = field(default_factory=dict)


class StateManager:
    """Manages execution state persistence with SQLite backend."""
    
    def __init__(self, state_dir: Optional[Path] = None):
        """Initialize the state manager."""
        self.state_dir = state_dir or Path.home() / ".claude_code_builder" / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Database path
        self.db_path = self.state_dir / "execution_state.db"
        
        # Thread-local storage for connections
        self._local = threading.local()
        
        # Initialize database
        self._init_database()
        
        # State cache
        self.cache: Dict[str, Any] = {}
        self.cache_size = 1000
        
        # Snapshot configuration
        self.auto_snapshot = True
        self.snapshot_interval = 300  # seconds
        self.max_snapshots = 100
        
        logger.info(f"State Manager initialized at {self.state_dir}")
    
    @property
    def connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def save_state(
        self,
        execution_id: str,
        state_type: StateType,
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Save a state entry."""
        entry_id = self._generate_entry_id(execution_id, state_type, key)
        
        # Serialize value
        serialized_value = self._serialize_value(value)
        
        # Insert or update
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO state_entries
            (id, execution_id, type, key, value, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entry_id,
            execution_id,
            state_type.value,
            key,
            serialized_value,
            datetime.now().isoformat(),
            json.dumps(metadata or {})
        ))
        
        self.connection.commit()
        
        # Update cache
        cache_key = f"{execution_id}:{state_type.value}:{key}"
        self.cache[cache_key] = value
        self._manage_cache_size()
        
        logger.debug(f"Saved state: {cache_key}")
        
        return entry_id
    
    def load_state(
        self,
        execution_id: str,
        state_type: StateType,
        key: str
    ) -> Optional[Any]:
        """Load a state entry."""
        # Check cache first
        cache_key = f"{execution_id}:{state_type.value}:{key}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Load from database
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT value FROM state_entries
            WHERE execution_id = ? AND type = ? AND key = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (execution_id, state_type.value, key))
        
        row = cursor.fetchone()
        if row:
            value = self._deserialize_value(row['value'])
            
            # Update cache
            self.cache[cache_key] = value
            self._manage_cache_size()
            
            return value
        
        return None
    
    def save_execution_state(
        self,
        execution_id: str,
        execution_state: Dict[str, Any]
    ) -> None:
        """Save complete execution state."""
        # Save main execution state
        self.save_state(
            execution_id,
            StateType.EXECUTION,
            "main",
            execution_state
        )
        
        # Save individual components
        if "phases" in execution_state:
            for phase_id, phase_data in execution_state["phases"].items():
                self.save_state(
                    execution_id,
                    StateType.PHASE,
                    phase_id,
                    phase_data
                )
        
        if "tasks" in execution_state:
            for task_id, task_data in execution_state["tasks"].items():
                self.save_state(
                    execution_id,
                    StateType.TASK,
                    task_id,
                    task_data
                )
        
        if "artifacts" in execution_state:
            for artifact_id, artifact_data in execution_state["artifacts"].items():
                self.save_state(
                    execution_id,
                    StateType.ARTIFACT,
                    artifact_id,
                    artifact_data
                )
        
        # Create snapshot if auto-snapshot is enabled
        if self.auto_snapshot:
            self.create_snapshot(execution_id)
    
    def load_execution_state(
        self,
        execution_id: str
    ) -> Optional[Dict[str, Any]]:
        """Load complete execution state."""
        # Load main state
        main_state = self.load_state(
            execution_id,
            StateType.EXECUTION,
            "main"
        )
        
        if not main_state:
            return None
        
        # Load components
        execution_state = main_state.copy()
        
        # Load phases
        phases = self.load_all_states(execution_id, StateType.PHASE)
        if phases:
            execution_state["phases"] = phases
        
        # Load tasks
        tasks = self.load_all_states(execution_id, StateType.TASK)
        if tasks:
            execution_state["tasks"] = tasks
        
        # Load artifacts
        artifacts = self.load_all_states(execution_id, StateType.ARTIFACT)
        if artifacts:
            execution_state["artifacts"] = artifacts
        
        return execution_state
    
    def load_all_states(
        self,
        execution_id: str,
        state_type: StateType
    ) -> Dict[str, Any]:
        """Load all states of a specific type for an execution."""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT key, value FROM state_entries
            WHERE execution_id = ? AND type = ?
            ORDER BY timestamp DESC
        """, (execution_id, state_type.value))
        
        states = {}
        for row in cursor.fetchall():
            key = row['key']
            value = self._deserialize_value(row['value'])
            states[key] = value
        
        return states
    
    def create_snapshot(
        self,
        execution_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a state snapshot."""
        snapshot_id = self._generate_snapshot_id(execution_id)
        
        # Get all current states
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM state_entries
            WHERE execution_id = ?
            ORDER BY timestamp DESC
        """, (execution_id,))
        
        entries = []
        for row in cursor.fetchall():
            entry = StateEntry(
                id=row['id'],
                type=StateType(row['type']),
                key=row['key'],
                value=self._deserialize_value(row['value']),
                timestamp=datetime.fromisoformat(row['timestamp']),
                execution_id=row['execution_id'],
                metadata=json.loads(row['metadata'])
            )
            entries.append(entry)
        
        # Create snapshot
        snapshot = StateSnapshot(
            snapshot_id=snapshot_id,
            execution_id=execution_id,
            timestamp=datetime.now(),
            entries=entries,
            metadata=metadata or {}
        )
        
        # Save snapshot
        cursor.execute("""
            INSERT INTO snapshots
            (id, execution_id, timestamp, data, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            snapshot_id,
            execution_id,
            snapshot.timestamp.isoformat(),
            pickle.dumps(snapshot),
            json.dumps(snapshot.metadata)
        ))
        
        self.connection.commit()
        
        # Clean up old snapshots
        self._cleanup_old_snapshots(execution_id)
        
        logger.info(f"Created snapshot: {snapshot_id}")
        
        return snapshot_id
    
    def restore_snapshot(
        self,
        snapshot_id: str
    ) -> Optional[StateSnapshot]:
        """Restore a state snapshot."""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT data FROM snapshots
            WHERE id = ?
        """, (snapshot_id,))
        
        row = cursor.fetchone()
        if row:
            snapshot = pickle.loads(row['data'])
            
            # Restore all entries
            for entry in snapshot.entries:
                self.save_state(
                    entry.execution_id,
                    entry.type,
                    entry.key,
                    entry.value,
                    entry.metadata
                )
            
            logger.info(f"Restored snapshot: {snapshot_id}")
            
            return snapshot
        
        return None
    
    def list_snapshots(
        self,
        execution_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List available snapshots."""
        cursor = self.connection.cursor()
        
        if execution_id:
            cursor.execute("""
                SELECT id, execution_id, timestamp, metadata
                FROM snapshots
                WHERE execution_id = ?
                ORDER BY timestamp DESC
            """, (execution_id,))
        else:
            cursor.execute("""
                SELECT id, execution_id, timestamp, metadata
                FROM snapshots
                ORDER BY timestamp DESC
            """)
        
        snapshots = []
        for row in cursor.fetchall():
            snapshots.append({
                "id": row['id'],
                "execution_id": row['execution_id'],
                "timestamp": row['timestamp'],
                "metadata": json.loads(row['metadata'])
            })
        
        return snapshots
    
    def get_execution_history(
        self,
        execution_id: str,
        state_type: Optional[StateType] = None,
        key: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get historical state changes."""
        cursor = self.connection.cursor()
        
        query = """
            SELECT * FROM state_entries
            WHERE execution_id = ?
        """
        params = [execution_id]
        
        if state_type:
            query += " AND type = ?"
            params.append(state_type.value)
        
        if key:
            query += " AND key = ?"
            params.append(key)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        history = []
        for row in cursor.fetchall():
            history.append({
                "id": row['id'],
                "type": row['type'],
                "key": row['key'],
                "timestamp": row['timestamp'],
                "metadata": json.loads(row['metadata'])
            })
        
        return history
    
    def update_execution_status(
        self,
        execution_id: str,
        status: BuildStatus,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update execution status."""
        status_data = {
            "status": status.value,
            "updated_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.save_state(
            execution_id,
            StateType.EXECUTION,
            "status",
            status_data
        )
    
    def track_metric(
        self,
        execution_id: str,
        metric_name: str,
        value: Any,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Track an execution metric."""
        metric_data = {
            "name": metric_name,
            "value": value,
            "timestamp": (timestamp or datetime.now()).isoformat()
        }
        
        # Generate unique key for time-series data
        key = f"{metric_name}_{datetime.now().timestamp()}"
        
        self.save_state(
            execution_id,
            StateType.METRIC,
            key,
            metric_data
        )
    
    def get_metrics(
        self,
        execution_id: str,
        metric_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get execution metrics."""
        metrics = self.load_all_states(execution_id, StateType.METRIC)
        
        if metric_name:
            # Filter by metric name
            filtered = []
            for key, metric_data in metrics.items():
                if metric_data.get("name") == metric_name:
                    filtered.append(metric_data)
            return filtered
        
        return list(metrics.values())
    
    def cleanup_execution(
        self,
        execution_id: str,
        keep_snapshots: bool = True
    ) -> int:
        """Clean up execution state."""
        cursor = self.connection.cursor()
        
        # Delete state entries
        cursor.execute("""
            DELETE FROM state_entries
            WHERE execution_id = ?
        """, (execution_id,))
        
        deleted_entries = cursor.rowcount
        
        # Delete snapshots if requested
        if not keep_snapshots:
            cursor.execute("""
                DELETE FROM snapshots
                WHERE execution_id = ?
            """, (execution_id,))
            
            deleted_entries += cursor.rowcount
        
        self.connection.commit()
        
        # Clear from cache
        keys_to_remove = [
            k for k in self.cache.keys()
            if k.startswith(f"{execution_id}:")
        ]
        for key in keys_to_remove:
            del self.cache[key]
        
        logger.info(f"Cleaned up execution {execution_id}: {deleted_entries} entries")
        
        return deleted_entries
    
    def export_state(
        self,
        execution_id: str,
        export_path: Path
    ) -> None:
        """Export execution state to file."""
        execution_state = self.load_execution_state(execution_id)
        
        if not execution_state:
            raise ValueError(f"No state found for execution: {execution_id}")
        
        # Add metadata
        export_data = {
            "execution_id": execution_id,
            "exported_at": datetime.now().isoformat(),
            "state": execution_state
        }
        
        # Write to file
        export_path.parent.mkdir(parents=True, exist_ok=True)
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Exported state to: {export_path}")
    
    def import_state(
        self,
        import_path: Path
    ) -> str:
        """Import execution state from file."""
        if not import_path.exists():
            raise FileNotFoundError(f"Import file not found: {import_path}")
        
        # Load data
        with open(import_path, 'r') as f:
            import_data = json.load(f)
        
        execution_id = import_data["execution_id"]
        execution_state = import_data["state"]
        
        # Save state
        self.save_execution_state(execution_id, execution_state)
        
        logger.info(f"Imported state for execution: {execution_id}")
        
        return execution_id
    
    def _init_database(self) -> None:
        """Initialize database schema."""
        cursor = self.connection.cursor()
        
        # State entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS state_entries (
                id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                type TEXT NOT NULL,
                key TEXT NOT NULL,
                value BLOB NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                UNIQUE(execution_id, type, key)
            )
        """)
        
        # Snapshots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                data BLOB NOT NULL,
                metadata TEXT DEFAULT '{}'
            )
        """)
        
        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_state_execution
            ON state_entries(execution_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_state_type
            ON state_entries(type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshot_execution
            ON snapshots(execution_id)
        """)
        
        self.connection.commit()
    
    def _generate_entry_id(
        self,
        execution_id: str,
        state_type: StateType,
        key: str
    ) -> str:
        """Generate unique entry ID."""
        import hashlib
        content = f"{execution_id}:{state_type.value}:{key}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _generate_snapshot_id(self, execution_id: str) -> str:
        """Generate unique snapshot ID."""
        import hashlib
        content = f"{execution_id}:{datetime.now().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage."""
        return pickle.dumps(value)
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        return pickle.loads(data)
    
    def _manage_cache_size(self) -> None:
        """Manage cache size by evicting old entries."""
        if len(self.cache) > self.cache_size:
            # Remove oldest entries (simple FIFO)
            num_to_remove = len(self.cache) - self.cache_size
            keys_to_remove = list(self.cache.keys())[:num_to_remove]
            for key in keys_to_remove:
                del self.cache[key]
    
    def _cleanup_old_snapshots(self, execution_id: str) -> None:
        """Clean up old snapshots."""
        cursor = self.connection.cursor()
        
        # Get snapshot count
        cursor.execute("""
            SELECT COUNT(*) as count FROM snapshots
            WHERE execution_id = ?
        """, (execution_id,))
        
        count = cursor.fetchone()['count']
        
        if count > self.max_snapshots:
            # Delete oldest snapshots
            cursor.execute("""
                DELETE FROM snapshots
                WHERE execution_id = ? AND id IN (
                    SELECT id FROM snapshots
                    WHERE execution_id = ?
                    ORDER BY timestamp ASC
                    LIMIT ?
                )
            """, (execution_id, execution_id, count - self.max_snapshots))
            
            self.connection.commit()
    
    def close(self) -> None:
        """Close database connection."""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')