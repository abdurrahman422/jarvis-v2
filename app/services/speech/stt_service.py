from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.services.speech.google_stt_service import (
    GoogleSTTRequestError,
    GoogleSTTService,
    InternetUnavailableError,
    MicrophoneNotFoundError,
    SpeechNotUnderstoodError,
    audio_backend_description,
)


@dataclass
class STTResult:
    text: str
    provider_used: str
    message: str


_EN_WAKE_PREFIXES: tuple[str, ...] = (
    "jarvis",
    "hey jarvis",
    "hi jarvis",
    "ok jarvis",
)

_BN_WAKE_PREFIXES: tuple[str, ...] = (
    "জারভিস",
    "হে জারভিস",
    "হাই জারভিস",
    "ওকে জারভিস",
    "ঠিক আছে জারভিস",
)


class STTService:
    def __init__(self) -> None:
        self._provider = "google"
        self._language = "bn-BD"
        self._google = GoogleSTTService(language=self._language)
        self._last_message = f"STT ready: Google Speech Recognition ({audio_backend_description()})."

    def configure_provider(self, provider: str) -> None:
        self._provider = "google"
        self._last_message = f"STT provider set to Google Speech Recognition ({audio_backend_description()})."

    def set_language(self, language_code: str) -> None:
        code = (language_code or "").strip()
        self._language = code if code else "bn-BD"
        self._google.set_language(self._language)
        self._last_message = (
            f"STT language set to {self._language}; provider: Google Speech Recognition "
            f"({audio_backend_description()})."
        )

    def configure_audio(self, *, noise_reduction_enabled: bool = True, mic_sensitivity: int = 50) -> None:
        self._google.configure_audio(
            noise_reduction_enabled=noise_reduction_enabled,
            mic_sensitivity=mic_sensitivity,
        )
        state = "on" if noise_reduction_enabled else "off"
        self._last_message = f"STT audio cleanup: noise reduction {state}; mic sensitivity {mic_sensitivity}."

    def calibrate_ambient(self) -> str:
        threshold = self._google.calibrate_ambient(duration=0.8)
        self._last_message = f"Ambient calibration complete. energy_threshold={threshold}"
        return self._last_message

    def get_language(self) -> str:
        return self._language

    def get_status(self) -> str:
        return (
            f"STT provider: Google Speech Recognition; language={self._language}. "
            f"({audio_backend_description()})"
        )

    def readiness(self) -> dict:
        backend_ok = not audio_backend_description().startswith("no audio backend")
        message = "" if backend_ok else "Microphone input unavailable: install PyAudio or PyAudioWPatch."
        return {
            "provider": "google",
            "language": self._language,
            "audio_backend": audio_backend_description(),
            "ready": backend_ok,
            "message": message,
        }

    def is_ready(self) -> bool:
        return bool(self.readiness().get("ready"))

    def transcribe_once(
        self,
        timeout: int = 8,
        phrase_time_limit: int = 12,
        level_callback: Callable[[float], None] | None = None,
    ) -> STTResult:
        if level_callback:
            level_callback(0.18)
        try:
            text = self._google.listen_once(timeout=timeout, phrase_time_limit=phrase_time_limit)
            normalized = self.normalize_command(text)
            self._last_message = "Google Speech Recognition succeeded"
            return STTResult(normalized, "google", self._last_message)
        except MicrophoneNotFoundError as exc:
            self._last_message = f"microphone not found: {exc}"
            return STTResult("", "none", self._last_message)
        except InternetUnavailableError as exc:
            self._last_message = f"internet unavailable: {exc}"
            return STTResult("", "google", self._last_message)
        except SpeechNotUnderstoodError as exc:
            self._last_message = f"speech not understood: {exc}"
            return STTResult("", "google", self._last_message)
        except GoogleSTTRequestError as exc:
            self._last_message = f"Google request failed: {exc}"
            return STTResult("", "google", self._last_message)
        except Exception as exc:
            self._last_message = f"Google STT failed: {exc}"
            return STTResult("", "google", self._last_message)
        finally:
            if level_callback:
                level_callback(0.05)

    def transcribe_with_retries(
        self,
        attempts: int = 1,
        level_callback: Callable[[float], None] | None = None,
    ) -> STTResult:
        last_result = STTResult("", "none", "")
        for _ in range(max(attempts, 1)):
            result = self.transcribe_once(level_callback=level_callback)
            last_result = result
            if result.text:
                return result
        return last_result

    def transcribe_raw_once(
        self,
        timeout: int = 5,
        phrase_time_limit: int = 3,
        level_callback: Callable[[float], None] | None = None,
    ) -> STTResult:
        if level_callback:
            level_callback(0.16)
        try:
            text = self._google.listen_once(timeout=timeout, phrase_time_limit=phrase_time_limit)
            self._last_message = "Google Speech Recognition succeeded"
            return STTResult(" ".join(text.strip().split()), "google", self._last_message)
        except MicrophoneNotFoundError as exc:
            self._last_message = f"microphone not found: {exc}"
            return STTResult("", "none", self._last_message)
        except InternetUnavailableError as exc:
            self._last_message = f"internet unavailable: {exc}"
            return STTResult("", "google", self._last_message)
        except SpeechNotUnderstoodError as exc:
            self._last_message = f"speech not understood: {exc}"
            return STTResult("", "google", self._last_message)
        except GoogleSTTRequestError as exc:
            self._last_message = f"Google request failed: {exc}"
            return STTResult("", "google", self._last_message)
        except Exception as exc:
            self._last_message = f"Google STT failed: {exc}"
            return STTResult("", "google", self._last_message)
        finally:
            if level_callback:
                level_callback(0.05)

    def normalize_command(self, text: str) -> str:
        cleaned_en = " ".join(text.lower().strip().split())
        cleaned_original = " ".join(text.strip().split())

        for wake in sorted(_EN_WAKE_PREFIXES, key=len, reverse=True):
            if cleaned_en.startswith(wake):
                cleaned_en = cleaned_en[len(wake) :].strip(" ,.!?")
                cleaned_original = cleaned_original[len(wake) :].strip(" ,.!?")
                break

        for wake in sorted(_BN_WAKE_PREFIXES, key=len, reverse=True):
            if cleaned_original.startswith(wake):
                cleaned_original = cleaned_original[len(wake) :].strip(" ,.!?।")
                break

        if self._language.lower().startswith("bn"):
            return cleaned_original.strip()
        if cleaned_original and any(ord(c) > 127 for c in cleaned_original):
            return cleaned_original.strip()
        return cleaned_en.strip()
