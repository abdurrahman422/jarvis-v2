from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Callable

from app.app_paths import PROJECT_ROOT
from app.services.ai.context_builder import ContextBuilder
from app.services.ai.providers import AIProviderError

LOG = logging.getLogger(__name__)

DEFAULT_QWEN_BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
DEFAULT_QWEN_LORA_PATH = "app/models/jarvis-qwen-lora"
DEFAULT_MAX_NEW_TOKENS = 320
SAFE_ACTIONS = {
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
}

CONFIRMATION_REQUIRED_ACTIONS = {
    "system.open_whatsapp",
    "system.youtube_search",
    "system.youtube_play",
    "music.play",
    "music.play_random",
    "music.next",
    "music.previous",
    "music.stop",
}


class QwenLoraProvider:
    provider_name = "qwen_lora"

    def __init__(self, get_setting: Callable[[str, str], str] | None = None) -> None:
        self._get_setting = get_setting
        self._context = ContextBuilder(get_setting)
        self._tokenizer = None
        self._model = None
        self._load_error = ""
        self._disabled_reason = ""
        self._load_attempted = False
        self._lock = threading.Lock()

    def generate_reply(self, prompt: str, history: list[dict] | None = None, tools: list | None = None) -> str:
        if not self.is_enabled():
            raise AIProviderError("Qwen LoRA brain is disabled.")
        self._ensure_loaded()
        LOG.info("Using trained Jarvis brain")
        messages = self._context.build(prompt, history)
        return self._generate_from_messages(messages, max_new_tokens=self._max_new_tokens())

    def detect_action_intent(self, text: str) -> dict | None:
        if not self.is_enabled() or not text.strip():
            return None
        self._ensure_loaded()
        LOG.info("Using trained Jarvis brain")
        actions = ", ".join(sorted(SAFE_ACTIONS))
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Jarvis intent detection. Return JSON only. "
                    "Detect whether the user is asking Jarvis to execute one of these safe actions: "
                    f"{actions}. If no action is clearly requested, use null action. "
                    "Schema: {\"action\": string|null, \"arguments\": string|null, "
                    "\"confidence\": number, \"should_execute\": boolean, \"reason\": string}."
                ),
            },
            {"role": "user", "content": text.strip()},
        ]
        raw = self._generate_from_messages(messages, max_new_tokens=180, temperature=0.1)
        data = self._parse_json(raw)
        action = data.get("action")
        confidence = float(data.get("confidence") or 0.0)
        should_execute = bool(data.get("should_execute")) and action in SAFE_ACTIONS and confidence >= 0.72
        if action not in SAFE_ACTIONS:
            action = None
            should_execute = False
        return {
            "action": action,
            "arguments": data.get("arguments") or text,
            "confidence": max(0.0, min(confidence, 1.0)),
            "should_execute": should_execute,
            "needs_confirmation": action in CONFIRMATION_REQUIRED_ACTIONS if action else False,
            "reason": str(data.get("reason") or "Qwen LoRA intent detection"),
        }

    def is_enabled(self) -> bool:
        if self._disabled_reason:
            return False
        value = self._setting_any(("USE_TRAINED_QWEN", "use_trained_qwen", "USE_QWEN_LORA", "use_qwen_lora"), "false")
        return value.strip().lower() in {"1", "true", "yes", "enabled", "on"}

    def is_loaded(self) -> bool:
        return self._model is not None and self._tokenizer is not None

    def is_available(self) -> bool:
        if not self.is_enabled():
            return False
        path = self._lora_path()
        return (path / "adapter_config.json").exists() and (
            (path / "adapter_model.safetensors").exists() or (path / "adapter_model.bin").exists()
        )

    def status(self) -> dict:
        return {
            "backend": self.provider_name,
            "enabled": self.is_enabled(),
            "configured": self.is_available(),
            "model": self._base_model_name(),
            "lora_path": str(self._lora_path()),
            "loaded": self._model is not None,
            "load_error": self._load_error,
            "disabled_reason": self._disabled_reason,
            "lazy_load": True,
            "load_policy": "primary_brain_when_enabled",
        }

    def _ensure_loaded(self) -> None:
        if self._model is not None and self._tokenizer is not None:
            return
        with self._lock:
            if self._model is not None and self._tokenizer is not None:
                return
            if self._load_attempted and self._load_error:
                raise AIProviderError(f"Qwen LoRA failed to load: {self._load_error}")
            self._load_attempted = True
            path = self._lora_path()
            try:
                if not self.is_available():
                    raise FileNotFoundError(f"LoRA adapter files not found at {path}")
                if self._adapter_declares_incompatible_base(path):
                    message = "LoRA adapter incompatible with 0.5B base model; disabling Qwen LoRA"
                    self._disabled_reason = message
                    self._load_error = message
                    LOG.error(message)
                    print(message)
                    raise AIProviderError(message)
                LOG.info("Qwen LoRA adapter found")
                print("Qwen LoRA adapter found")

                import torch
                from peft import PeftModel
                from transformers import AutoModelForCausalLM, AutoTokenizer

                tokenizer = AutoTokenizer.from_pretrained(
                    self._base_model_name(),
                    trust_remote_code=True,
                    local_files_only=True,
                )
                dtype = torch.float16 if torch.cuda.is_available() else torch.float32
                base_model = AutoModelForCausalLM.from_pretrained(
                    self._base_model_name(),
                    torch_dtype=dtype,
                    device_map="auto" if torch.cuda.is_available() else None,
                    trust_remote_code=True,
                    local_files_only=True,
                )
                model = PeftModel.from_pretrained(base_model, str(path))
                model.eval()
                if not torch.cuda.is_available():
                    model.to("cpu")

                self._tokenizer = tokenizer
                self._model = model
                self._load_error = ""
                LOG.info("Qwen LoRA loaded")
                print("Qwen LoRA loaded")
            except AIProviderError:
                if self._disabled_reason:
                    raise
                LOG.exception("Qwen LoRA load failed")
                raise
            except Exception as exc:
                self._load_error = str(exc)
                LOG.exception("Qwen LoRA load failed")
                raise AIProviderError(f"Qwen LoRA failed to load: {exc}") from exc

    def _generate_from_messages(
        self,
        messages: list[dict],
        *,
        max_new_tokens: int,
        temperature: float = 0.7,
    ) -> str:
        if self._model is None or self._tokenizer is None:
            raise AIProviderError("Qwen LoRA model is not loaded.")
        import torch

        prompt = self._tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self._tokenizer(prompt, return_tensors="pt")
        device = next(self._model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.inference_mode():
            output_ids = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=temperature > 0,
                temperature=temperature,
                top_p=0.9,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        generated = output_ids[0][inputs["input_ids"].shape[-1] :]
        return self._tokenizer.decode(generated, skip_special_tokens=True).strip()

    def _parse_json(self, raw: str) -> dict:
        text = raw.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AIProviderError(f"Qwen LoRA returned invalid intent JSON: {raw[:120]}") from exc
        return data if isinstance(data, dict) else {}

    def _base_model_name(self) -> str:
        configured = self._setting_any(("QWEN_BASE_MODEL", "qwen_base_model"), DEFAULT_QWEN_BASE_MODEL).strip()
        if "qwen2.5-1.5b-instruct" in configured.lower():
            LOG.warning("Ignoring heavy Qwen 1.5B base model setting; using Qwen/Qwen2.5-0.5B-Instruct")
            return DEFAULT_QWEN_BASE_MODEL
        return configured or DEFAULT_QWEN_BASE_MODEL

    def _adapter_declares_incompatible_base(self, path: Path) -> bool:
        try:
            config_path = path / "adapter_config.json"
            data = json.loads(config_path.read_text(encoding="utf-8"))
            trained_base = str(data.get("base_model_name_or_path") or "").lower()
            requested_base = self._base_model_name().lower()
            return "qwen2.5-1.5b-instruct" in trained_base and "qwen2.5-0.5b-instruct" in requested_base
        except Exception:
            return False

    def _lora_path(self) -> Path:
        raw = self._setting_any(("QWEN_LORA_PATH", "qwen_lora_path"), DEFAULT_QWEN_LORA_PATH).strip() or DEFAULT_QWEN_LORA_PATH
        path = Path(raw)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path.resolve()

    def _max_new_tokens(self) -> int:
        raw = self._setting_any(("QWEN_MAX_NEW_TOKENS", "qwen_max_new_tokens"), str(DEFAULT_MAX_NEW_TOKENS)).strip()
        if raw.isdigit():
            return max(64, min(int(raw), 1024))
        return DEFAULT_MAX_NEW_TOKENS

    def _setting_any(self, keys: tuple[str, ...], default: str) -> str:
        for key in keys:
            value = self._setting(key, "")
            if value:
                return value
            env_value = os.environ.get(key, "").strip()
            if env_value:
                return env_value
        return default

    def _setting(self, key: str, default: str) -> str:
        if self._get_setting is None:
            return default
        return self._get_setting(key, default)
