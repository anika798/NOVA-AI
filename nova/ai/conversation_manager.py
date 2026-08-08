"""
NOVA Conversation History Manager
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger("NOVA.ConversationManager")


@dataclass
class Message:
    """Represents a single message turn in a conversation."""

    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            metadata=data.get("metadata", {}),
        )


class ConversationManager:
    """
    Manages in-memory message history and windowing for an active chat thread.
    """

    def __init__(self, max_history_messages: int = 50):
        self.max_history_messages = max_history_messages
        self._messages: List[Message] = []

    @property
    def message_count(self) -> int:
        return len(self._messages)

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """Appends a new message turn to conversation history."""
        msg = Message(role=role, content=content, metadata=metadata or {})
        self._messages.append(msg)
        self._trim_history()
        return msg

    def add_user_message(self, content: str) -> Message:
        return self.add_message("user", content)

    def add_assistant_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        return self.add_message("assistant", content, metadata)

    def add_system_message(self, content: str) -> Message:
        return self.add_message("system", content)

    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Returns message history formatted as dictionaries for Ollama payload:
        [{"role": "user", "content": "..."}, ...]
        """
        messages = self._messages if limit is None else self._messages[-limit:]
        return [{"role": m.role, "content": m.content} for m in messages]

    def get_raw_messages(self) -> List[Message]:
        return self._messages

    def clear(self) -> None:
        """Clears all conversation messages."""
        self._messages.clear()

    def to_list(self) -> List[Dict[str, Any]]:
        """Serializes messages to list of dictionaries for JSON storage."""
        return [m.to_dict() for m in self._messages]

    def load_from_list(self, data_list: List[Dict[str, Any]]) -> None:
        """Deserializes messages from list of dictionaries."""
        self._messages = [Message.from_dict(d) for d in data_list]

    def _trim_history(self) -> None:
        """Trims message buffer if it exceeds max history limits."""
        if len(self._messages) > self.max_history_messages:
            excess = len(self._messages) - self.max_history_messages
            self._messages = self._messages[excess:]
