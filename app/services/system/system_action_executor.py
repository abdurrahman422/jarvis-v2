from __future__ import annotations
"""Primary system-action executor.

Architecture note:
    This is the canonical executor for dataset-backed system actions. Older
    compatibility logic still exists in app.services.system.system_control and
    app.services.automation.system_tools. Do not delete or bypass this module;
    future cleanup should migrate remaining callers toward app.actions.system_actions.
"""

import ctypes
import logging
import os
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.core.system_action_dataset_loader import SystemActionExample
from app.services.system.app_launcher import open_app

LOG = logging.getLogger(__name__)
USE_SAFE_VOLUME_KEYS = True


def _safe_print(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        print(message.encode(encoding, errors="backslashreplace").decode(encoding, errors="replace"))

DANGEROUS_TARGETS = {
    "shutdown_pc",
    "restart_pc",
    "sleep_pc",
    "sign_out",
    "close_window",
    "close_app",
    "delete_file",
    "rename_file",
    "move_file",
}


@dataclass
class SystemActionExecutionResult:
    success: bool
    intent: str
    action: str
    target: str
    response: str
    speak_text: str = ""
    handled: bool = True
    path: str = ""
    candidates: list[str] = field(default_factory=list)
    error: str = ""
    requires_confirmation: bool = False


def execute_system_action(record: SystemActionExample, original_text: str = "") -> SystemActionExecutionResult:
    LOG.info("[system-action] matched id=%s action=%s target=%s", record.id, record.action, record.target)
    _safe_print(f"[system-action] matched id={record.id} action={record.action} target={record.target}")
    LOG.info(
        "[system-action] matched record: intent=%s action=%s target=%s",
        record.intent,
        record.action,
        record.target,
    )
    executor = ACTION_EXECUTORS.get(record.action)
    if executor is None:
        LOG.warning("[system-action] failed: missing executor for action=%s target=%s", record.action, record.target)
        _safe_print(f"[system-action] failed: missing executor for action={record.action} target={record.target}")
        msg = f"স্যার, এই action-এর code এখনো implement করা হয়নি: {record.action} {record.target}"
        return SystemActionExecutionResult(False, record.intent, record.action, record.target, msg, msg, error="missing_executor")
    if _is_dangerous(record):
        msg = _confirm_message(record.target)
        LOG.info("[system-action] executor result: %s", msg)
        _safe_print(f"[system-action] executor result: {msg}")
        return SystemActionExecutionResult(False, record.intent, record.action, record.target, msg, msg, requires_confirmation=True)
    try:
        LOG.info("[system-action] executing real Windows action")
        _safe_print("[system-action] executing real Windows action")
        LOG.info("[system-control] executing: action=%s target=%s", record.action, record.target)
        result = executor(record)
        if result.success:
            LOG.info("[system-action] success")
            LOG.info("[system-control] success")
        else:
            LOG.warning("[system-action] failed: %s", result.error)
            LOG.warning("[system-control] failed: %s", result.error)
            _safe_print(f"[system-action] failed: {result.error}")
        LOG.info("[system-action] executor result: %s", result.response)
        _safe_print(f"[system-action] executor result: {result.response}")
        return result
    except Exception as exc:
        LOG.exception("[system-action] failed: %s", exc)
        LOG.exception("[system-control] failed: %s", exc)
        _safe_print(f"[system-action] failed: {exc}")
        msg = f"স্যার, action execute করতে পারিনি: {record.action} {record.target}"
        return SystemActionExecutionResult(False, record.intent, record.action, record.target, msg, msg, error=str(exc))


def execute_dataset_action(record: SystemActionExample, original_text: str = "") -> SystemActionExecutionResult:
    return execute_system_action(record, original_text=original_text)


def execute_confirmed_dataset_action(target: str) -> SystemActionExecutionResult:
    mapped = {
        "shutdown_pc": "shutdown_confirm",
        "restart_pc": "restart_confirm",
        "sleep_pc": "sleep_confirm",
        "close_window": "close_current_window",
        "close_app": "close_current_window",
        "sign_out": "sign_out",
    }.get(target, target)
    if mapped == "sign_out":
        subprocess.Popen(["shutdown", "/l"], shell=False)
        return SystemActionExecutionResult(True, "sign_out", "sign_out", target, "ঠিক আছে স্যার, sign out করছি।", "ঠিক আছে স্যার, sign out করছি।")
    if mapped == "shutdown_confirm":
        subprocess.Popen(["shutdown", "/s", "/t", "5"], shell=False)
        msg = "ঠিক আছে স্যার, ৫ সেকেন্ড পরে shutdown করছি।"
        return SystemActionExecutionResult(True, mapped, "shutdown", target, msg, msg)
    if mapped == "restart_confirm":
        subprocess.Popen(["shutdown", "/r", "/t", "5"], shell=False)
        msg = "ঠিক আছে স্যার, ৫ সেকেন্ড পরে restart করছি।"
        return SystemActionExecutionResult(True, mapped, "restart", target, msg, msg)
    if mapped == "sleep_confirm":
        subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], shell=False)
        msg = "ঠিক আছে স্যার, sleep mode করছি।"
        return SystemActionExecutionResult(True, mapped, "sleep", target, msg, msg)
    if mapped == "close_current_window":
        record = SystemActionExample(
            id="confirmed_close_current_window",
            intent="close_current_window",
            action="window_control",
            target="close_current_window",
            instruction="",
            response="ঠিক আছে স্যার, current window close করছি।",
            speak_text="ঠিক আছে স্যার, current window close করছি।",
            normalized="close_current_window",
        )
        return _hotkey(record, ["alt", "f4"], "ঠিক আছে স্যার, current window close করছি।")
    msg = "স্যার, confirm action খুঁজে পাইনি।"
    return SystemActionExecutionResult(False, "confirm", "confirm", target, msg, msg, error="unknown_confirm")


