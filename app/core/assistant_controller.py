"""
Assistant Controller - Core orchestration for Jarvis.

This module provides the main controller class that orchestrates
the Jarvis desktop assistant. It handles:
- Text and voice command processing
- Intent routing
- Action execution
- AI brain integration
- Tone response generation
"""

import logging
import re
import time
from datetime import datetime
from typing import Callable

from app.core.action_registry import ActionRegistry
from app.core.advanced_brain import AdvancedBrain
from app.core.intent_router import IntentRouter
from app.core.locale_responses import (
    chitchat_response,
    conversational_youtube_reply,
    feedback_prefix,
    infer_lang_from_stt_code,
    localize_action_result,
    looks_conversational_soft,
    natural_english_reply,
    normalize_unicode,
    resolve_reply_language,
    soft_unknown_reply,
    strip_mode_suffix,
    stt_user_failure_message,
    tts_speak_failed_message,
    tts_unavailable_bangla_warning,
    whatsapp_flow_ask_recipient,
)
from app.core.command_normalizer import (
    extract_app_name,
    is_open_app_command,
    normalize_voice_command,
    resolve_app_name,
)
from app.core.command_router import CommandRoute, CommandRouter
from app.core.response_builder import ResponseBuilder
from app.core.route_handler import RouteHandler
from app.actions.alias_actions import execute_alias_route
from app.core.action_executor import execute_alias_action
from app.core.alias_command_matcher import ALIAS_CONFIRM_THRESHOLD, AliasMatch, match_alias_command
from app.core.response_engine import ResponseEngine
from app.core.system_action_dataset_loader import match_dataset_action
from app.data.repositories.alarm_repository import AlarmRepository
from app.data.repositories.command_repository import CommandRepository
from app.data.repositories.contacts_repository import ContactsRepository
from app.data.repositories.conversation_repository import ConversationRepository
from app.data.repositories.settings_repository import SettingsRepository
from app.data.repositories.time_management_repository import TimeManagementRepository
from app.services.automation.email_tools import (
    edit_email,
    generate_email,
    generate_formal_email,
    generate_leave_email,
    preview_email,
    send_email,
)
from app.services.automation.music_tools import (
    next_track,
    play_music,
    play_random_music,
    previous_track,
    set_music_folder,
    stop_music,
)
from app.services.automation.network_tools import last_speedtest, run_speedtest
from app.services.automation.system_tools import (
    get_battery,
    get_time,
    greet,
    open_desktop_item_stub,
    open_google,
    open_notepad,
    open_youtube,
    system_info,
    system_status,
    unknown,
    youtube_play,
    youtube_search,
)
from app.services.automation.whatsapp_tools import (
    resolve_whatsapp_recipient,
    send_whatsapp_message,
)
from app.actions.file_actions import (
    complete_pick,
    execute_file_route,
    execute_legacy_file_control,
    get_latest_file,
    is_file_action,
    search_file,
)
from app.actions.web_actions import (
    build_web_search_query,
    execute_web_route,
    handle_web_or_weather_query,
    is_weather_query,
    is_web_or_weather_query,
    matches_weather_keywords,
)
from app.services.analytics_service import AnalyticsService
from app.services.speech.stt_service import STTService
from app.services.speech.tts_service import TTSService
from app.services.system.app_launcher import open_app
from app.services.system.system_action_executor import (
    execute_confirmed_dataset_action,
    execute_dataset_action,
    is_confirm_command as is_dataset_confirm_command,
)
from app.services.system.system_control import execute_system_action, match_system_action
from app.services.vision.ocr_service import image_to_text as ocr_image_from_path

LOG = logging.getLogger(__name__)

FIXED_GREETING_QUERIES = {"hi", "hello", "hey"}
FIXED_GREETING_REPLY_BN = "জি স্যার, আমি আছি। কী করতে বলবেন?"

FIXED_LOCAL_REPLIES = {
    "ki koro": "আমি এখানে আছি স্যার, আপনার কাজের জন্য প্রস্তুত।",
    "ki kor": "আমি এখানে আছি স্যার, আপনার কাজের জন্য প্রস্তুত।",
    "কি করো": "আমি এখানে আছি স্যার, আপনার কাজের জন্য প্রস্তুত।",
    "nam ki": "আমার নাম Jarvis, আপনার personal assistant.",
    "tomar nam ki": "আমার নাম Jarvis, আপনার personal assistant.",
    "তোমার নাম কী": "আমার নাম Jarvis, আপনার personal assistant.",
}

FIXED_TIME_QUERIES = {
    "koita baze",
    "koita baje",
    "koyta baze",
    "koyta baje",
    "কয়টা বাজে",
    "কয়টা বাজে",
    "এখন কয়টা বাজে",
    "এখন কয়টা বাজে",
    "time",
}

FIXED_HEARING_QUERIES = {
    "তুমি কি আমার কথা শুনতে পাচ্ছ",
    "তুমি কি আমার কথা শুনতে পাচ্ছো",
    "আমার কথা শুনতে পাচ্ছ",
    "আমার কথা শুনতে পাচ্ছো",
}

BN_PERSONA_PREFIXES = ("স্যার", "জি স্যার", "ঠিক আছে স্যার", "দুঃখিত স্যার")

_WA_FLOW_ABORT_ACTIONS = frozenset(
    (
        "system.greet",
        "system.time",
        "system.battery",
        "system.status",
        "system.info",
        "system.open_notepad",
        "system.open_google",
        "system.open_youtube",
        "system.youtube_search",
        "system.youtube_play",
        "system.unknown",
    )
)

_YOUTUBE_VOICE_ACTIONS = frozenset(
    ("system.youtube_search", "system.youtube_play", "system.youtube_voice_play")
)


