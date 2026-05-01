from __future__ import annotations

from pathlib import Path

from app.services.automation import windows_desktop
from app.services.system import file_automation
from app.services.system.file_automation import FileActionResult


def is_file_action(text: str, normalized_text: str = "") -> bool:
    return file_automation.is_file_automation_command(text, normalized_text)


def execute_file_action(text: str, normalized_text: str = "") -> FileActionResult:
    return execute_file_route(text, normalized_text)


def open_folder(folder_name: str) -> FileActionResult:
    return open_known_folder(folder_name)


def open_known_folder(folder_name: str) -> FileActionResult:
    return file_automation.open_folder(folder_name)


def open_file(path: str | Path) -> FileActionResult:
    return file_automation.open_file(str(path))


def open_recent_file(location: str = "downloads") -> FileActionResult:
    return file_automation.open_recent_file(location)


def open_project_folder() -> FileActionResult:
    return file_automation.open_project_folder()


def open_file_by_name(query: str, search_dirs: list[str | Path] | None = None) -> FileActionResult:
    matches = file_automation.find_file_by_name(query, search_dirs)
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
    return file_automation.open_file(str(matches[0]))


def find_file_by_name(query: str, search_dirs: list[str | Path] | None = None) -> list[Path]:
    return file_automation.find_file_by_name(query, search_dirs)


def search_file(query: str) -> list[str]:
    return windows_desktop.search_file(query)


def get_latest_file(folder: str) -> str | None:
    return windows_desktop.get_latest_file(folder)


def looks_like_desktop_launch(q: str, ql: str) -> bool:
    return windows_desktop.looks_like_desktop_launch(q, ql)


def resolve_desktop_command(user_text: str, getter):
    return windows_desktop.resolve_desktop_command(user_text, getter)


def complete_pick(user_reply: str, candidates: list[str]):
    return windows_desktop.complete_pick(user_reply, candidates)


def execute_file_route(text: str, normalized_text: str = "") -> FileActionResult:
    return file_automation.handle_file_automation_command(text, normalized_text)


def execute_legacy_file_control(user_text: str) -> str:
    return windows_desktop.execute_file_control(user_text)
