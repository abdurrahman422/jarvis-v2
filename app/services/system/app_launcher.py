from __future__ import annotations

import logging
import os
import subprocess
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

LOG = logging.getLogger(__name__)


@dataclass
class LaunchResult:
    success: bool
    message: str
    app_name: str = ""
    opened: str = ""


def _program_files_path(*parts: str) -> str:
    base = os.environ.get("ProgramFiles", r"C:\Program Files")
    return str(Path(base).joinpath(*parts))


def _program_files_x86_path(*parts: str) -> str:
    base = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    return str(Path(base).joinpath(*parts))


def _local_appdata_path(*parts: str) -> str:
    base = os.environ.get("LOCALAPPDATA", "")
    return str(Path(base).joinpath(*parts)) if base else ""


_KNOWN_APPS: dict[str, dict[str, object]] = {
    "youtube": {"display": "YouTube", "url": "https://www.youtube.com"},
    "chrome": {
        "display": "Chrome",
        "commands": [["chrome"], ["google-chrome"]],
        "paths": [
            _program_files_path("Google", "Chrome", "Application", "chrome.exe"),
            _program_files_x86_path("Google", "Chrome", "Application", "chrome.exe"),
        ],
    },
    "notepad": {"display": "Notepad", "commands": [["notepad.exe"]]},
    "calculator": {"display": "Calculator", "commands": [["calc.exe"]]},
    "vscode": {
        "display": "VS Code",
        "commands": [["code"]],
        "paths": [_local_appdata_path("Programs", "Microsoft VS Code", "Code.exe")],
        "start_menu": ["Visual Studio Code", "VS Code"],
    },
    "whatsapp": {"display": "WhatsApp", "url": "https://web.whatsapp.com"},
    "chatgpt": {"display": "ChatGPT", "url": "https://chatgpt.com"},
    "edge": {"display": "Edge", "commands": [["msedge"], ["msedge.exe"]]},
    "firefox": {"display": "Firefox", "commands": [["firefox"], ["firefox.exe"]]},
    "brave": {"display": "Brave", "commands": [["brave"], ["brave.exe"]]},
    "google": {"display": "Google", "url": "https://www.google.com"},
    "facebook": {"display": "Facebook", "url": "https://www.facebook.com"},
    "messenger": {"display": "Messenger", "url": "https://www.messenger.com"},
    "paint": {"display": "Paint", "commands": [["mspaint.exe"]]},
    "word": {"display": "Word", "commands": [["winword"], ["winword.exe"]]},
    "excel": {"display": "Excel", "commands": [["excel"], ["excel.exe"]]},
    "powerpoint": {"display": "PowerPoint", "commands": [["powerpnt"], ["powerpnt.exe"]]},
    "cursor": {"display": "Cursor", "commands": [["cursor"], ["cursor.exe"]]},
    "pycharm": {"display": "PyCharm", "commands": [["pycharm"], ["pycharm64.exe"]]},
    "file explorer": {"display": "File Explorer", "commands": [["explorer.exe"]]},
    "control panel": {"display": "Control Panel", "commands": [["control.exe"]]},
    "settings": {"display": "Settings", "commands": [["cmd", "/c", "start", "", "ms-settings:"]]},
    "camera": {"display": "Camera", "commands": [["cmd", "/c", "start", "", "microsoft.windows.camera:"]]},
    "spotify": {"display": "Spotify", "commands": [["spotify"], ["spotify.exe"]]},
    "vlc": {"display": "VLC", "commands": [["vlc"], ["vlc.exe"]]},
    "telegram": {"display": "Telegram", "commands": [["telegram"], ["telegram.exe"]]},
    "zoom": {"display": "Zoom", "commands": [["zoom"], ["zoom.exe"]]},
    "discord": {"display": "Discord", "commands": [["discord"], ["discord.exe"]]},
    "github desktop": {"display": "GitHub Desktop", "commands": [["githubdesktop"], ["GitHubDesktop.exe"]]},
    "cmd": {"display": "CMD", "commands": [["cmd.exe"]]},
    "powershell": {"display": "PowerShell", "commands": [["powershell.exe"]]},
    "windows terminal": {"display": "Windows Terminal", "commands": [["wt.exe"], ["wt"]]},
    "task manager": {"display": "Task Manager", "commands": [["taskmgr.exe"]]},
}


