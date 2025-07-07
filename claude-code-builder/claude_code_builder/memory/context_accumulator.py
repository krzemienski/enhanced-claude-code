"""Context accumulation for building comprehensive execution context."""

import logging
from typing import Dict, Any, List, Optional, Set, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import threading

from .store import PersistentMemoryStore, MemoryType, MemoryPriority
from ..models.project import ProjectSpec
from ..models.phase import Phase, Task, TaskResult
from ..models.base import Result

logger = logging.getLogger(__name__)


class ContextType(Enum):
    """Types of context information."""
    PROJECT = "project"
    EXECUTION = "execution"
    PHASE = "phase"
    TASK = "task"
    ERROR = "error"
    DECISION = "decision"
    LEARNING = "learning"
    PATTERN = "pattern"


class ContextScope(Enum):
    """Scope of context relevance."""
    GLOBAL = "global"          # Relevant across all projects
    PROJECT = "project"        # Relevant to specific project type
    EXECUTION = "execution"    # Relevant to current execution
    SESSION = "session"        # Relevant to current session
    TEMPORARY = "temporary"    # Short-term relevance


@dataclass
class ContextFragment:
    """Individual piece of context information."""
    id: str
    context_type: ContextType
    scope: ContextScope
    content: Any
    timestamp: datetime
    source: str
    relevance_score: float = 1.0
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccumulatedContext:
    """Accumulated context for an execution."""
    execution_id: str
    project_id: str
    fragments: List[ContextFragment] = field(default_factory=list)
    relationships: Dict[str, List[str]] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextAccumulator:
    """Accumulates and manages execution context."""
    
    def __init__(self, memory_store: PersistentMemoryStore):
        """Initialize the context accumulator."""
        self.memory_store = memory_store
        self.lock = threading.RLock()
        
        # Active contexts
        self.active_contexts: Dict[str, AccumulatedContext] = {}
        
        # Context configuration
        self.max_fragments_per_context = 10000
        self.max_contexts = 100
        self.relevance_threshold = 0.1
        self.consolidation_interval = 300  # 5 minutes
        
        # Context patterns
        self.learned_patterns: Dict[str, Any] = {}
        
        # Performance tracking
        self.stats = {
            "fragments_added": 0,
            "contexts_created": 0,
            "patterns_learned": 0,
            "consolidations": 0
        }
        
        logger.info("Context Accumulator initialized")
    
    def create_context(
        self,
        execution_id: str,
        project_id: str,
        initial_project: Optional[ProjectSpec] = None
    ) -> AccumulatedContext:
        """Create a new accumulated context."""
        with self.lock:
            context = AccumulatedContext(
                execution_id=execution_id,
                project_id=project_id
            )
            
            # Add initial project context if provided
            if initial_project:
                self.add_project_context(context, initial_project)
            
            # Load relevant historical context
            self._load_relevant_context(context)
            
            # Store in active contexts
            self.active_contexts[execution_id] = context
            self._manage_context_count()
            
            # Store in memory
            self._persist_context(context)
            
            self.stats["contexts_created"] += 1
            
            logger.info(f"Created context for execution: {execution_id}")
            
            return context
    
    def add_fragment(
        self,
        execution_id: str,
        context_type: ContextType,
        content: Any,
        source: str,
        scope: ContextScope = ContextScope.EXECUTION,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        relevance_score: float = 1.0
    ) -> str:
        """Add a context fragment."""
        with self.lock:
            if execution_id not in self.active_contexts:
                logger.warning(f"No active context for execution: {execution_id}")
                return ""
            
            context = self.active_contexts[execution_id]
            
            # Create fragment
            fragment_id = self._generate_fragment_id(execution_id, context_type, source)
            fragment = ContextFragment(
                id=fragment_id,
                context_type=context_type,
                scope=scope,
                content=content,
                timestamp=datetime.now(),
                source=source,
                relevance_score=relevance_score,
                tags=tags or [],
                metadata=metadata or {}
            )
            
            # Add to context
            context.fragments.append(fragment)
            self._manage_fragment_count(context)
            
            # Update relationships
            self._update_relationships(context, fragment)
            
            # Check for patterns
            self._analyze_patterns(context, fragment)
            
            # Store in memory
            self._store_fragment(fragment)
            
            self.stats["fragments_added"] += 1
            
            logger.debug(f"Added fragment: {fragment_id} to context {execution_id}")
            
            return fragment_id
    
    def add_project_context(
        self,
        context: AccumulatedContext,
        project: ProjectSpec
    ) -> None:
        """Add project-specific context."""
        # Project configuration
        self.add_fragment(
            context.execution_id,
            ContextType.PROJECT,
            {
                "name": project.config.name,
                "type": project.config.project_type,
                "language": project.config.primary_language,
                "config": project.config.to_dict() if hasattr(project.config, 'to_dict') else {}
            },
            "project_config",
            ContextScope.EXECUTION,
            tags=["project", "config"]
        )
        
        # Project phases
        for phase in project.phases:
            self.add_fragment(
                context.execution_id,
                ContextType.PHASE,
                {
                    "id": phase.id,
                    "name": phase.name,
                    "description": phase.description,
                    "tasks": [task.id for task in phase.tasks],
                    "dependencies": phase.dependencies,
                    "metadata": phase.metadata
                },
                f"phase_{phase.id}",
                ContextScope.EXECUTION,
                tags=["phase", "planning"]
            )
            
            # Phase tasks
            for task in phase.tasks:
                self.add_fragment(
                    context.execution_id,
                    ContextType.TASK,
                    {
                        "id": task.id,
                        "name": task.name,
                        "type": task.type,
                        "description": task.description,
                        "phase_id": phase.id,
                        "dependencies": task.dependencies,
                        "metadata": task.metadata
                    },
                    f"task_{task.id}",
                    ContextScope.EXECUTION,
                    tags=["task", "planning", phase.name.lower().replace(" ", "_")]
                )
    
    def add_execution_context(
        self,
        execution_id: str,
        execution_context: Dict[str, Any]
    ) -> None:
        """Add execution context information."""
        self.add_fragment(
            execution_id,
            ContextType.EXECUTION,
            {
                "project_id": execution_context.project_id,
                "execution_id": execution_context.execution_id,
                "project_root": execution_context.project_root,
                "config": execution_context.config,
                "metadata": execution_context.metadata
            },
            "execution_context",
            ContextScope.EXECUTION,
            tags=["execution", "context"]
        )
    
    def add_phase_result(
        self,
        execution_id: str,
        phase: Phase,
        result: TaskResult
    ) -> None:
        """Add phase execution result."""
        self.add_fragment(
            execution_id,
            ContextType.PHASE,
            {
                "phase_id": phase.id,
                "phase_name": phase.name,
                "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
                "start_time": result.start_time.isoformat() if result.start_time else None,
                "end_time": result.end_time.isoformat() if result.end_time else None,
                "outputs": result.outputs,
                "artifacts": result.artifacts,
                "metrics": result.metrics,
                "metadata": result.metadata
            },
            f"phase_result_{phase.id}",
            ContextScope.EXECUTION,
            tags=["phase", "result", phase.name.lower().replace(" ", "_")]
        )
    
    def add_task_result(
        self,
        execution_id: str,
        task: Task,
        result: TaskResult
    ) -> None:
        """Add task execution result."""
        self.add_fragment(
            execution_id,
            ContextType.TASK,
            {
                "task_id": task.id,
                "task_name": task.name,
                "task_type": task.type,
                "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
                "start_time": result.start_time.isoformat() if result.start_time else None,
                "end_time": result.end_time.isoformat() if result.end_time else None,
                "outputs": result.outputs,
                "artifacts": result.artifacts,
                "metrics": result.metrics,
                "metadata": result.metadata
            },
            f"task_result_{task.id}",
            ContextScope.EXECUTION,
            tags=["task", "result", task.type]
        )
    
    def add_error_context(
        self,
        execution_id: str,
        error: Exception,
        phase_id: Optional[str] = None,
        task_id: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add error context."""
        self.add_fragment(
            execution_id,
            ContextType.ERROR,
            {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "phase_id": phase_id,
                "task_id": task_id,
                "context": context_data or {},
                "traceback": str(error.__traceback__) if error.__traceback__ else None
            },
            f"error_{datetime.now().timestamp()}",
            ContextScope.EXECUTION,
            tags=["error", "failure"],
            relevance_score=0.9  # High relevance for errors
        )
    
    def add_decision_context(
        self,
        execution_id: str,
        decision: str,
        rationale: str,
        alternatives: List[str],
        context_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add decision-making context."""
        self.add_fragment(
            execution_id,
            ContextType.DECISION,
            {
                "decision": decision,
                "rationale": rationale,
                "alternatives": alternatives,
                "context": context_data or {}
            },
            f"decision_{datetime.now().timestamp()}",
            ContextScope.EXECUTION,
            tags=["decision", "reasoning"],
            relevance_score=0.8
        )
    
    def get_context(self, execution_id: str) -> Optional[AccumulatedContext]:
        """Get accumulated context for execution."""
        with self.lock:
            return self.active_contexts.get(execution_id)
    
    def get_relevant_fragments(
        self,
        execution_id: str,
        context_type: Optional[ContextType] = None,
        tags: Optional[List[str]] = None,
        min_relevance: float = 0.1,
        limit: int = 100
    ) -> List[ContextFragment]:
        """Get relevant context fragments."""
        with self.lock:
            context = self.active_contexts.get(execution_id)
            if not context:
                return []
            
            fragments = context.fragments
            
            # Filter by type
            if context_type:
                fragments = [f for f in fragments if f.context_type == context_type]
            
            # Filter by tags
            if tags:
                fragments = [
                    f for f in fragments
                    if any(tag in f.tags for tag in tags)
                ]
            
            # Filter by relevance
            fragments = [f for f in fragments if f.relevance_score >= min_relevance]
            
            # Sort by relevance and timestamp
            fragments.sort(
                key=lambda f: (f.relevance_score, f.timestamp),
                reverse=True
            )
            
            return fragments[:limit]
    
    def consolidate_context(self, execution_id: str) -> Dict[str, Any]:
        """Consolidate context into a summary."""
        with self.lock:
            context = self.active_contexts.get(execution_id)
            if not context:
                return {}
            
            summary = {
                "execution_id": execution_id,
                "project_id": context.project_id,
                "timestamp": datetime.now().isoformat(),
                "total_fragments": len(context.fragments),
                "fragment_types": {},
                "key_decisions": [],
                "errors": [],
                "patterns": [],
                "relationships": context.relationships
            }
            
            # Count fragments by type
            for fragment in context.fragments:
                ftype = fragment.context_type.value
                summary["fragment_types"][ftype] = summary["fragment_types"].get(ftype, 0) + 1
            
            # Extract key decisions
            decision_fragments = [
                f for f in context.fragments
                if f.context_type == ContextType.DECISION
            ]
            summary["key_decisions"] = [
                {
                    "decision": f.content.get("decision"),
                    "rationale": f.content.get("rationale"),
                    "timestamp": f.timestamp.isoformat()
                }
                for f in decision_fragments[-10:]  # Last 10 decisions
            ]
            
            # Extract errors
            error_fragments = [
                f for f in context.fragments
                if f.context_type == ContextType.ERROR
            ]
            summary["errors"] = [
                {
                    "error_type": f.content.get("error_type"),
                    "error_message": f.content.get("error_message"),
                    "phase_id": f.content.get("phase_id"),
                    "task_id": f.content.get("task_id"),
                    "timestamp": f.timestamp.isoformat()
                }
                for f in error_fragments[-10:]  # Last 10 errors
            ]
            
            # Add learned patterns
            summary["patterns"] = list(self.learned_patterns.keys())
            
            # Update context summary
            context.summary = summary
            
            # Store consolidated context
            self._persist_context(context)
            
            self.stats["consolidations"] += 1
            
            logger.info(f"Consolidated context for execution: {execution_id}")
            
            return summary
    
    def close_context(self, execution_id: str) -> None:
        """Close and persist context."""
        with self.lock:
            if execution_id in self.active_contexts:
                context = self.active_contexts[execution_id]
                
                # Final consolidation
                self.consolidate_context(execution_id)
                
                # Store final context in memory
                self.memory_store.store(
                    f"final_context_{execution_id}",
                    context,
                    MemoryType.CONTEXT,
                    MemoryPriority.HIGH,
                    tags=["final_context", "execution", context.project_id],
                    ttl_hours=168  # Keep for 1 week
                )
                
                # Remove from active contexts
                del self.active_contexts[execution_id]
                
                logger.info(f"Closed context for execution: {execution_id}")
    
    def _load_relevant_context(self, context: AccumulatedContext) -> None:
        """Load relevant historical context."""
        # Load project-specific context
        project_entries = self.memory_store.query(
            query_obj_from_dict({
                "memory_type": MemoryType.CONTEXT,
                "tags": [context.project_id],
                "limit": 50
            })
        )
        
        for entry in project_entries:
            if isinstance(entry.data, dict) and "fragments" in entry.data:
                # Add relevant fragments from historical context
                for fragment_data in entry.data["fragments"][-10:]:  # Last 10 fragments
                    if fragment_data.get("scope") in [ContextScope.GLOBAL.value, ContextScope.PROJECT.value]:
                        # Create fragment from historical data
                        fragment = ContextFragment(
                            id=fragment_data["id"],
                            context_type=ContextType(fragment_data["context_type"]),
                            scope=ContextScope(fragment_data["scope"]),
                            content=fragment_data["content"],
                            timestamp=datetime.fromisoformat(fragment_data["timestamp"]),
                            source=fragment_data["source"],
                            relevance_score=fragment_data.get("relevance_score", 0.5) * 0.8,  # Reduce historical relevance
                            tags=fragment_data.get("tags", []) + ["historical"],
                            metadata=fragment_data.get("metadata", {})
                        )
                        context.fragments.append(fragment)
    
    def _update_relationships(
        self,
        context: AccumulatedContext,
        fragment: ContextFragment
    ) -> None:
        """Update fragment relationships."""
        # Simple relationship detection based on content
        for existing_fragment in context.fragments[-10:]:  # Check last 10 fragments
            if existing_fragment.id == fragment.id:
                continue
            
            # Check for relationships
            relationship_score = self._calculate_relationship_score(
                existing_fragment, fragment
            )
            
            if relationship_score > 0.5:
                if fragment.id not in context.relationships:
                    context.relationships[fragment.id] = []
                context.relationships[fragment.id].append(existing_fragment.id)
    
    def _calculate_relationship_score(
        self,
        fragment1: ContextFragment,
        fragment2: ContextFragment
    ) -> float:
        """Calculate relationship score between fragments."""
        score = 0.0
        
        # Same type
        if fragment1.context_type == fragment2.context_type:
            score += 0.3
        
        # Shared tags
        shared_tags = set(fragment1.tags) & set(fragment2.tags)
        score += len(shared_tags) * 0.2
        
        # Temporal proximity (within 1 hour)
        time_diff = abs((fragment1.timestamp - fragment2.timestamp).total_seconds())
        if time_diff < 3600:  # 1 hour
            score += 0.3 * (1 - time_diff / 3600)
        
        # Content relationship (simple keyword matching)
        if isinstance(fragment1.content, dict) and isinstance(fragment2.content, dict):
            content1_str = json.dumps(fragment1.content).lower()
            content2_str = json.dumps(fragment2.content).lower()
            
            # Check for common identifiers
            common_words = set(content1_str.split()) & set(content2_str.split())
            if len(common_words) > 3:
                score += 0.2
        
        return min(score, 1.0)
    
    def _analyze_patterns(
        self,
        context: AccumulatedContext,
        fragment: ContextFragment
    ) -> None:
        """Analyze patterns in context."""
        # Simple pattern detection for common sequences
        recent_fragments = context.fragments[-5:]  # Last 5 fragments
        
        # Error patterns
        if fragment.context_type == ContextType.ERROR:
            error_sequence = [f.context_type for f in recent_fragments]
            pattern_key = f"error_sequence_{len(error_sequence)}"
            
            if pattern_key not in self.learned_patterns:
                self.learned_patterns[pattern_key] = {
                    "type": "error_sequence",
                    "sequence": [t.value for t in error_sequence],
                    "count": 1,
                    "last_seen": datetime.now()
                }
                self.stats["patterns_learned"] += 1
            else:
                self.learned_patterns[pattern_key]["count"] += 1
                self.learned_patterns[pattern_key]["last_seen"] = datetime.now()
    
    def _generate_fragment_id(
        self,
        execution_id: str,
        context_type: ContextType,
        source: str
    ) -> str:
        """Generate unique fragment ID."""
        import hashlib
        content = f"{execution_id}:{context_type.value}:{source}:{datetime.now().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _store_fragment(self, fragment: ContextFragment) -> None:
        """Store fragment in memory."""
        self.memory_store.store(
            f"fragment_{fragment.id}",
            fragment,
            MemoryType.CONTEXT,
            MemoryPriority.MEDIUM,
            tags=["fragment"] + fragment.tags,
            ttl_hours=24  # Keep fragments for 1 day
        )
    
    def _persist_context(self, context: AccumulatedContext) -> None:
        """Persist context to memory store."""
        context_data = {
            "execution_id": context.execution_id,
            "project_id": context.project_id,
            "timestamp": context.timestamp.isoformat(),
            "fragments": [
                {
                    "id": f.id,
                    "context_type": f.context_type.value,
                    "scope": f.scope.value,
                    "content": f.content,
                    "timestamp": f.timestamp.isoformat(),
                    "source": f.source,
                    "relevance_score": f.relevance_score,
                    "tags": f.tags,
                    "metadata": f.metadata
                }
                for f in context.fragments
            ],
            "relationships": context.relationships,
            "summary": context.summary,
            "metadata": context.metadata
        }
        
        self.memory_store.store(
            f"context_{context.execution_id}",
            context_data,
            MemoryType.CONTEXT,
            MemoryPriority.HIGH,
            tags=["context", "execution", context.project_id],
            ttl_hours=168  # Keep for 1 week
        )
    
    def _manage_fragment_count(self, context: AccumulatedContext) -> None:
        """Manage fragment count by removing low-relevance fragments."""
        if len(context.fragments) > self.max_fragments_per_context:
            # Sort by relevance and keep top fragments
            context.fragments.sort(
                key=lambda f: (f.relevance_score, f.timestamp),
                reverse=True
            )
            
            # Keep the most relevant fragments
            keep_count = int(self.max_fragments_per_context * 0.8)
            context.fragments = context.fragments[:keep_count]
    
    def _manage_context_count(self) -> None:
        """Manage active context count."""
        if len(self.active_contexts) > self.max_contexts:
            # Remove oldest contexts
            oldest_contexts = sorted(
                self.active_contexts.items(),
                key=lambda x: x[1].timestamp
            )
            
            # Keep most recent contexts
            keep_count = int(self.max_contexts * 0.8)
            for execution_id, context in oldest_contexts[:-keep_count]:
                self.close_context(execution_id)


def query_obj_from_dict(query_dict: Dict[str, Any]):
    """Helper to create query object from dictionary."""
    from .store import MemoryQuery
    return MemoryQuery(
        memory_type=query_dict.get("memory_type"),
        key_pattern=query_dict.get("key_pattern"),
        tags=query_dict.get("tags", []),
        priority_min=query_dict.get("priority_min"),
        since=query_dict.get("since"),
        until=query_dict.get("until"),
        limit=query_dict.get("limit", 100),
        include_expired=query_dict.get("include_expired", False)
    )