"""
NOVA Multi-Session Manager
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from nova.ai.conversation_manager import ConversationManager
from nova.utils.constants import SESSIONS_DIR, SessionError

logger = logging.getLogger("NOVA.SessionManager")


class SessionManager:
    """
    Manages multiple independent conversation sessions with local JSON persistence.
    """

    def __init__(self, sessions_dir: Optional[Path] = None):
        self.sessions_dir: Path = sessions_dir or SESSIONS_DIR
        self._sessions: Dict[str, Dict[str, Any]] = {}  # session_id -> metadata + ConversationManager
        self._active_session_id: str = "default"

        # Ensure sessions directory exists
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._initialize_default_session()

    @property
    def active_session_id(self) -> str:
        return self._active_session_id

    @property
    def active_session_name(self) -> str:
        if self._active_session_id in self._sessions:
            return self._sessions[self._active_session_id]["name"]
        return "Default Session"

    def get_active_conversation(self) -> ConversationManager:
        """Returns the ConversationManager instance for the current active session."""
        if self._active_session_id not in self._sessions:
            self.create_session("Default Session", session_id="default")
        return self._sessions[self._active_session_id]["conversation"]

    def create_session(self, name: str, session_id: Optional[str] = None) -> str:
        """
        Creates a new conversation session.
        """
        sid = session_id or name.lower().replace(" ", "_").strip()
        if not sid:
            sid = f"session_{int(datetime.now().timestamp())}"

        conv = ConversationManager()
        self._sessions[sid] = {
            "session_id": sid,
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "conversation": conv,
        }

        self._active_session_id = sid
        self.save_session(sid)
        logger.info(f"Created new conversation session: '{name}' (ID: {sid})")
        return sid

    def switch_session(self, session_id: str) -> bool:
        """
        Switches current active session to target session ID.
        Attempts to load session from disk if not currently in memory.
        """
        if session_id not in self._sessions:
            if not self.load_session(session_id):
                logger.error(f"Cannot switch to non-existent session: {session_id}")
                return False

        self._active_session_id = session_id
        logger.info(f"Switched active session to '{self.active_session_name}' ({session_id})")
        return True

    def save_session(self, session_id: str) -> bool:
        """Saves session metadata and conversation history to local JSON file."""
        if session_id not in self._sessions:
            return False

        sess = self._sessions[session_id]
        sess["updated_at"] = datetime.now(timezone.utc).isoformat()
        file_path = self.sessions_dir / f"{session_id}.json"

        data = {
            "session_id": sess["session_id"],
            "name": sess["name"],
            "created_at": sess["created_at"],
            "updated_at": sess["updated_at"],
            "messages": sess["conversation"].to_list(),
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except OSError as e:
            logger.error(f"Failed to save session {session_id} to disk: {e}")
            return False

    def load_session(self, session_id: str) -> bool:
        """Loads a session from local JSON file into memory."""
        file_path = self.sessions_dir / f"{session_id}.json"
        if not file_path.exists():
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            conv = ConversationManager()
            conv.load_from_list(data.get("messages", []))

            self._sessions[session_id] = {
                "session_id": data.get("session_id", session_id),
                "name": data.get("name", session_id),
                "created_at": data.get("created_at", datetime.now(timezone.utc).isoformat()),
                "updated_at": data.get("updated_at", datetime.now(timezone.utc).isoformat()),
                "conversation": conv,
            }
            return True
        except Exception as e:
            logger.error(f"Failed to load session file {file_path}: {e}")
            return False

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        Lists all available sessions (both in-memory and on disk).
        """
        # Discover session files on disk
        for file in self.sessions_dir.glob("*.json"):
            sid = file.stem
            if sid not in self._sessions:
                self.load_session(sid)

        result: List[Dict[str, Any]] = []
        for sid, sess in self._sessions.items():
            result.append({
                "session_id": sid,
                "name": sess["name"],
                "is_active": (sid == self._active_session_id),
                "created_at": sess["created_at"],
                "updated_at": sess["updated_at"],
                "message_count": sess["conversation"].message_count,
            })
        return result

    def clear_session(self, session_id: str) -> bool:
        """Clears messages for specified session and updates disk file."""
        if session_id in self._sessions:
            self._sessions[session_id]["conversation"].clear()
            self.save_session(session_id)
            return True
        return False

    def _initialize_default_session(self) -> None:
        """Loads or initializes default session on startup."""
        if not self.load_session("default"):
            self.create_session("Default Session", session_id="default")
