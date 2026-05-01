"""
Context builder for local Jarvis conversation requests.

Builds proper message structure with:
- system prompt
- conversation history
- current user input
- optional summarization hook for future
"""

from typing import Callable, Optional

DEFAULT_HISTORY_MESSAGES = 8
MAX_USER_INPUT_LENGTH = 2000

SYSTEM_PROMPT = "You are Jarvis, a friendly Bangla-English assistant. Always reply naturally."


class ContextBuilder:
    """Builds conversation context for local model requests."""

    def __init__(
        self,
        get_setting: Callable[[str, str], str] | None = None,
    ) -> None:
        self._get_setting = get_setting

    def build(
        self,
        user_input: str,
        chat_history: list[dict] | None = None,
    ) -> list[dict]:
        """
        Build message list for a local model request.
        Returns list of messages with correct roles.
        """
        messages: list[dict] = []

        system = self._get_system_prompt()
        messages.append({"role": "system", "content": system})

        history = self._load_history(chat_history)
        messages.extend(history)

        user_msg = self._sanitize_user_input(user_input)
        messages.append({"role": "user", "content": user_msg})

        return messages

    def _get_system_prompt(self) -> str:
        """Get the system prompt."""
        custom = self._setting("ai_system_prompt", "").strip()
        if custom:
            return custom
        return SYSTEM_PROMPT

    def _load_history(self, chat_history: list[dict] | None) -> list[dict]:
        """Load conversation history within window limit."""
        limit = self._history_limit()

        if not chat_history:
            return []

        messages: list[dict] = []
        count = 0

        for item in reversed(chat_history):
            if count >= limit:
                break

            role = item.get("role", "user")
            if role not in ("user", "assistant"):
                continue

            content = (item.get("text") or "").strip()
            if not content:
                continue

            api_role = "assistant" if role == "assistant" else "user"
            messages.append({"role": api_role, "content": content})
            count += 1

        return list(reversed(messages))

    def _history_limit(self) -> int:
        """Get configured history window size."""
        raw = self._setting(
            "ai_history_messages",
            str(DEFAULT_HISTORY_MESSAGES),
        ).strip()
        if raw.isdigit():
            return max(1, min(int(raw), 20))
        return DEFAULT_HISTORY_MESSAGES

    def _sanitize_user_input(self, text: str) -> str:
        """Sanitize user input to prevent issues."""
        if not text:
            return ""
        text = text.strip()[:MAX_USER_INPUT_LENGTH]
        return text

    def _setting(self, key: str, default: str) -> str:
        if self._get_setting is None:
            return default
        return self._get_setting(key, default)

    def build_summary_context(
        self,
        user_input: str,
        chat_history: list[dict] | None,
    ) -> list[dict]:
        """
        Placeholder for future summarization integration.

        Currently just delegates to build().
        Future: could summarize older messages for context window efficiency.
        """
        return self.build(user_input, chat_history)
