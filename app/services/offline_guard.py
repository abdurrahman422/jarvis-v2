from __future__ import annotations

import logging
import os
import socket
from typing import Any


LOG = logging.getLogger("jarvis.offline")
_INSTALLED = False


def offline_mode_enabled() -> bool:
    return os.environ.get("OFFLINE_MODE", "false").strip().lower() in {"1", "true", "yes", "on", "enabled"}


def block_internet(feature: str = "network") -> str:
    LOG.error("[error] internet access blocked in offline mode")
    return f"{feature} is unavailable because Jarvis is running fully offline."


def log_offline_mode() -> None:
    mode = "OFFLINE" if offline_mode_enabled() else "ONLINE-CAPABLE"
    LOG.info("[system] running in %s mode", mode)
    print(f"[system] running in {mode} mode")


def install_internet_block() -> None:
    global _INSTALLED
    if _INSTALLED or not offline_mode_enabled():
        return
    _INSTALLED = True

    def _blocked_create_connection(*args: Any, **kwargs: Any) -> Any:
        LOG.error("[error] internet access blocked in offline mode")
        raise OSError("internet access blocked in offline mode")

    socket.create_connection = _blocked_create_connection
