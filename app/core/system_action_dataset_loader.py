from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.command_normalizer import normalize_voice_command

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class SystemActionExample:
    id: str
    intent: str
    action: str
    target: str
    instruction: str
    response: str
    speak_text: str
    normalized: str


def _assets_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "assets"


@lru_cache(maxsize=1)
def load_system_action_examples() -> tuple[SystemActionExample, ...]:
    paths = [
        _assets_dir() / "system_action_dataset_500.jsonl",
        _assets_dir() / "system_action_dataset.txt",
    ]
    examples: list[SystemActionExample] = []
    for path in paths:
        if not path.exists():
            continue
        if path.suffix.lower() == ".jsonl":
            examples.extend(_load_jsonl(path))
        else:
            examples.extend(_load_text(path))
        if examples:
            break
    LOG.info("[dataset] loaded system action examples: %s", len(examples))
    LOG.info("[dataset] loaded: %s", len(examples))
    print(f"[dataset] loaded system action examples: {len(examples)}")
    print(f"[dataset] loaded: {len(examples)}")
    return tuple(examples)


def match_system_action(text: str, normalized: str = "") -> SystemActionExample | None:
    LOG.info("[system-action] input: %s", text)
    haystack = _norm(f"{text} {normalized}")
    direct = _norm(text)
    if not haystack:
        return None
    hard = _match_hard_rule(text, direct, haystack)
    if hard is not None:
        LOG.info(
            "[system-action] matched id=%s intent=%s action=%s target=%s",
            hard.id,
            hard.intent,
            hard.action,
            hard.target,
        )
        return hard
    examples = load_system_action_examples()
    best: tuple[int, SystemActionExample] | None = None
    for example in examples:
        instruction = _norm(example.instruction)
        if instruction and instruction == direct:
            LOG.info(
                "[system-action] matched id=%s intent=%s action=%s target=%s",
                example.id,
                example.intent,
                example.action,
                example.target,
            )
            return example

    alias = _match_alias_rule(direct, haystack)
    if alias is not None:
        LOG.info(
            "[system-action] matched id=%s intent=%s action=%s target=%s",
            alias.id,
            alias.intent,
            alias.action,
            alias.target,
        )
        return alias

    for example in examples:
        instruction = _norm(example.instruction)
        needles = {
            example.normalized,
            instruction,
            _norm(example.target),
            _norm(example.intent),
            _norm(example.action),
        }
        target_norm = _norm(example.target)
        target_core = " ".join(token for token in target_norm.split() if token not in {"folder", "pc"})
        if target_core and all(token in haystack.split() for token in target_core.split()):
            score = len(target_core)
            if best is None or score > best[0]:
                best = (score, example)
        for needle in needles:
            if not needle:
                continue
            if needle == haystack:
                return example
            if len(needle) >= 4 and (needle in haystack or haystack in needle):
                score = len(needle)
                if best is None or score > best[0]:
                    best = (score, example)
    matched = best[1] if best and best[0] >= 4 else None
    if matched is not None:
        LOG.info(
            "[system-action] matched id=%s intent=%s action=%s target=%s",
            matched.id,
            matched.intent,
            matched.action,
            matched.target,
        )
    return matched


def match_dataset_action(text: str, normalized: str = "") -> SystemActionExample | None:
    return match_system_action(text, normalized)


