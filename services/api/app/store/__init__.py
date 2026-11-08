"""Storage. v1 dev uses memory; production uses Postgres in an India region with
field-level encryption of health data (see docs/privacy/data-map.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from ritu_engine import CycleRecord


@dataclass
class User:
    wa_id: str
    language: str | None = None
    consented_at: datetime | None = None
    record: CycleRecord = field(default_factory=CycleRecord)
    pending: dict = field(default_factory=dict)  # follow-up questions in flight, e.g. pain score
    alerted_codes: set[str] = field(default_factory=set)  # urgent alerts already sent this episode


class Store(Protocol):
    def get_or_create(self, wa_id: str) -> User: ...
    def save(self, user: User) -> None: ...
    def delete(self, wa_id: str) -> None: ...
    def seen_message(self, message_id: str) -> bool: ...


class MemoryStore:
    """Dev/test store. Not for production: no encryption, no persistence."""

    def __init__(self) -> None:
        self._users: dict[str, User] = {}
        self._seen: set[str] = set()

    def get_or_create(self, wa_id: str) -> User:
        return self._users.setdefault(wa_id, User(wa_id=wa_id))

    def save(self, user: User) -> None:
        self._users[user.wa_id] = user

    def delete(self, wa_id: str) -> None:
        self._users.pop(wa_id, None)

    def exists(self, wa_id: str) -> bool:
        return wa_id in self._users

    def seen_message(self, message_id: str) -> bool:
        """WhatsApp retries webhooks; process each message id once."""
        if message_id in self._seen:
            return True
        self._seen.add(message_id)
        return False
