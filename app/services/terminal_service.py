from __future__ import annotations

import gc
import ipaddress
import platform
import socket
import subprocess
import sys
import time
from pathlib import Path

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None

from app.app_paths import DATA_DIR, LOGS_DIR, PROJECT_ROOT
from app.data.db import get_connection
from app.data.repositories.settings_repository import SettingsRepository
from app.data.terminal_repository import TerminalRepository


APP_NAME = "CPA Neural Interface"
APP_VERSION = "V1.0"


class SafeTerminalService:
    """Backend for the Jarvis terminal page.

    This service intentionally does not expose a general Windows shell. Only the
    commands in ALLOWED_COMMANDS are supported.
    """

    BLOCKED_PREFIXES = (
        "del",
        "erase",
        "rm",
        "rmdir",
        "format",
        "shutdown",
        "restart",
        "regedit",
        "reg ",
        "taskkill",
        "powershell",
        "pwsh",
        "cmd",
        "sudo",
    )

    ALLOWED_COMMANDS = (
        "help",
        "clear",
        "status",
        "systeminfo",
        "cpu",
        "memory",
        "disk",
        "battery",
        "network",
        "ip",
        "ping <host>",
        "logs",
        "diagnostics",
        "memory clean",
        "clear cache",
        "uptime",
        "version",
        "model",
        "voice status",
        "neural link status",
    )

    def __init__(self, controller=None, repository: TerminalRepository | None = None) -> None:
        self.controller = controller
        self.repository = repository or TerminalRepository()
        self.repository.ensure_schema()
        self._app_started = time.time()

    def execute(self, command: str, session_id: str = "Terminal 1") -> str:
        command = (command or "").strip()
        if not command:
            return ""

        lowered = command.lower()
        if self._is_dangerous(lowered):
            output = "Blocked: this terminal only supports safe Jarvis commands. Type 'help' for allowed commands."
            self._save(session_id, command, output)
            return output

        try:
            output = self._execute_safe(lowered, command)
        except Exception as exc:
            output = f"Terminal command failed: {exc}"

        if output:
            self._save(session_id, command, output)
        return output

    def clear_session(self, session_id: str) -> str:
        return self.banner()

    def banner(self) -> str:
        return (
            f"[{APP_NAME} Terminal]\n"
            f"{platform.system()} {platform.release()} {platform.version()} | {APP_NAME} {APP_VERSION}\n"
            "Type 'help' to see available safe commands.\n"
        )

    def get_system_snapshot(self) -> dict:
        if psutil is None:
            return {
                "cpu_percent": 0,
                "memory_text": "psutil unavailable",
                "memory_percent": 0,
                "uptime": self._format_seconds(time.time() - self._app_started),
                "connection": self._connection_status(),
            }
        mem = psutil.virtual_memory()
        return {
            "cpu_percent": int(psutil.cpu_percent(interval=None)),
            "memory_text": f"{mem.used / (1024 ** 3):.1f} GB / {mem.total / (1024 ** 3):.1f} GB",
            "memory_percent": int(mem.percent),
            "uptime": self._format_seconds(time.time() - self._app_started),
            "connection": self._connection_status(),
        }

    def get_voice_snapshot(self) -> dict:
        if self.controller is None:
            return {"online": False, "voice_status": "UNKNOWN", "listening": False}
        stt_ok = bool(getattr(self.controller, "stt", None))
        tts_ok = bool(getattr(self.controller, "tts", None))
        voice_enabled = False
        try:
            voice_enabled = self.controller.is_voice_reply_enabled()
        except Exception:
            pass
        status = "READY" if stt_ok and tts_ok else "UNAVAILABLE"
        return {"online": True, "voice_status": status, "voice_reply_enabled": voice_enabled, "listening": False}

    def _execute_safe(self, lowered: str, original: str) -> str:
        if lowered == "help":
            return self._help()
        if lowered == "clear":
            return ""
        if lowered in {"status", "systeminfo"}:
            return self._systeminfo()
        if lowered == "cpu":
            return self._cpu()
        if lowered == "memory":
            return self._memory()
        if lowered == "disk":
            return self._disk()
        if lowered == "battery":
            return self._battery()
        if lowered == "network":
            return self._network()
        if lowered == "ip":
            return self._ip()
        if lowered.startswith("ping "):
            return self._ping(original.split(maxsplit=1)[1].strip())
        if lowered == "logs":
            return self._logs()
        if lowered == "diagnostics":
            return self._diagnostics()
        if lowered == "memory clean":
            return self._memory_clean()
        if lowered == "clear cache":
            return self._clear_cache()
        if lowered == "uptime":
            return f"App Uptime: {self.get_system_snapshot()['uptime']}\nSystem Uptime: {self._system_uptime()}"
        if lowered == "version":
            return f"{APP_NAME}: {APP_VERSION}\nPython: {sys.version.split()[0]}\nQt App: PySide6 desktop"
        if lowered == "model":
            return self._model()
        if lowered == "voice status":
            return self._voice_status()
        if lowered == "neural link status":
            return self._neural_link_status()
        return "Unknown command. Type 'help' for allowed commands."

    def _help(self) -> str:
        return "Allowed commands:\n" + "\n".join(f"  - {cmd}" for cmd in self.ALLOWED_COMMANDS)

    def _systeminfo(self) -> str:
        snapshot = self.get_system_snapshot()
        lines = [
            f"System Name              : {platform.node() or 'Unknown'}",
            f"OS                       : {platform.platform()}",
            f"Python                   : {sys.version.split()[0]}",
            f"App                      : {APP_NAME} {APP_VERSION}",
            f"App Uptime               : {snapshot['uptime']}",
            f"System Uptime            : {self._system_uptime()}",
            f"CPU Usage                : {snapshot['cpu_percent']}%",
            f"Memory Usage             : {snapshot['memory_text']} ({snapshot['memory_percent']}%)",
            f"Disk Usage               : {self._disk_summary()}",
            f"Battery                  : {self._battery_summary()}",
            f"Connection               : {snapshot['connection']}",
        ]
        return "\n".join(lines)

    def _cpu(self) -> str:
        if psutil is None:
            return self._psutil_missing()
        return f"CPU Usage: {int(psutil.cpu_percent(interval=0.2))}%\nCPU Cores: {psutil.cpu_count(logical=True)} logical"

    def _memory(self) -> str:
        if psutil is None:
            return self._psutil_missing()
        mem = psutil.virtual_memory()
        return (
            f"Memory Used: {mem.used / (1024 ** 3):.2f} GB\n"
            f"Memory Total: {mem.total / (1024 ** 3):.2f} GB\n"
            f"Memory Usage: {mem.percent}%"
        )

    def _disk(self) -> str:
        if psutil is None:
            return self._psutil_missing()
        disk = psutil.disk_usage(str(PROJECT_ROOT.anchor or Path.cwd().anchor or "/"))
        return (
            f"Disk Used: {disk.used / (1024 ** 3):.1f} GB\n"
            f"Disk Total: {disk.total / (1024 ** 3):.1f} GB\n"
            f"Disk Usage: {disk.percent}%"
        )

    def _battery(self) -> str:
        return f"Battery: {self._battery_summary()}"

    def _network(self) -> str:
        return f"Connection: {self._connection_status()}\nIP Addresses:\n{self._ip()}"

    def _ip(self) -> str:
        addresses = []
        if psutil is not None:
            for name, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if getattr(addr, "family", None) == socket.AF_INET and not addr.address.startswith("127."):
                        addresses.append(f"{name}: {addr.address}")
        if not addresses:
            try:
                addresses.append(f"Host: {socket.gethostbyname(socket.gethostname())}")
            except OSError:
                pass
        return "\n".join(addresses) if addresses else "No active IP address found."

    def _ping(self, host: str) -> str:
        host = host.strip()
        if not host:
            return "Usage: ping <host>"
        if not self._safe_host(host):
            return "Blocked: invalid host."
        try:
            cmd = ["ping", "-n", "2", host] if platform.system().lower() == "windows" else ["ping", "-c", "2", host]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=8, check=False)
            output = (proc.stdout or proc.stderr or "").strip()
            return output if output else f"Ping exited with code {proc.returncode}."
        except Exception as exc:
            return f"Ping failed: {exc}"

    def _logs(self) -> str:
        log_file = LOGS_DIR / "app.log"
        if not log_file.exists():
            return "No logs found yet."
        try:
            lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            return f"Could not read logs: {exc}"
        if not lines:
            return "No logs found yet."
        return "\n".join(lines[-80:])

    def _diagnostics(self) -> str:
        checks = []
        checks.append(("Database connection", self._check_database()))
        checks.append(("Settings repository", self._check_settings()))
        checks.append(("AI provider config", self._check_ai_provider()))
        checks.append(("STT service", self._check_attr("stt")))
        checks.append(("TTS service", self._check_attr("tts")))
        checks.append(("Internet connection", self._check_internet()))
        checks.append(("Log file", "PASS" if (LOGS_DIR / "app.log").exists() else "UNKNOWN"))
        return "\n".join(f"{name:<24}: {status}" for name, status in checks)

    def _memory_clean(self) -> str:
        before = self.get_system_snapshot()
        collected = gc.collect()
        after = self.get_system_snapshot()
        return (
            f"Python GC collected objects: {collected}\n"
            f"Memory before: {before['memory_text']} ({before['memory_percent']}%)\n"
            f"Memory after : {after['memory_text']} ({after['memory_percent']}%)\n"
            "Note: this runs safe Python garbage collection only."
        )

    def _clear_cache(self) -> str:
        safe_dirs = [DATA_DIR / "cache", DATA_DIR / "tmp", DATA_DIR / ".cache"]
        existing = [path for path in safe_dirs if path.exists() and path.is_dir()]
        if not existing:
            return "No app cache folder found."
        removed = 0
        freed = 0
        for folder in existing:
            if not self._is_safe_cache_dir(folder):
                continue
            for path in sorted(folder.rglob("*"), reverse=True):
                try:
                    if path.is_file():
                        freed += path.stat().st_size
                        path.unlink()
                        removed += 1
                    elif path.is_dir():
                        path.rmdir()
                except OSError:
                    continue
        return f"Cache clean complete.\nFiles removed: {removed}\nFreed: {self._format_bytes(freed)}"

    def _model(self) -> str:
        if self.controller is None:
            return "Selected AI Provider: UNKNOWN"
        try:
            status = self.controller.advanced_brain.status()
            return (
                f"Selected AI Provider: {status.get('selected_provider') or status.get('backend') or 'unknown'}\n"
                f"Configured: {status.get('configured')}\n"
                f"Model: {status.get('model', 'unknown')}"
            )
        except Exception as exc:
            return f"Selected AI Provider: UNKNOWN\nReason: {exc}"

    def _voice_status(self) -> str:
        snap = self.get_voice_snapshot()
        return (
            f"Controller Online: {snap['online']}\n"
            f"Voice Status     : {snap['voice_status']}\n"
            f"Voice Replies    : {snap.get('voice_reply_enabled', False)}\n"
            f"Listening        : {snap['listening']}"
        )

    def _neural_link_status(self) -> str:
        status = "ONLINE" if self.controller is not None else "UNKNOWN"
        db_status = self._check_database()
        ai_status = self._check_ai_provider()
        return (
            f"Neural Link              : {status}\n"
            f"Database                 : {db_status}\n"
            f"AI Provider              : {ai_status}\n"
            f"Voice Pipeline           : {self._check_attr('stt')} / {self._check_attr('tts')}\n"
            f"Status                   : {'Secure' if db_status == 'PASS' else 'Degraded'}"
        )

    def _disk_summary(self) -> str:
        if psutil is None:
            return "psutil unavailable"
        disk = psutil.disk_usage(str(PROJECT_ROOT.anchor or Path.cwd().anchor or "/"))
        return f"{disk.used / (1024 ** 3):.1f} GB / {disk.total / (1024 ** 3):.1f} GB ({disk.percent}%)"

    def _battery_summary(self) -> str:
        if psutil is None:
            return "psutil unavailable"
        try:
            battery = psutil.sensors_battery()
        except Exception:
            battery = None
        if battery is None:
            return "No battery detected"
        plugged = "plugged in" if battery.power_plugged else "on battery"
        return f"{battery.percent}% ({plugged})"

    def _system_uptime(self) -> str:
        if psutil is None:
            return "psutil unavailable"
        return self._format_seconds(time.time() - psutil.boot_time())

    def _connection_status(self) -> str:
        try:
            with socket.create_connection(("1.1.1.1", 53), timeout=2):
                return "Online"
        except OSError:
            return "Offline"

    def _check_database(self) -> str:
        try:
            conn = get_connection()
            conn.execute("SELECT 1").fetchone()
            conn.close()
            return "PASS"
        except Exception:
            return "FAIL"

    def _check_settings(self) -> str:
        try:
            SettingsRepository().get("startup_page", "0")
            return "PASS"
        except Exception:
            return "FAIL"

    def _check_ai_provider(self) -> str:
        if self.controller is None:
            return "UNKNOWN"
        try:
            return "PASS" if self.controller.advanced_brain.is_available() else "UNKNOWN"
        except Exception:
            return "FAIL"

    def _check_attr(self, attr: str) -> str:
        return "PASS" if self.controller is not None and getattr(self.controller, attr, None) is not None else "UNKNOWN"

    def _check_internet(self) -> str:
        return "PASS" if self._connection_status() == "Online" else "FAIL"

    def _save(self, session_id: str, command: str, output: str) -> None:
        try:
            self.repository.add(session_id, command, output)
        except Exception:
            pass

    def _is_dangerous(self, lowered: str) -> bool:
        return any(lowered == prefix.strip() or lowered.startswith(prefix) for prefix in self.BLOCKED_PREFIXES)

    def _safe_host(self, host: str) -> bool:
        if len(host) > 253 or any(ch in host for ch in ";&|<>`$\\\"'"):
            return False
        try:
            ipaddress.ip_address(host)
            return True
        except ValueError:
            pass
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")
        return all(ch in allowed for ch in host) and "." in host and not host.startswith(".")

    def _is_safe_cache_dir(self, folder: Path) -> bool:
        try:
            return folder.resolve().is_relative_to(DATA_DIR.resolve())
        except Exception:
            return False

    def _format_seconds(self, seconds: float) -> str:
        seconds = max(0, int(seconds))
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _format_bytes(self, size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024 or unit == "GB":
                return f"{value:.1f} {unit}"
            value /= 1024

    def _psutil_missing(self) -> str:
        return "psutil is not installed. Install it with: pip install psutil"
