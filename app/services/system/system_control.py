from __future__ import annotations
"""Legacy system-control compatibility module.

Architecture note:
    New dataset-backed routes should go through
    app.services.system.system_action_executor via app.actions.system_actions.
    This module is still imported for confirmed actions and legacy fallback
    paths, so keep it until those callers are migrated.
"""

import ctypes
import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from app.core.command_normalizer import normalize_voice_command

LOG = logging.getLogger(__name__)
USE_SAFE_VOLUME_KEYS = True


@dataclass
class SystemControlResult:
    success: bool
    intent: str
    action: str
    target: str
    message: str
    speak_text: str = ""
    path: str = ""
    candidates: list[str] = field(default_factory=list)
    error: str = ""
    requires_confirmation: bool = False


DANGEROUS_TARGETS = {"shutdown_confirm", "restart_confirm", "sleep_confirm", "close_current_window"}


def match_system_action(text: str, dataset_match=None) -> dict | None:
    normalized = _norm(text)
    if dataset_match is not None:
        mapped = _map_dataset_target(dataset_match.intent, dataset_match.action, dataset_match.target, normalized)
        if mapped:
            return mapped
    return _rule_match(normalized)


def execute_system_action(match: dict) -> SystemControlResult:
    target = str(match.get("target") or "")
    intent = str(match.get("intent") or target or "system_action")
    LOG.info("[system-control] executing: %s", target)
    if target in DANGEROUS_TARGETS:
        return SystemControlResult(False, intent, "confirm_required", target, _confirm_message(target), requires_confirmation=True)
    record = _legacy_match_to_record(match)
    if record is not None:
        from app.services.system.system_action_executor import execute_system_action as execute_canonical_system_action

        return _from_canonical_result(execute_canonical_system_action(record), fallback_intent=intent)
    try:
        if target == "wifi_on":
            return _wifi(True)
        if target == "wifi_off":
            return _wifi(False)
        if target == "bluetooth_on":
            return _open_settings("ms-settings:bluetooth", "bluetooth_on", "স্যার, Bluetooth settings খুলেছি। এখানে থেকে অন করতে পারবেন।")
        if target == "bluetooth_off":
            return _open_settings("ms-settings:bluetooth", "bluetooth_off", "স্যার, Bluetooth settings খুলেছি। এখানে থেকে অফ করতে পারবেন।")
        if target == "volume_up":
            return _volume("up")
        if target == "volume_down":
            return _volume("down")
        if target.startswith("volume_"):
            digits = "".join(ch for ch in target if ch.isdigit())
            return _volume("set", int(digits) if digits else 50)
        if target == "mute":
            return _volume("mute")
        if target == "unmute":
            return _volume("unmute")
        if target == "brightness_up":
            return _brightness("up")
        if target == "brightness_down":
            return _brightness("down")
        if target == "brightness_set":
            return _brightness("set", int(match.get("value") or 50))
        if target == "screenshot":
            return _screenshot()
        if target == "lock_screen":
            ctypes.windll.user32.LockWorkStation()
            return _ok("lock_screen", "lock_screen", "ঠিক আছে স্যার, screen lock করছি।")
        if target == "minimize_window":
            return _hotkey("minimize_window", ["win", "down"], "ঠিক আছে স্যার, window minimize করছি।")
        if target == "maximize_window":
            return _hotkey("maximize_window", ["win", "up"], "ঠিক আছে স্যার, window maximize করছি।")
        if target == "alt_tab":
            return _hotkey("alt_tab", ["alt", "tab"], "ঠিক আছে স্যার, window switch করছি।")
        if target in DANGEROUS_TARGETS:
            return SystemControlResult(False, intent, "confirm_required", target, _confirm_message(target), requires_confirmation=True)
    except Exception as exc:
        LOG.exception("[system-control] failed: %s", exc)
        return SystemControlResult(False, intent, "system_control", target, f"স্যার, কাজটি করতে পারিনি: {exc}", error=str(exc))
    return SystemControlResult(False, intent, "system_control", target, "স্যার, এই system action এখনো support করা হয়নি।", error="unsupported")


def execute_confirmed_action(target: str) -> SystemControlResult:
    LOG.info("[system-control] executing confirmed: %s", target)
    from app.services.system.system_action_executor import execute_confirmed_dataset_action

    return _from_canonical_result(execute_confirmed_dataset_action(target), fallback_intent="confirm")


