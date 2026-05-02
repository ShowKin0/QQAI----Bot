import time
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Session:
    user_id: str
    messages: List[dict] = field(default_factory=list)
    last_active: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)


class SessionManager:
    """Manage per-user conversation sessions with expiry and max rounds."""

    def __init__(self, max_rounds: int = 10, expire_minutes: int = 30):
        self._sessions: Dict[str, Session] = {}
        self.max_rounds = max_rounds
        self.expire_seconds = expire_minutes * 60

    def get_or_create(self, user_id: str) -> Session:
        self._cleanup_expired()
        if user_id not in self._sessions:
            self._sessions[user_id] = Session(user_id=user_id)
        return self._sessions[user_id]

    def add_message(self, user_id: str, role: str, content: str) -> None:
        session = self.get_or_create(user_id)
        session.messages.append({"role": role, "content": content})
        session.last_active = time.time()
        max_messages = self.max_rounds * 2
        if len(session.messages) > max_messages:
            session.messages = session.messages[-max_messages:]

    def is_first_interaction(self, user_id: str) -> bool:
        session = self.get_or_create(user_id)
        return len(session.messages) == 0

    def get_history(self, user_id: str) -> List[dict]:
        session = self.get_or_create(user_id)
        return session.messages.copy()

    def clear(self, user_id: str) -> None:
        self._sessions.pop(user_id, None)

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired = [
            uid for uid, s in self._sessions.items()
            if now - s.last_active > self.expire_seconds
        ]
        for uid in expired:
            del self._sessions[uid]