def is_confirm_command(text: str) -> bool:
    value = (text or "").casefold()
    return any(token in value for token in ("confirm", "কনফার্ম", "নিশ্চিত"))


def _execute_open_folder(record: SystemActionExample) -> SystemActionExecutionResult:
    folder = _folder_key(record.target)
    if folder == "recycle_bin":
        return _open_uri(record, "shell:RecycleBinFolder", "ঠিক আছে স্যার, Recycle Bin খুলছি।")
    if folder == "this_pc":
        return _open_uri(record, "shell:MyComputerFolder", "ঠিক আছে স্যার, This PC খুলছি।")
    path = _known_folder_path(folder)
    if path is None:
        return _missing_target(record)
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
        return SystemActionExecutionResult(True, record.intent, record.action, record.target, f"ঠিক আছে স্যার, {record.target} খুলছি।", path=str(path))
    except Exception as exc:
        return _fail(record, f"স্যার, {record.target} খুলতে পারিনি।", str(exc))


def _execute_open_app(record: SystemActionExample) -> SystemActionExecutionResult:
    app = _app_key(record.target)
    result = open_app(app, allow_fallback=True)
    return SystemActionExecutionResult(result.success, record.intent, record.action, record.target, result.message, result.message, path=result.opened, error="" if result.success else "open_failed")


def _execute_toggle_setting(record: SystemActionExample) -> SystemActionExecutionResult:
    target = (record.target or "").casefold()
    text = f"{record.instruction} {record.target}".casefold()
    if "wifi" in target:
        return _wifi(record, enable=_wants_on(text))
    if "bluetooth" in target:
        return _open_settings(record, "ms-settings:bluetooth", "স্যার, Bluetooth settings খুলেছি। এখানে থেকে অন/অফ করতে পারবেন।")
    if "airplane" in target:
        return _open_settings(record, "ms-settings:network-airplanemode", "স্যার, Airplane mode settings খুলেছি।")
    if "battery" in target:
        return _open_settings(record, "ms-settings:batterysaver", "স্যার, Battery saver settings খুলেছি।")
    if "dark" in target:
        return _open_settings(record, "ms-settings:colors", "স্যার, Dark mode settings খুলেছি।")
    if "night" in target:
        return _open_settings(record, "ms-settings:nightlight", "স্যার, Night light settings খুলেছি।")
    if "do_not_disturb" in target:
        return _open_settings(record, "ms-settings:notifications", "স্যার, Notification settings খুলেছি।")
    return _missing_target(record)


def _execute_set_volume(record: SystemActionExample) -> SystemActionExecutionResult:
    target = (record.target or "").casefold()
    if target == "mute":
        return _volume(record, "mute")
    if target == "unmute":
        return _volume(record, "unmute")
    if target == "volume_up":
        return _volume(record, "up")
    if target == "volume_down":
        return _volume(record, "down")
    if target.startswith("volume_"):
        return _volume(record, "set", _target_number(target))
    return _missing_target(record)


