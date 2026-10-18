"""Fast replay hints plus authoritative atomic replay stores."""

from __future__ import annotations

import sqlite3
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ReplayRecord:
    message_id: str
    session_id: str
    accepted_at: datetime
    expires_at: datetime


class ReplayStore(Protocol):
    def check_ready(self) -> bool: ...

    def get(self, message_id: str, now: datetime) -> ReplayRecord | None: ...

    def commit(
        self,
        message_id: str,
        session_id: str,
        now: datetime,
        ttl: timedelta,
    ) -> bool: ...


class FastReplayCache(Protocol):
    def might_contain(self, message_id: str) -> bool: ...

    def add(self, message_id: str) -> None: ...


class InMemoryFastReplayCache:
    def __init__(self, max_entries: int = 100_000) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self.max_entries = max_entries
        self._ids: set[str] = set()
        self._order: deque[str] = deque()
        self._lock = threading.Lock()

    def might_contain(self, message_id: str) -> bool:
        with self._lock:
            return message_id in self._ids

    def add(self, message_id: str) -> None:
        with self._lock:
            if message_id in self._ids:
                return
            self._ids.add(message_id)
            self._order.append(message_id)
            while len(self._order) > self.max_entries:
                self._ids.discard(self._order.popleft())


class InMemoryReplayStore:
    def __init__(self) -> None:
        self._records: dict[str, ReplayRecord] = {}
        self._lock = threading.Lock()

    def _purge(self, now: datetime) -> None:
        expired = [
            message_id
            for message_id, record in self._records.items()
            if record.expires_at <= now
        ]
        for message_id in expired:
            del self._records[message_id]

    def check_ready(self) -> bool:
        return True

    def get(self, message_id: str, now: datetime) -> ReplayRecord | None:
        with self._lock:
            self._purge(now)
            return self._records.get(message_id)

    def commit(
        self,
        message_id: str,
        session_id: str,
        now: datetime,
        ttl: timedelta,
    ) -> bool:
        with self._lock:
            self._purge(now)
            if message_id in self._records:
                return False
            self._records[message_id] = ReplayRecord(
                message_id=message_id,
                session_id=session_id,
                accepted_at=now,
                expires_at=now + ttl,
            )
            return True


class SQLiteReplayStore:
    """Persistent replay store with a database-enforced unique message ID."""

    def __init__(self, path: str | Path, *, timeout_seconds: float = 10.0) -> None:
        self.path = Path(path)
        self.timeout_seconds = timeout_seconds
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=self.timeout_seconds,
            isolation_level=None,
        )
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS replay_ids (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    accepted_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )

    def check_ready(self) -> bool:
        try:
            with self._connect() as connection:
                return connection.execute("SELECT 1").fetchone() == (1,)
        except sqlite3.Error:
            return False

    @staticmethod
    def _iso(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds")

    @staticmethod
    def _datetime(value: str) -> datetime:
        return datetime.fromisoformat(value).astimezone(timezone.utc)

    def get(self, message_id: str, now: datetime) -> ReplayRecord | None:
        now_value = self._iso(now)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM replay_ids WHERE expires_at <= ?", (now_value,))
            row = connection.execute(
                """
                SELECT message_id, session_id, accepted_at, expires_at
                FROM replay_ids
                WHERE message_id = ?
                """,
                (message_id,),
            ).fetchone()
            connection.commit()
        if row is None:
            return None
        return ReplayRecord(
            message_id=row[0],
            session_id=row[1],
            accepted_at=self._datetime(row[2]),
            expires_at=self._datetime(row[3]),
        )

    def commit(
        self,
        message_id: str,
        session_id: str,
        now: datetime,
        ttl: timedelta,
    ) -> bool:
        now_value = self._iso(now)
        expires_at = self._iso(now + ttl)
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "DELETE FROM replay_ids WHERE expires_at <= ?",
                    (now_value,),
                )
                connection.execute(
                    """
                    INSERT INTO replay_ids(message_id, session_id, accepted_at, expires_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (message_id, session_id, now_value, expires_at),
                )
                connection.commit()
                return True
            except sqlite3.IntegrityError:
                connection.rollback()
                return False
