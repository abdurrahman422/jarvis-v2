from __future__ import annotations

from app.core.action_executor import ActionExecutionResult, execute_alias_action
from app.core.alias_command_matcher import AliasMatch


def execute_alias_route(match: AliasMatch) -> ActionExecutionResult:
    """Execute a matched alias route using the existing alias executor."""
    return execute_alias_action(match.action)

