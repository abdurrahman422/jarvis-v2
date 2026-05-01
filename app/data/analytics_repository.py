from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from app.data.db import get_connection


class AnalyticsRepository:
    """Read and write persisted analytics data."""

    def ensure_schema(self) -> None:
        conn = get_connection()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                source TEXT DEFAULT '',
                action TEXT DEFAULT '',
                status TEXT DEFAULT 'success',
                message TEXT DEFAULT '',
                metadata TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        conn.close()

    def log_event(
        self,
        event_type: str,
        *,
        source: str = "",
        action: str = "",
        status: str = "success",
        message: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.ensure_schema()
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO analytics_events(event_type, source, action, status, message, metadata)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                source,
                action,
                status,
                message,
                json.dumps(metadata or {}, ensure_ascii=False),
            ),
        )
        conn.commit()
        conn.close()

    def snapshot(self) -> dict:
        self.ensure_schema()
        conn = get_connection()
        try:
            return {
                "conversation": self._conversation_counts(conn),
                "commands": self._command_counts(conn),
                "tasks": self._task_counts(conn),
                "events": self._event_counts(conn),
                "hourly_usage": self._hourly_usage(conn),
                "categories": self._categories(conn),
                "top_actions": self._top_actions(conn),
                "recent_activity": self._recent_activity(conn),
            }
        finally:
            conn.close()

    def _one(self, conn, sql: str, params: tuple = ()) -> int:
        row = conn.execute(sql, params).fetchone()
        if row is None:
            return 0
        return int(row[0] or 0)

    def _conversation_counts(self, conn) -> dict:
        return {
            "total": self._one(conn, "SELECT COUNT(*) FROM conversation_history"),
            "user": self._one(conn, "SELECT COUNT(*) FROM conversation_history WHERE role = 'user'"),
            "assistant": self._one(conn, "SELECT COUNT(*) FROM conversation_history WHERE role = 'assistant'"),
        }

    def _command_counts(self, conn) -> dict:
        total = self._one(conn, "SELECT COUNT(*) FROM commands_log")
        api = self._one(conn, "SELECT COUNT(*) FROM commands_log WHERE action LIKE 'brain.%'")
        voice = self._one(conn, "SELECT COUNT(*) FROM analytics_events WHERE event_type = 'voice_command'")
        drafts = self._one(
            conn,
            """
            SELECT COUNT(*)
            FROM commands_log
            WHERE lower(action) LIKE '%email%'
               OR lower(raw_input) LIKE '%draft%'
               OR lower(raw_input) LIKE '%email%'
            """,
        )
        errors = self._one(
            conn,
            """
            SELECT COUNT(*)
            FROM commands_log
            WHERE lower(result) LIKE '%error%'
               OR lower(result) LIKE '%failed%'
               OR lower(result) LIKE '%trouble%'
               OR action = 'system.stt_failure'
            """,
        )
        errors += self._one(conn, "SELECT COUNT(*) FROM analytics_events WHERE status = 'error'")
        return {"total": total, "api": api, "voice": voice, "drafts": drafts, "errors": errors}

    def _task_counts(self, conn) -> dict:
        alarms_total = self._one(conn, "SELECT COUNT(*) FROM alarms_tasks")
        alarms_done = self._one(conn, "SELECT COUNT(*) FROM alarms_tasks WHERE status IN ('done', 'completed')")
        memory_tasks = self._one(conn, "SELECT COUNT(*) FROM memory_notes WHERE note LIKE 'TASK:%'")
        pending = max(alarms_total - alarms_done, 0) + memory_tasks
        return {"total": alarms_total + memory_tasks, "completed": alarms_done, "pending": pending}

    def _event_counts(self, conn) -> dict:
        return {
            "total": self._one(conn, "SELECT COUNT(*) FROM analytics_events"),
            "success": self._one(conn, "SELECT COUNT(*) FROM analytics_events WHERE status = 'success'"),
            "error": self._one(conn, "SELECT COUNT(*) FROM analytics_events WHERE status = 'error'"),
        }

    def _hourly_usage(self, conn) -> list[int]:
        now = datetime.now()
        buckets = [0] * 24
        since = (now - timedelta(hours=23)).strftime("%Y-%m-%d %H:00:00")
        rows = conn.execute(
            """
            SELECT strftime('%Y-%m-%d %H:00:00', created_at) AS bucket, COUNT(*) AS count
            FROM commands_log
            WHERE created_at >= ?
            GROUP BY bucket
            """,
            (since,),
        ).fetchall()
        counts = {str(row["bucket"]): int(row["count"] or 0) for row in rows}
        for index in range(24):
            hour = (now - timedelta(hours=23 - index)).strftime("%Y-%m-%d %H:00:00")
            buckets[index] = counts.get(hour, 0)
        return buckets

    def _categories(self, conn) -> list[dict]:
        rows = conn.execute(
            """
            SELECT action, COUNT(*) AS count
            FROM commands_log
            GROUP BY action
            ORDER BY count DESC
            """
        ).fetchall()
        counts: Counter[str] = Counter()
        for row in rows:
            action = str(row["action"] or "unknown")
            counts[self._category_for_action(action)] += int(row["count"] or 0)
        total = sum(counts.values())
        if total == 0:
            return []
        return [
            {"name": name, "count": count, "percent": round(count / total * 100)}
            for name, count in counts.most_common()
        ]

    def _top_actions(self, conn) -> list[dict]:
        rows = conn.execute(
            """
            SELECT action, COUNT(*) AS count,
                   SUM(CASE WHEN lower(result) LIKE '%error%'
                              OR lower(result) LIKE '%failed%'
                              OR lower(result) LIKE '%trouble%'
                            THEN 1 ELSE 0 END) AS failures
            FROM commands_log
            WHERE action IS NOT NULL AND action != ''
            GROUP BY action
            ORDER BY count DESC
            LIMIT 5
            """
        ).fetchall()
        out = []
        for row in rows:
            count = int(row["count"] or 0)
            failures = int(row["failures"] or 0)
            success_rate = 0 if count <= 0 else round(max(count - failures, 0) / count * 100)
            out.append({"name": str(row["action"]), "count": count, "success_rate": success_rate})
        return out

    def _recent_activity(self, conn) -> list[dict]:
        rows = conn.execute(
            """
            SELECT created_at, raw_input AS message, action, result
            FROM commands_log
            ORDER BY id DESC
            LIMIT 6
            """
        ).fetchall()
        out = []
        for row in rows:
            result = str(row["result"] or "")
            failed = any(token in result.lower() for token in ("error", "failed", "trouble"))
            out.append(
                {
                    "time": str(row["created_at"] or ""),
                    "message": str(row["message"] or ""),
                    "action": str(row["action"] or ""),
                    "status": "ERROR" if failed else "SUCCESS",
                }
            )
        return out

    def _category_for_action(self, action: str) -> str:
        action = action.lower()
        if action.startswith("brain."):
            return "AI/API"
        if "file" in action or "desktop" in action or "ocr" in action:
            return "File Operations"
        if "whatsapp" in action or "email" in action or "voice" in action or "stt" in action:
            return "Communication"
        if "music" in action or "youtube" in action or "automation" in action:
            return "Automation"
        if action.startswith("system.") or action.startswith("network.") or action.startswith("weather."):
            return "System"
        if action.startswith("scheduler.") or action.startswith("time."):
            return "Tasks"
        return "Other"
