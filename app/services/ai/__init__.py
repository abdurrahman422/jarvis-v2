"""Offline AI service exports for Jarvis."""

from app.services.ai.context_builder import ContextBuilder
from app.services.ai.providers import AIProviderError, AIProviderRouter, LocalFallbackProvider
from app.services.ai.qwen_lora_provider import QwenLoraProvider

__all__ = [
    "AIProviderError",
    "AIProviderRouter",
    "ContextBuilder",
    "LocalFallbackProvider",
    "QwenLoraProvider",
]

DEFAULT_BACKEND = "offline_local"
