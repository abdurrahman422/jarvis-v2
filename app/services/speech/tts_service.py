import logging
import os
import queue
import re
import hashlib
import shutil
import sys
import threading
import time
import importlib.util
import traceback
import subprocess
import wave
from pathlib import Path
from typing import Any, Optional

from app.app_paths import LOGS_DIR, PROJECT_ROOT

def _preload_clean_typing_extensions() -> None:
    if "typing_extensions" in sys.modules:
        return
    for path_text in sys.path:
        if "codex-primary-runtime" not in path_text or not path_text.endswith("site-packages"):
            continue
        candidate = Path(path_text) / "typing_extensions.py"
        if not candidate.exists():
            continue
        spec = importlib.util.spec_from_file_location("typing_extensions", candidate)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules["typing_extensions"] = module
        return


_preload_clean_typing_extensions()


def _prepare_pywin32_paths() -> None:
    """Make pywin32 DLL modules visible when the app runs from a recovered env."""
    candidates: list[Path] = []
    for raw in list(sys.path):
        if raw:
            base = Path(raw)
            candidates.append(base / "pywin32_system32")
            candidates.append(base / "win32")
            candidates.append(base / "win32" / "lib")
    candidates.append(PROJECT_ROOT / ".venv" / "Lib" / "site-packages" / "pywin32_system32")
    candidates.append(PROJECT_ROOT / ".venv" / "Lib" / "site-packages" / "win32")
    candidates.append(PROJECT_ROOT / ".venv" / "Lib" / "site-packages" / "win32" / "lib")

    for path in candidates:
        if not path.exists():
            continue
        path_text = str(path)
        if path_text not in sys.path:
            sys.path.append(path_text)
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(path_text)
            except OSError:
                pass


_prepare_pywin32_paths()

try:
    import pyttsx3
except Exception as exc:  # pragma: no cover - optional dependency
    pyttsx3 = None
    print(f"TTS not available in current interpreter: {exc}")

try:
    import winsound
except ImportError:  # pragma: no cover - winsound is Windows-only
    winsound = None

