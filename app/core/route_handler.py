from __future__ import annotations

import logging
from typing import Any

from app.actions.alias_actions import execute_alias_route
from app.actions.system_actions import execute_confirmed_system_action, execute_system_route
from app.actions.web_actions import execute_web_route
from app.core.alias_command_matcher import AliasMatch
from app.core.command_router import CommandRoute
from app.core.response_builder import ResponseBuilder

LOG = logging.getLogger(__name__)


class RouteHandler:
    """Execute a decided command route using the existing controller context.

    This phase intentionally keeps response formatting and persistence on the
    controller so the UI response dicts stay unchanged. It is the bridge between
    CommandRouter decisions and the new app.actions wrapper layer.
    """

    @staticmethod
    def handle(route: CommandRoute, controller_context: Any, *, speak: bool, original_text: str) -> dict | None:
        if route.kind == "pending_confirmation":
            return RouteHandler._handle_pending_confirmation(route, controller_context, speak, original_text)

        if route.kind == "volume_clarification":
            return ResponseBuilder.volume_clarification(controller_context, original_text, speak)

        if route.kind == "system_action" and route.system_record is not None:
            result = execute_system_route(
                route.system_record,
                original_text=original_text,
                normalized_text=route.normalized_text,
            )
            if result.requires_confirmation:
                controller_context._pending_system_confirmation = route.system_record.target
            return ResponseBuilder.system_action(controller_context, original_text, result, speak)

        if route.kind == "alias_action" and route.alias_match is not None:
            return controller_context._handle_alias_match(original_text, route.alias_match, speak)

        if route.kind == "web_action":
            mode = route.match.get("mode", "chat") if isinstance(route.match, dict) else "chat"
            result = execute_web_route(original_text, route.normalized_text, mode=mode)
            if result is None:
                return None
            return ResponseBuilder.direct_action(
                controller_context,
                original_text,
                intent=result.intent,
                action=result.action,
                response=result.response,
                confidence=result.confidence,
                speak=speak,
                extra={
                    "handled": True,
                    "success": result.success,
                    "type": "web_search",
                    "search_query": result.query,
                    "query": result.query,
                    "search_url": result.search_url,
                    "google_url": result.google_url,
                    "search_kind": result.search_kind,
                    "results": result.results,
                    "speak_text": result.speak_text,
                    "error": result.error,
                },
            )

        return None

    @staticmethod
    def _handle_pending_confirmation(
        route: CommandRoute,
        controller_context: Any,
        speak: bool,
        original_text: str,
    ) -> dict | None:
        if route.clear_pending_alias:
            controller_context._pending_alias_action = None
            return None

        if route.pending_alias_action is not None:
            controller_context._pending_alias_action = None
            confidence = float(route.pending_alias_action.get("confidence") or 0.0)
            if not route.pending_confidence_valid:
                LOG.info(
                    "[alias-confirm] ignored low confidence %.3f input=%r",
                    confidence,
                    route.pending_alias_action.get("original_text"),
                )
                print(
                    f"[alias-confirm] ignored low confidence {confidence:.3f} "
                    f"input={route.pending_alias_action.get('original_text')!r}"
                )
                return None
            match = route.pending_alias_action.get("match")
            if isinstance(match, AliasMatch):
                result = execute_alias_route(match)
                return ResponseBuilder.alias_action(controller_context, original_text, match, result, speak)
            return None

        if route.pending_system_confirmation:
            controller_context._pending_system_confirmation = ""
            result = execute_confirmed_system_action(route.pending_system_confirmation)
            return ResponseBuilder.system_action(controller_context, original_text, result, speak)

        return None
