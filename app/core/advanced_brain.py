"""
Local-first brain manager for Jarvis.

Routing order:
local rules -> registered actions -> selected AI provider only when needed.
"""

import logging
from dataclasses import dataclass
from typing import Callable

from app.services.ai import AIProviderError, AIProviderRouter

DEFAULT_HISTORY_MESSAGES = 8

_ACTION_LOG = logging.getLogger("jarvis.action")
_BRAIN_LOG = logging.getLogger("jarvis.brain")

SAFE_ACTIONS = frozenset((
    "system.time",
    "system.battery",
    "system.status",
    "system.info",
    "system.greet",
    "system.open_google",
    "system.open_youtube",
    "system.open_notepad",
    "system.open_whatsapp",
    "system.youtube_search",
    "system.youtube_play",
    "music.play",
    "music.play_random",
    "music.next",
    "music.previous",
    "music.stop",
    "weather.current",
    "network.speedtest",
    "network.speedtest_last",
))

CONFIRMATION_REQUIRED_ACTIONS = frozenset((
    "system.open_whatsapp",
    "system.youtube_search",
    "system.youtube_play",
    "music.play",
    "music.play_random",
    "music.next",
    "music.previous",
    "music.stop",
))

NO_CONFIRMATION_ACTIONS = frozenset((
    "system.time",
    "system.battery",
    "system.status",
    "system.info",
    "system.greet",
    "system.open_google",
    "system.open_notepad",
    "weather.current",
    "network.speedtest",
    "network.speedtest_last",
))

CONFIRMATION_THRESHOLD = 0.8

EXCLUDED_PATTERNS = frozenset((
    "what is",
    "how do i",
    "how to",
    "can you",
    "could you",
    "would you",
    "should i",
    "explain",
    "why does",
    "what's the",
    "tell me about",
    "do you know",
    "any idea",
    "maybe",
    "perhaps",
    "think about",
    "remember",
    "like to",
    "want to know",
    "question",
    "?",
    "hello how",
    "hi how",
    "hey how",
))


def _log_action(action: str, confidence: float, blocked: str, reason: str) -> None:
    _ACTION_LOG.info(f"ACTION: action={action} confidence={confidence:.2f} blocked={blocked} reason={reason}")


@dataclass
class ActionIntent:
    """Structured output from AI action detection."""
    action: str | None
    arguments: str | None
    confidence: float
    should_execute: bool
    needs_confirmation: bool
    reason: str


