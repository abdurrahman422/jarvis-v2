"""Legacy ActionRegistry system tools.

Architecture note:
    These functions support older local intent actions registered by
    AssistantController._register_actions(). New system-action routing should
    prefer app.actions.system_actions and system_action_executor. Keep this
    module until all registered legacy actions are replaced safely.
"""

import datetime
import os
import platform
import subprocess

import psutil

from app.services.offline_guard import block_internet
from app.services.system.app_launcher import google_search, open_app


def _execute_canonical_system_tool(intent: str, action: str, target: str) -> str:
    from app.core.system_action_dataset_loader import SystemActionExample
    from app.services.system.system_action_executor import execute_system_action

    record = SystemActionExample(
        id=f"legacy_system_tools_{target}",
        intent=intent,
        action=action,
        target=target,
        instruction=target,
        response="",
        speak_text="",
        normalized=f"{intent} {action} {target}",
    )
    result = execute_system_action(record)
    return result.response


def get_time(_: str) -> str:
    return datetime.datetime.now().strftime("It is %I:%M %p on %A, %d %B %Y.")


def get_battery(_: str) -> str:
    battery = psutil.sensors_battery()
    if not battery:
        return "Battery details are not available on this system."
    mins_left = battery.secsleft // 60 if battery.secsleft and battery.secsleft > 0 else -1
    eta = f", about {mins_left} min left" if mins_left > 0 else ""
    return (
        f"Battery is {int(battery.percent)} percent. "
        f"Plugged in: {battery.power_plugged}{eta}."
    )


def open_notepad(_: str) -> str:
    try:
        return _execute_canonical_system_tool("open_app", "open_app", "notepad")
    except OSError as exc:
        return f"Could not open Notepad: {exc}"
    except Exception:
        subprocess.Popen(["notepad.exe"])
        return "Opening Notepad."


def system_status(_: str) -> str:
    cpu = psutil.cpu_percent(interval=0.4)
    memory = psutil.virtual_memory()
    return f"CPU {cpu:.0f}% used, RAM {memory.percent:.0f}% used."


def system_info(_: str) -> str:
    return (
        f"Running on {platform.system()} {platform.release()}, "
        f"Python {platform.python_version()}."
    )


def open_google(_: str) -> str:
    return _execute_canonical_system_tool("open_app", "open_app", "google")


def open_youtube(_: str) -> str:
    return _execute_canonical_system_tool("open_app", "open_app", "youtube")


def youtube_search(user_text: str) -> str:
    from app.services.automation.youtube_multimodal import execute_youtube

    return execute_youtube(user_text, "search")


def youtube_play(user_text: str) -> str:
    from app.services.automation.youtube_multimodal import execute_youtube

    return execute_youtube(user_text, "play")


def greet(_: str) -> str:
    return "Hello. I am Jarvis. How can I help you?"


def unknown(_: str) -> str:
    return (
        "I'm not sure I got that--try 'open YouTube', 'search on YouTube for...', "
        "or ask for the time, and I'll help from there."
    )


def open_path(path: str) -> str:
    if not os.path.exists(path):
        return f"Path not found: {path}"
    os.startfile(path)
    return f"Opening {path}"


def open_desktop_item_stub(_: str) -> str:
    """Real handling runs in AssistantController._desktop_open_main; registry requires a handler."""
    return ""
