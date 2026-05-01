from __future__ import annotations
"""Focused file/folder automation helpers.

Architecture note:
    This module is wrapped by app.actions.file_actions. It overlaps with
    app.services.automation.windows_desktop, but should not be deleted until
    the file-action API owns all callers and behavior is covered by tests.
"""

import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from difflib import SequenceMatcher

LOG = logging.getLogger(__name__)


@dataclass
class FileActionResult:
    success: bool
    message: str
    intent: str
    path: str = ""
    candidates: list[str] = field(default_factory=list)
    error: str = ""


_FOLDER_ALIASES: dict[str, tuple[str, ...]] = {
    "downloads": ("downloads", "download", "downloads folder", "download folder", "ডাউনলোড", "ডাউনলোডস"),
    "desktop": ("desktop", "desktop folder", "ডেস্কটপ"),
    "documents": ("documents", "document", "documents folder", "document folder", "ডকুমেন্ট", "ডকুমেন্টস"),
    "pictures": ("pictures", "picture", "photos", "ছবি", "পিকচার"),
    "music": ("music", "songs", "মিউজিক", "গান"),
    "videos": ("videos", "video", "ভিডিও"),
    "project": ("project", "project folder", "jarvis", "jarvis folder"),
}

_RECENT_WORDS = (
    "এই ফাইলটা",
    "এই ফাইল",
    "last downloaded file",
    "last download",
    "recent file",
    "latest file",
)

_FILE_WORDS = (
    "file",
    "ফাইল",
    "pdf",
    "doc",
    "docx",
    "document",
    "assignment",
)

_DROP_WORDS = {
    "open",
    "launch",
    "start",
    "run",
    "folder",
    "file",
    "please",
    "my",
    "this",
    "that",
    "করো",
    "করুন",
    "খুলো",
    "ওপেন",
    "চালু",
    "দাও",
    "আমার",
    "এই",
    "ফাইলটা",
    "ফাইল",
    "ফোল্ডার",
}


def open_folder(folder_name: str) -> FileActionResult:
    path = _known_folder_path(folder_name)
    if not path:
        return FileActionResult(False, "স্যার, এই ফোল্ডারটি খুঁজে পাইনি।", "open_folder", error="not_found")
    return _open_path(path, "open_folder", f"ঠিক আছে স্যার, {_display_folder(folder_name)} folder খুলছি।")


def open_file(path: str) -> FileActionResult:
    return _open_path(Path(path), "open_file", f"ঠিক আছে স্যার, {Path(path).name} খুলছি।")


def open_recent_file(location: str = "downloads") -> FileActionResult:
    folder = _known_folder_path(location)
    if not folder:
        return FileActionResult(False, "স্যার, Downloads folder খুঁজে পাইনি।", "open_file", error="not_found")
    files = [item for item in folder.iterdir() if item.is_file()]
    if not files:
        return FileActionResult(False, "স্যার, Downloads-এ কোনো ফাইল খুঁজে পাইনি।", "open_file", error="not_found")
    latest = max(files, key=lambda item: item.stat().st_mtime)
    LOG.info("[file] recent file: %s", latest)
    return _open_path(latest, "open_file", "ঠিক আছে স্যার, সর্বশেষ ডাউনলোড করা ফাইল খুলছি।")


def open_project_folder() -> FileActionResult:
    return _open_path(_project_root(), "open_folder", "ঠিক আছে স্যার, Jarvis project folder খুলছি।")


def find_file_by_name(query: str, search_dirs: list[str | Path] | None = None) -> list[Path]:
    q = _clean_query(query)
    LOG.info("[file] search query: %s", q)
    if not q:
        return []
    dirs = [Path(path) for path in search_dirs] if search_dirs else _default_search_dirs()
    matches: list[tuple[float, float, Path]] = []
    q_lower = q.lower()
    for folder in dirs:
        if not folder.exists() or not folder.is_dir():
            continue
        try:
            iterator = folder.rglob("*") if folder == _project_root() else folder.glob("*")
            for path in iterator:
                if not path.is_file():
                    continue
                name = path.name.lower()
                stem = path.stem.lower()
                contains = q_lower in name or all(part in name for part in q_lower.split())
                ratio = max(SequenceMatcher(None, q_lower, name).ratio(), SequenceMatcher(None, q_lower, stem).ratio())
                if contains or ratio >= 0.45:
                    matches.append((1.0 if contains else ratio, path.stat().st_mtime, path))
        except OSError:
            continue
    matches.sort(key=lambda item: (item[0], item[1]), reverse=True)
    paths = [item[2] for item in matches[:5]]
    if paths:
        LOG.info("[file] matched file: %s", paths[0])
    return paths


