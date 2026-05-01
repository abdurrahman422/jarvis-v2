import logging
import sys
import importlib
import os
import subprocess
import ctypes
from pathlib import Path

from app.app_paths import LOGS_DIR, PROJECT_ROOT
from app.services.offline_guard import install_internet_block, log_offline_mode

_DPI_CONFIGURED = False


def _configure_qt_process_environment() -> None:
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")
    existing_rules = os.environ.get("QT_LOGGING_RULES", "").strip()
    font_rule = "qt.text.font.db.warning=false"
    if font_rule not in existing_rules:
        os.environ["QT_LOGGING_RULES"] = f"{existing_rules};{font_rule}".strip(";")


def _configure_dpi_awareness_once() -> None:
    global _DPI_CONFIGURED
    if _DPI_CONFIGURED or os.name != "nt":
        return
    _DPI_CONFIGURED = True
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except OSError as exc:
        if getattr(exc, "winerror", None) != 5:
            logging.debug("DPI awareness setup skipped: %s", exc)
    except Exception as exc:
        logging.debug("DPI awareness setup skipped: %s", exc)


def _configure_logging() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if any(
        isinstance(handler, logging.FileHandler)
        and getattr(handler, "baseFilename", "").endswith("app.log")
        for handler in root.handlers
    ):
        return
    file_handler = logging.FileHandler(LOGS_DIR / "app.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)


def _project_venv_python() -> Path:
    scripts_dir = PROJECT_ROOT.resolve() / ".venv" / "Scripts"
    return scripts_dir / ("python.exe" if os.name == "nt" else "python")


def _running_from_project_venv() -> bool:
    venv_root = (PROJECT_ROOT.resolve() / ".venv").resolve()
    try:
        executable = Path(sys.executable).resolve()
    except OSError:
        executable = Path(os.path.abspath(sys.executable))
    return executable == _project_venv_python().resolve() or venv_root in executable.parents


def _ensure_project_venv_or_warn() -> None:
    if os.environ.get("JARVIS_VENV_BOOTSTRAPPED") == "1":
        return
    if _running_from_project_venv():
        return

    venv_python = _project_venv_python()
    if not venv_python.exists():
        print(f"WARNING: Project .venv interpreter was not found: {venv_python}")
        logging.warning("Project .venv interpreter was not found: %s", venv_python)
        return

    try:
        check = subprocess.run(
            [str(venv_python), "-c", "import sys; print(sys.executable)"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception as exc:
        print(f"WARNING: Project .venv interpreter could not be checked: {exc}")
        logging.warning("Project .venv interpreter could not be checked: %s", exc)
        return

    if check.returncode != 0:
        message = (check.stderr or check.stdout or "").strip()
        print(f"WARNING: Project .venv interpreter is not usable: {message}")
        logging.warning("Project .venv interpreter is not usable: %s", message)
        return

    print(f"Restarting with project .venv interpreter: {venv_python}")
    logging.info("Restarting with project .venv interpreter: %s", venv_python)
    os.environ["JARVIS_VENV_BOOTSTRAPPED"] = "1"
    os.execv(str(venv_python), [str(venv_python), *sys.argv])


def _startup_diagnostics() -> None:
    print(f"Python executable: {sys.executable}")
    if not _running_from_project_venv():
        logging.warning("App is not running from the project .venv: %s", sys.executable)
        print(f"WARNING: App is not running from project .venv: {sys.executable}")

    pyttsx3_available = importlib.util.find_spec("pyttsx3") is not None
    print("TTS deps available:", "true" if pyttsx3_available else "false")
    if not pyttsx3_available:
        print("TTS not available in current interpreter")
        logging.error("TTS not available in current interpreter")
        return

    try:
        from app.services.speech.stt_service import STTService
        from app.services.speech.tts_service import TTSService, log_tts_startup_status
    except Exception as exc:
        logging.exception("Voice dependency check failed")
        print(f"Voice diagnostics failed: {exc}")
        return

    log_tts_startup_status()
    stt = STTService()
    stt.set_language(os.environ.get("STT_LANGUAGE", "bn-BD"))
    print(stt.get_status())
    tts = TTSService()
    status = tts.debug_check()
    print("TTS engine ready:", "true" if not status.get("last_error") else "false")
    if status.get("last_error"):
        print(f"TTS startup warning: {status['last_error']}")
    self_test = os.environ.get("ENABLE_TTS_SELF_TEST", "false").strip().lower()
    if self_test in {"1", "true", "yes", "on", "enabled"}:
        tts.test_tts()


def main() -> int:
    os.environ.setdefault("OFFLINE_MODE", "false")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    _configure_logging()
    log_offline_mode()
    install_internet_block()
    _configure_qt_process_environment()
    _configure_dpi_awareness_once()
    try:
        from dotenv import load_dotenv

        load_dotenv(PROJECT_ROOT / ".env")
    except Exception:
        logging.exception("Failed to load .env")
    _ensure_project_venv_or_warn()
    _startup_diagnostics()
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication, QMessageBox

    from app.data.db import init_db
    from app.ui.main_window import MainWindow
    from app.ui.theme import GLOBAL_STYLESHEET

    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(GLOBAL_STYLESHEET)
    try:
        init_db()
        optional_modules = ["speech_recognition", "pyaudiowpatch", "pyttsx3"]
        missing = [m for m in optional_modules if importlib.util.find_spec(m) is None]
        if missing:
            QMessageBox.information(
                None,
                "Jarvis Dependency Notice",
                "Some optional modules are missing: "
                + ", ".join(missing)
                + "\nFeatures may run in degraded mode.",
            )
        window = MainWindow()
        window.show()
        return app.exec()
    except Exception as exc:
        logging.exception("Jarvis failed to start")
        QMessageBox.critical(
            None,
            "Jarvis Startup Error",
            f"Jarvis failed to start.\n\nReason:\n{exc}",
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