def _match_hard_rule(text: str, direct: str, haystack: str) -> SystemActionExample | None:
    raw = f" {(text or '').casefold()} "
    value = f" {haystack} "

    if any(alias in raw for alias in (" আনমিউট", " unmute", "মিউট খুলে", "mute khule", "mute খুলে")):
        return _synthetic("hard_unmute", "volume_control", "set_volume", "unmute", "স্যার, volume unmute করছি।")
    if " মিউট" in raw or " mute" in raw or direct == "মিউট" or direct == "mute":
        return _synthetic("hard_mute", "volume_control", "set_volume", "mute", "স্যার, volume mute করছি।")

    if any(alias in raw for alias in ("ব্লুটুথ অফ", "bluetooth off", "bluetooth bondho", "ব্লুটুথ বন্ধ")):
        return _synthetic("hard_bluetooth_off", "toggle_setting", "toggle_setting", "bluetooth_off", "স্যার, Bluetooth settings খুলছি।")
    if any(alias in raw for alias in ("ব্লুটুথ অন", "bluetooth on", "bluetooth chalu", "ব্লুটুথ চালু")):
        return _synthetic("hard_bluetooth_on", "toggle_setting", "toggle_setting", "bluetooth_on", "স্যার, Bluetooth settings খুলছি।")

    if any(alias in raw for alias in ("স্ক্রিনশট", "স্ক্রীনশট", "screenshot", "screen capture")):
        return _synthetic("hard_screenshot", "window_control", "window_control", "screenshot", "স্যার, screenshot নিচ্ছি।")

    if any(alias in raw for alias in ("ডাউনলোড ফোল্ডার", "ডাউনলোডস", "ডাউনলোড", "downloads", "download folder")):
        return _synthetic("hard_downloads_folder", "open_folder", "open_folder", "Downloads folder", "স্যার, Downloads খুলছি।")

    if any(alias in raw for alias in ("ডেস্কটপ", "ডেক্সটপ", "desktop")):
        return _synthetic("hard_desktop_folder", "open_folder", "open_folder", "Desktop folder", "স্যার, Desktop খুলছি।")

    return None


def _match_alias_rule(direct: str, haystack: str) -> SystemActionExample | None:
    value = f" {haystack} "
    compact = " ".join(haystack.split())

    if "volume" in value or "ভলিউম" in value or "sound" in value or "mute" in value or "মিউট" in value:
        if "unmute" in value or "sound chalu" in value:
            return _synthetic("rule_unmute", "volume_control", "set_volume", "unmute", "ঠিক আছে স্যার, sound চালু করছি।")
        if "mute" in value or "ভলিউম মিউট" in value or "মিউট" in value:
            return _synthetic("rule_mute", "volume_control", "set_volume", "mute", "ঠিক আছে স্যার, volume mute করছি।")
        if "volume full" in value:
            return _synthetic("rule_volume_100", "volume_control", "set_volume", "volume_100", "ঠিক আছে স্যার, volume 100 করছি।")
        volume_number = re.search(r"\bvolume\s+(25|50|75|100)\b", compact)
        if volume_number:
            number = volume_number.group(1)
            return _synthetic(f"rule_volume_{number}", "volume_control", "set_volume", f"volume_{number}", f"ঠিক আছে স্যার, volume {number} করছি।")
        if "volume komao" in value or "volume decrease" in value or "ভলিউম কমাও" in value:
            return _synthetic("rule_volume_down", "volume_control", "set_volume", "volume_down", "ঠিক আছে স্যার, volume কমাচ্ছি।")
        if "volume barao" in value or "volume baraw" in value or "volume increase" in value or "ভলিউম বাড়াও" in value or "ভলিউম বাড়াও" in value:
            return _synthetic("rule_volume_up", "volume_control", "set_volume", "volume_up", "ঠিক আছে স্যার, volume বাড়াচ্ছি।")

    if _contains_any(value, ("shutdown", "pc shutdown", "পিসি বন্ধ", "computer bondho")):
        return _synthetic("rule_shutdown_pc", "power_control", "power_control", "shutdown_pc", "স্যার, আপনি কি নিশ্চিত? confirm shutdown বললে shutdown হবে।")
    if _contains_any(value, ("restart", "রিস্টার্ট")):
        return _synthetic("rule_restart_pc", "power_control", "power_control", "restart_pc", "স্যার, আপনি কি নিশ্চিত? confirm restart বললে restart হবে।")
    if _contains_any(value, ("sleep", "স্লিপ")):
        return _synthetic("rule_sleep_pc", "power_control", "power_control", "sleep_pc", "স্যার, আপনি কি নিশ্চিত? confirm sleep বললে sleep হবে।")
    if _contains_any(value, ("logout", "sign out")):
        return _synthetic("rule_sign_out", "power_control", "power_control", "sign_out", "স্যার, আপনি কি নিশ্চিত? confirm sign out বললে sign out হবে।")
    if _contains_any(value, ("lock", "লক")):
        return _synthetic("rule_lock_pc", "power_control", "power_control", "lock_pc", "ঠিক আছে স্যার, screen lock করছি।")

    if _contains_any(value, ("internet check", "ইন্টারনেট আছে কিনা")):
        return _synthetic("rule_internet_status", "system_info", "get_system_info", "internet_status", "স্যার, ইন্টারনেট কানেকশন চেক করছি।")
    if _contains_any(value, ("cpu usage", "সিপিউ ইউজেজ")):
        return _synthetic("rule_cpu_usage", "system_info", "get_system_info", "cpu_usage", "স্যার, CPU usage দেখছি।")
    if _contains_any(value, ("ram usage", "র‍্যাম কত ইউজ", "র্যাম কত ইউজ")):
        return _synthetic("rule_ram_usage", "system_info", "get_system_info", "ram_usage", "স্যার, RAM usage দেখছি।")
    if _contains_any(value, ("battery status", "battery koto ache")):
        return _synthetic("rule_battery_status", "system_info", "get_system_info", "battery_status", "স্যার, battery status দেখছি।")
    if _contains_any(value, ("storage status", "disk space")):
        return _synthetic("rule_storage_status", "system_info", "get_system_info", "storage_status", "স্যার, storage status দেখছি।")

    if _contains_any(value, ("koita baje", "time bolo")):
        return _synthetic("rule_current_time", "time_date", "get_time_date", "current_time", "স্যার, সময় বলছি।")
    if _contains_any(value, ("date bolo", "আজকের তারিখ")):
        return _synthetic("rule_current_date", "time_date", "get_time_date", "current_date", "স্যার, আজকের তারিখ বলছি।")
    if _contains_any(value, ("aj ki bar", "আজ কী বার")):
        return _synthetic("rule_current_day", "time_date", "get_time_date", "current_day", "স্যার, আজ কী বার বলছি।")
    if _contains_any(value, ("month bolo", "এখন কোন মাস")):
        return _synthetic("rule_current_month", "time_date", "get_time_date", "current_month", "স্যার, মাস বলছি।")

    return None