def is_file_automation_command(text: str, normalized: str = "") -> bool:
    value = _fold(f"{text} {normalized}")
    if _resolve_folder_name(value):
        return True
    if any(_fold(word) in value for word in _RECENT_WORDS):
        return True
    return any(_fold(word) in value for word in _FILE_WORDS) and any(word in value for word in ("open", "খুলো", "ওপেন", "চালু"))


def handle_file_automation_command(text: str, normalized: str = "") -> FileActionResult:
    LOG.info("[file] command: %s", text)
    value = _fold(f"{text} {normalized}")
    if any(_fold(word) in value for word in _RECENT_WORDS):
        return open_recent_file("downloads")
    folder = _resolve_folder_name(value)
    if folder:
        LOG.info("[file] resolved folder: %s", folder)
        if folder == "project":
            return open_project_folder()
        return open_folder(folder)
    matches = find_file_by_name(_clean_query(f"{text} {normalized}"))
    if not matches:
        return FileActionResult(False, "স্যার, এই নামে কোনো ফাইল খুঁজে পাইনি।", "open_file", error="not_found")
    if len(matches) > 1:
        return FileActionResult(
            False,
            "স্যার, একাধিক ফাইল পেয়েছি। কোনটি খুলবেন?",
            "open_file",
            candidates=[str(path) for path in matches],
            error="ambiguous",
        )
    return open_file(str(matches[0]))


def _known_folder_path(folder_name: str) -> Path | None:
    profile = Path(os.environ.get("USERPROFILE") or Path.home())
    mapping = {
        "downloads": profile / "Downloads",
        "desktop": profile / "Desktop",
        "documents": profile / "Documents",
        "pictures": profile / "Pictures",
        "music": profile / "Music",
        "videos": profile / "Videos",
        "project": _project_root(),
    }
    return mapping.get((folder_name or "").strip().lower())


def _open_path(path: Path, intent: str, message: str) -> FileActionResult:
    LOG.info("[file] opening: %s", path)
    if not path.exists():
        return FileActionResult(False, "স্যার, path খুঁজে পাইনি।", intent, str(path), error="not_found")
    try:
        if path.is_dir():
            subprocess.Popen(["explorer", str(path)], shell=False)
        else:
            os.startfile(str(path))  # type: ignore[attr-defined]
        return FileActionResult(True, message, intent, str(path))
    except Exception as exc:
        LOG.exception("[file] open failed")
        return FileActionResult(False, f"স্যার, খুলতে পারিনি: {path.name}", intent, str(path), error=str(exc))


def _resolve_folder_name(value: str) -> str:
    folded = _fold(value)
    for canonical, aliases in _FOLDER_ALIASES.items():
        if any(_fold(alias) in folded for alias in aliases):
            return canonical
    return ""


def _default_search_dirs() -> list[Path]:
    return [
        path
        for key in ("downloads", "desktop", "documents", "project")
        if (path := _known_folder_path(key)) is not None
    ]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _clean_query(text: str) -> str:
    value = _fold(text)
    for canonical, aliases in _FOLDER_ALIASES.items():
        for alias in aliases:
            value = value.replace(_fold(alias), " ")
    words = [word for word in value.replace(".", " ").split() if word and word not in _DROP_WORDS]
    return " ".join(words).strip()


def _display_folder(folder_name: str) -> str:
    return {
        "downloads": "Downloads",
        "desktop": "Desktop",
        "documents": "Documents",
        "pictures": "Pictures",
        "music": "Music",
        "videos": "Videos",
        "project": "Jarvis project",
    }.get(folder_name, folder_name.title())


def _fold(text: str) -> str:
    return (text or "").casefold().replace("য়", "য়")