def create_controller() -> "AssistantController":
    """Factory function to create a new controller."""
    return AssistantController()


# =============================================================================
# WARNING: PUBLIC CONTROLLER API
# =============================================================================
# These methods are part of the PUBLIC API used by the UI layer (main_window.py).
# DO NOT remove, rename, or change signatures of these methods without updating
# the corresponding UI code.
#
# If you need to modify internal behavior, add new private methods instead.
# =============================================================================

class AssistantController:
    """
    Main Controller for Jarvis Desktop Assistant.
    
    This class provides the PUBLIC API used by the UI layer. All public methods
    are documented with their UI dependencies below.
    """

    def __init__(self) -> None:
        self.router = IntentRouter()
        self.registry = ActionRegistry()
        self.stt = STTService()
        self.tts = TTSService()

        self._settings = SettingsRepository()
        self.conversations = ConversationRepository()
        self.commands = CommandRepository()
        self.alarms = AlarmRepository()
        self.contacts = ContactsRepository()
        self.time_tools = TimeManagementRepository()
        self.analytics = AnalyticsService()
        self.advanced_brain = AdvancedBrain(get_setting=self._settings.get)
        self._voice_rate = 170
        self._voice_volume = 1.0
        self._pending_system_confirmation = ""
        self._pending_alias_action: dict | None = None

        self._register_actions()
        self._load_stt_defaults()
        self._load_voice_defaults()
        self._load_music_defaults()

    # ========================================================================
    # PUBLIC API: COMMAND ENTRY POINTS
    # ========================================================================

    def process(self, text: str, speak: bool = True, mode: str = "chat") -> dict:
        """
        Process a text command and generate a response.
        
        Used by: HomePage text input field (main_window.py _run_text_command)
        
        Args:
            text: The user's input text
            speak: Whether to speak the response via TTS
            
        Returns:
            dict with keys: intent, action, confidence, response, reply_lang, recognized_text
        """
        print(f"[process] input={text!r} mode={mode} speak={speak}")
        normalized = normalize_voice_command(text, log=False)
        print(f"[process] normalized={normalized!r}")
        print("[routing] system-action-first")
        route = CommandRouter.route(
            text,
            pending_alias_action=self._pending_alias_action,
            pending_system_confirmation=self._pending_system_confirmation,
            mode=mode,
        )
        if route is not None:
            routed_out = RouteHandler.handle(route, self, speak=speak, original_text=text)
            if routed_out is not None:
                return routed_out
        try:
            out = self._process_impl(text, speak, mode=mode)
        except Exception:
            LOG.exception("Assistant processing failed")
            print("[process] reaching hearing fallback")
            return ResponseBuilder.fallback(text)
        if not out:
            print("[process] reaching hearing fallback")
            return ResponseBuilder.fallback(text)
        if not str(out.get("response") or "").strip():
            print("[process] reaching hearing fallback")
            out["response"] = f"জি স্যার, আমি শুনতে পাচ্ছি। আপনি বললেন: {text}"
            out.setdefault("reply_lang", "bn")
        return out

    def listen_once_and_process(
        self,
        speak: bool = True,
        level_callback: Callable[[float], None] | None = None,
    ) -> dict:
        """
        Process voice input from microphone.
        
        Used by: HomePage microphone button (main_window.py _listen_once_command)
        
        Captures audio from microphone, transcribes via STT, then processes
        the recognized text as a command.
        
        Args:
            speak: Whether to speak the response via TTS
            
        Returns:
            dict with keys: intent, action, confidence, response, reply_lang, heard, recognized_text
        """
        stt_result = self.stt.transcribe_with_retries(attempts=1, level_callback=level_callback)
        heard = stt_result.text
        resp_pref = self._settings.get("response_language", "auto").strip().lower()
        stt_lang_guess = infer_lang_from_stt_code(self._settings.get("stt_language", "bn-BD"))

        if not heard:
            err_lang = "bn" if resp_pref in ("bn", "bangla", "bengali") else "en"
            detail = (stt_result.message or "").lower()
            if "initialization" in detail or "microphone" in detail or "no audio backend" in detail:
                response = "Microphone not available."
            elif "internet unavailable" in detail:
                response = "Internet unavailable. Google speech recognition needs an internet connection."
            elif "google request failed" in detail:
                response = "Google speech recognition request failed. Please try again."
            elif "no speech" in detail or "timeout" in detail:
                response = "I didn't hear anything. Please try again."
            elif "speech not understood" in detail:
                response = "I didn't catch that. Please try again."
            else:
                response = "I didn't catch that. Please try again."
            self.conversations.add("user", "[voice input failed]")
            self.conversations.add("assistant", response)
            self.log_voice_command(response, status="error")
            return {
                "intent": "stt_failure",
                "action": "system.stt_failure",
                "confidence": 0.0,
                "response": response,
                "reply_lang": err_lang,
                "heard": heard,
                "recognized_text": "",
            }

        self.log_voice_command(heard)
        out = self.process(heard, speak=speak, mode="voice")
        out["heard"] = heard
        out["recognized_text"] = heard
        return out

    # ========================================================================
    # SETTINGS ACCESS
    # ========================================================================

    @property
    def settings(self) -> SettingsRepository:
        """Settings repository for UI access."""
        return self._settings

    @settings.setter
    def settings(self, value: SettingsRepository) -> None:
        self._settings = value

    # ========================================================================
    # PUBLIC API: VOICE & TTS INTERFACE
    # ========================================================================

    def is_voice_reply_enabled(self) -> bool:
        """
        Check if voice reply is enabled in settings.
        
        Used by: HomePage, VoicePage (multiple checks)
        """
        value = self._settings.get(
            "speak_assistant_replies",
            self._settings.get("voice_reply_enabled", "true"),
        )
        return value.strip().lower() in (
            "1", "true", "yes", "enabled"
        )

    def is_wake_word_enabled(self) -> bool:
        value = self._settings.get("wake_word_enabled", "false")
        return value.strip().lower() in ("1", "true", "yes", "enabled", "on")

    def get_tts_status_line(self) -> str:
        """
        Get current TTS status for display.
        
        Used by: VoicePage (tts_status_label)
        """
        return self.tts.describe_current_voice()

    def voice_input_ready(self) -> bool:
        return self.stt.is_ready()

    def voice_input_unavailable_message(self) -> str:
        status = self.stt.readiness()
        message = str(status.get("message") or "").strip()
        if message:
            return message
        return "Voice input is ready: Google Speech Recognition."

    def preview_tts(self, text: str) -> str:
        """
        Preview TTS without full command processing.
        
        Used by: VoicePage (preview button)
        
        Args:
            text: The text to speak
            
        Returns:
            Warning string if TTS issue, empty string if successful
        """
        lang = resolve_reply_language(self._settings.get("response_language", "auto"), text)
        token = self.tts.speak_async(
            text,
            language_hint=lang,
            allow_auto_bengali_voice=self._tts_auto_bengali_enabled(),
        )
        return self._format_tts_warning(token, lang)

    def test_bangla_tts(self) -> str:
        """
        Test Bengali TTS voice.
        
        Used by: VoicePage (Test Bangla voice button)
        
        Returns:
            Warning string if voice issue, empty string if successful
        """
        phrase = "টেস্ট। বাংলা ভয়েস ঠিক আছে।"
        if not self.tts.bengali_voice_installed():
            return "[TTS] No Bengali voice installed."
        tok = self.tts.speak_async(phrase, language_hint="bn", allow_auto_bengali_voice=True)
        return self._format_tts_warning(tok, "bn")

    def apply_speech_preferences(
        self,
        stt_language: str = "bn-BD",
        response_language: str = "auto",
        voice_reply_enabled: bool = True,
        tts_auto_bengali_voice: bool = True,
        wake_word_enabled: bool = False,
        noise_reduction_enabled: bool = True,
        mic_sensitivity: int = 50,
        bengali_tts_speed: str = "normal",
    ) -> None:
        """
        Apply speech preferences from VoicePage UI.
        
        Used by: VoicePage (Apply speech settings button)
        
        Args:
            voice_id: TTS voice identifier
            rate: Speech rate (words per minute)
            voice_reply_enabled: Whether to speak responses
            tts_auto_bengali_voice: Whether to auto-select Bengali voice for Bangla text
        """
        self._settings.set("stt_language", stt_language or "bn-BD")
        self._settings.set("response_language", response_language or "auto")
        self._settings.set("voice_reply_enabled", "true" if voice_reply_enabled else "false")
        self._settings.set("speak_assistant_replies", "true" if voice_reply_enabled else "false")
        self._settings.set("tts_auto_bengali_voice", "1" if tts_auto_bengali_voice else "0")
        self._settings.set("wake_word_enabled", "true" if wake_word_enabled else "false")
        self._settings.set("noise_reduction_enabled", "true" if noise_reduction_enabled else "false")
        self._settings.set("mic_sensitivity", str(max(0, min(100, int(mic_sensitivity)))))
        speed_key = "faster" if str(bengali_tts_speed).strip().lower() == "faster" else "normal"
        self._settings.set("bengali_tts_speed", speed_key)
        self.tts.set_bengali_gtts_speed(speed_key)
        self.stt.set_language(self._settings.get("stt_language", "bn-BD"))
        self.stt.configure_audio(
            noise_reduction_enabled=noise_reduction_enabled,
            mic_sensitivity=mic_sensitivity,
        )

    def calibrate_ambient_noise(self) -> str:
        return self.stt.calibrate_ambient()

    def save_voice_preferences(self, voice_id: str, rate: int) -> None:
        """
        Save voice preferences to settings.
        
        Used by: VoicePage (voice sliders after change)
        
        Args:
            voice_id: TTS voice identifier
            rate: Speech rate
        """
        self._settings.set("voice_id", voice_id)
        self._settings.set("voice_rate", str(rate))

    # ========================================================================
    # PUBLIC API: SCHEDULER & TASKS INTERFACE
    # ========================================================================

    def add_alarm(self, title: str, due_at: str, recurrence: str = "none") -> str:
        """
        Add an alarm to the scheduler.
        
        Used by: SchedulerPage (add alarm button)
        
        Args:
            title: Alarm title
            due_at: Time for alarm (e.g., "07:00")
            recurrence: How often (e.g., "daily", "none")
            
        Returns:
            Confirmation message
        """
        self.alarms.add(title, due_at, recurrence)
        return f"Alarm saved for {due_at}."

    def delete_alarm(self, alarm_id: int) -> str:
        """
        Delete an alarm from the scheduler.
        
        Used by: SchedulerPage (delete alarm button)
        
        Args:
            alarm_id: The ID of the alarm to delete
            
        Returns:
            Confirmation message
        """
        self.alarms.remove(alarm_id)
        return "Alarm deleted."

    def mark_alarm_done(self, alarm_id: int) -> str:
        """
        Mark an alarm as completed.
        
        Used by: SchedulerPage (complete alarm button)
        
        Args:
            alarm_id: The ID of the alarm to mark done
            
        Returns:
            Confirmation message
        """
        self.alarms.mark_done(alarm_id)
        return "Alarm marked done."

    def start_focus_timer(self, minutes: int) -> str:
        """
        Start a focus timer.
        
        Used by: SchedulerPage (focus timer button)
        
        Args:
            minutes: Duration of focus session
            
        Returns:
            Confirmation message
        """
        self.time_tools.add("focus", f"{minutes} min focus", "pending")
        return f"Focus timer started for {minutes} minutes."

    def add_task(self, task: str) -> str:
        """
        Add a task to the task list.
        
        Used by: SchedulerPage (add task button)
        
        Args:
            task: Task description
            
        Returns:
            Confirmation message
        """
        self.time_tools.add("task", task, "pending")
        return "Task added."

    def list_tasks(self) -> list[str]:
        """
        List all tasks.
        
        Used by: SchedulerPage (task list display)
        
        Returns:
            List of task descriptions
        """
        return [t["title"] for t in self.time_tools.list_all()]

    def delete_alarm(self, alarm_id: int) -> str:
        """Delete an alarm."""
        self.alarms.remove(alarm_id)
        return "Alarm deleted."

    def mark_alarm_done(self, alarm_id: int) -> str:
        """Mark alarm as done."""
        self.alarms.mark_done(alarm_id)
        return "Alarm marked done."

    def start_focus_timer(self, minutes: int) -> str:
        """Start a focus timer."""
        self.time_tools.add("focus", f"{minutes} min focus", "pending")
        return f"Focus timer started for {minutes} minutes."

    def add_task(self, task: str) -> str:
        """Add a task."""
        self.time_tools.add("task", task, "pending")
        return "Task added."

    def list_tasks(self) -> list[str]:
        """List all tasks."""
        return [t["title"] for t in self.time_tools.list_all()]

    # ========================================================================
    # OTHER UI INTERFACE
    # ========================================================================

    def save_music_folder(self, path: str) -> str:
        """Set music folder path."""
        return set_music_folder(path)

    def ocr_file(self, path: str) -> str:
        """Perform OCR on an image file."""
        return ocr_image_from_path(path)

    # ========================================================================
    # PRIVATE IMPLEMENTATION
    # ========================================================================

    def _process_impl(self, text: str, speak: bool, mode: str = "chat") -> dict:
        text = normalize_unicode(text)
        ql = text.lower()
        reply_lang = resolve_reply_language(self._settings.get("response_language", "auto"), text)
        LOG.info("[reply] user_text=%s", text)

        self.conversations.add("user", text)
        self._log_analytics_event("text_command", source="controller", message=text)

        normalized_command = normalize_voice_command(text)
        print(f"[process] normalized={normalized_command!r}")
        if self._matches_weather_keywords(text, normalized_command):
            print("[intent] checking web_search/weather")
            print("[intent] matched weather_search")
            query = "today weather Kaliganj Bangladesh"
            print(f"[search] query: {query}")
            result = handle_web_or_weather_query(text, weather_search=True)
            summary = result.summary
            if result.error:
                summary = "স্যার, ইন্টারনেট কানেকশন সমস্যা হচ্ছে, তাই আবহাওয়ার তথ্য আনতে পারিনি।"
            return self._direct_action_response(
                text,
                intent="weather_search",
                action="web.search",
                response=summary,
                confidence=0.95 if result.results else 0.45,
                speak=speak,
                extra={
                    "handled": True,
                    "success": not bool(result.error),
                    "type": "web_search",
                    "search_kind": "weather",
                    "search_query": query,
                    "query": query,
                    "search_url": result.search_url,
                    "google_url": result.search_url,
                    "results": [
                        {"title": item.title, "snippet": item.snippet, "url": item.url}
                        for item in result.results
                    ],
                    "speak_text": summary,
                    "error": result.error,
                },
            )
        local_out = self._try_direct_command(text, normalized_command, speak, mode=mode)
        if local_out is not None:
            return local_out

        fixed = self._fixed_local_reply(text, reply_lang)
        if fixed is not None:
            if normalize_unicode(text).strip().lower() in FIXED_GREETING_QUERIES:
                reply_lang = "bn"
            return self._return_fixed_local_reply(text, fixed, reply_lang, speak)

        route = self.router.route(text)

        ai_intent = None
        needs_confirmation = False
        if route.action == "system.unknown":
            ai_intent = self.advanced_brain.detect_action_intent(text)
            if ai_intent.should_execute:
                action = ai_intent.action
                route.action = action
                route.confidence = ai_intent.confidence
                needs_confirmation = ai_intent.needs_confirmation
                import logging
                logging.getLogger("jarvis.action").info(
                    f"AI_ACTION: action={action} confidence={ai_intent.confidence:.2f} confirmation={needs_confirmation}"
                )

        if self._should_use_brain(route.action, route.confidence, text):
            brain_reply = self.advanced_brain.generate_reply(text, chat_history=self._brain_history())
            brain_reply = self._apply_persona(brain_reply, reply_lang, "brain.offline_chat", "offline_chat")
            source = self.advanced_brain.last_source()
            self.commands.add(text, route.intent, "brain.provider", brain_reply, max(route.confidence, 0.72))
            self._log_analytics_event(
                "api_call",
                source="advanced_brain",
                action="brain.provider",
                message=text,
                status="success" if "had trouble" not in brain_reply.lower() else "error",
            )
            self._conversations_add("assistant", brain_reply)
            self._log_reply(route.intent, source, brain_reply)
            out = {
                "intent": "offline_chat",
                "action": "brain.offline_chat",
                "confidence": max(route.confidence, 0.72),
                "response": brain_reply,
                "reply_lang": reply_lang,
                "recognized_text": text,
            }
            if speak and self.is_voice_reply_enabled():
                tts_note = self._speak_reply(brain_reply, reply_lang, source="brain.provider")
                if tts_note:
                    out["tts_warning"] = tts_note
            return out

        if route.action in {"system.greet", "system.chitchat"}:
            LOG.info("Local rule matched")
            LOG.info("local rule handled: %s", route.action)
            self._log_analytics_event("local_rule", source="intent_router", action=route.action, message=text)
        else:
            LOG.info("local action executed: %s", route.action)
            self._log_analytics_event("local_action", source="action_registry", action=route.action, message=text)
        result = self.registry.call(route.action, text)

        if route.action == "system.open_youtube":
            display_core = "ঠিক আছে স্যার, YouTube খুলছি।"
        elif route.action in _YOUTUBE_VOICE_ACTIONS:
            display_core = conversational_youtube_reply(route.action, text, reply_lang)
        elif route.action == "system.chitchat":
            display_core = chitchat_response(route.intent, reply_lang)
        elif reply_lang == "bn":
            if route.action == "system.unknown" and looks_conversational_soft(normalize_unicode(text), ql):
                display_core = soft_unknown_reply("bn", text)
            else:
                display_core = localize_action_result(route.action, result, "bn", route.intent, route.confidence, user_text=text)
        else:
            display_core = natural_english_reply(route.intent, route.action, result, route.confidence, text)

        display_core = ResponseEngine.render_reply(route.intent, display_core, route.confidence, reply_lang, route.action)

        response_dict = self._finalize_response(text, display_core, route, reply_lang, speak)

        if needs_confirmation:
            response_dict["needs_confirmation"] = True
            response_dict["pending_action"] = route.action

        return response_dict

    def _try_direct_command(self, text: str, normalized: str, speak: bool, mode: str = "chat") -> dict | None:
        resolved_app = resolve_app_name(f"{text} {normalized}")
        if resolved_app:
            LOG.info("[intent] matched open_app: %s", resolved_app)
            result = open_app(resolved_app, allow_fallback=False)
            return self._direct_action_response(
                text,
                intent="open_app",
                action="system.open_app",
                response=result.message,
                confidence=0.98 if result.success else 0.45,
                speak=speak,
                extra={
                    "handled": True,
                    "success": result.success,
                    "app_name": result.app_name or resolved_app,
                    "opened": result.opened,
                },
            )
        if is_file_action(text, normalized):
            file_result = execute_file_route(text, normalized)
            return self._direct_action_response(
                text,
                intent=file_result.intent,
                action="system.file_automation",
                response=file_result.message,
                confidence=0.92 if file_result.success else 0.55,
                speak=speak,
                extra={
                    "handled": True,
                    "success": file_result.success,
                    "type": "system_action",
                    "path": file_result.path,
                    "candidates": file_result.candidates,
                    "speak_text": file_result.message,
                    "error": file_result.error,
                },
            )
        system_out = self._try_system_control_command(text, normalized, speak)
        if system_out is not None:
            return system_out
        if is_open_app_command(normalized, text):
            app_name = extract_app_name(normalized)
            if app_name:
                LOG.info("[intent] matched open_app: %s", app_name)
                result = open_app(app_name, allow_fallback=True)
                return self._direct_action_response(
                    text,
                    intent="open_app",
                    action="system.open_app",
                    response=result.message,
                    confidence=0.98 if result.success else 0.45,
                    speak=speak,
                    extra={
                        "handled": True,
                        "success": result.success,
                        "app_name": result.app_name or app_name,
                        "opened": result.opened,
                    },
                )
        LOG.info("[intent] checking web_search/weather")
        weather_search = self._is_weather_query(text, normalized)
        if self._should_web_search(text, normalized, mode):
            query = self._build_web_search_query(text, normalized, weather_search=weather_search)
            if query:
                if weather_search:
                    LOG.info("[intent] matched weather_search")
                LOG.info("[intent] matched google_search: %s", query)
                result = handle_web_or_weather_query(text, weather_search=weather_search)
                summary = result.summary
                if weather_search and result.error:
                    summary = "স্যার, আবহাওয়ার তথ্য আনতে পারিনি। ইন্টারনেট কানেকশন চেক করুন।"
                return self._direct_action_response(
                    text,
                    intent="google_search",
                    action="web.search",
                    response=summary,
                    confidence=0.95 if result.results else 0.45,
                    speak=speak,
                    extra={
                        "handled": True,
                        "success": not bool(result.error),
                        "type": "web_search",
                        "search_query": query,
                        "query": query,
                        "search_url": result.search_url,
                        "google_url": result.search_url,
                        "search_kind": "weather" if weather_search else "web",
                        "results": [
                            {"title": item.title, "snippet": item.snippet, "url": item.url}
                            for item in result.results
                        ],
                        "speak_text": summary,
                        "error": result.error,
                    },
                )
        return None

    def _apply_voice_text_correction(self, text: str) -> str:
        before = text or ""
        after = before
        replacements = (
            ("আনমিউট", "unmute"),
            ("ভলিউম", "volume"),
            ("ভলিওম", "volume"),
            ("voliom", "volume"),
            ("কমাও", "decrease"),
            ("komao", "decrease"),
            ("বাড়াও", "increase"),
            ("বাড়াও", "increase"),
            ("baraw", "increase"),
            ("মিউট", "mute"),
        )
        for source, target in replacements:
            if source.isascii():
                after = re.sub(rf"\b{re.escape(source)}\b", target, after, flags=re.IGNORECASE)
            else:
                after = after.replace(source, target)
        if after != before:
            LOG.info("[voice-correction] before=%s after=%s", before, after)
            print(f"[voice-correction] before={before} after={after}")
        return after

    def _try_volume_clarification(self, text: str, normalized: str, speak: bool) -> dict | None:
        if (normalized or "").strip().casefold() != "volume":
            return None
        return ResponseBuilder.volume_clarification(self, text, speak)

    def _handle_command_route(self, route: CommandRoute, speak: bool, original_text: str) -> dict | None:
        return RouteHandler.handle(route, self, speak=speak, original_text=original_text)

    def _try_pending_system_confirmation(self, text: str, speak: bool) -> dict | None:
        pending_alias = self._pending_alias_action
        if pending_alias is not None:
            if self._is_alias_confirm_command(text):
                self._pending_alias_action = None
                confidence = float(pending_alias.get("confidence") or 0.0)
                if confidence < ALIAS_CONFIRM_THRESHOLD:
                    LOG.info("[alias-confirm] ignored low confidence %.3f input=%r", confidence, pending_alias.get("original_text"))
                    print(f"[alias-confirm] ignored low confidence {confidence:.3f} input={pending_alias.get('original_text')!r}")
                    return None
                match = pending_alias.get("match")
                if isinstance(match, AliasMatch):
                    result = execute_alias_action(match.action)
                    return self._alias_action_response(text, match, result, speak)
                return None
            self._pending_alias_action = None

        pending = self._pending_system_confirmation
        if not pending:
            return None
        if not is_dataset_confirm_command(text):
            return None
        self._pending_system_confirmation = ""
        result = execute_confirmed_dataset_action(pending)
        return self._system_control_response(text, result, speak)

    def _is_alias_confirm_command(self, text: str) -> bool:
        value = normalize_voice_command(text, log=False).casefold()
        raw = (text or "").casefold()
        return is_dataset_confirm_command(text) or value in {"yes", "y", "ha", "haa"} or raw in {"হ্যাঁ", "হাঁ", "হ্যা"}

    def _try_alias_command(self, text: str, speak: bool, original_text: str | None = None) -> dict | None:
        display_text = original_text or text
        match = match_alias_command(text)
        if match is None:
            return None
        return self._handle_alias_match(display_text, match, speak)

    def _handle_alias_match(self, display_text: str, match: AliasMatch, speak: bool) -> dict | None:
        if match.should_execute:
            result = execute_alias_route(match)
            return self._alias_action_response(display_text, match, result, speak)
        if match.should_confirm:
            self._pending_alias_action = {
                "original_text": display_text,
                "action": match.action.action,
                "target": match.action.target,
                "confidence": match.confidence,
                "created_at": time.time(),
                "match": match,
            }
            return ResponseBuilder.alias_confirmation(self, display_text, match, speak)

        LOG.info("[alias-confirm] ignored low confidence %.3f input=%r", match.confidence, display_text)
        print(f"[alias-confirm] ignored low confidence {match.confidence:.3f} input={display_text!r}")
        return None

    def _alias_action_response(self, text: str, match: AliasMatch, result, speak: bool) -> dict:
        return ResponseBuilder.alias_action(self, text, match, result, speak)

    def _try_dataset_system_action(self, text: str, normalized: str, speak: bool, original_text: str | None = None) -> dict | None:
        display_text = original_text or text
        LOG.info("[system-action] input: %s", text)
        record = match_dataset_action(text, normalized)
        if record is None:
            return None
        result = execute_dataset_action(record, original_text=display_text)
        if result.requires_confirmation:
            self._pending_system_confirmation = record.target
        return self._system_control_response(display_text, result, speak)

    def _try_system_control_command(self, text: str, normalized: str, speak: bool) -> dict | None:
        LOG.info("[system-action] input: %s", text)
        dataset_match = match_dataset_action(text, normalized)
        match = match_system_action(text, dataset_match)
        if not match:
            return None
        LOG.info("[system-action] matched: %s target=%s", match.get("intent"), match.get("target"))
        result = execute_system_action(match)
        if result.requires_confirmation:
            self._pending_system_confirmation = str(match.get("target") or result.target)
        return self._system_control_response(text, result, speak)

    def _system_control_response(self, text: str, result, speak: bool) -> dict:
        return ResponseBuilder.system_action(self, text, result, speak)

    def _should_web_search(self, text: str, normalized: str, mode: str) -> bool:
        return is_web_or_weather_query(text, normalized, mode)

    def _matches_weather_keywords(self, text: str, normalized: str) -> bool:
        return matches_weather_keywords(text, normalized)

    def _weather_search_response(self, text: str, *, speak: bool = False) -> dict:
        result = execute_web_route(text, normalize_voice_command(text, log=False))
        if result is None:
            result = execute_web_route("today weather Kaliganj Bangladesh", "today weather")
        query = result.query if result is not None else "today weather Kaliganj Bangladesh"
        print(f"[search] query: {query}")
        LOG.info("[intent] matched weather_search")
        LOG.info("[search] query: %s", query)
        results = result.results if result is not None else []
        summary = result.response if result is not None else ""
        error = result.error if result is not None else "search_failed"
        google_url = result.google_url if result is not None else ""
        if error or not summary:
            summary = "স্যার, ইন্টারনেট কানেকশন সমস্যা হচ্ছে, তাই আবহাওয়ার তথ্য আনতে পারিনি।"

        self.conversations.add("user", text)
        self.conversations.add("assistant", summary)
        self.commands.add(text, "weather_search", "web.search", summary, 0.95 if results else 0.45)
        self._log_analytics_event("local_action", source="weather_search", action="web.search", message=text)

        out = {
            "type": "web_search",
            "intent": "weather_search",
            "action": "web.search",
            "handled": True,
            "success": not bool(error),
            "confidence": 0.95 if results else 0.45,
            "query": query,
            "search_query": query,
            "google_url": google_url,
            "search_url": google_url,
            "response": summary,
            "speak_text": summary,
            "results": results,
            "reply_lang": "bn",
            "recognized_text": text,
            "error": error,
        }
        if speak and self.is_voice_reply_enabled():
            warning = self._speak_reply(summary, "bn", source="web.search")
            if warning:
                out["tts_warning"] = warning
        return out

    def _is_weather_query(self, text: str, normalized: str) -> bool:
        return is_weather_query(text, normalized)

    def _build_web_search_query(self, text: str, normalized: str, *, weather_search: bool = False) -> str:
        return build_web_search_query(text, normalized, weather_search=weather_search)

    def _contains_any(self, value: str, needles: tuple[str, ...]) -> bool:
        folded = (value or "").casefold()
        return any(needle.casefold() in folded for needle in needles)

    def _direct_action_response(
        self,
        text: str,
        *,
        intent: str,
        action: str,
        response: str,
        confidence: float,
        speak: bool,
        extra: dict | None = None,
    ) -> dict:
        if extra and extra.get("type") == "web_search":
            LOG.info("[voice] speaking search answer")
        return ResponseBuilder.direct_action(
            self,
            text,
            intent=intent,
            action=action,
            response=response,
            confidence=confidence,
            speak=speak,
            extra=extra,
        )

    def _fixed_local_reply(self, text: str, reply_lang: str) -> str | None:
        q = normalize_unicode(text).strip().lower()
        if q in FIXED_GREETING_QUERIES:
            LOG.info("Local rule matched")
            return FIXED_GREETING_REPLY_BN
        if q in FIXED_LOCAL_REPLIES:
            LOG.info("Local rule matched")
            return self._apply_persona(FIXED_LOCAL_REPLIES[q], reply_lang, "local.fixed_reply", "fixed_local_chat")
        if q in FIXED_TIME_QUERIES:
            LOG.info("Local rule matched")
            return self._apply_persona(f"এখন সময় {datetime.now().strftime('%I:%M %p')}.", "bn", "system.time", "time")
        if q in FIXED_HEARING_QUERIES:
            LOG.info("Local rule matched")
            return "জি স্যার, আমি আপনার কথা শুনতে পাচ্ছি।"
        return None

    def _return_fixed_local_reply(self, text: str, reply: str, reply_lang: str, speak: bool) -> dict:
        self.commands.add(text, "fixed_local_chat", "local.fixed_reply", reply, 1.0)
        self.conversations.add("assistant", reply)
        self._log_analytics_event("local_rule", source="fixed_local_reply", action="local.fixed_reply", message=text)
        q = normalize_unicode(text).strip().lower()
        if q in FIXED_GREETING_QUERIES:
            intent = "greeting"
        else:
            intent = "time" if q in FIXED_TIME_QUERIES else "fixed_local_chat"
            if q in FIXED_HEARING_QUERIES:
                intent = "hearing_check"
        self._log_reply(intent, "local_intent", reply)
        out = {
            "intent": intent,
            "action": "local.fixed_reply",
            "confidence": 1.0,
            "response": reply,
            "reply_lang": reply_lang,
            "recognized_text": text,
        }
        if speak and self.is_voice_reply_enabled():
            tts_note = self._speak_reply(reply, reply_lang, source="local.fixed_reply")
            if tts_note:
                out["tts_warning"] = tts_note
        return out

    def _finalize_response(self, text: str, display: str, route, reply_lang: str, speak: bool) -> dict:
        if route.action.startswith("brain.") or route.action == "system.open_youtube":
            response = display.strip()
        else:
            fb = feedback_prefix(route.intent, route.confidence, reply_lang, seed=text)
            mode_hint = self.advanced_brain.suggest_mode(text)
            prefix = f"{fb} " if fb else ""
            response = f"{prefix}{display} [mode:{mode_hint}]"
        response = self._apply_persona(response, reply_lang, route.action, route.intent)

        self.commands.add(text, route.intent, route.action, response, route.confidence)
        self.conversations.add("assistant", response)
        self._log_reply(route.intent, "local_intent", response)

        want_speak = speak and self.is_voice_reply_enabled()
        tts_note = ""
        if want_speak:
            tts_note = self._speak_reply(response, reply_lang, source=route.action)

        out = {
            "intent": route.intent,
            "action": route.action,
            "confidence": route.confidence,
            "response": response,
            "reply_lang": reply_lang,
            "recognized_text": text,
        }
        if tts_note:
            out["tts_warning"] = tts_note
        return out

    def log_voice_command(self, text: str, *, status: str = "success") -> None:
        self._log_analytics_event("voice_command", source="stt", action="voice.input", status=status, message=text)

    def _log_analytics_event(
        self,
        event_type: str,
        *,
        source: str = "",
        action: str = "",
        status: str = "success",
        message: str = "",
    ) -> None:
        try:
            self.analytics.log_event(event_type, source=source, action=action, status=status, message=message)
        except Exception:
            LOG.exception("Failed to log analytics event: %s", event_type)

    def _conversations_add(self, role: str, text: str) -> None:
        try:
            self.conversations.add(role, text)
        except Exception:
            pass

    def _log_reply(self, intent: str, source: str, final_text: str) -> None:
        LOG.info("[reply] intent=%s", intent)
        LOG.info("[reply] source=%s", source)
        LOG.info("[reply] final_text=%s", final_text)

    def _persona_style(self) -> str:
        return self._settings.get("JARVIS_PERSONA_STYLE", self._settings.get("jarvis_persona_style", "bn_sir")).strip()

    def _apply_persona(self, text: str, reply_lang: str, action: str, intent: str) -> str:
        final = strip_mode_suffix(text).strip()
        if reply_lang != "bn" or self._persona_style() != "bn_sir" or not final:
            return final
        if final.startswith(BN_PERSONA_PREFIXES):
            return final
        lowered = final.lower()
        if "trouble" in lowered or "failed" in lowered or "error" in lowered or action.endswith("failure"):
            return f"দুঃখিত স্যার, {final}"
        if action == "system.time" or intent in {"time", "time_query"}:
            cleaned = final
            if cleaned.startswith("এখন সময়"):
                cleaned = cleaned.replace("এখন সময়", "এখন সময়", 1)
            return f"স্যার, {cleaned}"
        command_success = (
            action.startswith("system.")
            or action.startswith("music.")
            or action.startswith("weather.")
            or action.startswith("network.")
            or action.startswith("local.")
        )
        if command_success:
            return f"ঠিক আছে স্যার, {final}"
        return f"জি স্যার, {final}"

    def _should_use_brain(self, action: str, confidence: float, text: str) -> bool:
        return self.advanced_brain.should_handle(action, confidence, text)

    def _brain_history(self, limit: int = 10) -> list[dict]:
        rows = self.conversations.latest(limit=limit)
        history = []
        for row in reversed(rows):
            role = str(row.get("role") or "").strip().lower()
            if role not in {"user", "assistant"}:
                continue
            text = strip_mode_suffix(str(row.get("text") or "").strip())
            if text:
                history.append({"role": role, "text": text})
        if history and history[-1]["role"] == "user":
            history.pop()
        return history

    def _tts_auto_bengali_enabled(self) -> bool:
        return self._settings.get("tts_auto_bengali_voice", "1").strip() == "1"

    def _speak_reply(self, text: str, reply_lang: str, *, source: str) -> str:
        spoken = strip_mode_suffix(text).strip()
        if not spoken:
            return ""
        if reply_lang != "bn":
            try:
                voice_id, voice_name = self.tts.current_voice_info()
            except Exception:
                voice_id, voice_name = "", "(unknown)"
            LOG.info("Speaking response via TTS: source=%s voice=%s", source, voice_name or voice_id or "(default)")
            print(f"Speaking response... Voice used: {voice_name or voice_id or '(default)'}")
        token = self.tts.speak_streaming(
            spoken,
            language_hint=reply_lang,
        )
        return self._format_tts_warning(token, reply_lang)

    def speak_reply_blocking(self, text: str, reply_lang: str = "auto", *, source: str = "voice.loop") -> str:
        lang = resolve_reply_language(reply_lang, text) if reply_lang == "auto" else reply_lang
        return self._speak_reply(text, lang, source=source)

    def _format_tts_warning(self, token: str, reply_lang: str) -> str:
        if not token:
            return ""
        if token == "bengali_voice_missing":
            return tts_unavailable_bangla_warning() if reply_lang == "bn" else ""
        if token in ("speak_failed", "engine_muted"):
            return tts_speak_failed_message(reply_lang)
        return ""

    def _register_actions(self) -> None:
        self.registry.register("system.greet", greet)
        self.registry.register("system.time", get_time)
        self.registry.register("system.battery", get_battery)
        self.registry.register("system.status", system_status)
        self.registry.register("system.info", system_info)
        self.registry.register("system.open_notepad", open_notepad)
        self.registry.register("system.open_desktop_item", open_desktop_item_stub)
        self.registry.register("system.file_control", execute_legacy_file_control)
        self.registry.register("system.open_google", open_google)
        self.registry.register("system.open_youtube", open_youtube)
        self.registry.register("system.open_whatsapp", lambda _: "Opening WhatsApp.")
        self.registry.register("system.youtube_search", youtube_search)
        self.registry.register("system.youtube_play", youtube_play)
        self.registry.register("system.unknown", unknown)
        self.registry.register("system.chitchat", lambda _: "")
        self.registry.register("music.play", play_music)
        self.registry.register("music.play_random", play_random_music)
        self.registry.register("music.next", next_track)
        self.registry.register("music.previous", previous_track)
        self.registry.register("music.stop", stop_music)
        self.registry.register("weather.current", lambda _: "Weather info")
        self.registry.register("network.speedtest", run_speedtest)
        self.registry.register("network.speedtest_last", last_speedtest)
        self.registry.register("whatsapp.send", send_whatsapp_message)
        self.registry.register("scheduler.alarm", lambda _: "Alarm set")
        self.registry.register("time.focus", lambda _: "Timer started")

    def _load_stt_defaults(self) -> None:
        self.stt.set_language(self._settings.get("stt_language", "bn-BD"))
        try:
            mic_sensitivity = int(self._settings.get("mic_sensitivity", "50") or "50")
        except ValueError:
            mic_sensitivity = 50
        self.stt.configure_audio(
            noise_reduction_enabled=self._settings.get("noise_reduction_enabled", "true").strip().lower()
            in ("1", "true", "yes", "on", "enabled"),
            mic_sensitivity=mic_sensitivity,
        )

    def _load_voice_defaults(self) -> None:
        voice_id = self._settings.get("voice_id", "")
        rate = int(self._settings.get("voice_rate", "170") or "170")
        if voice_id:
            self.tts.set_voice(voice_id)
        self.tts.set_rate(rate)
        volume = float(self._settings.get("voice_volume", "1.0") or "1.0")
        self.tts.set_volume(volume)
        self.tts.set_bengali_gtts_speed(self._settings.get("bengali_tts_speed", "normal"))
        self._voice_rate = rate
        self._voice_volume = volume

    def _load_music_defaults(self) -> None:
        folder = self._settings.get("music_folder", "")
        if folder:
            set_music_folder(folder)
