from app.data.db import get_connection


class SettingsRepository:
    def get(self, key: str, default: str = "") -> str:
        conn = get_connection()
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        conn.close()
        return row["value"] if row else default

    def set(self, key: str, value: str) -> None:
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO settings(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        conn.commit()
        conn.close()
