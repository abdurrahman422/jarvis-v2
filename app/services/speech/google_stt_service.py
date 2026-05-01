from __future__ import annotations

import logging
import sys
import audioop
import time
from dataclasses import dataclass

try:
    import pyaudio  # noqa: F401

    _AUDIO_BACKEND = "PyAudio"
except ImportError:
    try:
        import pyaudiowpatch as pyaudio  # type: ignore[import-not-found]

        sys.modules["pyaudio"] = pyaudio
        _AUDIO_BACKEND = "PyAudioWPatch"
    except ImportError:
        _AUDIO_BACKEND = None

import speech_recognition as sr

LOG = logging.getLogger("jarvis.voice.stt")


class GoogleSTTError(Exception):
    """Base error for user-facing Google STT failures."""


class MicrophoneNotFoundError(GoogleSTTError):
    pass


class InternetUnavailableError(GoogleSTTError):
    pass


class SpeechNotUnderstoodError(GoogleSTTError):
    pass


class GoogleSTTRequestError(GoogleSTTError):
    pass


@dataclass
class GoogleSTTResult:
    text: str
    message: str
    provider_used: str = "google"


def audio_backend_description() -> str:
    if _AUDIO_BACKEND is None:
        return "no audio backend available (install PyAudio or PyAudioWPatch for microphone capture)"
    return f"audio backend: {_AUDIO_BACKEND}"


