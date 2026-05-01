"""
Local-only AI backend routing for Jarvis.

The controller calls this layer only after deterministic local intents/actions
have had the first chance to answer. In offline mode this router never calls an
HTTP API. The only optional model backend is the local trained Qwen LoRA.
"""

from __future__ import annotations

import logging
from typing import Callable, Protocol

from app.services.ai.context_builder import ContextBuilder
from app.services.offline_guard import block_internet, offline_mode_enabled

LOG = logging.getLogger(__name__)

FRIENDLY_LOCAL_FALLBACK = "আমি এখানে আছি স্যার, আপনার কাজের জন্য প্রস্তুত।"


class AIProviderError(Exception):
    """Friendly provider error safe to show to the user."""


class AIProvider(Protocol):
    def generate_reply(self, prompt: str, history: list[dict] | None = None, tools: list | None = None) -> str:
        """Generate a reply for the selected provider."""

    def is_available(self) -> bool:
        """Return True when the provider can run locally."""

    def status(self) -> dict:
        """Return local provider status without network calls."""


class LocalFallbackProvider:
    provider_name = "local_fallback"

    def __init__(self, get_setting: Callable[[str, str], str] | None = None) -> None:
        self._context = ContextBuilder(get_setting)

    def generate_reply(self, prompt: str, history: list[dict] | None = None, tools: list | None = None) -> str:
        return FRIENDLY_LOCAL_FALLBACK

    def is_available(self) -> bool:
        return True

    def status(self) -> dict:
        return {"backend": self.provider_name, "configured": True, "offline": True}


class AIProviderRouter:
    """Routes local brain calls: trained Qwen first, then local fallback."""

    def __init__(self, get_setting: Callable[[str, str], str] | None = None) -> None:
        from app.services.ai.qwen_lora_provider import QwenLoraProvider

        self._get_setting = get_setting
        self._last_source = "local_intent"
        self._qwen_lora = QwenLoraProvider(get_setting)
        self._fallback = LocalFallbackProvider(get_setting)

    def selected_name(self) -> str:
        return "trained_qwen" if self._qwen_lora.is_enabled() else "local_fallback"

    def selected_provider(self) -> AIProvider:
        return self._qwen_lora if self._qwen_lora.is_enabled() else self._fallback

    def generate_reply(self, prompt: str, history: list[dict] | None = None, tools: list | None = None) -> str:
        if not offline_mode_enabled():
            LOG.warning("OFFLINE_MODE is disabled in settings, but cloud providers have been removed")

        if self._qwen_lora.is_enabled():
            try:
                reply = self._qwen_lora.generate_reply(prompt, history, tools)
                LOG.info("Qwen LoRA response used")
                self._last_source = "trained_qwen"
                return reply
            except AIProviderError as exc:
                if self._qwen_lora.is_loaded():
                    LOG.exception("Qwen LoRA failed after loading")
                else:
                    LOG.info("Trained Qwen LoRA not loaded; using local fallback")
                    LOG.warning("Qwen LoRA unavailable locally: %s", exc)
            except Exception as exc:
                if self._qwen_lora.is_loaded():
                    LOG.exception("Unexpected Qwen LoRA failure after loading")
                else:
                    LOG.info("Trained Qwen LoRA not loaded; using local fallback")
                    LOG.exception("Unexpected Qwen LoRA load/generation error: %s", exc)

        self._last_source = "local_intent"
        LOG.info("Friendly fallback used")
        return self._fallback.generate_reply(prompt, history, tools)

    def detect_action_intent(self, prompt: str) -> dict | None:
        if not self._qwen_lora.is_enabled():
            return None
        try:
            intent = self._qwen_lora.detect_action_intent(prompt)
            if intent:
                self._last_source = "trained_qwen"
            return intent
        except AIProviderError as exc:
            if self._qwen_lora.is_loaded():
                LOG.exception("Qwen LoRA intent detection failed after loading")
            else:
                LOG.info("Trained Qwen LoRA not loaded; using local fallback")
                LOG.warning("Qwen LoRA intent detection unavailable locally: %s", exc)
        except Exception:
            if self._qwen_lora.is_loaded():
                LOG.exception("Qwen LoRA intent detection failed after loading")
            else:
                LOG.info("Trained Qwen LoRA not loaded; using local fallback")
                LOG.exception("Unexpected Qwen LoRA intent detection error")
        return None

    def is_available(self) -> bool:
        return True

    def status(self) -> dict:
        return {
            "backend": "offline_local",
            "selected_provider": self.selected_name(),
            "offline_mode": offline_mode_enabled(),
            "qwen_lora": self._qwen_lora.status(),
            "fallback": self._fallback.status(),
            "last_source": self._last_source,
        }

    def last_source(self) -> str:
        return self._last_source or "local_intent"

    def block_network_provider(self, feature: str = "cloud AI") -> str:
        return block_internet(feature)

    def _setting(self, key: str, default: str) -> str:
        if self._get_setting is None:
            return default
        return self._get_setting(key, default)
