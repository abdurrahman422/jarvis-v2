from __future__ import annotations

from app.data.db import get_connection


class TerminalRepository:
    """Persists safe terminal command history."""

    def ensure_schema(self) -> None:
        conn = get_connection()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS terminal_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_name TEXT,
                command TEXT NOT NULL,
                output TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        conn.close()

    def add(self, session_name: str, command: str, output: str) -> None:
        self.ensure_schema()
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO terminal_history(session_name, command, output)
            VALUES(?, ?, ?)
            """,
            (session_name, command, output),
        )
        conn.commit()
        conn.close()

    def latest(self, session_name: str, limit: int = 50) -> list[dict]:
        self.ensure_schema()
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT session_name, command, output, created_at
            FROM terminal_history
            WHERE session_name = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_name, limit),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]
