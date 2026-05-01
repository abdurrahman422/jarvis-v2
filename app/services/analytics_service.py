from __future__ import annotations

from datetime import datetime

try:
    import psutil
except Exception:  # pragma: no cover - psutil is optional at runtime
    psutil = None

from app.data.analytics_repository import AnalyticsRepository


class AnalyticsService:
    """Builds Analytics page data from real persisted app data and live system metrics."""

    def __init__(self, repository: AnalyticsRepository | None = None) -> None:
        self.repository = repository or AnalyticsRepository()

    def get_dashboard(self) -> dict:
        data = self.repository.snapshot()
        commands = data["commands"]
        tasks = data["tasks"]
        events = data["events"]
        total_work = commands["total"] + tasks["total"]
        completed = max(commands["total"] - commands["errors"], 0) + tasks["completed"] + events["success"]
        pending = tasks["pending"]
        failed = commands["errors"] + events["error"]
        success_rate = 0 if total_work + events["total"] == 0 else round(completed / max(total_work + events["total"], 1) * 100)

        categories = data["categories"]
        top_actions = data["top_actions"]

        return {
            "summary": {
                "total_work": total_work,
                "completed": completed,
                "pending": pending,
                "failed": failed,
                "success_rate": min(max(success_rate, 0), 100),
                "total_chats": data["conversation"]["total"],
                "user_messages": data["conversation"]["user"],
                "assistant_replies": data["conversation"]["assistant"],
                "voice_commands": commands["voice"],
                "drafts_generated": commands["drafts"],
                "api_calls": commands["api"],
                "automation_actions": commands["total"],
            },
            "hourly_usage": data["hourly_usage"],
            "categories": categories,
            "agent_activity": self._agent_activity(categories),
            "top_actions": top_actions,
            "recent_activity": data["recent_activity"],
            "system": self._system_metrics(),
        }

    def log_event(self, *args, **kwargs) -> None:
        self.repository.log_event(*args, **kwargs)

    def _agent_activity(self, categories: list[dict]) -> list[dict]:
        if not categories:
            return []
        mapping = {
            "Automation": "Task Agent",
            "Tasks": "Task Agent",
            "File Operations": "File Agent",
            "Communication": "Comm Agent",
            "AI/API": "Brain Agent",
            "System": "System Agent",
        }
        totals: dict[str, int] = {}
        for item in categories:
            agent = mapping.get(item["name"], "System Agent")
            totals[agent] = totals.get(agent, 0) + int(item["count"])
        whole = sum(totals.values())
        return [
            {"name": name, "count": count, "percent": round(count / whole * 100) if whole else 0}
            for name, count in sorted(totals.items(), key=lambda pair: pair[1], reverse=True)
        ]

    def _system_metrics(self) -> dict:
        if psutil is None:
            return {
                "cpu_percent": 0,
                "memory_percent": 0,
                "memory_used_gb": 0.0,
                "memory_total_gb": 0.0,
                "disk_percent": 0,
                "disk_used_gb": 0.0,
                "disk_total_gb": 0.0,
                "boot_uptime": "Unavailable",
                "connection": "Unknown",
                "data_sync": "Active",
                "last_sync": datetime.now().strftime("%H:%M:%S"),
            }

        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        uptime_seconds = max(0, int(datetime.now().timestamp() - psutil.boot_time()))
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        return {
            "cpu_percent": int(psutil.cpu_percent(interval=None)),
            "memory_percent": int(memory.percent),
            "memory_used_gb": round(memory.used / (1024 ** 3), 1),
            "memory_total_gb": round(memory.total / (1024 ** 3), 1),
            "disk_percent": int(disk.percent),
            "disk_used_gb": round(disk.used / (1024 ** 3), 1),
            "disk_total_gb": round(disk.total / (1024 ** 3), 1),
            "boot_uptime": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            "connection": "Secure",
            "data_sync": "Active",
            "last_sync": datetime.now().strftime("%H:%M:%S"),
        }