def _execute_set_brightness(record: SystemActionExample) -> SystemActionExecutionResult:
    target = (record.target or "").casefold()
    if target == "brightness_up":
        return _brightness(record, "up")
    if target == "brightness_down":
        return _brightness(record, "down")
    if target.startswith("brightness_"):
        return _brightness(record, "set", _target_number(target))
    return _missing_target(record)


def _execute_window_control(record: SystemActionExample) -> SystemActionExecutionResult:
    target = (record.target or "").casefold()
    if target == "screenshot":
        return _screenshot(record)
    if target == "minimize_window":
        return _hotkey(record, ["win", "down"], "ঠিক আছে স্যার, window minimize করছি।")
    if target == "maximize_window":
        return _hotkey(record, ["win", "up"], "ঠিক আছে স্যার, window maximize করছি।")
    if target == "switch_window":
        return _hotkey(record, ["alt", "tab"], "ঠিক আছে স্যার, window switch করছি।")
    if target == "show_desktop":
        return _hotkey(record, ["win", "d"], "ঠিক আছে স্যার, desktop দেখাচ্ছি।")
    return _missing_target(record)


def _execute_power_control(record: SystemActionExample) -> SystemActionExecutionResult:
    target = (record.target or "").casefold()
    if target == "lock_pc":
        try:
            subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"], shell=False)
            return _ok(record, "ঠিক আছে স্যার, screen lock করছি।")
        except Exception:
            ctypes.windll.user32.LockWorkStation()
            return _ok(record, "ঠিক আছে স্যার, screen lock করছি।")
    if target == "sign_out":
        return SystemActionExecutionResult(False, record.intent, record.action, record.target, _confirm_message("sign_out"), _confirm_message("sign_out"), requires_confirmation=True)
    return _missing_target(record)


def _execute_media_control(record: SystemActionExample) -> SystemActionExecutionResult:
    target = (record.target or "").casefold()
    key = {
        "play_pause": "playpause",
        "next_track": "nexttrack",
        "previous_track": "prevtrack",
        "stop_media": "stop",
    }.get(target)
    if not key:
        return _missing_target(record)
    return _press_key(record, key, "ঠিক আছে স্যার, media control করছি।")


def _execute_get_time_date(record: SystemActionExample) -> SystemActionExecutionResult:
    now = datetime.now()
    target = (record.target or "").casefold()
    if target == "current_time":
        return _ok(record, f"স্যার, এখন সময় {now.strftime('%I:%M %p')}।")
    if target == "current_date":
        return _ok(record, f"স্যার, আজকের তারিখ {now.strftime('%d %B %Y')}।")
    if target == "current_day":
        return _ok(record, f"স্যার, আজ {now.strftime('%A')}।")
    if target == "current_month":
        return _ok(record, f"স্যার, এখন {now.strftime('%B')} মাস।")
    return _ok(record, f"স্যার, এখন {now.strftime('%A, %d %B %Y %I:%M %p')}।")
    if target == "current_time":
        msg = f"স্যার, এখন সময় {now.strftime('%I:%M %p')}."
    elif target == "current_date":
        msg = f"স্যার, আজ {now.strftime('%d %B %Y')}."
    elif target == "current_day":
        msg = f"স্যার, আজ {now.strftime('%A')}."
    elif target == "current_month":
        msg = f"স্যার, এখন {now.strftime('%B')} মাস."
    else:
        msg = f"স্যার, এখন {now.strftime('%A, %d %B %Y %I:%M %p')}."
    return _ok(record, msg)


