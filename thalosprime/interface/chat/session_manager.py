"""
Session Manager — lifecycle management for chat sessions (Section 24.6).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from thalosprime.interface.chat.context_tracker import ContextTracker
from thalosprime.interface.chat.query_parser import QueryParser


@dataclass
class ChatSession:
    """A single user session with its own context and query history."""

    session_id: str
    created_at: int
    context: ContextTracker = field(default_factory=ContextTracker)
    query_history: list[str] = field(default_factory=list)

    def record_query(self, user_input: str) -> None:
        self.query_history.append(user_input)


class SessionManager:
    """
    Creates, retrieves, and expires chat sessions.

    Each session is isolated; belief-base mutations require explicit
    admission through the validation pipeline.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, ChatSession] = {}
        self._parser = QueryParser()

    def create_session(self) -> ChatSession:
        session_id = str(uuid.uuid4())
        session = ChatSession(
            session_id=session_id,
            created_at=int(time.time()),
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> ChatSession | None:
        return self._sessions.get(session_id)

    def close_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session:
            session.context.clear()

    @property
    def active_sessions(self) -> list[str]:
        return list(self._sessions.keys())