def _legacy_match_to_record(match: dict):
    from app.core.system_action_dataset_loader import SystemActionExample

    target = str(match.get("target") or "")
    value = int(match.get("value") or 50)
    action = ""
    canonical_target = target
    if target in {"wifi_on", "wifi_off", "bluetooth_on", "bluetooth_off"}:
        action = "toggle_setting"
    elif target in {"volume_up", "volume_down", "mute", "unmute"} or target.startswith("volume_"):
        action = "set_volume"
    elif target in {"brightness_up", "brightness_down"}:
        action = "set_brightness"
    elif target == "brightness_set":
        action = "set_brightness"
        canonical_target = f"brightness_{max(0, min(100, value))}"
    elif target in {"screenshot", "minimize_window", "maximize_window"}:
        action = "window_control"
    elif target == "alt_tab":
        action = "window_control"
        canonical_target = "switch_window"
    elif target == "lock_screen":
        action = "power_control"
        canonical_target = "lock_pc"
    else:
        return None

    intent = str(match.get("intent") or target or "system_action")
    return SystemActionExample(
        id=f"legacy_system_control_{target}",
        intent=intent,
        action=action,
        target=canonical_target,
        instruction=target,
        response="",
        speak_text="",
        normalized=_norm(f"{intent} {action} {canonical_target}"),
    )


def _from_canonical_result(result, fallback_intent: str = "system_action") -> SystemControlResult:
    response = getattr(result, "response", "") or getattr(result, "message", "")
    return SystemControlResult(
        bool(getattr(result, "success", False)),
        str(getattr(result, "intent", "") or fallback_intent),
        str(getattr(result, "action", "") or "system_control"),
        str(getattr(result, "target", "") or fallback_intent),
        response,
        str(getattr(result, "speak_text", "") or response),
        path=str(getattr(result, "path", "") or ""),
        candidates=list(getattr(result, "candidates", []) or []),
        error=str(getattr(result, "error", "") or ""),
        requires_confirmation=bool(getattr(result, "requires_confirmation", False)),
    )


def is_confirm_command(text: str, pending_target: str = "") -> bool:
    normalized = _norm(text)
    if "confirm" in normalized or "কনফার্ম" in normalized or "নিশ্চিত" in normalized:
        if not pending_target:
            return True
        return pending_target.replace("_confirm", "").replace("_", " ") in normalized or True
    return False


def _map_dataset_target(intent: str, action: str, target: str, normalized: str) -> dict | None:
    haystack = _norm(f"{intent} {action} {target} {normalized}")
    if "wifi" in haystack or "wireless" in haystack or "ওয়াইফাই" in haystack or "ওয়াইফাই" in haystack:
        turn_on = _has_on(haystack) or not _has_off(haystack)
        return {"intent": "wifi_on" if turn_on else "wifi_off", "target": "wifi_on" if turn_on else "wifi_off"}
    if "bluetooth" in haystack or "ব্লুটুথ" in haystack:
        turn_on = _has_on(haystack) or not _has_off(haystack)
        return {"intent": "bluetooth_on" if turn_on else "bluetooth_off", "target": "bluetooth_on" if turn_on else "bluetooth_off"}
    if "volume_up" in haystack or "volume" in haystack or "sound" in haystack or "ভলিউম" in haystack:
        if _has_off(haystack) or "mute" in haystack:
            return {"intent": "mute", "target": "mute"}
        if "unmute" in haystack:
            return {"intent": "unmute", "target": "unmute"}
        if _has_up(haystack):
            return {"intent": "volume_up", "target": "volume_up"}
        if _has_down(haystack):
            return {"intent": "volume_down", "target": "volume_down"}
    if "volume_up" in haystack or "barao" in haystack or "বাড়াও" in haystack or "বাড়াও" in haystack or "ভলিউম বাড়" in haystack or "ভলিউম বাড়" in haystack or "sound barao" in haystack:
        return {"intent": "volume_up", "target": "volume_up"}
    if "volume_down" in haystack or "komao" in haystack or "কমান" in haystack or "কমাও" in haystack:
        return {"intent": "volume_down", "target": "volume_down"}
    if "unmute" in haystack:
        return {"intent": "unmute", "target": "unmute"}
    if "mute" in haystack:
        return {"intent": "mute", "target": "mute"}
    if "brightness" in haystack or "ব্রাইটনেস" in haystack:
        value = _number(haystack)
        if value is not None:
            return {"intent": "brightness_set", "target": "brightness_set", "value": value}
        return {"intent": "brightness_up" if _has_up(haystack) else "brightness_down", "target": "brightness_up" if _has_up(haystack) else "brightness_down"}
    if "screenshot" in haystack or "screen capture" in haystack or "স্ক্রিনশট" in haystack:
        return {"intent": "screenshot", "target": "screenshot"}
    if "lock" in haystack and "screen" in haystack:
        return {"intent": "lock_screen", "target": "lock_screen"}
    if "shutdown" in haystack:
        return {"intent": "shutdown_confirm", "target": "shutdown_confirm"}
    if "restart" in haystack:
        return {"intent": "restart_confirm", "target": "restart_confirm"}
    if "sleep" in haystack:
        return {"intent": "sleep_confirm", "target": "sleep_confirm"}
    if "minimize" in haystack:
        return {"intent": "minimize_window", "target": "minimize_window"}
    if "maximize" in haystack:
        return {"intent": "maximize_window", "target": "maximize_window"}
    if "alt tab" in haystack or "switch window" in haystack:
        return {"intent": "alt_tab", "target": "alt_tab"}
    return None


