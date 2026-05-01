from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Literal

from app.core.alias_command_matcher import ALIAS_CONFIRM_THRESHOLD
from app.core.alias_command_matcher import AliasMatch
from app.core.command_normalizer import normalize_voice_command
from app.core.system_action_dataset_loader import SystemActionExample
from app.services.system.system_action_executor import is_confirm_command as is_dataset_confirm_command
from app.actions.web_actions import is_web_or_weather_query
from app.intents.alias_matcher import match_alias
from app.intents.dataset_matcher import match_dataset
from app.intents.hard_rules import match_hard_rule

LOG = logging.getLogger(__name__)

RouteKind = Literal["system_action", "alias_action", "volume_clarification", "pending_confirmation", "web_action"]


@dataclass(frozen=True)
class CommandRoute:
    kind: RouteKind
    original_text: str
    normalized_text: str
    source: str
    corrected_text: str = ""
    match: Any | None = None
    system_record: SystemActionExample | None = None
    alias_match: AliasMatch | None = None
    pending_alias_action: dict | None = None
    pending_system_confirmation: str = ""
    clear_pending_alias: bool = False
    pending_confidence_valid: bool = True

    @property
    def text(self) -> str:
        return self.original_text

    @property
    def normalized(self) -> str:
        return self.normalized_text


class CommandRouter:
    """Thin orchestration layer for command matching.

    The router decides which path should handle a command. It does not execute
    actions or build UI response dictionaries.
    """

    @staticmethod
    def route(
        text: str,
        *,
        pending_alias_action: dict | None = None,
        pending_system_confirmation: str = "",
        mode: str = "chat",
    ) -> CommandRoute | None:
        normalized = normalize_voice_command(text, log=False)
        corrected_text = apply_voice_text_correction(text)
        corrected_normalized = normalize_voice_command(corrected_text, log=False)
        LOG.info("[router] normalized=%r", normalized)

        if pending_alias_action is not None:
            if is_alias_confirm_command(text):
                confidence = float(pending_alias_action.get("confidence") or 0.0)
                return CommandRoute(
                    kind="pending_confirmation",
                    original_text=text,
                    normalized_text=normalized,
                    corrected_text=corrected_text,
                    source="pending_alias",
                    pending_alias_action=pending_alias_action,
                    pending_confidence_valid=confidence >= ALIAS_CONFIRM_THRESHOLD,
                )
            return CommandRoute(
                kind="pending_confirmation",
                original_text=text,
                normalized_text=normalized,
                corrected_text=corrected_text,
                source="pending_alias_clear",
                clear_pending_alias=True,
            )

        if pending_system_confirmation and is_dataset_confirm_command(text):
            return CommandRoute(
                kind="pending_confirmation",
                original_text=text,
                normalized_text=normalized,
                corrected_text=corrected_text,
                source="pending_system",
                pending_system_confirmation=pending_system_confirmation,
            )

        if corrected_normalized.strip().casefold() == "volume":
            return CommandRoute(
                kind="volume_clarification",
                original_text=text,
                normalized_text=normalized,
                corrected_text=corrected_text,
                source="volume_clarification",
            )

        hard_record = match_hard_rule(corrected_text, corrected_normalized)
        if hard_record is not None:
            return CommandRoute(
                kind="system_action",
                original_text=text,
                normalized_text=normalized,
                corrected_text=corrected_text,
                source="hard_rules",
                match=hard_record,
                system_record=hard_record,
            )

        dataset_record = match_dataset(corrected_text, corrected_normalized)
        if dataset_record is not None:
            return CommandRoute(
                kind="system_action",
                original_text=text,
                normalized_text=normalized,
                corrected_text=corrected_text,
                source="dataset_matcher",
                match=dataset_record,
                system_record=dataset_record,
            )

        alias_match = match_alias(corrected_text)
        if alias_match is not None and (alias_match.should_execute or alias_match.should_confirm):
            return CommandRoute(
                kind="alias_action",
                original_text=text,
                normalized_text=normalized,
                corrected_text=corrected_text,
                source="alias_matcher",
                match=alias_match,
                alias_match=alias_match,
            )

        if is_web_or_weather_query(text, normalized, mode):
            return CommandRoute(
                kind="web_action",
                original_text=text,
                normalized_text=normalized,
                corrected_text=corrected_text,
                source="web_actions",
                match={"mode": mode},
            )

        return None


def apply_voice_text_correction(text: str) -> str:
    before = text or ""
    after = before
    replacements = (
        ("আনমিউট", "unmute"),
        ("ভলিউম", "volume"),
        ("ভলিওম", "volume"),
        ("voliom", "volume"),
        ("কম", "decrease"),
        ("কমাও", "decrease"),
        ("komao", "decrease"),
        ("বাড়", "increase"),
        ("বাড়", "increase"),
        ("বাড়াও", "increase"),
        ("বাড়াও", "increase"),
        ("baraw", "increase"),
        ("মিউট", "mute"),
    )
    for source, target in replacements:
        if source.isascii():
            after = re.sub(rf"\b{re.escape(source)}\b", target, after, flags=re.IGNORECASE)
        else:
            after = after.replace(source, target)
    if after != before:
        LOG.info("[voice-correction] before=%s after=%s", before, after)
        print(f"[voice-correction] before={before} after={after}")
    return after


def is_alias_confirm_command(text: str) -> bool:
    value = normalize_voice_command(text, log=False).casefold()
    raw = (text or "").casefold()
    return is_dataset_confirm_command(text) or value in {"yes", "y", "ha", "haa"} or raw in {"হ্যাঁ", "হাঁ", "হ্যা"}


def route_command(text: str) -> CommandRoute | None:
    return CommandRouter.route(text)