def _execute_get_system_info(record: SystemActionExample) -> SystemActionExecutionResult:
    target = (record.target or "").casefold()
    try:
        import psutil

        if target == "internet_status":
            msg = "স্যার, ইন্টারনেট কানেকশন ঠিক আছে।" if _internet_ok() else "স্যার, ইন্টারনেট কানেকশনে সমস্যা আছে।"
        elif target == "cpu_usage":
            percent = psutil.cpu_percent(interval=0.5)
            msg = f"স্যার, এই মুহূর্তে CPU usage {percent:.1f}%।"
        elif target == "ram_usage":
            memory = psutil.virtual_memory()
            used_gb = memory.used / (1024 ** 3)
            total_gb = memory.total / (1024 ** 3)
            msg = f"স্যার, RAM ব্যবহার হচ্ছে {used_gb:.1f} GB / {total_gb:.1f} GB, {memory.percent:.1f}%।"
        elif target == "battery_status":
            battery = psutil.sensors_battery()
            if battery is None:
                msg = "স্যার, battery status পাওয়া যায়নি।"
            else:
                plugged = "চার্জে আছে" if battery.power_plugged else "চার্জে নেই"
                msg = f"স্যার, battery {battery.percent:.0f}%, {plugged}।"
        elif target == "storage_status":
            disk = shutil.disk_usage(Path.home().anchor or "C:\\")
            used_gb = disk.used / (1024 ** 3)
            free_gb = disk.free / (1024 ** 3)
            total_gb = disk.total / (1024 ** 3)
            msg = f"স্যার, storage ব্যবহার হচ্ছে {used_gb:.1f} GB, free {free_gb:.1f} GB, total {total_gb:.1f} GB।"
        else:
            msg = "স্যার, system information দেখাচ্ছি।"
        return _ok(record, msg)

        if target == "cpu_usage":
            msg = f"স্যার, CPU usage {int(psutil.cpu_percent(interval=0.2))}%."
        elif target == "ram_usage":
            msg = f"স্যার, RAM usage {int(psutil.virtual_memory().percent)}%."
        elif target == "battery_status":
            battery = psutil.sensors_battery()
            msg = "স্যার, battery তথ্য পাওয়া যায়নি।" if battery is None else f"স্যার, battery {int(battery.percent)}%."
        elif target == "storage_status":
            disk = psutil.disk_usage(str(Path.home().anchor or "C:\\"))
            msg = f"স্যার, storage used {int(disk.percent)}%."
        elif target == "internet_status":
            msg = "স্যার, internet connection active আছে।" if _internet_ok() else "স্যার, internet connection সমস্যা হচ্ছে।"
        else:
            msg = "স্যার, system information দেখাচ্ছি।"
        return _ok(record, msg)
    except Exception as exc:
        return _fail(record, "স্যার, system info নিতে পারিনি।", str(exc))


ACTION_EXECUTORS = {
    "open_folder": _execute_open_folder,
    "open_app": _execute_open_app,
    "toggle_setting": _execute_toggle_setting,
    "set_volume": _execute_set_volume,
    "set_brightness": _execute_set_brightness,
    "window_control": _execute_window_control,
    "power_control": _execute_power_control,
    "media_control": _execute_media_control,
    "get_time_date": _execute_get_time_date,
    "get_system_info": _execute_get_system_info,
}


def _wifi(record: SystemActionExample, *, enable: bool) -> SystemActionExecutionResult:
    adapters = _wifi_adapters()
    if not adapters:
        return _fail(record, "স্যার, WiFi adapter খুঁজে পাইনি।", "adapter_not_found")
    state = "enabled" if enable else "disabled"
    for adapter in adapters:
        completed = subprocess.run(["netsh", "interface", "set", "interface", f"name={adapter}", f"admin={state}"], capture_output=True, text=True, timeout=10, check=False)
        if completed.returncode == 0:
            return _ok(record, "ঠিক আছে স্যার, WiFi অন করছি।" if enable else "ঠিক আছে স্যার, WiFi অফ করছি।")
        output = f"{completed.stdout}\n{completed.stderr}".casefold()
        if any(word in output for word in ("access", "administrator", "denied")):
            return _fail(record, "স্যার, WiFi পরিবর্তন করতে Administrator permission লাগতে পারে।", output)
    return _fail(record, "স্যার, WiFi পরিবর্তন করতে পারিনি।", "netsh_failed")


def _wifi_adapters() -> list[str]:
    completed = subprocess.run(["netsh", "interface", "show", "interface"], capture_output=True, text=True, timeout=10, check=False)
    names: list[str] = []
    for line in (completed.stdout or "").splitlines():
        if any(key in line.casefold() for key in ("wi-fi", "wireless", "wlan")):
            parts = line.split()
            if len(parts) >= 4:
                names.append(" ".join(parts[3:]))
    return names


def _volume(record: SystemActionExample, mode: str, value: int = 50) -> SystemActionExecutionResult:
    target = _volume_target(mode, value)
    if USE_SAFE_VOLUME_KEYS and target in {"volume_up", "volume_down", "mute"}:
        fallback = _volume_key_fallback(record, target)
        if fallback.success:
            return fallback
    try:
        message = execute_volume_target(target)
        return _ok(record, message)
    except ImportError as exc:
        return _fail(record, "স্যার, pycaw/comtypes install করা নেই।", str(exc))
    except Exception as exc:
        return _fail(record, f"স্যার, Windows audio endpoint access করতে সমস্যা হচ্ছে: {exc}", str(exc))


