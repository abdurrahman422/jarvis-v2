from __future__ import annotations

import logging
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.core.alias_dataset_loader import AliasAction, load_alias_actions
from app.core.command_normalizer import normalize_voice_command

LOG = logging.getLogger(__name__)

ALIAS_EXECUTE_THRESHOLD = 0.90
ALIAS_CONFIRM_THRESHOLD = 0.78


@dataclass(frozen=True)
class AliasMatch:
    action: AliasAction
    confidence: float
    matched_alias: str
    normalized_text: str

    @property
    def should_execute(self) -> bool:
        return self.confidence >= ALIAS_EXECUTE_THRESHOLD

    @property
    def should_confirm(self) -> bool:
        return ALIAS_CONFIRM_THRESHOLD <= self.confidence < ALIAS_EXECUTE_THRESHOLD


def match_alias_command(text: str) -> AliasMatch | None:
    normalized = _norm(text)
    if not normalized:
        return None

    best: AliasMatch | None = None
    for action in load_alias_actions():
        for alias in action.normalized_aliases:
            score = _score(normalized, alias)
            if best is None or score > best.confidence:
                best = AliasMatch(action=action, confidence=score, matched_alias=alias, normalized_text=normalized)

    if best is None:
        LOG.info("[alias-match] no dataset actions")
        return None

    LOG.info(
        "[alias-match] input=%r normalized=%r id=%s alias=%r confidence=%.3f",
        text,
        normalized,
        best.action.id,
        best.matched_alias,
        best.confidence,
    )
    print(f"[alias-match] id={best.action.id} confidence={best.confidence:.3f} alias={best.matched_alias}")
    return best


def _score(text: str, alias: str) -> float:
    if text == alias:
        return 1.0

    text_tokens = set(text.split())
    alias_tokens = set(alias.split())
    if text_tokens and text_tokens == alias_tokens:
        return 0.98

    seq = SequenceMatcher(None, text, alias).ratio()
    token_overlap = 0.0
    if text_tokens and alias_tokens:
        token_overlap = len(text_tokens & alias_tokens) / max(len(text_tokens), len(alias_tokens))

    containment = 0.0
    if len(text) >= 3 and len(alias) >= 3 and (text in alias or alias in text):
        containment = min(len(text), len(alias)) / max(len(text), len(alias))

    return max(seq, token_overlap, containment)


def _norm(text: str) -> str:
    return normalize_voice_command(text, log=False).casefold().replace("য়", "য়")
