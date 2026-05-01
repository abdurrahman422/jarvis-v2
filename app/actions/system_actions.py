from __future__ import annotations

from app.core.system_action_dataset_loader import SystemActionExample
from app.services.system.system_action_executor import (
    SystemActionExecutionResult,
    execute_confirmed_dataset_action,
    execute_dataset_action,
)


def execute_system_route(
    match: SystemActionExample,
    original_text: str = "",
    normalized_text: str = "",
) -> SystemActionExecutionResult:
    """Execute a matched system-action route using the existing executor."""
    return execute_dataset_action(match, original_text=original_text)


def execute_confirmed_system_action(confirmation: str) -> SystemActionExecutionResult:
    """Execute a previously confirmed dangerous system action."""
    return execute_confirmed_dataset_action(confirmation)

