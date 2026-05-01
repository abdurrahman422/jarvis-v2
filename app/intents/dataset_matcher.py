from __future__ import annotations

import logging

from app.core.system_action_dataset_loader import SystemActionExample, match_dataset_action

LOG = logging.getLogger(__name__)


def match_dataset(text: str, normalized: str = "") -> SystemActionExample | None:
    """Compatibility wrapper around the existing dataset system-action matcher."""
    record = match_dataset_action(text, normalized)
    if record is not None:
        LOG.info(
            "[router] dataset matched id=%s action=%s target=%s",
            record.id,
            record.action,
            record.target,
        )
    return record

