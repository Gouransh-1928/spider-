import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from spider.core.config import settings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConfirmationStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or settings.memory_database
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connection() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_confirmations (
                    id TEXT PRIMARY KEY,
                    conversation_id INTEGER NOT NULL,
                    tool_name TEXT NOT NULL,
                    arguments TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                )
                """
            )

    def create(
        self,
        conversation_id: int,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        confirmation_id = str(uuid.uuid4())

        with self.connection() as db:
            db.execute(
                """
                INSERT INTO pending_confirmations(
                    id,
                    conversation_id,
                    tool_name,
                    arguments,
                    created_at,
                    status
                )
                VALUES (?, ?, ?, ?, ?, 'pending')
                """,
                (
                    confirmation_id,
                    conversation_id,
                    tool_name,
                    json.dumps(arguments),
                    utc_now(),
                ),
            )

        return confirmation_id

    def get(self, confirmation_id: str) -> dict[str, Any] | None:
        with self.connection() as db:
            row = db.execute(
                """
                SELECT *
                FROM pending_confirmations
                WHERE id = ?
                  AND status = 'pending'
                """,
                (confirmation_id,),
            ).fetchone()

        if row is None:
            return None

        result = dict(row)
        result["arguments"] = json.loads(result["arguments"])
        return result

    def mark_approved(self, confirmation_id: str) -> bool:
        with self.connection() as db:
            cursor = db.execute(
                """
                UPDATE pending_confirmations
                SET status = 'approved'
                WHERE id = ?
                  AND status = 'pending'
                """,
                (confirmation_id,),
            )

        return cursor.rowcount == 1

    def mark_rejected(self, confirmation_id: str) -> bool:
        with self.connection() as db:
            cursor = db.execute(
                """
                UPDATE pending_confirmations
                SET status = 'rejected'
                WHERE id = ?
                  AND status = 'pending'
                """,
                (confirmation_id,),
            )

        return cursor.rowcount == 1