class GoogleSTTService:
    def __init__(self, language: str = "bn-BD") -> None:
        self.language = language or "bn-BD"
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.recognizer.phrase_threshold = 0.3
        self.recognizer.non_speaking_duration = 0.5
        self.noise_reduction_enabled = True
        self.mic_sensitivity = 50
        self._last_ambient_adjusted_at = 0.0

    def set_language(self, language: str) -> None:
        self.language = (language or "bn-BD").strip() or "bn-BD"

    def configure_audio(self, *, noise_reduction_enabled: bool = True, mic_sensitivity: int = 50) -> None:
        self.noise_reduction_enabled = bool(noise_reduction_enabled)
        self.mic_sensitivity = max(0, min(100, int(mic_sensitivity)))
        sensitivity = max(0.55, min(1.8, 1.5 - (self.mic_sensitivity / 100.0)))
        self.recognizer.dynamic_energy_adjustment_ratio = sensitivity
        self.recognizer.pause_threshold = 0.8
        self.recognizer.phrase_threshold = 0.3
        self.recognizer.non_speaking_duration = 0.5

    def calibrate_ambient(self, duration: float = 0.8) -> int:
        if _AUDIO_BACKEND is None:
            raise MicrophoneNotFoundError(audio_backend_description())
        try:
            with sr.Microphone() as source:
                self._prepare_recognizer()
                self.recognizer.adjust_for_ambient_noise(source, duration=duration)
                self._last_ambient_adjusted_at = time.monotonic()
                self._stabilize_energy_threshold()
                self._log_audio(f"[stt-audio] ambient adjusted")
                self._log_audio(f"[stt-audio] energy_threshold={int(self.recognizer.energy_threshold)}")
                return int(self.recognizer.energy_threshold)
        except (OSError, AttributeError) as exc:
            raise MicrophoneNotFoundError(str(exc)) from exc

    def listen_once(self, timeout: int = 8, phrase_time_limit: int = 12) -> str:
        if _AUDIO_BACKEND is None:
            raise MicrophoneNotFoundError(audio_backend_description())

        try:
            with sr.Microphone() as source:
                LOG.info("[stt] Listening...")
                print("[stt] Listening...")
                self._prepare_recognizer()
                now = time.monotonic()
                if now - self._last_ambient_adjusted_at > 20.0:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.8)
                    self._last_ambient_adjusted_at = now
                    self._log_audio("[stt-audio] ambient adjusted")
                self._stabilize_energy_threshold()
                self._log_audio(f"[stt-audio] energy_threshold={int(self.recognizer.energy_threshold)}")
                audio = self.recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_time_limit
                )
                audio = self._preprocess_audio(audio)
        except sr.WaitTimeoutError as exc:
            raise SpeechNotUnderstoodError("no speech detected before timeout") from exc
        except (OSError, AttributeError) as exc:
            raise MicrophoneNotFoundError(str(exc)) from exc

        try:
            text = self.recognizer.recognize_google(audio, language=self.language)
        except sr.UnknownValueError as exc:
            raise SpeechNotUnderstoodError("speech was not understood") from exc
        except sr.RequestError as exc:
            message = str(exc)
            LOG.error("[stt] Google STT failed: %s", message)
            print(f"[stt] Google STT failed: {message}")
            if _looks_like_network_error(message):
                raise InternetUnavailableError(message) from exc
            raise GoogleSTTRequestError(message) from exc

        cleaned = " ".join((text or "").strip().split())
        LOG.info("[stt] Recognized: %s", cleaned)
        print(f"[stt] Recognized: {cleaned}")
        return cleaned

    def _prepare_recognizer(self) -> None:
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.recognizer.phrase_threshold = 0.3
        self.recognizer.non_speaking_duration = 0.5
        self._stabilize_energy_threshold()

    def _stabilize_energy_threshold(self) -> None:
        if float(self.recognizer.energy_threshold) < 100:
            old = int(self.recognizer.energy_threshold)
            self.recognizer.energy_threshold = 300
            self._log_audio(f"[stt-audio] threshold reset {old}->300")

    def _preprocess_audio(self, audio: sr.AudioData) -> sr.AudioData:
        raw = audio.get_raw_data()
        sample_width = audio.sample_width
        sample_rate = audio.sample_rate
        if sample_width <= 0 or sample_rate <= 0:
            self._reject_audio("invalid audio metadata")

        raw = self._trim_silence(raw, sample_rate, sample_width)
        duration = len(raw) / float(sample_rate * sample_width)
        rms = audioop.rms(raw, sample_width) if raw else 0
        min_rms = max(35, int(float(self.recognizer.energy_threshold) * 0.08))
        if duration < 0.4 or rms < min_rms:
            self._reject_audio(f"duration={duration:.2f}s rms={rms}")

        if self.noise_reduction_enabled:
            raw = self._normalize_volume(raw, sample_width)
            duration = len(raw) / float(sample_rate * sample_width)
            rms = audioop.rms(raw, sample_width) if raw else 0
            if duration < 0.4 or rms < min_rms:
                self._reject_audio(f"post-normalize duration={duration:.2f}s rms={rms}")

        return sr.AudioData(raw, sample_rate, sample_width)

    def _trim_silence(self, raw: bytes, sample_rate: int, sample_width: int) -> bytes:
        if not raw:
            return raw
        chunk_size = max(sample_width, int(0.02 * sample_rate) * sample_width)
        threshold = max(80, min(900, int(float(self.recognizer.energy_threshold) * 0.35)))
        start = 0
        end = len(raw)
        while start + chunk_size <= end and audioop.rms(raw[start : start + chunk_size], sample_width) < threshold:
            start += chunk_size
        while end - chunk_size >= start and audioop.rms(raw[end - chunk_size : end], sample_width) < threshold:
            end -= chunk_size
        trimmed = raw[start:end]
        return trimmed if trimmed else raw

    def _normalize_volume(self, raw: bytes, sample_width: int) -> bytes:
        rms = audioop.rms(raw, sample_width) if raw else 0
        if rms <= 0:
            return raw
        target_rms = 3000 + int(self.mic_sensitivity * 20)
        factor = max(0.5, min(4.0, target_rms / float(rms)))
        try:
            return audioop.mul(raw, sample_width, factor)
        except audioop.error:
            return raw

    def _reject_audio(self, reason: str) -> None:
        self._log_audio(f"[stt-audio] rejected too short/noisy audio ({reason})")
        raise SpeechNotUnderstoodError("rejected too short/noisy audio")

    def _log_audio(self, message: str) -> None:
        LOG.info(message)
        print(message)


def _looks_like_network_error(message: str) -> bool:
    low = (message or "").lower()
    return any(
        token in low
        for token in (
            "internet",
            "network",
            "connection",
            "timed out",
            "timeout",
            "name resolution",
            "getaddrinfo",
            "urlopen",
            "socket",
            "unreachable",
        )
    )
