from __future__ import annotations

import logging

from app.core.alias_command_matcher import AliasMatch, match_alias_command

LOG = logging.getLogger(__name__)


def match_alias(text: str) -> AliasMatch | None:
    """Compatibility wrapper around the existing alias command matcher."""
    match = match_alias_command(text)
    if match is not None:
        LOG.info(
            "[router] alias matched id=%s confidence=%.3f target=%s",
            match.action.id,
            match.confidence,
            match.action.target,
        )
    return match