def execute_volume_target(target: str) -> str:
    import pythoncom
    from ctypes import POINTER, cast
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    speakers = None
    interface = None
    volume = None
    pythoncom.CoInitialize()
    try:
        speakers = AudioUtilities.GetSpeakers()
        device = getattr(speakers, "_dev", speakers)
        interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        current = int(round(volume.GetMasterVolumeLevelScalar() * 100))
        LOG.info("[volume] current=%s", current)
        LOG.info("[volume] target=%s", target)
        _safe_print(f"[volume] current={current}")
        _safe_print(f"[volume] target={target}")

        if target == "volume_up":
            new = min(100, current + 10)
            volume.SetMasterVolumeLevelScalar(new / 100.0, None)
            message = f"স্যার, volume বাড়িয়ে {new}% করা হয়েছে।"
        elif target == "volume_down":
            new = max(0, current - 10)
            volume.SetMasterVolumeLevelScalar(new / 100.0, None)
            message = f"স্যার, volume কমিয়ে {new}% করা হয়েছে।"
        elif target.startswith("volume_"):
            new = int(target.split("_", 1)[1])
            new = max(0, min(100, new))
            volume.SetMasterVolumeLevelScalar(new / 100.0, None)
            message = f"স্যার, volume {new}% করা হয়েছে।"
        elif target == "mute":
            volume.SetMute(1, None)
            new = current
            message = "স্যার, volume mute করা হয়েছে।"
        elif target == "unmute":
            volume.SetMute(0, None)
            new = current
            message = "স্যার, volume unmute করা হয়েছে।"
        else:
            raise ValueError(f"unsupported volume target: {target}")

        LOG.info("[volume] new=%s", new)
        _safe_print(f"[volume] new={new}")
        return message
    finally:
        try:
            del volume
            del interface
            del speakers
        except Exception:
            pass
        pythoncom.CoUninitialize()


def _volume_target(mode: str, value: int = 50) -> str:
    if mode == "up":
        return "volume_up"
    if mode == "down":
        return "volume_down"
    if mode == "set":
        return f"volume_{max(0, min(100, int(value)))}"
    return mode


def _volume_key_fallback(record: SystemActionExample, target: str) -> SystemActionExecutionResult:
    key = {
        "volume_down": "volumedown",
        "volume_up": "volumeup",
        "mute": "volumemute",
    }.get(target)
    if not key:
        return _fail(record, "স্যার, exact volume set করতে pycaw লাগবে।", "pycaw_required_for_exact_volume")
    try:
        import pyautogui

        LOG.info("[volume] target=%s", target)
        _safe_print(f"[volume] target={target}")
        pyautogui.press(key)
        if target == "volume_down":
            message = "স্যার, volume কমানো হয়েছে।"
        elif target == "volume_up":
            message = "স্যার, volume বাড়ানো হয়েছে।"
        elif target == "mute":
            message = "স্যার, volume mute করা হয়েছে।"
        else:
            message = "স্যার, volume unmute করা হয়েছে।"
        return _ok(record, message)
    except Exception as exc:
        LOG.warning("[volume] key fallback failed: %s", exc)
        return _fail(record, f"স্যার, volume key control করতে সমস্যা হচ্ছে: {exc}", str(exc))


def _brightness(record: SystemActionExample, mode: str, value: int = 50) -> SystemActionExecutionResult:
    try:
        import screen_brightness_control as sbc

        if mode != "set":
            current = int((sbc.get_brightness(display=0) or [50])[0])
            value = min(100, current + 10) if mode == "up" else max(0, current - 10)
        sbc.set_brightness(max(0, min(100, value)))
        return _ok(record, f"ঠিক আছে স্যার, brightness {value}% করছি।")
    except Exception as exc:
        return _fail(record, "স্যার, brightness control করতে screen-brightness-control লাগবে।", str(exc))


def _screenshot(record: SystemActionExample) -> SystemActionExecutionResult:
    try:
        import pyautogui

        folder = Path(__file__).resolve().parents[2] / "runtime" / "screenshots"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        pyautogui.screenshot().save(path)
        return SystemActionExecutionResult(True, record.intent, record.action, record.target, f"ঠিক আছে স্যার, screenshot save করেছি: {path}", path=str(path))
    except Exception as exc:
        return _fail(record, "স্যার, screenshot নিতে pyautogui লাগবে।", str(exc))


