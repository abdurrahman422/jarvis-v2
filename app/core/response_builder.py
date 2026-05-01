from __future__ import annotations

from typing import Any

from app.core.alias_command_matcher import AliasMatch


class ResponseBuilder:
    """Build Jarvis response dictionaries without changing their public shape.

    The controller context is still responsible for repositories, analytics,
    settings, and TTS. This builder centralizes the dict construction so the
    controller can become thinner over time.
    """

    @staticmethod
    def volume_clarification(context: Any, text: str, speak: bool) -> dict:
        response = "স্যার, volume বাড়াবো, কমাবো, নাকি mute করবো?"
        context.commands.add(text, "volume_control", "volume.clarify", response, 0.92)
        context.conversations.add("assistant", response)
        out = {
            "type": "system_action",
            "intent": "volume_control",
            "action": "volume.clarify",
            "target": "volume",
            "handled": True,
            "success": True,
            "confidence": 0.92,
            "response": response,
            "speak_text": response,
            "reply_lang": "bn",
            "recognized_text": text,
        }
        if speak and context.is_voice_reply_enabled():
            warning = context._speak_reply(response, "bn", source="volume.clarify")
            if warning:
                out["tts_warning"] = warning
        return out

    @staticmethod
    def system_action(context: Any, text: str, result: Any, speak: bool) -> dict:
        response = getattr(result, "message", None) or getattr(result, "response", "")
        speak_text = getattr(result, "speak_text", "") or response
        context.commands.add(text, result.intent, result.action, response, 0.92 if result.success else 0.55)
        context.conversations.add("assistant", response)
        context._log_analytics_event("local_action", source="system_control", action=result.action, message=text)
        out = {
            "type": "system_action",
            "intent": result.intent,
            "action": result.action,
            "target": result.target,
            "handled": True,
            "success": result.success,
            "confidence": 0.92 if result.success else 0.55,
            "response": response,
            "speak_text": speak_text,
            "reply_lang": "bn",
            "recognized_text": text,
            "path": getattr(result, "path", ""),
            "candidates": getattr(result, "candidates", []),
            "error": getattr(result, "error", ""),
            "requires_confirmation": getattr(result, "requires_confirmation", False),
        }
        if speak and context.is_voice_reply_enabled():
            warning = context._speak_reply(speak_text, "bn", source=result.action)
            if warning:
                out["tts_warning"] = warning
        return out

    @staticmethod
    def alias_action(context: Any, text: str, match: AliasMatch, result: Any, speak: bool) -> dict:
        response = result.response
        context.commands.add(text, result.intent, result.action, response, match.confidence if result.success else 0.55)
        context.conversations.add("assistant", response)
        context._log_analytics_event("local_action", source="alias_executor", action=result.action, message=text)
        out = {
            "type": "alias_command",
            "intent": result.intent,
            "action": result.action,
            "target": result.target,
            "matched_id": match.action.id,
            "matched_alias": match.matched_alias,
            "handled": True,
            "success": result.success,
            "confidence": match.confidence if result.success else 0.55,
            "response": response,
            "speak_text": response,
            "reply_lang": "bn",
            "recognized_text": text,
            "error": result.error,
        }
        if speak and context.is_voice_reply_enabled():
            warning = context._speak_reply(response, "bn", source=result.action)
            if warning:
                out["tts_warning"] = warning
        return out

    @staticmethod
    def alias_confirmation(context: Any, display_text: str, match: AliasMatch, speak: bool) -> dict:
        response = (
            f"স্যার, আপনি কি {match.action.name} ({match.action.target}) খুলতে চান? "
            f"confirm বললে {match.action.action} করব।"
        )
        context.commands.add(display_text, "alias_command", "alias.confirm_required", response, match.confidence)
        context.conversations.add("assistant", response)
        context._log_analytics_event("local_action", source="alias_matcher", action="alias.confirm_required", message=display_text)
        out = {
            "type": "alias_command",
            "intent": "alias_command",
            "action": "alias.confirm_required",
            "target": match.action.target,
            "matched_id": match.action.id,
            "matched_alias": match.matched_alias,
            "handled": True,
            "success": False,
            "requires_confirmation": True,
            "confidence": match.confidence,
            "response": response,
            "speak_text": response,
            "reply_lang": "bn",
            "recognized_text": display_text,
        }
        if speak and context.is_voice_reply_enabled():
            warning = context._speak_reply(response, "bn", source="alias.confirm_required")
            if warning:
                out["tts_warning"] = warning
        return out

    @staticmethod
    def direct_action(
        context: Any,
        text: str,
        *,
        intent: str,
        action: str,
        response: str,
        confidence: float,
        speak: bool,
        extra: dict | None = None,
    ) -> dict:
        context.commands.add(text, intent, action, response, confidence)
        context.conversations.add("assistant", response)
        context._log_analytics_event("local_action", source="direct_command", action=action, message=text)
        context._log_reply(intent, "direct_command", response)
        out = {
            "intent": intent,
            "action": action,
            "confidence": confidence,
            "response": response,
            "reply_lang": "bn" if any("\u0980" <= ch <= "\u09ff" for ch in response) else "en",
            "recognized_text": text,
        }
        if extra:
            out.update(extra)
        if speak and context.is_voice_reply_enabled():
            spoken = str(out.get("speak_text") or response)
            tts_note = context._speak_reply(spoken, out["reply_lang"], source=action)
            if tts_note:
                out["tts_warning"] = tts_note
        return out

    @staticmethod
    def fallback(text: str, response: str | None = None) -> dict:
        final = response or f"জি স্যার, আমি শুনতে পাচ্ছি। আপনি বললেন: {text}"
        return {
            "intent": "fallback",
            "action": "system.fallback",
            "confidence": 0.0,
            "response": final,
            "reply_lang": "bn",
            "recognized_text": text,
        }