def open_app(app_name: str, *, allow_fallback: bool = True) -> LaunchResult:
    canonical = (app_name or "").strip().lower()
    spec = _KNOWN_APPS.get(canonical)
    display = str(spec.get("display")) if spec else _display_name(canonical)

    LOG.info("[launcher] trying known app: %s", canonical)
    if spec:
        url = spec.get("url")
        if isinstance(url, str) and url:
            LOG.info("[launcher] method: known/url")
            if webbrowser.open(url):
                LOG.info("[launcher] success/fail: opened %s", url)
                LOG.info("[launcher] opened: %s", url)
                return LaunchResult(True, f"ঠিক আছে স্যার, {display} খুলছি।", display, url)
            LOG.info("[launcher] success/fail: url open failed")

        for path_text in spec.get("paths", []):
            if isinstance(path_text, str) and path_text and Path(path_text).exists():
                LOG.info("[launcher] method: known/path")
                if _try_command([path_text]):
                    LOG.info("[launcher] success/fail: opened %s", path_text)
                    LOG.info("[launcher] opened: %s", path_text)
                    return LaunchResult(True, f"ঠিক আছে স্যার, {display} খুলছি।", display, path_text)

        for command in spec.get("commands", []):
            LOG.info("[launcher] method: known")
            if _try_command(command):
                opened = " ".join(str(part) for part in command)
                LOG.info("[launcher] success/fail: opened %s", opened)
                LOG.info("[launcher] opened: %s", opened)
                return LaunchResult(True, f"ঠিক আছে স্যার, {display} খুলছি।", display, opened)

        search_terms = [canonical, display, *[str(v) for v in spec.get("start_menu", [])]]
    else:
        search_terms = [canonical]

    LOG.info("[launcher] trying start menu search: %s", canonical)
    shortcut = _find_start_menu_shortcut(search_terms)
    if shortcut is not None:
        try:
            LOG.info("[launcher] method: startmenu")
            os.startfile(str(shortcut))  # type: ignore[attr-defined]
            LOG.info("[launcher] success/fail: opened %s", shortcut)
            LOG.info("[launcher] opened: %s", shortcut)
            return LaunchResult(True, f"ঠিক আছে স্যার, {display} খুলছি।", display, str(shortcut))
        except OSError:
            LOG.exception("[launcher] success/fail: start menu shortcut failed")

    if allow_fallback and _is_safe_fallback_name(canonical):
        LOG.info("[launcher] method: fallback")
        resolved = _resolve_path_command(canonical)
        if resolved and _try_command([resolved]):
            LOG.info("[launcher] success/fail: opened fallback %s", resolved)
            LOG.info("[launcher] opened: %s", resolved)
            return LaunchResult(True, f"ঠিক আছে স্যার, {display} খুলছি।", display, resolved)

    LOG.info("[launcher] success/fail: app not found")
    return LaunchResult(False, "স্যার, এই অ্যাপটি খুঁজে পাইনি।", display, "")


def google_search(query: str) -> LaunchResult:
    q = (query or "").strip()
    url = f"https://www.google.com/search?q={quote_plus(q)}"
    LOG.info("[search] google query: %s", q)
    if webbrowser.open(url):
        return LaunchResult(True, f"ঠিক আছে স্যার, Google-এ সার্চ করছি: {q}", "Google", url)
    return LaunchResult(False, f"স্যার, Google search খুলতে পারিনি: {q}", "Google", url)


def _try_command(command: object) -> bool:
    if not isinstance(command, list) or not command:
        return False
    try:
        subprocess.Popen([str(part) for part in command], shell=False)
        return True
    except OSError:
        return False


def _resolve_path_command(name: str) -> str:
    if not name or " " in name:
        return ""
    try:
        completed = subprocess.run(
            ["where", name],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except Exception:
        return ""
    if completed.returncode != 0:
        return ""
    first = (completed.stdout or "").splitlines()[0].strip()
    return first if first else ""


def _find_start_menu_shortcut(terms: list[str]) -> Path | None:
    needles = {term.lower().strip() for term in terms if term and term.strip()}
    needles |= {needle.replace(" ", "") for needle in list(needles)}
    folders = [
        Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    ]
    appdata = os.environ.get("APPDATA")
    if appdata:
        folders.append(Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")

    for folder in folders:
        if not folder.exists():
            continue
        for path in folder.rglob("*.lnk"):
            stem = path.stem.lower()
            compact = stem.replace(" ", "")
            if any(needle and (needle in stem or needle in compact) for needle in needles):
                return path
    return None


def _is_safe_fallback_name(value: str) -> bool:
    return bool(value) and value.isascii() and all(ch.isalnum() or ch in "._-" for ch in value)


def _display_name(value: str) -> str:
    return " ".join(part.capitalize() for part in (value or "app").split())