def _contains_any(value: str, aliases: tuple[str, ...]) -> bool:
    return any(_norm(alias) in value for alias in aliases)


def _synthetic(id_: str, intent: str, action: str, target: str, response: str) -> SystemActionExample:
    return SystemActionExample(
        id=id_,
        intent=intent,
        action=action,
        target=target,
        instruction="",
        response=response,
        speak_text=response,
        normalized=_norm(f"{intent} {action} {target}"),
    )


def _load_jsonl(path: Path) -> list[SystemActionExample]:
    out: list[SystemActionExample] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    for line in lines:
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        out.append(_from_mapping(item))
    return out


def _load_text(path: Path) -> list[SystemActionExample]:
    out: list[SystemActionExample] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        instruction = line.strip()
        if not instruction:
            continue
        out.append(
            SystemActionExample(
                id=f"txt_{len(out) + 1:04d}",
                intent="system_action",
                action="system_action",
                target="",
                instruction=instruction,
                response="ঠিক আছে স্যার, কাজটি করছি।",
                speak_text="ঠিক আছে স্যার, কাজটি করছি।",
                normalized=_norm(instruction),
            )
        )
    return out


def _from_mapping(item: dict) -> SystemActionExample:
    instruction = str(item.get("instruction") or "")
    target = str(item.get("target") or "")
    intent = str(item.get("intent") or "")
    action = str(item.get("action") or "")
    response = str(item.get("response") or "")
    speak_text = str(item.get("speak_text") or response)
    return SystemActionExample(
        id=str(item.get("id") or ""),
        intent=intent,
        action=action,
        target=target,
        instruction=instruction,
        response=response,
        speak_text=speak_text,
        normalized=_norm(f"{instruction} {target} {intent} {action}"),
    )


def _norm(text: str) -> str:
    return normalize_voice_command(text, log=False).casefold().replace("য়", "য়")
