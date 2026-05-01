from __future__ import annotations

import logging

from app.core.system_action_dataset_loader import SystemActionExample
from app.core.system_action_dataset_loader import _match_hard_rule, _norm

LOG = logging.getLogger(__name__)


def match_hard_rule(text: str, normalized: str = "") -> SystemActionExample | None:
    """Compatibility wrapper around the existing system-action hard rules."""
    haystack = _norm(f"{text or ''} {normalized or ''}")
    direct = _norm(text or "")
    if not haystack:
        return None
    record = _match_hard_rule(text or "", direct, haystack)
    if record is not None:
        LOG.info(
            "[router] hard rule matched id=%s action=%s target=%s",
            record.id,
            record.action,
            record.target,
        )
    return record

