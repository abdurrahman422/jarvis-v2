from app.data.db import get_connection


class TimeManagementRepository:
    TASK_PREFIX = "TASK:"

    def add_task(self, task: str) -> None:
        conn = get_connection()
        conn.execute(
            "INSERT INTO memory_notes(note) VALUES(?)",
            (f"{self.TASK_PREFIX}{task.strip()}",),
        )
        conn.commit()
        conn.close()

    def list_tasks(self, limit: int = 20) -> list[str]:
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT note
            FROM memory_notes
            WHERE note LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (f"{self.TASK_PREFIX}%", limit),
        ).fetchall()
        conn.close()
        return [str(row["note"]).replace(self.TASK_PREFIX, "", 1) for row in rows]

    def list_all(self) -> list[dict]:
        """Return all tasks as list of dicts with title/key."""
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT note
            FROM memory_notes
            WHERE note LIKE ?
            ORDER BY id DESC
            LIMIT 20
            """,
            (f"{self.TASK_PREFIX}%",),
        ).fetchall()
        conn.close()
        return [{"title": str(row["note"]).replace(self.TASK_PREFIX, "", 1)} for row in rows]
