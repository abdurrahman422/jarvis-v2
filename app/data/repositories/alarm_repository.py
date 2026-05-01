from app.data.db import get_connection


class AlarmRepository:
    def add(self, title: str, due_at: str, recurrence: str = "none") -> None:
        conn = get_connection()
        conn.execute(
            "INSERT INTO alarms_tasks(title, due_at, recurrence) VALUES(?, ?, ?)",
            (title, due_at, recurrence),
        )
        conn.commit()
        conn.close()

    def list_all(self) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT id, title, due_at, status, recurrence FROM alarms_tasks ORDER BY due_at"
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def remove(self, alarm_id: int) -> bool:
        conn = get_connection()
        cur = conn.execute("DELETE FROM alarms_tasks WHERE id = ?", (alarm_id,))
        conn.commit()
        conn.close()
        return cur.rowcount > 0

    def mark_done(self, alarm_id: int) -> bool:
        conn = get_connection()
        cur = conn.execute(
            "UPDATE alarms_tasks SET status = 'done' WHERE id = ?",
            (alarm_id,),
        )
        conn.commit()
        conn.close()
        return cur.rowcount > 0
