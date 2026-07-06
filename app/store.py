"""Store abstraction (design.md §8).

An interface plus an in-memory implementation. DynamoDB (or SQLite) can be
dropped in later behind the same :class:`Store` protocol without touching the
API layer. The runtime tables mirror design.md §7: items, users, progress,
answers (rehearsal), sessions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.models import Item, Progress, RehearsalAnswer, Session, User


class Store(ABC):
    """Persistence interface. Swap in-memory for DynamoDB later."""

    # --- items (read-mostly, populated by ingest) ---
    @abstractmethod
    def put_item(self, item: Item) -> None: ...

    @abstractmethod
    def get_item(self, item_id: str) -> Optional[Item]: ...

    @abstractmethod
    def list_items(
        self, *, skill: Optional[str] = None, type: Optional[str] = None
    ) -> list[Item]: ...

    # --- users ---
    @abstractmethod
    def get_user(self, user_id: str) -> Optional[User]: ...

    @abstractmethod
    def put_user(self, user: User) -> None: ...

    # --- progress / SRS ---
    @abstractmethod
    def get_progress(self, user_id: str, item_id: str) -> Optional[Progress]: ...

    @abstractmethod
    def put_progress(self, progress: Progress) -> None: ...

    # --- rehearsal answers ---
    @abstractmethod
    def get_answer(self, user_id: str, item_id: str) -> Optional[RehearsalAnswer]: ...

    @abstractmethod
    def put_answer(self, answer: RehearsalAnswer) -> None: ...

    # --- sessions ---
    @abstractmethod
    def get_session(self, session_id: str) -> Optional[Session]: ...

    @abstractmethod
    def put_session(self, session: Session) -> None: ...


class InMemoryStore(Store):
    """Dict-backed store for local dev and tests."""

    def __init__(self) -> None:
        self.items: dict[str, Item] = {}
        self.users: dict[str, User] = {}
        self.progress: dict[tuple[str, str], Progress] = {}
        self.answers: dict[tuple[str, str], RehearsalAnswer] = {}
        self.sessions: dict[str, Session] = {}

    # items
    def put_item(self, item: Item) -> None:
        self.items[item.id] = item

    def get_item(self, item_id: str) -> Optional[Item]:
        return self.items.get(item_id)

    def list_items(
        self, *, skill: Optional[str] = None, type: Optional[str] = None
    ) -> list[Item]:
        out = list(self.items.values())
        if skill is not None:
            out = [i for i in out if i.skill == skill]
        if type is not None:
            out = [i for i in out if i.type == type]
        return out

    # users
    def get_user(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)

    def put_user(self, user: User) -> None:
        self.users[user.id] = user

    # progress
    def get_progress(self, user_id: str, item_id: str) -> Optional[Progress]:
        return self.progress.get((user_id, item_id))

    def put_progress(self, progress: Progress) -> None:
        self.progress[(progress.user_id, progress.item_id)] = progress

    # answers
    def get_answer(self, user_id: str, item_id: str) -> Optional[RehearsalAnswer]:
        return self.answers.get((user_id, item_id))

    def put_answer(self, answer: RehearsalAnswer) -> None:
        self.answers[(answer.user_id, answer.item_id)] = answer

    # sessions
    def get_session(self, session_id: str) -> Optional[Session]:
        return self.sessions.get(session_id)

    def put_session(self, session: Session) -> None:
        self.sessions[session.id] = session
