from app.data.db import get_connection


class CommandRepository:
    def add(
        self,
        raw_input: str,
        intent: str,
        action: str,
        result: str,
        confidence: float,
    ) -> None:
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO commands_log(raw_input, intent, action, result, confidence)
            VALUES(?, ?, ?, ?, ?)
            """,
            (raw_input, intent, action, result, confidence),
        )
        conn.commit()
        conn.close()
