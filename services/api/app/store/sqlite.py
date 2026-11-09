"""Encrypted persistent store (SQLite).

Health data is encrypted at rest with Fernet (AES-128-CBC + HMAC) before it
touches disk. The phone number is never a column: rows are keyed by an HMAC of
it, and the real number lives only inside the encrypted blob. Message ids used
for de-duplication are stored hashed, and purged after a week.

SQLite is fine for a pilot on one server. For scale, keep this interface and
swap the body for Postgres in an India region (see docs/privacy/data-map.md).
Keep the key outside the database host (secret manager, not the repo).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import threading
import time
from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken
from cycle_engine import record_from_data, record_to_data

from . import User

SEEN_TTL_SECONDS = 7 * 24 * 3600


class SqliteStore:
    def __init__(self, path: str, key: str) -> None:
        if not key:
            raise ValueError("STORE_KEY is required for the persistent store (generate with: python -m app.store.sqlite genkey)")
        self._fernet = Fernet(key.encode())
        self._hmac_key = hashlib.sha256(b"index:" + key.encode()).digest()
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, blob BLOB NOT NULL)")
        self._db.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY, ts REAL NOT NULL)")
        self._db.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v BLOB NOT NULL)")
        self._check_key()
        self._db.commit()

    def _check_key(self) -> None:
        """Refuse to start with the wrong key. Otherwise lookups (keyed by an HMAC of the key)
        would all miss and every user would look brand new, silently losing their history."""
        row = self._db.execute("SELECT v FROM meta WHERE k = 'canary'").fetchone()
        if row is None:
            self._db.execute("INSERT INTO meta (k, v) VALUES ('canary', ?)", (self._fernet.encrypt(b"ok"),))
            return
        try:
            self._fernet.decrypt(row[0])
        except InvalidToken as exc:
            raise RuntimeError("STORE_KEY does not match this database. Refusing to start.") from exc

    # ---- helpers -------------------------------------------------------------
    def _index(self, value: str) -> str:
        return hmac.new(self._hmac_key, value.encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def _pack(user: User) -> bytes:
        return json.dumps(
            {
                "wa_id": user.wa_id,
                "language": user.language,
                "consented_at": user.consented_at.isoformat() if user.consented_at else None,
                "record": record_to_data(user.record),
                "pending": user.pending,
                "alerted_codes": sorted(user.alerted_codes),
                "discreet": user.discreet,
                "nudged_for": user.nudged_for,
            }
        ).encode()

    @staticmethod
    def _unpack(raw: bytes) -> User:
        d = json.loads(raw)
        return User(
            wa_id=d["wa_id"],
            language=d["language"],
            consented_at=datetime.fromisoformat(d["consented_at"]) if d["consented_at"] else None,
            record=record_from_data(d["record"]),
            pending=d["pending"],
            alerted_codes=set(d["alerted_codes"]),
            discreet=d.get("discreet", False),  # rows saved before these fields existed
            nudged_for=d.get("nudged_for"),
        )

    # ---- Store protocol --------------------------------------------------------
    def get_or_create(self, wa_id: str) -> User:
        with self._lock:
            row = self._db.execute("SELECT blob FROM users WHERE id = ?", (self._index(wa_id),)).fetchone()
        if row is None:
            return User(wa_id=wa_id)
        try:
            return self._unpack(self._fernet.decrypt(row[0]))
        except InvalidToken as exc:
            raise RuntimeError("Cannot decrypt stored data: wrong STORE_KEY?") from exc

    def save(self, user: User) -> None:
        blob = self._fernet.encrypt(self._pack(user))
        with self._lock:
            self._db.execute(
                "INSERT INTO users (id, blob) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET blob = excluded.blob",
                (self._index(user.wa_id), blob),
            )
            self._db.commit()

    def delete(self, wa_id: str) -> None:
        with self._lock:
            self._db.execute("DELETE FROM users WHERE id = ?", (self._index(wa_id),))
            self._db.commit()

    def exists(self, wa_id: str) -> bool:
        with self._lock:
            return self._db.execute("SELECT 1 FROM users WHERE id = ?", (self._index(wa_id),)).fetchone() is not None

    def seen_message(self, message_id: str) -> bool:
        now = time.time()
        with self._lock:
            self._db.execute("DELETE FROM seen WHERE ts < ?", (now - SEEN_TTL_SECONDS,))
            cur = self._db.execute("INSERT OR IGNORE INTO seen (id, ts) VALUES (?, ?)", (self._index(message_id), now))
            self._db.commit()
            return cur.rowcount == 0

    def close(self) -> None:
        self._db.close()


if __name__ == "__main__":
    import sys

    if sys.argv[1:] == ["genkey"]:
        print(Fernet.generate_key().decode())
    else:
        print("usage: python -m app.store.sqlite genkey")