def _rule_match(normalized: str) -> dict | None:
    return _map_dataset_target("", "", "", normalized)


def _wifi(enable: bool) -> SystemControlResult:
    adapters = _wifi_adapters()
    if not adapters:
        return SystemControlResult(False, "wifi_on" if enable else "wifi_off", "netsh", "wifi", "স্যার, WiFi adapter খুঁজে পাইনি।", error="adapter_not_found")
    target_state = "enabled" if enable else "disabled"
    for adapter in adapters:
        cmd = ["netsh", "interface", "set", "interface", f'name={adapter}', f"admin={target_state}"]
        LOG.info("[system-control] executing: %s", cmd)
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
        if completed.returncode == 0:
            msg = "ঠিক আছে স্যার, WiFi অন করছি।" if enable else "ঠিক আছে স্যার, WiFi অফ করছি।"
            LOG.info("[system-control] success: %s", msg)
            return _ok("wifi_on" if enable else "wifi_off", "netsh", msg)
        output = f"{completed.stdout}\n{completed.stderr}".lower()
        if "access" in output or "administrator" in output or "denied" in output:
            return SystemControlResult(False, "wifi_on" if enable else "wifi_off", "netsh", "স্যার, WiFi পরিবর্তন করতে Administrator permission লাগতে পারে।", error=output)
    return SystemControlResult(False, "wifi_on" if enable else "wifi_off", "netsh", "স্যার, WiFi পরিবর্তন করতে পারিনি।", error="netsh_failed")


def _wifi_adapters() -> list[str]:
    completed = subprocess.run(["netsh", "interface", "show", "interface"], capture_output=True, text=True, timeout=10, check=False)
    names: list[str] = []
    for line in (completed.stdout or "").splitlines():
        if any(key in line.lower() for key in ("wi-fi", "wireless", "wlan")):
            parts = line.split()
            if parts:
                names.append(" ".join(parts[3:]) if len(parts) > 3 else parts[-1])
    return [name for name in names if name]


def _open_settings(uri: str, intent: str, message: str) -> SystemControlResult:
    subprocess.Popen(["cmd", "/c", "start", "", uri], shell=False)
    return _ok(intent, "open_settings", message)


def _volume(mode: str, value: int = 50) -> SystemControlResult:
    target = _volume_target(mode, value)
    if USE_SAFE_VOLUME_KEYS and target in {"volume_up", "volume_down", "mute"}:
        fallback = _volume_key_fallback(target)
        if fallback.success:
            return fallback
    try:
        message = execute_volume_target(target)
        return _ok(target, "set_volume", message)
    except ImportError as exc:
        return SystemControlResult(False, f"volume_{mode}", "set_volume", f"volume_{mode}", "স্যার, pycaw/comtypes install করা নেই।", error=str(exc))
    except Exception as exc:
        return SystemControlResult(False, f"volume_{mode}", "set_volume", f"volume_{mode}", f"স্যার, Windows audio endpoint access করতে সমস্যা হচ্ছে: {exc}", error=str(exc))


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


