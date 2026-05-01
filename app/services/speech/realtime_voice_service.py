from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QObject, Signal

from app.services.speech.stt_service import STTService


@dataclass
class RealtimeSpeechResult:
    text: str
    message: str
    provider_used: str = "google"


class RealtimeMicrophoneService(QObject):
    """Compatibility wrapper for the old realtime service name."""

    volume_changed = Signal(float)
    text_detected = Signal(str)
    debug = Signal(str)
    failed = Signal(str)

    def __init__(self, *, language: str = "bn-BD", **_: object) -> None:
        super().__init__()
        self._stt = STTService()
        self._stt.set_language(language or "bn-BD")

    def stop(self) -> None:
        return

    def listen_once(
        self,
        *,
        volume_callback: Callable[[float], None] | None = None,
        text_callback: Callable[[str], None] | None = None,
        timeout: float = 8.0,
        phrase_time_limit: float = 12.0,
        **_: object,
    ) -> RealtimeSpeechResult:
        result = self._stt.transcribe_once(
            timeout=int(timeout),
            phrase_time_limit=int(phrase_time_limit),
            level_callback=volume_callback,
        )
        if result.text:
            self.text_detected.emit(result.text)
            if text_callback:
                text_callback(result.text)
        else:
            self.failed.emit(result.message)
        return RealtimeSpeechResult(result.text, result.message, result.provider_used)
