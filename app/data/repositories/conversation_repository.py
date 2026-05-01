from app.data.db import get_connection


class ConversationRepository:
    def add(self, role: str, text: str) -> None:
        conn = get_connection()
        conn.execute(
            "INSERT INTO conversation_history(role, text) VALUES(?, ?)",
            (role, text),
        )
        conn.commit()
        conn.close()

    def latest(self, limit: int = 50) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT role, text, created_at
            FROM conversation_history
            ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]