class AdvancedBrain:
    """
    High-level brain manager.

    It keeps the public controller contract stable while making the actual
    decision local-first and provider-selectable.
    """

    def __init__(
        self,
        *,
        get_setting: Callable[[str, str], str] | None = None,
    ) -> None:
        self._get_setting = get_setting
        self._providers = AIProviderRouter(get_setting)

    def score_priority(self, text: str) -> float:
        """Score how urgent the message is."""
        q = text.lower()
        if "urgent" in q or "now" in q:
            return 1.0
        if "later" in q:
            return 0.4
        return 0.6

    def suggest_mode(self, text: str) -> str:
        """Suggest which UI mode is most relevant."""
        q = text.lower()
        if any(k in q for k in ["camera", "image", "ocr", "vision"]):
            return "vision"
        if any(k in q for k in ["whatsapp", "message", "send"]):
            return "automation"
        if any(k in q for k in ["alarm", "task", "focus"]):
            return "scheduler"
        return "general"

    def should_handle(self, action: str, confidence: float, text: str) -> bool:
        """Decide if a selected external provider should handle this input."""
        q = text.strip().lower()
        if not q:
            return False

        if self._is_local_rule_text(q):
            _BRAIN_LOG.info("local rule handled: %s", q[:80])
            return False

        if action in {"system.chitchat", "system.greet"}:
            _BRAIN_LOG.info("local rule handled: %s", action)
            return False

        if action == "system.unknown":
            return True

        return False

    def generate_reply(
        self,
        user_text: str,
        chat_history: list[dict] | None = None,
    ) -> str:
        """Generate a conversational reply using the selected AI provider."""
        try:
            return self._providers.generate_reply(user_text, history=chat_history)
        except AIProviderError as exc:
            _BRAIN_LOG.warning("provider error: %s", exc)
            _BRAIN_LOG.info("Friendly fallback used")
            return "আমি এখানে আছি স্যার, আপনার কাজের জন্য প্রস্তুত।"

    def is_available(self) -> bool:
        """Check if selected AI provider is configured."""
        return self._providers.is_available()

    def status(self) -> dict:
        """Get status information about the selected AI provider."""
        return self._providers.status()

    def last_source(self) -> str:
        return self._providers.last_source()

    def _is_local_rule_text(self, text: str) -> bool:
        local_phrases = {
            "hi",
            "hello",
            "hey",
            "thanks",
            "thank you",
            "goodbye",
            "bye",
            "assalamualaikum",
            "salam",
            "kemon acho",
            "kemon achho",
        }
        return text in local_phrases

    def _needs_provider(self, text: str) -> bool:
        """Return True for reasoning/content tasks that local tools cannot answer."""
        if self._is_local_rule_text(text):
            return False

        local_action_words = (
            "time",
            "battery",
            "open youtube",
            "open google",
            "open notepad",
            "whatsapp",
            "email",
            "file",
            "search docs",
            "clean junk",
            "weather",
            "speed test",
            "play music",
        )
        if any(word in text for word in local_action_words):
            return False

        provider_starters = (
            "explain",
            "write",
            "draft",
            "create",
            "generate",
            "summarize",
            "analyse",
            "analyze",
            "compare",
            "solve",
            "debug",
            "code",
            "teach",
            "tell me about",
            "what is",
            "why",
            "how to",
            "how do",
            "can you explain",
            "could you explain",
        )
        if text.startswith(provider_starters):
            return True

        if text.endswith("?"):
            return True

        return len(text.split()) >= 4

    def _is_false_trigger(self, text: str) -> bool:
        """Check if input is a question or conversational - not a clear action."""
        text_lower = text.lower().strip()

        for pattern in EXCLUDED_PATTERNS:
            if pattern in text_lower:
                return True

        words = text_lower.split()
        if len(words) < 2:
            return True

        if text_lower.endswith("?"):
            return True

        return False

    def detect_action_intent(self, text: str) -> ActionIntent:
        """
        Analyze user input and detect if it matches a safe action.

        Uses local keyword matching first. If no local action is found, the
        trained Qwen LoRA brain can classify safe actions before API fallback.
        Returns ActionIntent with action, arguments, confidence, and execution decision.

        TEST CASES:
        -----------
        SHOULD EXECUTE (high confidence, clear action):
            - "what time is it" -> system.time, confidence 0.9
            - "play some music" -> music.play, confidence 0.9
            - "open whatsapp" -> system.open_whatsapp, confidence 0.9
            - "check battery" -> system.battery, confidence 0.9
            - "what's the weather" -> weather.current, confidence 0.9

        SHOULD STAY CONVERSATIONAL (false triggers):
            - "hi how are you" -> no action, conversational
            - "what is python" -> no action, question
            - "can you help me" -> no action, question
            - "why not" -> no action, question
            - "tell me about music" -> no action, request for info

        SHOULD REQUIRE CONFIRMATION:
            - "play music" -> music.play, needs_confirmation=True
            - "open whatsapp" -> system.open_whatsapp, needs_confirmation=True
            - "search youtube for cats" -> system.youtube_search, needs_confirmation=True
        """
        text_lower = text.lower().strip()

        if not text_lower:
            result = ActionIntent(
                action=None,
                arguments=None,
                confidence=0.0,
                should_execute=False,
                needs_confirmation=False,
                reason="Empty input",
            )
            _log_action("none", 0.0, "empty", result.reason)
            return result

        try:
            qwen_intent = self._providers.detect_action_intent(text)
        except AIProviderError as exc:
            _BRAIN_LOG.warning("Qwen LoRA intent detection failed: %s", exc)
            qwen_intent = None
        if qwen_intent:
            action = qwen_intent.get("action")
            confidence = float(qwen_intent.get("confidence") or 0.0)
            should_execute = bool(qwen_intent.get("should_execute")) and action in SAFE_ACTIONS
            needs_confirm = bool(qwen_intent.get("needs_confirmation")) or action in CONFIRMATION_REQUIRED_ACTIONS
            result = ActionIntent(
                action=action,
                arguments=qwen_intent.get("arguments") or text,
                confidence=confidence,
                should_execute=should_execute,
                needs_confirmation=needs_confirm,
                reason=str(qwen_intent.get("reason") or "Qwen LoRA intent detection"),
            )
            blocked = "none" if should_execute and not needs_confirm else "confirmation" if needs_confirm else "no_execute"
            _log_action(action or "none", confidence, blocked, result.reason)
            return result

        if self._is_false_trigger(text_lower):
            result = ActionIntent(
                action=None,
                arguments=None,
                confidence=0.0,
                should_execute=False,
                needs_confirmation=False,
                reason="False trigger pattern detected",
            )
            _log_action("none", 0.0, "false_trigger", result.reason)
            return result

        action_map = {
            "time": "system.time",
            "battery": "system.battery",
            "status": "system.status",
            "info": "system.info",
            "hello": "system.greet",
            "hi": "system.greet",
            "hey": "system.greet",
            "open google": "system.open_google",
            "open youtube": "system.open_youtube",
            "open notepad": "system.open_notepad",
            "open whatsapp": "system.open_whatsapp",
            "youtube search": "system.youtube_search",
            "search youtube": "system.youtube_search",
            "play youtube": "system.youtube_play",
            "play music": "music.play",
            "play a song": "music.play",
            "random music": "music.play_random",
            "shuffle music": "music.play_random",
            "next song": "music.next",
            "skip": "music.next",
            "previous song": "music.previous",
            "previous": "music.previous",
            "stop music": "music.stop",
            "stop": "music.stop",
            "weather": "weather.current",
            "how's the weather": "weather.current",
            "speed test": "network.speedtest",
            "test speed": "network.speedtest",
            "last speed": "network.speedtest_last",
        }

        for phrase, action in action_map.items():
            if phrase in text_lower:
                needs_confirm = action in CONFIRMATION_REQUIRED_ACTIONS
                result = ActionIntent(
                    action=action,
                    arguments=text,
                    confidence=0.9,
                    should_execute=True,
                    needs_confirmation=needs_confirm,
                    reason=f"Matched keyword: {phrase}",
                )
                _log_action(action, 0.9, "none" if not needs_confirm else "confirmation", result.reason)
                return result

        result = ActionIntent(
            action=None,
            arguments=None,
            confidence=0.0,
            should_execute=False,
            needs_confirmation=False,
            reason="No matching action found",
        )
        _log_action("none", 0.0, "no_match", result.reason)
        return result