def _volume_key_fallback(target: str) -> SystemControlResult:
    key = {
        "volume_down": "volumedown",
        "volume_up": "volumeup",
        "mute": "volumemute",
    }.get(target)
    if not key:
        return SystemControlResult(False, target, "set_volume", target, "স্যার, exact volume set করতে pycaw লাগবে।", error="pycaw_required_for_exact_volume")
    try:
        import pyautogui

        LOG.info("[volume] target=%s", target)
        pyautogui.press(key)
        if target == "volume_down":
            message = "স্যার, volume কমানো হয়েছে।"
        elif target == "volume_up":
            message = "স্যার, volume বাড়ানো হয়েছে।"
        elif target == "mute":
            message = "স্যার, volume mute করা হয়েছে।"
        else:
            message = "স্যার, volume unmute করা হয়েছে।"
        return _ok(target, "set_volume", message)
    except Exception as exc:
        LOG.warning("[volume] key fallback failed: %s", exc)
        return SystemControlResult(False, target, "set_volume", target, f"স্যার, volume key control করতে সমস্যা হচ্ছে: {exc}", error=str(exc))


def _brightness(mode: str, value: int = 50) -> SystemControlResult:
    try:
        import screen_brightness_control as sbc

        current = int((sbc.get_brightness(display=0) or [50])[0])
        if mode == "up":
            value = min(100, current + 10)
        elif mode == "down":
            value = max(0, current - 10)
        else:
            value = max(0, min(100, int(value)))
        sbc.set_brightness(value)
        return _ok("brightness_set", "set_brightness", f"ঠিক আছে স্যার, brightness {value}% করছি।")
    except Exception as exc:
        return SystemControlResult(False, f"brightness_{mode}", "set_brightness", f"brightness_{mode}", "স্যার, brightness control করতে screen-brightness-control লাগবে।", error=str(exc))


def _screenshot() -> SystemControlResult:
    try:
        import pyautogui

        folder = Path(__file__).resolve().parents[2] / "runtime" / "screenshots"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "screenshot.png"
        counter = 1
        while path.exists():
            path = folder / f"screenshot_{counter}.png"
            counter += 1
        pyautogui.screenshot().save(path)
        return SystemControlResult(True, "screenshot", "screenshot", "screenshot", f"ঠিক আছে স্যার, screenshot save করেছি: {path}", path=str(path))
    except Exception as exc:
        return SystemControlResult(False, "screenshot", "screenshot", "screenshot", "স্যার, screenshot নিতে pyautogui লাগবে।", error=str(exc))


def _hotkey(intent: str, keys: list[str], message: str) -> SystemControlResult:
    try:
        import pyautogui

        pyautogui.hotkey(*keys)
        return _ok(intent, "hotkey", message)
    except Exception as exc:
        return SystemControlResult(False, intent, "hotkey", intent, "স্যার, window control করতে pyautogui লাগবে।", error=str(exc))


def _ok(intent: str, action: str, message: str) -> SystemControlResult:
    LOG.info("[system-control] success: %s", message)
    return SystemControlResult(True, intent, action, intent, message, speak_text=message)


def _confirm_message(target: str) -> str:
    label = target.replace("_confirm", "").replace("_", " ")
    return f"স্যার, আপনি কি নিশ্চিত? বলুন confirm {label}."


def _has_on(value: str) -> bool:
    return any(word in value for word in (" on", "enable", "turn on", "open", "চালু", "অন"))


def _has_off(value: str) -> bool:
    return any(word in value for word in (" off", "disable", "turn off", "বন্ধ", "অফ"))


def _has_up(value: str) -> bool:
    return any(word in value for word in ("up", "increase", "barao", "baraw", "বাড়", "বাড়", "বৃদ্ধি"))


def _has_down(value: str) -> bool:
    return any(word in value for word in ("down", "decrease", "komao", "কম", "কমান"))


def _number(value: str) -> int | None:
    value = value.translate(str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789"))
    match = re.search(r"\b(\d{1,3})\b", value)
    if not match:
        return None
    return max(0, min(100, int(match.group(1))))


def _norm(text: str) -> str:
    value = normalize_voice_command(text, log=False).casefold().replace("য়", "য়")
    value = value.replace("wi fi", "wifi").replace("ওয়াইফাই", "ওয়াইফাই")
    return value
