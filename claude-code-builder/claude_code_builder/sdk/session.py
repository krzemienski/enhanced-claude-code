"""Session management for Claude Code SDK."""

import asyncio
import json
import uuid
from typing import Optional, Dict, Any, List, Set
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
import logging

from ..models.base import BaseModel
from ..models.memory import ContextEntry
from ..exceptions.base import SDKError
from ..config.settings import AIConfig

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Represents a Claude Code session."""
    id: str
    project_path: Path
    created_at: datetime
    last_active: datetime
    active: bool = True
    instructions: Optional[str] = None
    mcp_servers: Optional[List[Dict[str, Any]]] = None
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    command_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "id": self.id,
            "project_path": str(self.project_path),
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "active": self.active,
            "instructions": self.instructions,
            "mcp_servers": self.mcp_servers,
            "context": self.context,
            "metadata": self.metadata,
            "command_history": self.command_history
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create session from dictionary."""
        return cls(
            id=data["id"],
            project_path=Path(data["project_path"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_active=datetime.fromisoformat(data["last_active"]),
            active=data.get("active", True),
            instructions=data.get("instructions"),
            mcp_servers=data.get("mcp_servers"),
            context=data.get("context", {}),
            metadata=data.get("metadata", {}),
            command_history=data.get("command_history", [])
        )


class SessionManager:
    """Manages Claude Code sessions lifecycle."""
    
    def __init__(self, config: AIConfig = None):
        """
        Initialize session manager.
        
        Args:
            config: SDK configuration
        """
        self.config = config
        self.sessions: Dict[str, Session] = {}
        self.active_sessions: Set[str] = set()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize session manager."""
        if self._initialized:
            return
        
        logger.info("Initializing session manager")
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_inactive_sessions())
        
        self._initialized = True
        logger.info("Session manager initialized")
    
    async def create_session(
        self,
        project_path: Path,
        instructions: Optional[str] = None,
        mcp_servers: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Session:
        """
        Create a new session.
        
        Args:
            project_path: Project directory path
            instructions: Custom instructions
            mcp_servers: MCP server configurations
            context: Initial context
            
        Returns:
            Created session
        """
        # Validate project path
        if not project_path.exists():
            raise SDKError(f"Project path does not exist: {project_path}")
        
        # Check session limit
        if len(self.active_sessions) >= self.config.max_concurrent_sessions:
            await self._evict_oldest_session()
        
        # Create session
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        session = Session(
            id=session_id,
            project_path=project_path,
            created_at=now,
            last_active=now,
            instructions=instructions,
            mcp_servers=mcp_servers or self.config.default_mcp_servers,
            context=context or {}
        )
        
        # Store session
        self.sessions[session_id] = session
        self.active_sessions.add(session_id)
        
        # Log session creation
        logger.info(f"Created session {session_id} for project {project_path}")
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session if found
        """
        session = self.sessions.get(session_id)
        
        if session and session.active:
            # Update last active time
            session.last_active = datetime.now()
            return session
        
        return None
    
    async def update_session_context(
        self,
        session_id: str,
        context_update: Dict[str, Any]
    ) -> None:
        """
        Update session context.
        
        Args:
            session_id: Session ID
            context_update: Context updates
        """
        session = await self.get_session(session_id)
        if not session:
            raise SDKError(f"Session not found: {session_id}")
        
        session.context.update(context_update)
        session.last_active = datetime.now()
        
        logger.debug(f"Updated context for session {session_id}")
    
    async def add_command_to_history(
        self,
        session_id: str,
        command: str,
        response: Optional[Dict[str, Any]] = None,
        duration: Optional[float] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Add command to session history.
        
        Args:
            session_id: Session ID
            command: Executed command
            response: Command response
            duration: Execution duration
            error: Error message if failed
        """
        session = await self.get_session(session_id)
        if not session:
            raise SDKError(f"Session not found: {session_id}")
        
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "duration": duration,
            "success": error is None
        }
        
        if response:
            history_entry["response_summary"] = self._summarize_response(response)
        
        if error:
            history_entry["error"] = error
        
        session.command_history.append(history_entry)
        
        # Limit history size
        if len(session.command_history) > self.config.max_history_size:
            session.command_history = session.command_history[-self.config.max_history_size:]
    
    async def close_session(self, session: Session) -> None:
        """
        Close a session.
        
        Args:
            session: Session to close
        """
        if session.id not in self.sessions:
            return
        
        session.active = False
        self.active_sessions.discard(session.id)
        
        # Archive session if needed
        if self.config.archive_sessions:
            await self._archive_session(session)
        
        logger.info(f"Closed session {session.id}")
    
    async def close_all_sessions(self) -> None:
        """Close all active sessions."""
        session_ids = list(self.active_sessions)
        
        for session_id in session_ids:
            session = self.sessions.get(session_id)
            if session:
                await self.close_session(session)
        
        logger.info(f"Closed {len(session_ids)} sessions")
    
    async def cleanup(self) -> None:
        """Cleanup session manager resources."""
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all sessions
        await self.close_all_sessions()
        
        self._initialized = False
        logger.info("Session manager cleaned up")
    
    async def _cleanup_inactive_sessions(self) -> None:
        """Periodically cleanup inactive sessions."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                now = datetime.now()
                timeout = timedelta(seconds=self.config.session_timeout)
                
                # Find inactive sessions
                inactive_sessions = []
                for session_id in list(self.active_sessions):
                    session = self.sessions.get(session_id)
                    if session and (now - session.last_active) > timeout:
                        inactive_sessions.append(session)
                
                # Close inactive sessions
                for session in inactive_sessions:
                    logger.info(f"Closing inactive session {session.id}")
                    await self.close_session(session)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
    
    async def _evict_oldest_session(self) -> None:
        """Evict the oldest session when limit is reached."""
        if not self.active_sessions:
            return
        
        # Find oldest session
        oldest_session = None
        oldest_time = datetime.now()
        
        for session_id in self.active_sessions:
            session = self.sessions.get(session_id)
            if session and session.last_active < oldest_time:
                oldest_session = session
                oldest_time = session.last_active
        
        if oldest_session:
            logger.info(f"Evicting oldest session {oldest_session.id}")
            await self.close_session(oldest_session)
    
    async def _archive_session(self, session: Session) -> None:
        """Archive a closed session."""
        archive_path = Path(self.config.session_archive_path) / f"{session.id}.json"
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(archive_path, "w") as f:
                json.dump(session.to_dict(), f, indent=2)
            
            logger.info(f"Archived session {session.id} to {archive_path}")
        except Exception as e:
            logger.error(f"Failed to archive session {session.id}: {e}")
    
    def _summarize_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of a response."""
        summary = {
            "type": response.get("type", "unknown"),
            "success": response.get("success", False)
        }
        
        # Add relevant fields based on response type
        if "tokens_used" in response:
            summary["tokens_used"] = response["tokens_used"]
        
        if "files_created" in response:
            summary["files_created"] = len(response["files_created"])
        
        if "files_modified" in response:
            summary["files_modified"] = len(response["files_modified"])
        
        if "tests_passed" in response:
            summary["tests_passed"] = response["tests_passed"]
            summary["tests_failed"] = response.get("tests_failed", 0)
        
        return summary
    
    async def restore_session(self, session_id: str) -> Optional[Session]:
        """
        Restore a session from archive.
        
        Args:
            session_id: Session ID to restore
            
        Returns:
            Restored session if found
        """
        archive_path = Path(self.config.session_archive_path) / f"{session_id}.json"
        
        if not archive_path.exists():
            return None
        
        try:
            with open(archive_path, "r") as f:
                data = json.load(f)
            
            session = Session.from_dict(data)
            
            # Reactivate session
            session.active = True
            session.last_active = datetime.now()
            
            self.sessions[session_id] = session
            self.active_sessions.add(session_id)
            
            logger.info(f"Restored session {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to restore session {session_id}: {e}")
            return None
    
    def get_active_session_count(self) -> int:
        """Get count of active sessions."""
        return len(self.active_sessions)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        total_commands = 0
        total_errors = 0
        
        for session in self.sessions.values():
            total_commands += len(session.command_history)
            total_errors += sum(
                1 for cmd in session.command_history
                if not cmd.get("success", True)
            )
        
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": len(self.active_sessions),
            "total_commands": total_commands,
            "total_errors": total_errors,
            "error_rate": total_errors / total_commands if total_commands > 0 else 0
        }