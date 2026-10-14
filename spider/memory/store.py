import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from spider.core.config import settings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or settings.memory_database
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """
        Open a SQLite connection and ALWAYS close it.

        This is important on Windows because an open SQLite connection
        can keep the database file locked and prevent cleanup/deletion.
        """
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row

        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def initialize(self) -> None:
        with self.connection() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(conversation_id)
                        REFERENCES conversations(id)
                );

                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS project_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(project_id)
                        REFERENCES projects(id)
                );

                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                    ON messages(conversation_id);

                CREATE INDEX IF NOT EXISTS idx_memories_type
                    ON memories(memory_type);

                CREATE INDEX IF NOT EXISTS idx_memories_importance
                    ON memories(importance);
                """
            )

    def create_conversation(self, title: str | None = None) -> int:
        with self.connection() as db:
            cursor = db.execute(
                """
                INSERT INTO conversations(title, created_at)
                VALUES (?, ?)
                """,
                (title, utc_now()),
            )

            return int(cursor.lastrowid)

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
    ) -> int:
        with self.connection() as db:
            cursor = db.execute(
                """
                INSERT INTO messages(
                    conversation_id,
                    role,
                    content,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    role,
                    content,
                    utc_now(),
                ),
            )

            return int(cursor.lastrowid)

    def add_memory(
        self,
        content: str,
        memory_type: str = "fact",
        importance: int = 1,
    ) -> int:
        now = utc_now()

        with self.connection() as db:
            cursor = db.execute(
                """
                INSERT INTO memories(
                    memory_type,
                    content,
                    importance,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    memory_type,
                    content,
                    importance,
                    now,
                    now,
                ),
            )

            return int(cursor.lastrowid)

    def search_memories(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        terms = [
            part.strip().lower()
            for part in query.split()
            if part.strip()
        ]

        if not terms:
            return []

        with self.connection() as db:
            rows = db.execute(
                """
                SELECT
                    id,
                    memory_type,
                    content,
                    importance,
                    created_at,
                    updated_at
                FROM memories
                ORDER BY importance DESC, updated_at DESC
                LIMIT 100
                """
            ).fetchall()

        scored: list[tuple[int, sqlite3.Row]] = []

        for row in rows:
            content = str(row["content"]).lower()

            score = sum(
                1
                for term in terms
                if term in content
            )

            if score > 0:
                scored.append((score, row))

        scored.sort(
            key=lambda item: (
                item[0],
                item[1]["importance"],
            ),
            reverse=True,
        )

        return [
            dict(row)
            for _, row in scored[:limit]
        ]

    def get_recent_messages(
        self,
        conversation_id: int,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        with self.connection() as db:
            rows = db.execute(
                """
                SELECT
                    role,
                    content,
                    created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (
                    conversation_id,
                    limit,
                ),
            ).fetchall()

        return [
            dict(row)
            for row in reversed(rows)
        ]