def _hotkey(record: SystemActionExample, keys: list[str], message: str) -> SystemActionExecutionResult:
    try:
        import pyautogui

        pyautogui.hotkey(*keys)
        return _ok(record, message)
    except Exception as exc:
        return _fail(record, "স্যার, window control করতে pyautogui লাগবে।", str(exc))


def _press_key(record: SystemActionExample, key: str, message: str) -> SystemActionExecutionResult:
    try:
        import pyautogui

        pyautogui.press(key)
        return _ok(record, message)
    except Exception as exc:
        return _fail(record, "স্যার, media control করতে pyautogui লাগবে।", str(exc))


def _open_settings(record: SystemActionExample, uri: str, message: str) -> SystemActionExecutionResult:
    subprocess.Popen(["cmd", "/c", "start", "", uri], shell=False)
    return _ok(record, message)


def _open_uri(record: SystemActionExample, uri: str, message: str) -> SystemActionExecutionResult:
    os.startfile(uri)  # type: ignore[attr-defined]
    return _ok(record, message)


def _folder_key(target: str) -> str:
    value = (target or "").casefold()
    if "download" in value:
        return "downloads"
    if "desktop" in value:
        return "desktop"
    if "document" in value:
        return "documents"
    if "picture" in value:
        return "pictures"
    if "video" in value:
        return "videos"
    if "music" in value:
        return "music"
    if "recycle" in value:
        return "recycle_bin"
    if "this pc" in value:
        return "this_pc"
    return value.replace(" folder", "").strip()


def _known_folder_path(folder: str) -> Path | None:
    profile = Path(os.environ.get("USERPROFILE") or Path.home())
    mapping = {
        "downloads": profile / "Downloads",
        "desktop": profile / "Desktop",
        "documents": profile / "Documents",
        "pictures": profile / "Pictures",
        "videos": profile / "Videos",
        "music": profile / "Music",
        "project": Path(__file__).resolve().parents[3],
    }
    return mapping.get(folder)


def _app_key(target: str) -> str:
    value = (target or "").casefold()
    return {
        "calculator": "calculator",
        "notepad": "notepad",
        "chrome": "chrome",
        "microsoft edge": "edge",
        "control panel": "control panel",
        "file explorer": "file explorer",
        "settings": "settings",
        "task manager": "task manager",
        "command prompt": "cmd",
        "powershell": "powershell",
    }.get(value, value)


def _target_number(target: str) -> int:
    digits = "".join(ch for ch in target if ch.isdigit())
    return int(digits) if digits else 50


def _wants_on(text: str) -> bool:
    value = (text or "").casefold()
    if any(word in value for word in ("off", "disable", "বন্ধ", "অফ")):
        return False
    return True


def _is_dangerous(record: SystemActionExample) -> bool:
    return (record.target or "").casefold() in DANGEROUS_TARGETS


def _confirm_message(target: str) -> str:
    action = (target or "").replace("_pc", "").replace("_", " ")
    return f"স্যার, আপনি কি নিশ্চিত? confirm {action} বললে {action} হবে।"
    label = (target or "").replace("_pc", "").replace("_window", " window").replace("_", " ")
    return f"স্যার, আপনি কি নিশ্চিত? বলুন confirm {label}."


def _ok(record: SystemActionExample, message: str) -> SystemActionExecutionResult:
    return SystemActionExecutionResult(True, record.intent, record.action, record.target, message, message)


def _fail(record: SystemActionExample, message: str, error: str) -> SystemActionExecutionResult:
    return SystemActionExecutionResult(False, record.intent, record.action, record.target, message, message, error=error)


def _missing_target(record: SystemActionExample) -> SystemActionExecutionResult:
    msg = f"স্যার, এই action-এর code এখনো implement করা হয়নি: {record.action} {record.target}"
    LOG.warning("[system-action] missing executor for action=%s target=%s", record.action, record.target)
    return SystemActionExecutionResult(False, record.intent, record.action, record.target, msg, msg, error="missing_target")


def _internet_ok() -> bool:
    try:
        with socket.create_connection(("google.com", 443), timeout=3):
            return True
    except OSError:
        return False
    return shutil.which("ping") is not None and subprocess.run(["ping", "-n", "1", "google.com"], capture_output=True, text=True, timeout=5, check=False).returncode == 0
