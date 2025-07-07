"""Context reconstruction and recovery system for execution state restoration."""

import logging
import json
from typing import Dict, Any, List, Optional, Union, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import hashlib
import threading

from .store import PersistentMemoryStore, MemoryQuery, MemoryType, MemoryPriority
from .context_accumulator import ContextAccumulator, AccumulatedContext, ContextFragment, ContextType
from .serializer import StateSerializer, StateSnapshot, SerializationConfig
from .error_context import ErrorContextManager, ErrorContext

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Recovery strategies for different failure scenarios."""
    FULL_RESTORE = "full_restore"
    PARTIAL_RESTORE = "partial_restore"
    CHECKPOINT_RESTORE = "checkpoint_restore"
    STATE_RECONSTRUCTION = "state_reconstruction"
    ERROR_RECOVERY = "error_recovery"
    CLEAN_START = "clean_start"


class RecoveryPriority(Enum):
    """Priority levels for recovery operations."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class RecoveryPoint:
    """Recovery checkpoint with state information."""
    id: str
    execution_id: str
    timestamp: datetime
    phase_id: Optional[str]
    task_id: Optional[str]
    state_snapshot: StateSnapshot
    context_summary: Dict[str, Any]
    error_context: Optional[ErrorContext] = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryPlan:
    """Plan for recovering execution state."""
    strategy: RecoveryStrategy
    priority: RecoveryPriority
    target_execution_id: str
    recovery_points: List[RecoveryPoint]
    estimated_recovery_time: float
    confidence_score: float
    required_actions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    fallback_strategy: Optional[RecoveryStrategy] = None