_BENGALI_RE = re.compile(r"[\u0980-\u09FF]")
_MODE_RE = re.compile(r"\[mode:[^\]]+\]\s*", re.IGNORECASE)
_CHUNK_SPLIT_RE = re.compile(r"([^,.;!?à¥¤]+[,.;!?à¥¤]?)")
_PAUSE_WORD_RE = re.compile(
    r"\s+("
    r"and|then|but|so|because|also|"
    r"à¦à¦¬à¦‚|à¦¤à¦¾à¦°à¦ªà¦°|à¦¤à¦¾à¦¹à¦²à§‡|à¦•à¦¿à¦¨à§à¦¤à§|à¦•à¦¾à¦°à¦£|à¦†à¦°"
    r")\s+",
    re.IGNORECASE,
)
BENGALI_WAV_PATH = PROJECT_ROOT / "assets" / "voices" / "bangla_voice.wav"
BENGALI_WAV_CANDIDATES = (BENGALI_WAV_PATH,)
BENGALI_RUNTIME_AUDIO_DIR = PROJECT_ROOT / "app" / "runtime" / "audio"
BENGALI_REPLY_MP3_PATH = BENGALI_RUNTIME_AUDIO_DIR / "bangla_reply_latest.mp3"
BENGALI_REPLY_WAV_PATH = BENGALI_RUNTIME_AUDIO_DIR / "bangla_reply_latest.wav"
BENGALI_AUDIO_CACHE_DIR = BENGALI_RUNTIME_AUDIO_DIR / "cache"
PIPER_EXE_ENV = "PIPER_EXE"
PIPER_BN_MODEL_ENV = "PIPER_BN_MODEL"
_SPEAK_ONCE_LOCK = threading.Lock()
_LAST_SPOKEN_HASH = ""
_LAST_SPOKEN_AT = 0.0
SPEAK_ONCE_WINDOW_SECONDS = 2.0
BENGALI_GTTS_SPEED = 1.0
BENGALI_GTTS_SPEEDS = {
    "normal": 1.0,
    "faster": 1.25,
}


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("jarvis.tts")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(LOGS_DIR / "tts.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)
    return logger


_LOG = _build_logger()
if pyttsx3 is None:
    _LOG.error("TTS not available in current interpreter: pyttsx3 import failed")
else:
    _LOG.info("TTS dependency available: pyttsx3")


def _beep_fallback(reason: str = "") -> None:
    """Last-resort audible signal when real speech cannot be started."""
    if winsound is None:
        _LOG.error("TTS fallback beep unavailable: winsound is not available; reason=%s", reason)
        return
    try:
        _LOG.warning("TTS fallback beep triggered: %s", reason or "unknown")
        print(f"TTS fallback beep triggered: {reason or 'unknown'}")
        winsound.Beep(1000, 300)
    except Exception as exc:
        _LOG.exception("TTS fallback beep failed")
        print(f"TTS fallback beep failed: {exc}")


def _beep_fallback_async(reason: str = "") -> None:
    threading.Thread(target=_beep_fallback, args=(reason,), name="JarvisTTSFallbackBeep", daemon=True).start()


def _console(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        safe = message.encode(encoding, errors="backslashreplace").decode(encoding, errors="replace")
        print(safe)


def _load_project_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path)
        return
    except Exception:
        pass
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue
            value = value.strip().strip('"').strip("'")
            os.environ[key] = value
    except Exception:
        _LOG.exception("Failed to load .env")


def _clean_spoken_text_value(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    cleaned = _MODE_RE.sub("", cleaned)
    cleaned = re.sub(r"https?://\S+", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[`~*_#<>|^]+", " ", cleaned)
    return cleaned.strip()


def split_text_chunks(text: str) -> list[str]:
    """
    Split text into natural speaking chunks.
    Split by:
    - comma (,)
    - period (.)
    - Bengali danda (à¥¤)
    - pause words
    """
    cleaned = _clean_spoken_text_value(text)
    if not cleaned:
        return []

    marked = _PAUSE_WORD_RE.sub(lambda match: f"|{match.group(1)} ", cleaned)
    chunks: list[str] = []
    for part in marked.split("|"):
        part = part.strip()
        if not part:
            continue
        for match in _CHUNK_SPLIT_RE.finditer(part):
            chunk = match.group(0).strip()
            if chunk:
                chunks.append(chunk)

    if not chunks:
        return [cleaned]
    return chunks


def _play_mp3_file(mp3_path: Path) -> bool:
    try:
        _LOG.info("playback started: %s", mp3_path)
        _console(f"playback started: {mp3_path}")
        from playsound import playsound

        playsound(str(mp3_path))
        return True
    except Exception:
        _LOG.exception("playsound mp3 playback failed")
        _console("playsound mp3 playback failed")
        return False


def _parse_audio_rate(mime_type: str) -> int:
    match = re.search(r"rate=(\d+)", mime_type or "")
    return int(match.group(1)) if match else 24000


def _write_pcm_wav(wav_path: Path, pcm_data: bytes, *, sample_rate: int = 24000) -> None:
    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)


def _audio_cache_path(provider: str, text: str, suffix: str, *, variant: str = "") -> Path:
    digest = hashlib.sha256(f"{provider}:{variant}:{text}".encode("utf-8")).hexdigest()
    return BENGALI_AUDIO_CACHE_DIR / f"{provider}_{digest}{suffix}"


def _text_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _claim_speak_once(text: str) -> bool:
    global _LAST_SPOKEN_AT, _LAST_SPOKEN_HASH
    digest = _text_hash(text)
    now = time.monotonic()
    with _SPEAK_ONCE_LOCK:
        if digest == _LAST_SPOKEN_HASH and now - _LAST_SPOKEN_AT < SPEAK_ONCE_WINDOW_SECONDS:
            _LOG.info("[tts] duplicate skipped text_hash=%s", digest[:12])
            return False
        _LAST_SPOKEN_HASH = digest
        _LAST_SPOKEN_AT = now
    _LOG.info("[tts] speak_once text_hash=%s", digest[:12])
    return True


def _write_debug_latest_copy(cache_path: Path) -> None:
    BENGALI_RUNTIME_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    latest = BENGALI_REPLY_MP3_PATH if cache_path.suffix.lower() == ".mp3" else BENGALI_REPLY_WAV_PATH
    try:
        shutil.copyfile(cache_path, latest)
    except Exception:
        _LOG.debug("Could not write Bengali latest debug copy: %s", latest, exc_info=True)


def _play_wav_path(wav_path: Path) -> bool:
    if winsound is None:
        _LOG.error("WAV playback failed: winsound is not available")
        return False
    try:
        _LOG.info("playback started: %s", wav_path)
        _console(f"playback started: {wav_path}")
        winsound.PlaySound(str(wav_path), winsound.SND_FILENAME)
        return True
    except Exception:
        _LOG.exception("WAV playback failed")
        return False


def _piper_paths() -> tuple[Path | None, Path | None]:
    _load_project_env()
    exe = os.environ.get(PIPER_EXE_ENV, "").strip()
    model = os.environ.get(PIPER_BN_MODEL_ENV, "").strip()
    exe_path = Path(exe).expanduser() if exe else None
    model_path = Path(model).expanduser() if model else None
    if exe_path is not None and not exe_path.is_absolute():
        exe_path = PROJECT_ROOT / exe_path
    if model_path is not None and not model_path.is_absolute():
        model_path = PROJECT_ROOT / model_path
    if exe_path and model_path and exe_path.exists() and model_path.exists():
        return exe_path, model_path
    return None, None


def bengali_piper_available() -> bool:
    exe_path, model_path = _piper_paths()
    return exe_path is not None and model_path is not None


def log_tts_startup_status() -> dict[str, bool]:
    english_ok = pyttsx3 is not None
    piper_ok = bengali_piper_available()
    _LOG.info("[tts] english_sapi_available=%s", str(english_ok).lower())
    _LOG.info("[tts] bengali_piper_available=%s", str(piper_ok).lower())
    _console(f"[tts] english_sapi_available={str(english_ok).lower()}")
    _console(f"[tts] bengali_piper_available={str(piper_ok).lower()}")
    if not piper_ok:
        message = "[tts] Bengali offline TTS unavailable: configure PIPER_EXE and PIPER_BN_MODEL"
        _LOG.info(message)
        _console(message)
    return {"english_sapi_available": english_ok, "bengali_piper_available": piper_ok}


def _generate_bangla_piper_audio(text: str) -> Path | None:
    exe_path, model_path = _piper_paths()
    if exe_path is None or model_path is None:
        return None

    cache_path = _audio_cache_path("piper", text, ".wav")
    BENGALI_AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if cache_path.exists() and cache_path.stat().st_size > 0:
        return cache_path

    command = [str(exe_path), "--model", str(model_path), "--output_file", str(cache_path)]
    completed = subprocess.run(
        command,
        input=text,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "Piper failed").strip())
    if not cache_path.exists() or cache_path.stat().st_size <= 0:
        raise RuntimeError(f"Piper did not create usable audio: {cache_path}")
    _write_debug_latest_copy(cache_path)
    return cache_path


def set_bengali_gtts_speed(speed: str | float) -> float:
    global BENGALI_GTTS_SPEED
    if isinstance(speed, str):
        key = speed.strip().lower()
        BENGALI_GTTS_SPEED = BENGALI_GTTS_SPEEDS.get(key, 1.0)
    else:
        BENGALI_GTTS_SPEED = max(1.0, min(1.5, float(speed)))
    _LOG.info("[tts] Bengali gTTS speed set: %.2f", BENGALI_GTTS_SPEED)
    return BENGALI_GTTS_SPEED


def bengali_gtts_speed_label() -> str:
    return "faster" if BENGALI_GTTS_SPEED > 1.0 else "normal"


def _generate_bangla_gtts_audio(text: str) -> Path | None:
    speed = BENGALI_GTTS_SPEED
    speed_variant = f"speed_{speed:.2f}"
    cache_path = _audio_cache_path("gtts_bn", text, ".mp3", variant=speed_variant)
    BENGALI_AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if cache_path.exists() and cache_path.stat().st_size > 0:
        _write_debug_latest_copy(cache_path)
        return cache_path

    from gtts import gTTS

    _LOG.info("[tts] gTTS slow=False speed=%.2f", speed)
    _console(f"[tts] gTTS slow=False speed={speed:.2f}")
    tts = gTTS(text=text, lang="bn", slow=False)
    tts.save(str(cache_path))
    if speed > 1.0:
        _speedup_mp3(cache_path, speed)
    if not cache_path.exists() or cache_path.stat().st_size <= 0:
        raise RuntimeError(f"gTTS did not create usable audio: {cache_path}")
    _write_debug_latest_copy(cache_path)
    return cache_path


def _speedup_mp3(mp3_path: Path, speed: float) -> None:
    try:
        from pydub import AudioSegment
        from pydub.effects import speedup

        audio = AudioSegment.from_file(str(mp3_path), format="mp3")
        faster = speedup(audio, playback_speed=speed)
        faster.export(str(mp3_path), format="mp3")
    except Exception as exc:
        _LOG.warning("[tts] pydub speedup failed; using normal gTTS file: %s", exc)
        _console(f"[tts] pydub speedup failed; using normal gTTS file: {exc}")


def _speak_bangla_gtts(text: str) -> bool:
    try:
        _LOG.info("[tts] Bengali Piper not configured; using gTTS fallback")
        _console("[tts] Bengali Piper not configured; using gTTS fallback")
        output_path = _generate_bangla_gtts_audio(text)
        if output_path is None:
            return False
        return _play_mp3_file(output_path)
    except Exception as exc:
        _LOG.warning("[tts] Bengali gTTS fallback failed; text-only reply shown: %s", exc)
        _console(f"[tts] Bengali gTTS fallback failed; text-only reply shown: {exc}")
        return False


def speak_bangla_offline_tts(text: str) -> bool:
    """Generate or play Bengali speech with Piper, falling back to online gTTS."""
    try:
        cleaned_text = _clean_spoken_text_value(text)
        if not cleaned_text:
            raise ValueError("Bengali offline TTS skipped: empty text")

        if not _claim_speak_once(cleaned_text):
            return True

        _LOG.info("Bengali TTS requested")
        _console("Bengali TTS requested")
        BENGALI_RUNTIME_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

        cached_path = _audio_cache_path("piper", cleaned_text, ".wav")
        if cached_path.exists() and cached_path.stat().st_size > 0:
            _LOG.info("Offline Bengali TTS cache hit: %s", cached_path)
            _console(f"Offline Bengali TTS cache hit: {cached_path}")
            return _play_wav_path(cached_path)

        exe_path, model_path = _piper_paths()
        if exe_path is None or model_path is None:
            return _speak_bangla_gtts(cleaned_text)

        _LOG.info("Trying Piper TTS")
        _console("Trying Piper TTS")
        try:
            output_path = _generate_bangla_piper_audio(cleaned_text)
            if output_path is not None:
                _LOG.info("Piper TTS success")
                _console("Piper TTS success")
                return _play_wav_path(output_path)
        except Exception as exc:
            _LOG.warning("Piper TTS failed; trying gTTS fallback: %s", exc)
            _console(f"Piper TTS failed; trying gTTS fallback: {exc}")
            return _speak_bangla_gtts(cleaned_text)

        return _speak_bangla_gtts(cleaned_text)
    except Exception:
        err = traceback.format_exc()
        _LOG.error("Bengali offline TTS failed:\n%s", err)
        _console(f"Bengali offline TTS failed:\n{err}")
        return False


def debug_bangla_offline_tts() -> bool:
    if bengali_piper_available():
        return speak_bangla_offline_tts("আমি বাংলা টেস্ট করছি")
    if BENGALI_WAV_PATH.exists():
        return _play_wav_path(BENGALI_WAV_PATH)
    return False


def speak_text(text: str) -> str:
    """Compatibility helper: speak text through the normal SAPI path."""
    TTSService().speak(text, language_hint="en")
    return ""


def speak_streaming(text: str, language_hint: str) -> str:
    return TTSService().speak_streaming(text, language_hint=language_hint)


class _TTSEngineManager:
    """Singleton engine owner running on one dedicated worker thread (Windows/SAPI5)."""

    def __init__(self) -> None:
        self._engine: Optional[Any] = None
        self._queue: queue.Queue[tuple[str, dict[str, Any], Optional[queue.Queue[Any]]]] = queue.Queue()
        self._speech_lock = threading.RLock()
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()
        self._alive = True
        self._last_error = ""
        self._current_voice_id = ""
        self._rate = 170
        self._volume = 1.0
        self._last_spoken_text = ""
        self._is_speaking = False
        self._worker = threading.Thread(target=self._run, name="JarvisTTSWorker", daemon=True)
        self._worker.start()
        self._ready_event.wait(timeout=5.0)

    def _run(self) -> None:
        _LOG.debug("TTS worker started")
        self._ensure_engine(force_reinit=True)
        self._ready_event.set()

        while self._alive:
            try:
                cmd, payload, response_queue = self._queue.get(timeout=0.15)
            except queue.Empty:
                continue

            _LOG.debug(
                "TTS handling next queue item: cmd=%s queued_remaining=%s worker_alive=%s speaking=%s",
                cmd,
                self._queue.qsize(),
                self._alive,
                self._is_speaking,
            )
            if cmd == "quit":
                self._alive = False
                self._shutdown_engine()
                self._reply(response_queue, True)
                continue

            try:
                if not self._ensure_engine():
                    raise RuntimeError(self._last_error or "tts_engine_unavailable")
                result = self._handle(cmd, payload)
                self._reply(response_queue, result)
            except Exception as exc:
                self._last_error = f"{cmd}_failed:{exc}"
                self._is_speaking = False
                _LOG.exception("TTS error during %s", cmd)
                print(f"TTS ERROR: {exc}")
                if cmd == "speak":
                    _beep_fallback_async(str(exc))
                if cmd == "speak":
                    with self._speech_lock:
                        self._safe_reinitialize()
                else:
                    self._safe_reinitialize()
                self._reply(response_queue, exc)

    def _reply(self, response_queue: Optional[queue.Queue[Any]], value: Any) -> None:
        if response_queue is not None:
            response_queue.put(value)

    def _ensure_engine(self, force_reinit: bool = False) -> bool:
        if force_reinit:
            self._shutdown_engine()
        if self._engine is not None:
            return True
        if pyttsx3 is None:
            self._last_error = "init_failed:pyttsx3_not_installed"
            _LOG.error("TTS not available in current interpreter: pyttsx3 is not installed")
            print("TTS not available in current interpreter")
            return False
        try:
            _LOG.debug("TTS init start")
            print("TTS initializing...")
            engine = pyttsx3.init()
            voices = list(engine.getProperty("voices") or [])
            selected_voice_id = self._current_voice_id
            valid_voice_ids = {str(getattr(voice, "id", "") or "") for voice in voices}
            if not selected_voice_id or selected_voice_id not in valid_voice_ids:
                selected_voice_id = str(getattr(voices[0], "id", "") or "") if voices else ""
            if selected_voice_id:
                engine.setProperty("voice", selected_voice_id)
                self._current_voice_id = selected_voice_id
            engine.setProperty("rate", self._rate)
            engine.setProperty("volume", self._volume)
            self._engine = engine
            self._last_error = ""
            voice_name = ""
            for voice in voices:
                if str(getattr(voice, "id", "") or "") == self._current_voice_id:
                    voice_name = str(getattr(voice, "name", "") or "")
                    break
            _LOG.info("TTS initialized: voice=%s rate=%s volume=%s", voice_name or self._current_voice_id or "(default)", self._rate, self._volume)
            print(f"TTS initialized. Voice used: {voice_name or self._current_voice_id or '(default)'}")
            return True
        except Exception as exc:
            self._engine = None
            self._last_error = f"init_failed:{exc}"
            _LOG.exception("TTS init failed")
            print(f"TTS ERROR: {exc}")
            return False

    def _shutdown_engine(self) -> None:
        engine = self._engine
        self._engine = None
        if engine is None:
            return
        try:
            engine.stop()
        except Exception:
            _LOG.exception("TTS error while stopping engine during shutdown")

    def _safe_reinitialize(self) -> bool:
        _LOG.debug("TTS reinitialize requested")
        return self._ensure_engine(force_reinit=True)

    def _handle(self, cmd: str, payload: dict[str, Any]) -> Any:
        if self._engine is None:
            raise RuntimeError("tts_engine_missing")

        if cmd == "speak":
            text = str(payload.get("text", "")).strip()
            if not text:
                _LOG.debug("TTS speak skipped in worker: empty text")
                return True
            with self._speech_lock:
                self._stop_event.clear()
                self._is_speaking = True
                _LOG.debug("TTS speak start: %s", text[:120])
                _LOG.debug(
                    "TTS engine state before speaking: voice=%s rate=%s volume=%s",
                    self._current_voice_id or str(self._engine.getProperty("voice") or ""),
                    self._rate,
                    self._volume,
                )
                _LOG.debug("TTS engine.say called")
                print(f"TTS triggered: {text}")
                self._engine.say(text)
                _LOG.debug("TTS engine.runAndWait called")
                self._engine.runAndWait()
                self._last_spoken_text = text
                _LOG.info("TTS finished")
                print("TTS finished")
                self._is_speaking = False
                _LOG.debug("TTS engine reinitialize after completed utterance")
                self._safe_reinitialize()
            self._last_error = ""
            return True

        if cmd == "set_voice":
            voice_id = str(payload.get("voice_id", "")).strip()
            if voice_id:
                self._engine.setProperty("voice", voice_id)
                self._current_voice_id = voice_id
                _LOG.debug("TTS voice selected: %s", voice_id)
            return True

        if cmd == "set_rate":
            self._rate = int(payload.get("rate", 170))
            self._engine.setProperty("rate", self._rate)
            return True

        if cmd == "set_volume":
            self._volume = float(payload.get("volume", 1.0))
            self._engine.setProperty("volume", self._volume)
            return True

        if cmd == "stop":
            with self._speech_lock:
                self._stop_event.set()
                _LOG.debug("TTS engine.stop called")
                self._engine.stop()
                self._is_speaking = False
            return True

        if cmd == "list_voices":
            voices: list[tuple[str, str]] = []
            for voice in self._engine.getProperty("voices"):
                voices.append((voice.id, voice.name))
            return voices

        if cmd == "current_voice":
            return self._current_voice_id or str(self._engine.getProperty("voice") or "")

        raise ValueError(f"unsupported_tts_command:{cmd}")

    def enqueue(self, cmd: str, payload: Optional[dict[str, Any]] = None) -> bool:
        if not self._alive:
            _LOG.error("TTS enqueue failed: manager not alive for command=%s", cmd)
            return False
        if payload is None:
            payload = {}
        if cmd == "speak":
            self._drain_stale_speak()
        _LOG.debug(
            "TTS enqueue command=%s queued_before=%s worker_alive=%s speaking=%s",
            cmd,
            self._queue.qsize(),
            self._alive,
            self._is_speaking,
        )
        self._queue.put((cmd, payload, None))
        return True

    def request(self, cmd: str, payload: Optional[dict[str, Any]] = None, timeout: float = 5.0) -> Any:
        if not self._alive:
            raise RuntimeError("tts_manager_not_alive")
        if payload is None:
            payload = {}
        _LOG.debug(
            "TTS request command=%s queued_before=%s worker_alive=%s speaking=%s",
            cmd,
            self._queue.qsize(),
            self._alive,
            self._is_speaking,
        )
        response_queue: queue.Queue[Any] = queue.Queue(maxsize=1)
        self._queue.put((cmd, payload, response_queue))
        try:
            result = response_queue.get(timeout=timeout)
        except queue.Empty as exc:
            raise TimeoutError(f"tts_request_timeout:{cmd}") from exc
        if isinstance(result, Exception):
            raise result
        return result

    def _drain_stale_speak(self) -> None:
        kept: list[tuple[str, dict[str, Any], Optional[queue.Queue[Any]]]] = []
        try:
            while True:
                item = self._queue.get_nowait()
                if item[0] != "speak":
                    kept.append(item)
        except queue.Empty:
            pass
        for item in kept:
            self._queue.put(item)

    def stop_now(self) -> None:
        try:
            self.request("stop", timeout=2.0)
        except Exception:
            _LOG.exception("TTS stop failed")

    def is_alive(self) -> bool:
        return self._alive

    def last_error(self) -> str:
        return self._last_error

    def last_spoken_text(self) -> str:
        return self._last_spoken_text

    def queue_size(self) -> int:
        return self._queue.qsize()

    def is_speaking(self) -> bool:
        return self._is_speaking


class TTSService:
    _manager: Optional[_TTSEngineManager] = None
    _manager_lock = threading.Lock()

    def __init__(self) -> None:
        self._mgr = TTSService._manager
        self.engine = None
        self._muted = False
        self._last_voice_id = ""
        self._last_rate = 170
        self._last_volume = 1.0
        self._default_voice_id = ""
        self._default_english_voice_id = ""

    def _ensure_english_manager(self) -> bool:
        """Start the pyttsx3/SAPI manager only for non-Bengali speech paths."""
        if self._mgr is not None and self._mgr.is_alive():
            return True
        with self._manager_lock:
            if TTSService._manager is None or not TTSService._manager.is_alive():
                TTSService._manager = _TTSEngineManager()
            self._mgr = TTSService._manager
        if self._mgr is None or not self._mgr.is_alive():
            return False
        try:
            self._mgr.request("set_rate", {"rate": self._last_rate}, timeout=3.0)
            self._mgr.request("set_volume", {"volume": self._last_volume}, timeout=3.0)
            self._autodetect_default_voices()
        except Exception:
            _LOG.exception("English TTS manager setup failed")
            return False
        return True

    def engine_label(self) -> str:
        if os.name != "nt":
            return "Unsupported OS for local SAPI5 TTS"
        return "pyttsx3 / Microsoft SAPI5 on Windows"

    def list_voices(self) -> list[tuple[str, str]]:
        if not self._ensure_english_manager():
            return []
        try:
            voices = self._mgr.request("list_voices", timeout=5.0)
            return list(voices or [])
        except Exception:
            _LOG.exception("list_voices failed")
            return []

    def current_voice_info(self) -> tuple[str, str]:
        """Returns (voice_id, display_name_or_id)."""
        try:
            if not self._ensure_english_manager():
                return self._last_voice_id, self._last_voice_id or "(default voice)"
            vid = str(self._mgr.request("current_voice", timeout=2.0) or "")
        except Exception:
            vid = self._last_voice_id
        for voice_id, name in self.list_voices():
            if voice_id == vid:
                return vid, name
        return vid, vid or "(default voice)"

    def describe_current_voice(self) -> str:
        """Returns a human-readable string describing the currently selected voice."""
        try:
            voice_id, voice_name = self.current_voice_info()
            if not voice_id or not voice_name:
                return "Default voice"
            if voice_name and voice_name != voice_id:
                return voice_name
            return "Default voice"
        except Exception:
            return "No voice available"

    def _id_suggests_bengali(self, voice_id: str, voice_name: str) -> bool:
        low_id = voice_id.lower()
        low_name = voice_name.lower()
        if "bengali" in low_name or "bangla" in low_name:
            return True
        if "\u09ac\u09be\u0982\u09b2\u09be" in voice_name:
            return True
        if any(tag in low_id for tag in ("bn-in", "bn-bd", "bn_in", "bn_bd", "-bn-", "_bn_")):
            return True
        if "mbn-" in low_id or "msbn" in low_id:
            return True
        if "microsoft" in low_name and ("bangla" in low_name or "bengali" in low_name):
            return True
        if "lang" in low_id and "bn" in low_id:
            return True
        return False

    def find_bengali_voice_id(self) -> Optional[str]:
        for voice_id, voice_name in self.list_voices():
            if self._id_suggests_bengali(voice_id, voice_name):
                return voice_id
        return None

    def bengali_voice_installed(self) -> bool:
        return True

    def bengali_voice_display_name(self) -> str:
        return "Offline Bengali TTS"

    def text_has_bengali(self, text: str) -> bool:
        return bool(_BENGALI_RE.search(text or ""))

    def resolve_bangla_wav_path(self, wav_path: Optional[Path] = None) -> Optional[Path]:
        """Return the Bengali speaker-reference WAV path."""
        if wav_path is not None:
            return wav_path if wav_path.exists() else None
        for candidate in BENGALI_WAV_CANDIDATES:
            if candidate.exists():
                return candidate
        return None

    def generate_bangla_tts(self, text: str) -> bool:
        """Generate and play Bengali speech using local offline TTS."""
        return speak_bangla_offline_tts(text)

    def generate_bangla_reply_mp3(self, text: str) -> Optional[Path]:
        """Generate and play a Bengali reply MP3 from the actual reply text."""
        return BENGALI_REPLY_MP3_PATH if self.generate_bangla_tts(text) else None

    def _play_wav_file(self, wav_path: Path, *, async_playback: bool) -> bool:
        if winsound is None:
            _LOG.error("WAV playback failed: winsound is not available")
            print("WAV playback failed: winsound is not available")
            return False
        if not wav_path.exists():
            _LOG.error("WAV playback failed: file not found: %s", wav_path)
            print(f"WAV playback failed: file not found: {wav_path}")
            return False
        try:
            if self._mgr is not None and self._mgr.is_alive() and not self._mgr.last_error():
                self._mgr.stop_now()
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
            flags = winsound.SND_FILENAME
            if async_playback:
                flags |= winsound.SND_ASYNC
            _LOG.debug("Playing WAV file: %s", wav_path)
            print(f"Playing WAV file: {wav_path}")
            winsound.PlaySound(str(wav_path), flags)
            _LOG.debug("Playback started")
            print("Playback started")
            return True
        except Exception as exc:
            _LOG.exception("WAV playback failed")
            print(f"WAV playback failed: {exc}")
            return False

    def speak_bangla_text(self, text: str, async_playback: bool = True) -> bool:
        """Generate and play Bengali speech from the actual reply text."""
        return speak_bangla_offline_tts(text)

    def speak_english_pyttsx3(self, text: str, *, async_playback: bool = False) -> bool:
        """Speak one English chunk through the existing pyttsx3/SAPI path."""
        cleaned_text, _pre_speak_warning, target_voice = self._prepare_speak(
            text,
            language_hint="en",
            allow_auto_bengali_voice=False,
        )
        if not cleaned_text:
            return True
        try:
            self._mgr.stop_now()
            self._apply_runtime_settings(target_voice)
            if async_playback:
                queued = self._mgr.enqueue("speak", {"text": cleaned_text})
                return bool(queued)
            self._mgr.request("speak", {"text": cleaned_text}, timeout=30.0)
            return True
        except Exception:
            self._muted = True
            _LOG.exception("English pyttsx3 chunk speak failed")
            print("TTS ERROR: English pyttsx3 chunk speak failed")
            _beep_fallback("English pyttsx3 chunk speak failed")
            return False

    def speak_streaming(self, text: str, *, language_hint: Optional[str] = None) -> str:
        """Simulate streaming TTS by speaking natural text chunks in order."""
        lang = (language_hint or "").lower()
        if lang == "bn":
            cleaned_text = _clean_spoken_text_value(text)
            if not cleaned_text:
                return ""
            return "" if speak_bangla_offline_tts(cleaned_text) else "speak_failed"

        chunks = split_text_chunks(text)
        if not chunks:
            return ""

        _LOG.info("Streaming TTS started: lang=%s chunks=%s", lang or "auto", len(chunks))
        print(f"Streaming TTS started: chunks={len(chunks)}")

        for index, chunk in enumerate(chunks, start=1):
            ok = self.speak_english_pyttsx3(chunk, async_playback=False)

            if not ok:
                _LOG.error("Streaming TTS chunk failed: chunk=%s text=%s", index, chunk)
                print(f"Streaming TTS chunk {index} failed")
                return "speak_failed"

            _LOG.info("Chunk %s spoken", index)
            print(f"Chunk {index} spoken")
            if index < len(chunks):
                time.sleep(0.15)

        _LOG.info("Streaming finished")
        print("Streaming finished")
        return ""

    def speak_bangla_wav(self, *, async_playback: bool = True, wav_path: Optional[Path] = None) -> str:
        """Static Bengali reference WAV playback is disabled for assistant replies."""
        _LOG.warning("Static Bengali WAV playback disabled; use speak_bangla_offline_tts instead")
        print("Static Bengali WAV playback disabled; use speak_bangla_offline_tts instead")
        return "speak_failed"

    @staticmethod
    def _clean_spoken_text(text: str) -> str:
        return _clean_spoken_text_value(text)

    def _autodetect_default_voices(self) -> None:
        voices = self.list_voices()
        if not voices:
            return
        current_id, _ = self.current_voice_info()
        self._default_voice_id = current_id or voices[0][0]
        self._default_english_voice_id = self._default_voice_id
        for voice_id, voice_name in voices:
            low_name = voice_name.lower()
            if "english" in low_name or "en-" in low_name or "us" in low_name or "uk" in low_name:
                self._default_english_voice_id = voice_id
                break
        if not self._last_voice_id:
            self._last_voice_id = self._default_voice_id

    def set_voice(self, voice_id: str) -> None:
        self._last_voice_id = voice_id
        try:
            if self._mgr is None or not self._mgr.is_alive():
                _LOG.debug("TTS set_voice skipped: manager unavailable")
                return
            self._mgr.request("set_voice", {"voice_id": voice_id}, timeout=3.0)
        except Exception:
            _LOG.exception("set_voice failed")
            self._muted = True

    def set_voice_by_name(self, name_hint: str) -> bool:
        hint = name_hint.lower().strip()
        for voice_id, voice_name in self.list_voices():
            if hint in voice_name.lower():
                self.set_voice(voice_id)
                return True
        return False

    def set_rate(self, rate: int) -> None:
        self._last_rate = rate
        try:
            if self._mgr is None or not self._mgr.is_alive():
                _LOG.debug("TTS set_rate skipped: manager unavailable")
                return
            self._mgr.request("set_rate", {"rate": rate}, timeout=3.0)
        except Exception:
            _LOG.exception("set_rate failed")
            self._muted = True

    def set_volume(self, volume: float) -> None:
        value = min(max(volume, 0.0), 1.0)
        self._last_volume = value
        try:
            if self._mgr is None or not self._mgr.is_alive():
                _LOG.debug("TTS set_volume skipped: manager unavailable")
                return
            self._mgr.request("set_volume", {"volume": value}, timeout=3.0)
        except Exception:
            _LOG.exception("set_volume failed")
            self._muted = True

    def set_bengali_gtts_speed(self, speed: str | float) -> float:
        return set_bengali_gtts_speed(speed)

    def _resolve_target_voice(
        self,
        *,
        prefer_bn_voice: bool,
        bn_voice_id: Optional[str],
    ) -> str:
        target_voice = self._last_voice_id or self._default_english_voice_id or self._default_voice_id
        if prefer_bn_voice and bn_voice_id:
            target_voice = bn_voice_id

        valid_voice_ids = {voice_id for voice_id, _ in self.list_voices()}
        if target_voice and target_voice in valid_voice_ids:
            return target_voice

        fallback = ""
        if prefer_bn_voice and bn_voice_id and bn_voice_id in valid_voice_ids:
            fallback = bn_voice_id
        elif self._default_english_voice_id and self._default_english_voice_id in valid_voice_ids:
            fallback = self._default_english_voice_id
        elif self._default_voice_id and self._default_voice_id in valid_voice_ids:
            fallback = self._default_voice_id
        elif valid_voice_ids:
            fallback = next(iter(valid_voice_ids))

        if fallback:
            _LOG.debug("TTS voice fallback: requested=%s fallback=%s", target_voice, fallback)
        else:
            _LOG.debug("TTS voice fallback unavailable: requested=%s", target_voice)
        return fallback

    def _apply_runtime_settings(self, target_voice: str) -> None:
        if self._mgr is None or not self._mgr.is_alive():
            raise RuntimeError("tts_manager_not_alive")
        chosen_voice = target_voice
        if chosen_voice:
            try:
                self._mgr.request("set_voice", {"voice_id": chosen_voice}, timeout=3.0)
            except Exception:
                _LOG.exception("TTS voice selection failed for %s", chosen_voice)
                fallback = self._default_english_voice_id or self._default_voice_id
                if fallback and fallback != chosen_voice:
                    _LOG.debug("TTS retrying with fallback voice: %s", fallback)
                    self._mgr.request("set_voice", {"voice_id": fallback}, timeout=3.0)
                    chosen_voice = fallback
                else:
                    raise
        self._mgr.request("set_rate", {"rate": self._last_rate}, timeout=3.0)
        self._mgr.request("set_volume", {"volume": self._last_volume}, timeout=3.0)
        self._last_voice_id = chosen_voice

    def _prepare_speak(
        self,
        text: str,
        *,
        language_hint: Optional[str],
        allow_auto_bengali_voice: bool,
    ) -> tuple[str, str, str]:
        cleaned_text = self._clean_spoken_text(text)
        if not cleaned_text:
            _LOG.debug("TTS speak skipped: empty text after cleanup")
            return "", "", ""

        bengali = self.text_has_bengali(cleaned_text)
        bn_voice_id = self.find_bengali_voice_id()
        prefer_bn_voice = bool(
            bengali
            and bn_voice_id
            and (allow_auto_bengali_voice or (language_hint or "").lower() == "bn")
        )

        pre_speak_warning = ""
        if bengali and bn_voice_id is None:
            pre_speak_warning = "bengali_voice_missing"
        elif bengali and bn_voice_id is not None and not prefer_bn_voice:
            active_voice_id, _ = self.current_voice_info()
            if active_voice_id != bn_voice_id:
                pre_speak_warning = "bengali_voice_not_selected"

        if self._muted or self._mgr is None or not self._mgr.is_alive():
            _LOG.debug("TTS recover requested before speak")
            if not self.recover():
                _LOG.error("TTS speak skipped: engine recovery failed")
                print("TTS ERROR: engine recovery failed")
                _beep_fallback_async("engine recovery failed")
                return "", "engine_muted", ""

        target_voice = self._resolve_target_voice(
            prefer_bn_voice=prefer_bn_voice,
            bn_voice_id=bn_voice_id,
        )
        voice_label = target_voice or self._default_english_voice_id or self._default_voice_id or "(default)"
        print(f"Speaking response... Voice used: {voice_label}")
        _LOG.debug(
            "TTS speak prepared: lang=%s prefer_bn=%s target_voice=%s warning=%s worker_alive=%s queue_size=%s speaking=%s",
            language_hint or "",
            prefer_bn_voice,
            target_voice or "(default)",
            pre_speak_warning or "(none)",
            self._mgr.is_alive() if self._mgr is not None else False,
            self._mgr.queue_size() if self._mgr is not None else -1,
            self._mgr.is_speaking() if self._mgr is not None else False,
        )
        return cleaned_text, pre_speak_warning, target_voice

    def recover(self) -> bool:
        if not self._muted and self._mgr is not None and self._mgr.is_alive():
            return True
        try:
            with self._manager_lock:
                if TTSService._manager is None or not TTSService._manager.is_alive():
                    TTSService._manager = _TTSEngineManager()
            self._mgr = TTSService._manager
            if self._mgr is None or not self._mgr.is_alive():
                return False
            if self._last_voice_id:
                self._mgr.request("set_voice", {"voice_id": self._last_voice_id}, timeout=3.0)
            self._mgr.request("set_rate", {"rate": self._last_rate}, timeout=3.0)
            self._mgr.request("set_volume", {"volume": self._last_volume}, timeout=3.0)
            self._muted = False
            _LOG.debug("TTS recover successful")
            return True
        except Exception:
            _LOG.exception("TTS recover failed")
            return False

    def speak_async(
        self,
        text: str,
        *,
        language_hint: Optional[str] = None,
        allow_auto_bengali_voice: bool = False,
    ) -> str:
        """
        Speaks text via SAPI/pyttsx3. Returns a machine token if a warning applies,
        empty string on clean success.
        Bengali replies use offline Bengali TTS.
        """
        if (language_hint or "").lower() == "bn":
            return "" if self.speak_bangla_text(text, async_playback=False) else "speak_failed"

        cleaned_text, pre_speak_warning, target_voice = self._prepare_speak(
            text,
            language_hint=language_hint,
            allow_auto_bengali_voice=allow_auto_bengali_voice,
        )
        if not cleaned_text:
            _LOG.debug("TTS speak_async returning early: token=%s", pre_speak_warning or "(none)")
            return pre_speak_warning
        try:
            self._mgr.stop_now()
            self._apply_runtime_settings(target_voice)
            _LOG.debug("TTS requested asynchronously")
            queued = self._mgr.enqueue("speak", {"text": cleaned_text})
            if not queued:
                self._muted = True
                _LOG.error("Failed to queue speech")
                return "speak_failed"
            _LOG.debug("TTS speak queued: %s", cleaned_text[:120])
            return pre_speak_warning
        except Exception:
            self._muted = True
            _LOG.exception("speak failed")
            print("TTS ERROR: speak failed")
            _beep_fallback_async("speak failed")
            return "speak_failed"

    def speak(
        self,
        text: str,
        *,
        language_hint: Optional[str] = None,
        allow_auto_bengali_voice: bool = False,
    ) -> str:
        if (language_hint or "").lower() == "bn":
            return "" if self.speak_bangla_text(text, async_playback=False) else "speak_failed"

        cleaned_text, pre_speak_warning, target_voice = self._prepare_speak(
            text,
            language_hint=language_hint,
            allow_auto_bengali_voice=allow_auto_bengali_voice,
        )
        if not cleaned_text:
            _LOG.debug("TTS blocking speak returning early: token=%s", pre_speak_warning or "(none)")
            return pre_speak_warning
        try:
            self._mgr.stop_now()
            self._apply_runtime_settings(target_voice)
            _LOG.debug("TTS requested synchronously")
            self._mgr.request("speak", {"text": cleaned_text}, timeout=30.0)
            return pre_speak_warning
        except Exception:
            self._muted = True
            _LOG.exception("blocking speak failed")
            print("TTS ERROR: blocking speak failed")
            _beep_fallback("blocking speak failed")
            return "speak_failed"

    def speak_simple(self, text: str) -> str:
        return self.speak_async(text)

    def test_tts(self) -> str:
        """Diagnostic helper used at startup and by manual checks."""
        return self.speak_async("Jarvis TTS system is working")

    def debug_bangla_tts(self, text: str = "আমি বাংলা বলছি") -> bool:
        """Generate and play Bengali offline audio with verbose console diagnostics."""
        _console("=== Bengali Offline TTS Debug ===")
        _console(f"Input text: {text}")
        _console(f"Output target: {BENGALI_REPLY_MP3_PATH}")
        ok = self.speak_bangla_text(text, async_playback=False)
        exists = BENGALI_REPLY_MP3_PATH.exists()
        size = BENGALI_REPLY_MP3_PATH.stat().st_size if exists else 0
        _console(f"Generated file exists: {exists}")
        _console(f"Generated file size: {size}")
        _console(f"Bengali offline TTS debug result: {'success' if ok else 'failed'}")
        return ok

    def debug_check(self) -> dict[str, str]:
        voice_id, voice_name = self.current_voice_info()
        last_error = self._mgr.last_error() if self._mgr is not None else "manager_missing"
        last_spoken = self._mgr.last_spoken_text() if self._mgr is not None else ""
        status = {
            "engine": self.engine_label(),
            "manager_alive": "true" if self._mgr is not None and self._mgr.is_alive() else "false",
            "queue_size": str(self._mgr.queue_size()) if self._mgr is not None else "-1",
            "is_speaking": "true" if self._mgr is not None and self._mgr.is_speaking() else "false",
            "voice_id": voice_id,
            "voice_name": voice_name,
            "last_error": last_error,
            "last_spoken_text": last_spoken,
            "bengali_tts": "Bengali TTS (Piper with online gTTS fallback)",
            "bengali_reply_mp3_path": str(BENGALI_REPLY_MP3_PATH),
            "bengali_reply_mp3_exists": "true" if BENGALI_REPLY_MP3_PATH.exists() else "false",
            "bengali_runtime_audio_dir": str(BENGALI_RUNTIME_AUDIO_DIR),
        }
        _LOG.debug("TTS debug check: %s", status)
        return status

