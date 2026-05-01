from __future__ import annotations

import logging
import webbrowser
from dataclasses import dataclass
from urllib.parse import urlparse

from app.core.alias_dataset_loader import AliasAction
from app.services.system.app_launcher import open_app as launch_app

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class ActionExecutionResult:
    success: bool
    intent: str
    action: str
    target: str
    response: str
    error: str = ""


def execute_alias_action(action: AliasAction) -> ActionExecutionResult:
    LOG.info("[alias-executor] executing id=%s action=%s target=%s", action.id, action.action, action.target)
    print(f"[alias-executor] executing action={action.action} target={action.target}")

    if action.action == "open_url":
        return _open_url(action)
    if action.action == "open_app":
        return _open_app(action)

    message = f"স্যার, এই alias action support করা হয়নি: {action.action}"
    LOG.warning("[alias-executor] blocked unsupported action=%s target=%s", action.action, action.target)
    return ActionExecutionResult(False, "alias_command", action.action, action.target, message, error="unsupported_action")


def _open_url(action: AliasAction) -> ActionExecutionResult:
    url = action.target.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        message = "স্যার, dataset URL নিরাপদ নয়, তাই খুলছি না।"
        LOG.warning("[alias-executor] blocked unsafe url=%s", url)
        return ActionExecutionResult(False, "alias_command", "open_url", url, message, error="unsafe_url")
    try:
        opened = webbrowser.open(url)
        if not opened:
            raise RuntimeError("webbrowser.open returned False")
        return ActionExecutionResult(True, "alias_command", "open_url", url, f"ঠিক আছে স্যার, {action.name} খুলছি।")
    except Exception as exc:
        LOG.exception("[alias-executor] open_url failed: %s", exc)
        return ActionExecutionResult(False, "alias_command", "open_url", url, f"স্যার, {action.name} খুলতে পারিনি।", error=str(exc))


def _open_app(action: AliasAction) -> ActionExecutionResult:
    app_name = action.target.strip()
    if not app_name or any(ch in app_name for ch in "\r\n;&|<>"):
        message = "স্যার, dataset app target নিরাপদ নয়, তাই চালাচ্ছি না।"
        LOG.warning("[alias-executor] blocked unsafe app target=%r", app_name)
        return ActionExecutionResult(False, "alias_command", "open_app", app_name, message, error="unsafe_app_target")
    result = launch_app(app_name, allow_fallback=True)
    return ActionExecutionResult(
        result.success,
        "alias_command",
        "open_app",
        app_name,
        result.message if result.message else f"ঠিক আছে স্যার, {action.name} খুলছি।",
        error="" if result.success else "open_app_failed",
    )