@dataclass
class RecoveryResult:
    """Result of recovery operation."""
    success: bool
    strategy_used: RecoveryStrategy
    recovered_state: Optional[Any]
    recovered_context: Optional[AccumulatedContext]
    recovery_time_seconds: float
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextRecoveryManager:
    """Advanced context reconstruction and recovery system."""
    
    def __init__(
        self,
        memory_store: PersistentMemoryStore,
        context_accumulator: ContextAccumulator,
        error_context_manager: ErrorContextManager,
        serializer: Optional[StateSerializer] = None
    ):
        """Initialize the recovery manager."""
        self.memory_store = memory_store
        self.context_accumulator = context_accumulator
        self.error_context_manager = error_context_manager
        self.serializer = serializer or StateSerializer()
        
        self.lock = threading.RLock()
        
        # Recovery configuration
        self.config = {
            "max_recovery_time_minutes": 30,
            "checkpoint_interval_minutes": 5,
            "max_recovery_points": 50,
            "context_reconstruction_depth": 10,
            "auto_recovery_enabled": True,
            "recovery_verification_enabled": True
        }
        
        # Recovery state tracking
        self.active_recoveries: Dict[str, RecoveryPlan] = {}
        self.recovery_history: List[RecoveryResult] = []
        
        # Performance tracking
        self.stats = {
            "recovery_attempts": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "avg_recovery_time_seconds": 0.0,
            "checkpoint_operations": 0,
            "state_reconstructions": 0
        }
        
        logger.info("Context Recovery Manager initialized")
    
    def create_recovery_point(
        self,
        execution_id: str,
        phase_id: Optional[str] = None,
        task_id: Optional[str] = None,
        state: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RecoveryPoint:
        """Create a recovery checkpoint."""
        with self.lock:
            # Get current context
            context = self.context_accumulator.get_context(execution_id)
            if not context:
                raise ValueError(f"No active context found for execution: {execution_id}")
            
            # Create state snapshot
            snapshot_data = {
                "execution_id": execution_id,
                "phase_id": phase_id,
                "task_id": task_id,
                "context": context,
                "custom_state": state,
                "timestamp": datetime.now().isoformat()
            }
            
            state_snapshot = self.serializer.create_snapshot(
                component=f"execution_{execution_id}",
                state=snapshot_data,
                tags=["recovery_point", execution_id],
                metadata=metadata or {}
            )
            
            # Generate recovery point ID
            recovery_id = self._generate_recovery_id(execution_id, phase_id, task_id)
            
            # Create context summary
            context_summary = self.context_accumulator.consolidate_context(execution_id)
            
            # Create recovery point
            recovery_point = RecoveryPoint(
                id=recovery_id,
                execution_id=execution_id,
                timestamp=datetime.now(),
                phase_id=phase_id,
                task_id=task_id,
                state_snapshot=state_snapshot,
                context_summary=context_summary,
                metadata=metadata or {}
            )
            
            # Store recovery point
            self._store_recovery_point(recovery_point)
            
            self.stats["checkpoint_operations"] += 1
            
            logger.info(f"Created recovery point: {recovery_id}")
            
            return recovery_point
    
    def analyze_recovery_options(
        self,
        execution_id: str,
        failure_context: Optional[Dict[str, Any]] = None
    ) -> List[RecoveryPlan]:
        """Analyze available recovery options for failed execution."""
        with self.lock:
            # Get available recovery points
            recovery_points = self._get_recovery_points(execution_id)
            
            if not recovery_points:
                logger.warning(f"No recovery points found for execution: {execution_id}")
                return [self._create_clean_start_plan(execution_id)]
            
            # Get error context if available
            error_context = None
            if failure_context and "error" in failure_context:
                error_context = failure_context["error"]
            
            # Generate recovery strategies
            recovery_plans = []
            
            # Full restore from latest checkpoint
            if recovery_points:
                full_restore_plan = self._create_full_restore_plan(
                    execution_id, recovery_points[-1], error_context
                )
                recovery_plans.append(full_restore_plan)
            
            # Partial restore (skip failed components)
            if len(recovery_points) > 1:
                partial_restore_plan = self._create_partial_restore_plan(
                    execution_id, recovery_points, error_context
                )
                recovery_plans.append(partial_restore_plan)
            
            # State reconstruction from fragments
            reconstruction_plan = self._create_reconstruction_plan(
                execution_id, recovery_points, error_context
            )
            recovery_plans.append(reconstruction_plan)
            
            # Error-specific recovery
            if error_context:
                error_recovery_plan = self._create_error_recovery_plan(
                    execution_id, error_context, recovery_points
                )
                recovery_plans.append(error_recovery_plan)
            
            # Sort by confidence score
            recovery_plans.sort(key=lambda p: p.confidence_score, reverse=True)
            
            logger.info(f"Analyzed {len(recovery_plans)} recovery options for {execution_id}")
            
            return recovery_plans
    
    def execute_recovery(
        self,
        recovery_plan: RecoveryPlan,
        verify_result: bool = True
    ) -> RecoveryResult:
        """Execute recovery plan and restore execution state."""
        start_time = datetime.now()
        
        with self.lock:
            try:
                self.active_recoveries[recovery_plan.target_execution_id] = recovery_plan
                
                # Execute recovery based on strategy
                if recovery_plan.strategy == RecoveryStrategy.FULL_RESTORE:
                    result = self._execute_full_restore(recovery_plan)
                elif recovery_plan.strategy == RecoveryStrategy.PARTIAL_RESTORE:
                    result = self._execute_partial_restore(recovery_plan)
                elif recovery_plan.strategy == RecoveryStrategy.CHECKPOINT_RESTORE:
                    result = self._execute_checkpoint_restore(recovery_plan)
                elif recovery_plan.strategy == RecoveryStrategy.STATE_RECONSTRUCTION:
                    result = self._execute_state_reconstruction(recovery_plan)
                elif recovery_plan.strategy == RecoveryStrategy.ERROR_RECOVERY:
                    result = self._execute_error_recovery(recovery_plan)
                elif recovery_plan.strategy == RecoveryStrategy.CLEAN_START:
                    result = self._execute_clean_start(recovery_plan)
                else:
                    raise ValueError(f"Unknown recovery strategy: {recovery_plan.strategy}")
                
                # Calculate recovery time
                recovery_time = (datetime.now() - start_time).total_seconds()
                result.recovery_time_seconds = recovery_time
                
                # Verify recovery if requested
                if verify_result and result.success:
                    verification_result = self._verify_recovery(result)
                    if not verification_result:
                        result.success = False
                        result.errors.append("Recovery verification failed")
                
                # Update statistics
                self._update_recovery_stats(result)
                
                # Store recovery result
                self.recovery_history.append(result)
                
                logger.info(f"Recovery executed: {recovery_plan.strategy.value} - {'Success' if result.success else 'Failed'}")
                
                return result
            
            except Exception as e:
                # Create failed result
                result = RecoveryResult(
                    success=False,
                    strategy_used=recovery_plan.strategy,
                    recovered_state=None,
                    recovered_context=None,
                    recovery_time_seconds=(datetime.now() - start_time).total_seconds(),
                    errors=[str(e)]
                )
                
                self._update_recovery_stats(result)
                self.recovery_history.append(result)
                
                logger.error(f"Recovery failed: {e}")
                
                return result
            
            finally:
                # Clean up active recovery tracking
                if recovery_plan.target_execution_id in self.active_recoveries:
                    del self.active_recoveries[recovery_plan.target_execution_id]
    
    def reconstruct_context_from_fragments(
        self,
        execution_id: str,
        time_window_hours: int = 24
    ) -> Optional[AccumulatedContext]:
        """Reconstruct context from available fragments."""
        with self.lock:
            # Get time window
            since = datetime.now() - timedelta(hours=time_window_hours)
            
            # Query for context fragments
            fragment_query = MemoryQuery(
                memory_type=MemoryType.CONTEXT,
                tags=["fragment", execution_id],
                since=since,
                limit=1000
            )
            
            fragment_entries = self.memory_store.query(fragment_query)
            
            if not fragment_entries:
                logger.warning(f"No context fragments found for execution: {execution_id}")
                return None
            
            # Reconstruct context
            reconstructed_context = AccumulatedContext(
                execution_id=execution_id,
                project_id="reconstructed",
                timestamp=datetime.now()
            )
            
            # Process fragments
            for entry in fragment_entries:
                try:
                    fragment_data = entry.data
                    
                    if isinstance(fragment_data, dict):
                        # Recreate context fragment
                        fragment = ContextFragment(
                            id=fragment_data.get("id", entry.id),
                            context_type=ContextType(fragment_data.get("context_type", "execution")),
                            scope=fragment_data.get("scope", "execution"),
                            content=fragment_data.get("content", {}),
                            timestamp=datetime.fromisoformat(fragment_data.get("timestamp", datetime.now().isoformat())),
                            source=fragment_data.get("source", "recovery"),
                            relevance_score=fragment_data.get("relevance_score", 0.5),
                            tags=fragment_data.get("tags", []),
                            metadata=fragment_data.get("metadata", {})
                        )
                        
                        reconstructed_context.fragments.append(fragment)
                
                except Exception as e:
                    logger.warning(f"Failed to process fragment {entry.id}: {e}")
            
            # Sort fragments by timestamp
            reconstructed_context.fragments.sort(key=lambda f: f.timestamp)
            
            # Rebuild relationships
            self._rebuild_fragment_relationships(reconstructed_context)
            
            # Generate summary
            summary = self._generate_reconstruction_summary(reconstructed_context)
            reconstructed_context.summary = summary
            
            self.stats["state_reconstructions"] += 1
            
            logger.info(f"Reconstructed context with {len(reconstructed_context.fragments)} fragments")
            
            return reconstructed_context
    
    def get_recovery_history(
        self,
        execution_id: Optional[str] = None,
        limit: int = 100
    ) -> List[RecoveryResult]:
        """Get recovery operation history."""
        history = self.recovery_history
        
        if execution_id:
            history = [r for r in history if execution_id in str(r.metadata)]
        
        return history[-limit:]
    
    def cleanup_old_recovery_points(self, max_age_hours: int = 168) -> int:
        """Clean up old recovery points."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        # Query for old recovery points
        query = MemoryQuery(
            memory_type=MemoryType.CONTEXT,
            tags=["recovery_point"],
            until=cutoff_time,
            limit=1000
        )
        
        old_entries = self.memory_store.query(query)
        cleaned_count = 0
        
        for entry in old_entries:
            if self.memory_store.delete(entry.id):
                cleaned_count += 1
        
        logger.info(f"Cleaned up {cleaned_count} old recovery points")
        
        return cleaned_count
    
    def _get_recovery_points(self, execution_id: str) -> List[RecoveryPoint]:
        """Get recovery points for execution."""
        query = MemoryQuery(
            memory_type=MemoryType.CONTEXT,
            tags=["recovery_point", execution_id],
            limit=self.config["max_recovery_points"]
        )
        
        entries = self.memory_store.query(query)
        recovery_points = []
        
        for entry in entries:
            try:
                recovery_point = self._deserialize_recovery_point(entry.data)
                recovery_points.append(recovery_point)
            except Exception as e:
                logger.warning(f"Failed to deserialize recovery point {entry.id}: {e}")
        
        # Sort by timestamp
        recovery_points.sort(key=lambda rp: rp.timestamp)
        
        return recovery_points
    
    def _create_full_restore_plan(
        self,
        execution_id: str,
        latest_recovery_point: RecoveryPoint,
        error_context: Optional[Any]
    ) -> RecoveryPlan:
        """Create full restore recovery plan."""
        confidence = 0.9  # High confidence for full restore
        
        # Reduce confidence if error suggests data corruption
        if error_context and "corruption" in str(error_context).lower():
            confidence *= 0.7
        
        return RecoveryPlan(
            strategy=RecoveryStrategy.FULL_RESTORE,
            priority=RecoveryPriority.HIGH,
            target_execution_id=execution_id,
            recovery_points=[latest_recovery_point],
            estimated_recovery_time=30.0,  # seconds
            confidence_score=confidence,
            required_actions=[
                "Restore state from latest checkpoint",
                "Verify data integrity",
                "Resume execution from checkpoint"
            ],
            risks=["May lose progress since last checkpoint"],
            fallback_strategy=RecoveryStrategy.PARTIAL_RESTORE
        )
    
    def _create_partial_restore_plan(
        self,
        execution_id: str,
        recovery_points: List[RecoveryPoint],
        error_context: Optional[Any]
    ) -> RecoveryPlan:
        """Create partial restore recovery plan."""
        # Use second-to-last checkpoint to avoid corrupted state
        target_point = recovery_points[-2] if len(recovery_points) > 1 else recovery_points[-1]
        
        return RecoveryPlan(
            strategy=RecoveryStrategy.PARTIAL_RESTORE,
            priority=RecoveryPriority.MEDIUM,
            target_execution_id=execution_id,
            recovery_points=[target_point],
            estimated_recovery_time=60.0,
            confidence_score=0.75,
            required_actions=[
                "Restore state from earlier checkpoint",
                "Skip failed components",
                "Resume with modified execution plan"
            ],
            risks=["More progress loss", "May skip important steps"],
            fallback_strategy=RecoveryStrategy.STATE_RECONSTRUCTION
        )
    
    def _create_reconstruction_plan(
        self,
        execution_id: str,
        recovery_points: List[RecoveryPoint],
        error_context: Optional[Any]
    ) -> RecoveryPlan:
        """Create state reconstruction recovery plan."""
        return RecoveryPlan(
            strategy=RecoveryStrategy.STATE_RECONSTRUCTION,
            priority=RecoveryPriority.MEDIUM,
            target_execution_id=execution_id,
            recovery_points=recovery_points,
            estimated_recovery_time=120.0,
            confidence_score=0.6,
            required_actions=[
                "Analyze available context fragments",
                "Reconstruct execution state",
                "Validate reconstructed state",
                "Resume with reconstructed context"
            ],
            risks=["Incomplete state reconstruction", "Potential data inconsistencies"],
            fallback_strategy=RecoveryStrategy.CLEAN_START
        )
    
    def _create_error_recovery_plan(
        self,
        execution_id: str,
        error_context: Any,
        recovery_points: List[RecoveryPoint]
    ) -> RecoveryPlan:
        """Create error-specific recovery plan."""
        # Get recovery suggestions from error context
        suggestions = []
        if hasattr(error_context, 'recovery_suggestions'):
            suggestions = error_context.recovery_suggestions
        
        return RecoveryPlan(
            strategy=RecoveryStrategy.ERROR_RECOVERY,
            priority=RecoveryPriority.HIGH,
            target_execution_id=execution_id,
            recovery_points=recovery_points[-1:] if recovery_points else [],
            estimated_recovery_time=90.0,
            confidence_score=0.8,
            required_actions=[
                "Apply error-specific recovery actions",
                "Fix underlying error conditions",
                "Resume execution with corrections"
            ] + suggestions,
            risks=["May not address root cause"],
            fallback_strategy=RecoveryStrategy.PARTIAL_RESTORE
        )
    
    def _create_clean_start_plan(self, execution_id: str) -> RecoveryPlan:
        """Create clean start recovery plan."""
        return RecoveryPlan(
            strategy=RecoveryStrategy.CLEAN_START,
            priority=RecoveryPriority.LOW,
            target_execution_id=execution_id,
            recovery_points=[],
            estimated_recovery_time=0.0,
            confidence_score=1.0,  # Always works but loses all progress
            required_actions=[
                "Clear all execution state",
                "Start fresh execution",
                "Initialize new context"
            ],
            risks=["Complete loss of progress"],
            fallback_strategy=None
        )
    
    def _execute_full_restore(self, plan: RecoveryPlan) -> RecoveryResult:
        """Execute full restore recovery."""
        if not plan.recovery_points:
            return RecoveryResult(
                success=False,
                strategy_used=plan.strategy,
                recovered_state=None,
                recovered_context=None,
                recovery_time_seconds=0.0,
                errors=["No recovery points available"]
            )
        
        recovery_point = plan.recovery_points[0]
        
        try:
            # Deserialize state snapshot
            serialized_state = self.serializer.serialize_snapshot(recovery_point.state_snapshot)
            snapshot = self.serializer.deserialize_snapshot(serialized_state)
            
            # Restore context
            context_data = snapshot.state_data.get("context")
            if context_data:
                # Recreate accumulated context
                restored_context = self._deserialize_context(context_data)
                
                # Reactivate context in accumulator
                self.context_accumulator.active_contexts[plan.target_execution_id] = restored_context
            
            return RecoveryResult(
                success=True,
                strategy_used=plan.strategy,
                recovered_state=snapshot.state_data,
                recovered_context=restored_context if context_data else None,
                recovery_time_seconds=0.0,  # Will be set by caller
                metadata={
                    "recovery_point_id": recovery_point.id,
                    "recovery_timestamp": recovery_point.timestamp.isoformat()
                }
            )
        
        except Exception as e:
            return RecoveryResult(
                success=False,
                strategy_used=plan.strategy,
                recovered_state=None,
                recovered_context=None,
                recovery_time_seconds=0.0,
                errors=[f"Full restore failed: {e}"]
            )
    
    def _execute_state_reconstruction(self, plan: RecoveryPlan) -> RecoveryResult:
        """Execute state reconstruction recovery."""
        try:
            # Reconstruct context from fragments
            reconstructed_context = self.reconstruct_context_from_fragments(
                plan.target_execution_id
            )
            
            if not reconstructed_context:
                return RecoveryResult(
                    success=False,
                    strategy_used=plan.strategy,
                    recovered_state=None,
                    recovered_context=None,
                    recovery_time_seconds=0.0,
                    errors=["Failed to reconstruct context from fragments"]
                )
            
            # Reactivate context
            self.context_accumulator.active_contexts[plan.target_execution_id] = reconstructed_context
            
            return RecoveryResult(
                success=True,
                strategy_used=plan.strategy,
                recovered_state={"reconstructed": True},
                recovered_context=reconstructed_context,
                recovery_time_seconds=0.0,
                warnings=["State reconstructed from fragments - may be incomplete"]
            )
        
        except Exception as e:
            return RecoveryResult(
                success=False,
                strategy_used=plan.strategy,
                recovered_state=None,
                recovered_context=None,
                recovery_time_seconds=0.0,
                errors=[f"State reconstruction failed: {e}"]
            )
    
    def _generate_recovery_id(
        self,
        execution_id: str,
        phase_id: Optional[str],
        task_id: Optional[str]
    ) -> str:
        """Generate unique recovery point ID."""
        content = f"{execution_id}:{phase_id}:{task_id}:{datetime.now().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _store_recovery_point(self, recovery_point: RecoveryPoint) -> None:
        """Store recovery point in memory."""
        # Serialize recovery point
        serialized_data = {
            "id": recovery_point.id,
            "execution_id": recovery_point.execution_id,
            "timestamp": recovery_point.timestamp.isoformat(),
            "phase_id": recovery_point.phase_id,
            "task_id": recovery_point.task_id,
            "state_snapshot": recovery_point.state_snapshot,
            "context_summary": recovery_point.context_summary,
            "error_context": recovery_point.error_context,
            "dependencies": recovery_point.dependencies,
            "metadata": recovery_point.metadata
        }
        
        # Store in memory
        self.memory_store.store(
            f"recovery_point_{recovery_point.id}",
            serialized_data,
            MemoryType.CONTEXT,
            MemoryPriority.HIGH,
            tags=["recovery_point", recovery_point.execution_id],
            ttl_hours=168  # 1 week
        )
    
    def _update_recovery_stats(self, result: RecoveryResult) -> None:
        """Update recovery statistics."""
        self.stats["recovery_attempts"] += 1
        
        if result.success:
            self.stats["successful_recoveries"] += 1
        else:
            self.stats["failed_recoveries"] += 1
        
        # Update average recovery time
        total_time = (self.stats["avg_recovery_time_seconds"] * 
                     (self.stats["recovery_attempts"] - 1) + 
                     result.recovery_time_seconds)
        
        self.stats["avg_recovery_time_seconds"] = total_time / self.stats["recovery_attempts"]