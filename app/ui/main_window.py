import logging
import threading
import time

from PySide6.QtCore import QObject, QEasingCurve, QPropertyAnimation, Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from PySide6.QtGui import QColor

from app.core.assistant_controller import AssistantController
from app.services.vision.camera_service import capture_single_frame
from app.services.speech.wake_word_service import is_wake_word, strip_wake_word
from app.ui.pages.api_brain_page import ApiBrainPage
from app.ui.pages.automation_page import AutomationPage
from app.ui.pages.brain_page import BrainPage
from app.ui.pages.home_page import HomePage
from app.ui.pages.scheduler_page import SchedulerPage
from app.ui.pages.settings_page import SettingsPage
from app.ui.pages.vision_page import VisionPage
from app.ui.pages.voice_mode_page import VoiceModePage
from app.ui.pages.voice_page import VoicePage
from app.ui.theme import (
    NEURAL_CYAN,
    NEURAL_BLUE,
    NEURAL_GREEN,
    NEURAL_TEXT_PRIMARY,
    NEURAL_TEXT_SECONDARY,
    NEURAL_TEXT_MUTED,
    BG_NEURAL_DEEP,
    BG_NEURAL_CORE,
    BG_NEURAL_PANEL,
    BG_NEURAL_SURFACE,
    MONO_FAMILY,
)

_LOG = logging.getLogger("jarvis.voice")


class _VoiceLoopWorker(QObject):
    level_changed = Signal(float)
    recognized = Signal(str)
    reply_ready = Signal(dict)
    status = Signal(str)
    error = Signal(str)
    finished = Signal()

    def __init__(self, controller: AssistantController, wake_word_enabled: bool = False) -> None:
        super().__init__()
        self._controller = controller
        self._wake_word_enabled = wake_word_enabled
        self._stop_requested = False

    def stop(self) -> None:
        self._stop_requested = True

    def run(self) -> None:
        self.status.emit("Listening...")
        try:
            while not self._stop_requested:
                if self._wake_word_enabled:
                    self._run_wake_cycle()
                    continue
                self.status.emit("[stt] Listening...")
                stt_result = self._controller.stt.transcribe_once(level_callback=self.level_changed.emit)
                if self._stop_requested:
                    break

                heard = stt_result.text.strip()
                if not heard:
                    message = stt_result.message or "voice input failed"
                    _LOG.info("STT loop retry: %s", message)
                    self._controller.log_voice_command(message, status="error")
                    self._emit_retry_status(message)
                    continue

                _LOG.info("[stt] Recognized: %s", heard)
                _LOG.info("[voice] Recognized command: %s", heard)
                self.status.emit(f"[stt] Recognized: {heard}")
                self._controller.log_voice_command(heard)
                self.recognized.emit(heard)

                if self._stop_requested:
                    break

                try:
                    self.status.emit("Processing...")
                    out = self._controller.process(heard, speak=False, mode="voice")
                    if not out:
                        out = {
                            "intent": "fallback",
                            "action": "system.fallback",
                            "confidence": 0.0,
                            "response": f"জি স্যার, আমি শুনেছি: {heard}",
                            "reply_lang": "bn",
                        }
                    out["heard"] = heard
                    out["recognized_text"] = heard
                    _LOG.info("assistant response completed")
                    self.reply_ready.emit(out)
                    response = str(out.get("speak_text") or out.get("response") or f"জি স্যার, আমি শুনেছি: {heard}")
                    if out.get("type") == "web_search":
                        _LOG.info("[voice] speaking search answer")
                    reply_lang = str(out.get("reply_lang") or "auto")
                    if response and self._controller.is_voice_reply_enabled() and not self._stop_requested:
                        self.status.emit("Speaking...")
                        warning = self._controller.speak_reply_blocking(response, reply_lang, source="voice.loop")
                        if warning:
                            out["tts_warning"] = warning
                            self.error.emit(warning)
                    if not self._stop_requested:
                        self.status.emit("Listening again...")
                except Exception as exc:
                    _LOG.exception("voice loop process failed")
                    self.error.emit(f"[voice] Loop error: {exc}")
                    time.sleep(1)
        finally:
            self.level_changed.emit(0.05)
            self.status.emit("Voice mode stopped.")
            self.finished.emit()

    def _run_wake_cycle(self) -> None:
        self.status.emit("[wake] Listening for wake word...")
        wake_result = self._controller.stt.transcribe_raw_once(
            timeout=5,
            phrase_time_limit=3,
            level_callback=self.level_changed.emit,
        )
        if self._stop_requested:
            return

        heard = wake_result.text.strip()
        if not heard:
            self._emit_wake_retry_status(wake_result.message)
            return

        _LOG.info("[wake] heard: %s", heard)
        self.status.emit(f"[wake] heard: {heard}")
        if not is_wake_word(heard):
            return

        _LOG.info("[wake] detected")
        self.status.emit("[wake] detected")
        command = strip_wake_word(heard)
        if command:
            _LOG.info("[wake] direct command: %s", command)
            self.status.emit(f"[wake] direct command: {command}")
        else:
            if not self._stop_requested:
                self.status.emit("Speaking...")
                warning = self._controller.speak_reply_blocking("জি স্যার, বলুন।", "bn", source="voice.wake")
                if warning:
                    self.error.emit(warning)
            if self._stop_requested:
                return
            self.status.emit("[stt] Listening for command...")
            command_result = self._controller.stt.transcribe_once(
                timeout=8,
                phrase_time_limit=12,
                level_callback=self.level_changed.emit,
            )
            if self._stop_requested:
                return
            command = command_result.text.strip()
            if not command:
                message = command_result.message or "voice input failed"
                self._emit_retry_status(message)
                return

        _LOG.info("[voice] command after wake: %s", command)
        self.status.emit(f"[voice] command after wake: {command}")
        self._handle_command(command)

    def _handle_command(self, heard: str) -> None:
        _LOG.info("[stt] Recognized: %s", heard)
        _LOG.info("[voice] Recognized command: %s", heard)
        self.status.emit(f"[stt] Recognized: {heard}")
        self._controller.log_voice_command(heard)
        self.recognized.emit(heard)

        if self._stop_requested:
            return

        try:
            self.status.emit("Processing...")
            out = self._controller.process(heard, speak=False, mode="voice")
            if not out:
                out = {
                    "intent": "fallback",
                    "action": "system.fallback",
                    "confidence": 0.0,
                    "response": f"জি স্যার, আমি শুনেছি: {heard}",
                    "reply_lang": "bn",
                }
            out["heard"] = heard
            out["recognized_text"] = heard
            _LOG.info("assistant response completed")
            self.reply_ready.emit(out)
            response = str(out.get("speak_text") or out.get("response") or f"জি স্যার, আমি শুনেছি: {heard}")
            if out.get("type") == "web_search":
                _LOG.info("[voice] speaking search answer")
            reply_lang = str(out.get("reply_lang") or "auto")
            if response and self._controller.is_voice_reply_enabled() and not self._stop_requested:
                self.status.emit("Speaking...")
                warning = self._controller.speak_reply_blocking(response, reply_lang, source="voice.loop")
                if warning:
                    out["tts_warning"] = warning
                    self.error.emit(warning)
            if not self._stop_requested:
                self.status.emit("[wake] Listening for wake word...")
        except Exception as exc:
            _LOG.exception("voice loop process failed")
            self.error.emit(f"[voice] Loop error: {exc}")
            time.sleep(1)

    def _emit_wake_retry_status(self, message: str) -> None:
        lower = (message or "").lower()
        if "google" in lower or "internet" in lower:
            self.error.emit(f"[stt] Google STT failed: {message}")
            time.sleep(2)

    def _emit_retry_status(self, message: str) -> None:
        lower = (message or "").lower()
        if "no speech" in lower or "timeout" in lower:
            self.status.emit("[stt] No speech detected; listening again...")
            return
        if "speech not understood" in lower:
            self.status.emit("[stt] Speech not understood; listening again...")
            return
        if "google" in lower or "internet" in lower:
            self.error.emit(f"[stt] Google STT failed: {message}")
            time.sleep(2)
            return
        self.error.emit(self._voice_failure(message)["response"])
        time.sleep(1)

    def _voice_failure(self, message: str) -> dict:
        lower = (message or "").lower()
        if "no audio backend" in lower or "initialization" in lower or "microphone" in lower:
            response = "Microphone not available."
        elif "internet unavailable" in lower:
            response = "Internet unavailable. Google speech recognition needs an internet connection."
        elif "google request failed" in lower:
            response = "Google speech recognition request failed. Please try again."
        elif "no speech" in lower or "timeout" in lower:
            response = "I didn't hear anything. Please try again."
        elif "speech not understood" in lower:
            response = "I didn't catch that. Please try again."
        else:
            response = "I didn't catch that. Please try again."
        return {
            "intent": "stt_failure",
            "action": "system.stt_failure",
            "confidence": 0.0,
            "response": response,
            "reply_lang": "en",
            "heard": "",
            "recognized_text": "",
        }


class MainWindow(QMainWindow):
    NAV_ITEMS = (
        ("Dashboard", "DB"),
        ("Voice Mode", "VO"),
        ("Commands", "CM"),
        ("Automation", "AU"),
        ("Brain", "AI"),
        ("Scheduler", "SC"),
        ("Vision / Terminal", ">_"),
        ("Settings", "ST"),
    )

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Jarvis Control Center")
        self.setMinimumSize(1366, 768)
        self.resize(1600, 900)

        self.controller = AssistantController()
        self._page_anim = None
        self._seconds_running = 0
        self._voice_thread = None
        self._voice_worker = None
        self._is_listening = False
        self._voice_state_lock = threading.RLock()

        self._build_ui()
        self._start_timers()

    def _start_timers(self) -> None:
        self._uptime_timer = QTimer(self)
        self._uptime_timer.timeout.connect(self._update_uptime)
        self._uptime_timer.start(1000)

    def _update_uptime(self) -> None:
        self._seconds_running += 1
        hours = self._seconds_running // 3600
        minutes = (self._seconds_running % 3600) // 60
        seconds = self._seconds_running % 60
        if hasattr(self, '_uptime_label'):
            self._uptime_label.setText(f"UPTIME: {hours:02d}:{minutes:02d}:{seconds:02d}")

    def _build_ui(self) -> None:
        root = QWidget()
        root.setStyleSheet(f"background: {BG_NEURAL_DEEP};")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        top_bar = self._build_top_bar()
        root_layout.addWidget(top_bar)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(0)

        icon_sidebar = self._build_icon_sidebar()
        content_row.addWidget(icon_sidebar)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background: {BG_NEURAL_DEEP}; border: none;")

        self.home = HomePage(
            controller=self.controller,
            get_setting=self.controller.settings.get,
        )
        self.voice_mode = VoiceModePage()
        self.voice = VoicePage()
        self.automation = AutomationPage()
        self.brain = BrainPage(analytics_service=self.controller.analytics)
        self.vision = VisionPage(controller=self.controller)
        self.api_brain = ApiBrainPage(
            get_setting=self.controller.settings.get,
            set_setting=self.controller.settings.set,
            test_callback=self.controller.advanced_brain.is_available,
        )
        self.scheduler = SchedulerPage()
        self.settings = SettingsPage(
            get_setting=self.controller.settings.get,
            set_setting=self.controller.settings.set,
            test_callback=self.controller.advanced_brain.is_available,
        )

        for page in (
            self.home,
            self.voice_mode,
            self.voice,
            self.automation,
            self.brain,
            self.scheduler,
            self.vision,
            self.settings,
        ):
            self.stack.addWidget(page)

        content_row.addWidget(self.stack, 1)
        root_layout.addLayout(content_row, 1)

        bottom_bar = self._build_bottom_bar()
        root_layout.addWidget(bottom_bar)

        self.setCentralWidget(root)
        self._wire_events()
        self._load_voice_list()
        self._sync_voice_tab_from_controller()
        self._refresh_alarms()

        self._nav_group.blockSignals(True)
        startup_index = self._initial_page_index()
        if self._nav_group.button(startup_index):
            self._nav_group.button(startup_index).setChecked(True)
        self._nav_group.blockSignals(False)
        self.stack.setCurrentIndex(startup_index)

    def _initial_page_index(self) -> int:
        try:
            index = int(self.controller.settings.get("startup_page", "0"))
        except (TypeError, ValueError):
            return 0
        return index if 0 <= index < self.stack.count() else 0

    def _build_top_bar(self) -> QFrame:
        top = QFrame()
        top.setFixedHeight(56)
        top.setStyleSheet(f"""
            background: rgba(2, 7, 19, 0.96);
            border-bottom: 1px solid rgba(47, 140, 255, 0.34);
        """)

        lay = QHBoxLayout(top)
        lay.setContentsMargins(22, 0, 22, 0)

        title = QLabel("JARVIS CONTROL CENTER")
        title.setStyleSheet(f"color: {NEURAL_BLUE}; font-family: {MONO_FAMILY}; font-size: 16px; font-weight: 900; letter-spacing: 1px;")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._system_status_text = QLabel("- BACKEND: ROUTER ONLINE")
        self._system_status_text.setStyleSheet(f"color: {NEURAL_CYAN}; font-family: {MONO_FAMILY}; font-size: 12px; font-weight: 900; letter-spacing: 1px;")

        indicator = QFrame()
        indicator.setFixedSize(20, 20)
        indicator.setStyleSheet(f"background: transparent; border-radius: 10px; border: 3px solid {NEURAL_CYAN};")
        glow = QGraphicsDropShadowEffect(indicator)
        glow.setBlurRadius(4)
        glow.setOffset(0, 0)
        glow.setColor(QColor(NEURAL_GREEN))
        indicator.setGraphicsEffect(glow)

        lay.addWidget(title, 1)
        lay.addWidget(self._system_status_text)
        lay.addWidget(indicator)

        return top

    def _build_icon_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setFixedWidth(84)
        sidebar.setStyleSheet(f"""
            background: rgba(2, 8, 22, 0.96);
            border-right: 1px solid rgba(47, 140, 255, 0.26);
        """)

        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(16, 44, 16, 18)
        lay.setSpacing(26)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)

        for idx, (name, icon) in enumerate(self.NAV_ITEMS):
            btn = QPushButton(icon)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedSize(52, 52)
            btn.setToolTip(name)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: 1px solid transparent;
                    border-radius: 13px;
                    color: {NEURAL_BLUE};
                    font-family: {MONO_FAMILY};
                    font-size: 14px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background: rgba(47, 140, 255, 0.12);
                    border: 1px solid rgba(47, 140, 255, 0.32);
                }}
                QPushButton:checked {{
                    background: rgba(47, 140, 255, 0.22);
                    border: 1px solid rgba(47, 140, 255, 0.55);
                    color: {NEURAL_CYAN};
                }}
            """)
            self._nav_group.addButton(btn, idx)
            lay.addWidget(btn)

        lay.addStretch(1)

        power = QPushButton("PWR")
        power.setFixedSize(52, 52)
        power.setStyleSheet(f"""
            QPushButton {{
                background: rgba(47, 140, 255, 0.10);
                border: 1px solid rgba(47, 140, 255, 0.32);
                border-radius: 26px;
                color: {NEURAL_BLUE};
                font-family: "Segoe UI Symbol", {MONO_FAMILY};
                font-size: 24px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: rgba(255, 70, 70, 0.1);
                border: 1px solid rgba(255, 70, 70, 0.2);
            }}
        """)
        power.setCursor(Qt.CursorShape.PointingHandCursor)
        lay.addWidget(power)

        self._nav_group.idClicked.connect(self._on_nav_changed)
        return sidebar

    def _build_bottom_bar(self) -> QFrame:
        bottom = QFrame()
        bottom.setFixedHeight(30)
        bottom.setStyleSheet(f"""
            background: {BG_NEURAL_CORE};
            border-top: 1px solid rgba(0, 245, 255, 0.04);
        """)

        lay = QHBoxLayout(bottom)
        lay.setContentsMargins(28, 0, 28, 0)

        self._uptime_label = QLabel("UPTIME: 00:00:00")
        self._uptime_label.setStyleSheet(f"color: {NEURAL_TEXT_MUTED}; font-family: {MONO_FAMILY}; font-size: 10px; font-weight: 800; letter-spacing: 1px;")

        model = QLabel("MODEL: CPA NEURAL ENGINE v1.0")
        model.setStyleSheet(f"color: {NEURAL_TEXT_MUTED}; font-family: {MONO_FAMILY}; font-size: 10px; font-weight: 800; letter-spacing: 1px;")
        model.setAlignment(Qt.AlignmentFlag.AlignCenter)

        user = QLabel("USER: ADMIN")
        user.setStyleSheet(f"color: {NEURAL_TEXT_MUTED}; font-family: {MONO_FAMILY}; font-size: 10px; font-weight: 800; letter-spacing: 1px;")

        lay.addWidget(self._uptime_label)
        lay.addWidget(model, 1)
        lay.addWidget(user)

        return bottom

    def _on_nav_changed(self, index: int) -> None:
        if index < 0 or index == self.stack.currentIndex():
            return
        if self.stack.currentIndex() == self.stack.indexOf(self.voice_mode):
            self._stop_voice_loop(wait=True)
        self.stack.setCurrentIndex(index)
        if index == self.stack.indexOf(self.brain):
            self.brain.refresh()
        self._page_anim = None

    def _wire_events(self) -> None:
        self.home.send_btn.clicked.connect(self._run_text_command)
        self.home.listen_btn.clicked.connect(self._listen_once_command)
        for button in getattr(self.home, "quick_buttons", []):
            button.clicked.connect(lambda checked=False, b=button: self._run_quick_command(str(b.property("command") or "")))
        self.voice_mode.back_requested.connect(self._return_to_dashboard)
        self.voice.preview_btn.clicked.connect(self._preview_voice)
        self.voice.test_bn_btn.clicked.connect(self._test_bangla_voice)
        self.voice.apply_btn.clicked.connect(self._apply_voice)
        self.voice.ambient_calibrate_btn.clicked.connect(self._calibrate_ambient_noise)
        self.vision.pick_btn.clicked.connect(self._ocr_from_file)
        self.vision.capture_btn.clicked.connect(self._capture_camera_frame)
        self.vision.ocr_last_capture_btn.clicked.connect(self._ocr_last_capture)
        self.scheduler.refresh_btn.clicked.connect(self._refresh_alarms)
        self.scheduler.add_alarm_btn.clicked.connect(self._add_alarm_from_scheduler)
        self.scheduler.delete_alarm_btn.clicked.connect(self._delete_selected_alarm)
        self.scheduler.done_alarm_btn.clicked.connect(self._mark_selected_alarm_done)
        self.scheduler.start_focus_btn.clicked.connect(self._start_focus_timer)
        self.scheduler.add_task_btn.clicked.connect(self._add_task)
        self.scheduler.list_task_btn.clicked.connect(self._refresh_tasks)
        self.api_brain.settings_changed.connect(self._on_settings_changed)
        self.settings.settings_changed.connect(self._on_settings_changed)
        self._show_startup_voice_warning()

    def _on_settings_changed(self) -> None:
        self.controller.stt.set_language(self.controller.settings.get("stt_language", "bn-BD"))
        self._sync_voice_tab_from_controller()
        self._show_startup_voice_warning()

    def _voice_warning(self) -> str:
        if self.controller.voice_input_ready():
            return ""
        return self.controller.voice_input_unavailable_message()

    def _show_startup_voice_warning(self) -> None:
        warning = self._voice_warning()
        if not warning:
            if hasattr(self, "_system_status_text"):
                self._system_status_text.setText("— SYSTEM STATUS: OPTIMAL  ⌁")
            return
        if hasattr(self, "_system_status_text"):
            self._system_status_text.setText(f"— {warning}")
        if hasattr(self, "home"):
            self.home.status.setText(warning)
            self.home.append_log(f"JARVIS: {warning}")

    def _load_voice_list(self) -> None:
        self.voice.voice_combo.clear()
        for voice_id, voice_name in self.controller.tts.list_voices():
            self.voice.voice_combo.addItem(voice_name, voice_id)

    def _sync_voice_tab_from_controller(self) -> None:
        stt = self.controller.settings.get("stt_language", "bn-BD")
        i = self.voice.stt_lang_combo.findData(stt)
        if i >= 0:
            self.voice.stt_lang_combo.setCurrentIndex(i)
        resp = self.controller.settings.get("response_language", "auto")
        j = self.voice.response_lang_combo.findData(resp)
        if j >= 0:
            self.voice.response_lang_combo.setCurrentIndex(j)
        self.voice.voice_reply_check.setChecked(self.controller.is_voice_reply_enabled())
        self.voice.auto_bn_voice_check.setChecked(
            self.controller.settings.get("tts_auto_bengali_voice", "1").strip() == "1"
        )
        self.voice.wake_word_check.setChecked(self.controller.is_wake_word_enabled())
        self.voice.noise_reduction_check.setChecked(
            self.controller.settings.get("noise_reduction_enabled", "true").strip().lower()
            in ("1", "true", "yes", "on", "enabled")
        )
        try:
            self.voice.mic_sensitivity_spin.setValue(int(self.controller.settings.get("mic_sensitivity", "50") or "50"))
        except ValueError:
            self.voice.mic_sensitivity_spin.setValue(50)
        speed = self.controller.settings.get("bengali_tts_speed", "normal")
        speed_index = self.voice.bengali_tts_speed_combo.findData(speed)
        if speed_index >= 0:
            self.voice.bengali_tts_speed_combo.setCurrentIndex(speed_index)
        self.voice.tts_status_label.setText(self.controller.get_tts_status_line())
        self.voice._sync_labels()

    def _handle_post_command(self, out: dict) -> None:
        if hasattr(self.home, "set_command_result"):
            self.home.set_command_result(out)
        if out.get("tts_warning"):
            warning = str(out.get("tts_warning") or "")
            self.home.append_log(f"JARVIS: {warning}")
            self.home.status.setText(warning)
        if out.get("type") == "web_search" or out.get("intent") == "google_search":
            _LOG.info("[ui] rendering web search cards")
            if hasattr(self.home, "append_search_results"):
                self.home.append_search_results(out)
            else:
                query = str(out.get("search_query") or out.get("query") or "")
                url = str(out.get("search_url") or "")
                self.home.append_log(f"Search query: {query}")
                self.home.append_log(f"Google search URL: {url}")
        if out.get("type") == "system_action" and out.get("candidates"):
            self.home.append_log("Matches:")
            for index, path in enumerate(list(out.get("candidates") or [])[:5], start=1):
                self.home.append_log(f"{index}. {path}")
        if out.get("action") == "ui.open_settings":
            idx = self.stack.indexOf(self.settings)
            if idx >= 0:
                self._select_nav(idx)

    def _run_quick_command(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        self.home.input_box.setPlainText(text)
        self._run_text_command()

    def _run_text_command(self) -> None:
        text = self.home.input_box.toPlainText().strip()
        if not text:
            return
        self.home.status.setText("Processing...")
        self.home.set_orb_state("thinking")
        if hasattr(self.home, "_agent_brain"):
            self.home._agent_brain.set_status("PROCESSING", "purple")
        self.home.append_log(f"You: {text}")
        try:
            out = self.controller.process(text, speak=True)
        except Exception:
            self.home.append_log("Something went wrong.")
            self.home.status.setText("Idle")
            self.home.set_orb_state("idle")
            return
        self.home.append_log(f"Jarvis: {out['response']}")
        self._handle_post_command(out)
        self.brain.log.append(f"intent={out['intent']} action={out['action']} confidence={out['confidence']:.2f}")
        self.home.status.setText("Ready")
        self.home.set_orb_state("idle")
        if hasattr(self.home, "_agent_brain"):
            self.home._agent_brain.set_status("READY", "purple")
        self.home.input_box.clear()

    def _listen_once_command(self) -> None:
        with self._voice_state_lock:
            active = self._is_listening or (self._voice_thread is not None and self._voice_thread.isRunning())
        if active:
            self._stop_voice_loop(wait=False)
            return
        self._start_voice_loop()

    def _start_voice_loop(self) -> None:
        warning = self._voice_warning()
        if warning:
            _LOG.warning("[voice] cannot start: %s", warning)
            print(f"[voice] cannot start: {warning}")
            self.home.status.setText(warning)
            self.home.append_log(f"JARVIS: {warning}")
            if hasattr(self.home, "_agent_voice"):
                self.home._agent_voice.set_status("UNAVAILABLE", "purple")
            return
        with self._voice_state_lock:
            if self._is_listening or (self._voice_thread is not None and self._voice_thread.isRunning()):
                _LOG.info("voice loop already running; start ignored")
                return
            self._is_listening = True
        wake_word_enabled = self.controller.is_wake_word_enabled()
        _LOG.info("voice loop starting; wake_word_enabled=%s", wake_word_enabled)
        self._show_voice_mode()
        self.voice_mode.reset_for_listening()
        start_text = "Listening for wake word..." if wake_word_enabled else "Listening..."
        self.home.status.setText(start_text)
        self.home.set_orb_state("listening")
        self.home.set_voice_active(True)
        if hasattr(self.home, "_agent_voice"):
            self.home._agent_voice.set_status("LISTENING", "cyan")
        self.home.listen_btn.setEnabled(True)
        self.home.listen_btn.setText("STOP")
        self.home.input_box.clear()
        self.home.input_box.setPlaceholderText("Say Jarvis to start" if wake_word_enabled else "Listening... speak now")
        self.home.set_voice_level(0.18)

        self._voice_thread = QThread(self)
        self._voice_worker = _VoiceLoopWorker(self.controller, wake_word_enabled=wake_word_enabled)
        self._voice_worker.moveToThread(self._voice_thread)
        self._voice_thread.started.connect(self._voice_worker.run)
        self._voice_worker.level_changed.connect(self.voice_mode.set_level)
        self._voice_worker.level_changed.connect(self.home.set_voice_level)
        self._voice_worker.status.connect(self._on_voice_loop_status)
        self._voice_worker.recognized.connect(self._on_voice_transcribed)
        self._voice_worker.reply_ready.connect(self._on_voice_reply_ready)
        self._voice_worker.error.connect(self._on_voice_loop_error)
        self._voice_worker.finished.connect(self._voice_thread.quit)
        self._voice_thread.finished.connect(self._voice_worker.deleteLater)
        self._voice_thread.finished.connect(self._voice_thread.deleteLater)
        self._voice_thread.finished.connect(self._on_voice_loop_finished)
        self._voice_thread.start()

    def _stop_voice_loop(self, *, wait: bool = False) -> bool:
        worker = self._voice_worker
        thread = self._voice_thread
        with self._voice_state_lock:
            active = self._is_listening or (thread is not None and thread.isRunning())
        if not active:
            return True
        self.home.status.setText("Stopping voice mode...")
        self.voice_mode.set_state("Idle")
        self.voice_mode.set_response("Stopping voice mode...")
        self.home.listen_btn.setText("MIC")
        if hasattr(self.home, "_agent_voice"):
            self.home._agent_voice.set_status("STOPPING", "purple")
        if worker is not None:
            try:
                worker.stop()
            except Exception:
                _LOG.exception("Failed to stop active voice loop")
        if thread is not None:
            thread.quit()
            if wait and thread.isRunning():
                if not thread.wait(3000):
                    _LOG.warning("Voice loop did not stop within 3000ms")
                    return False
            if wait and not thread.isRunning():
                with self._voice_state_lock:
                    self._is_listening = False
                self._voice_thread = None
                self._voice_worker = None
        return True

    def _on_voice_transcribed(self, text: str) -> None:
        self.voice_mode.set_transcript(text)
        self.voice_mode.set_state("Processing")
        self.voice_mode.set_response("Processing command...")
        self.home.input_box.setPlainText(text)
        self.home.append_log(f"You: {text}")
        self.home.status.setText("Processing...")
        self.home.set_orb_state("thinking")
        if hasattr(self.home, "_agent_voice"):
            self.home._agent_voice.set_status("PROCESSING", "purple")

    def _on_voice_reply_ready(self, out: dict) -> None:
        try:
            heard = out.get("heard") or out.get("recognized_text", "")
            if heard and self.home.input_box.toPlainText().strip() != heard:
                self.home.input_box.setPlainText(heard)
                self.home.append_log(f"You: {heard}")
            response = out.get("response", "Jarvis had trouble replying. Please try again.")
            if out.get("action") == "system.stt_failure":
                self.voice_mode.show_error(response)
            else:
                self.voice_mode.set_state("Speaking")
                self.voice_mode.set_response(response)
            self.home.append_log(f"Jarvis: {response}")
            self._handle_post_command(out)
            self.brain.log.append(f"intent={out['intent']} action={out['action']} confidence={out['confidence']:.2f}")
        finally:
            if out.get("action") == "system.stt_failure":
                self.voice_mode.show_error(out.get("response", "Voice input failed."))
            elif self._is_listening:
                self.voice_mode.set_state("Speaking")
                self.home.status.setText("Speaking...")
                self.home.set_orb_state("thinking")
                if hasattr(self.home, "_agent_voice"):
                    self.home._agent_voice.set_status("SPEAKING", "cyan")

    def _on_voice_loop_status(self, message: str) -> None:
        text = message or ""
        if text.startswith("[wake] Listening"):
            self.voice_mode.set_state("Listening")
            self.voice_mode.set_response("Listening for wake word...")
            self.home.status.setText("Listening for wake word...")
            self.home.set_orb_state("listening")
            if hasattr(self.home, "_agent_voice"):
                self.home._agent_voice.set_status("WAKE", "cyan")
        elif text.startswith("[wake] detected"):
            self.voice_mode.set_state("Listening")
            self.voice_mode.set_response("Wake word detected.")
            self.home.status.setText("Wake word detected.")
        elif text.startswith("[wake] direct command"):
            self.home.status.setText("Processing...")
        elif "Listening" in text or "[stt] Listening" in text:
            self.voice_mode.set_state("Listening")
            self.voice_mode.set_response("Listening...")
            self.home.status.setText("Listening...")
            self.home.set_orb_state("listening")
            if hasattr(self.home, "_agent_voice"):
                self.home._agent_voice.set_status("LISTENING", "cyan")
        elif "Recognized" in text or "Processing" in text:
            self.home.status.setText("Processing...")
        elif "Speaking" in text:
            self.voice_mode.set_state("Speaking")
            self.home.status.setText("Speaking...")
        elif "listening again" in text.lower():
            self.voice_mode.set_state("Listening")
            self.voice_mode.set_response("Listening again...")
            self.home.status.setText("Listening...")
        elif "stopped" in text.lower():
            self.home.status.setText("Voice mode stopped.")
        if text.startswith("[stt]") or text.startswith("[voice]") or text.startswith("[wake]"):
            _LOG.info(text)

    def _on_voice_loop_error(self, message: str) -> None:
        _LOG.error("Voice loop error: %s", message)
        self.voice_mode.show_error(message)
        self.home.append_log(f"JARVIS: {message}")
        self.home.status.setText(message)

    def _reset_voice_ui(self, status_text: str) -> None:
        with self._voice_state_lock:
            self._is_listening = False
        self.home.status.setText(status_text)
        self.home.set_orb_state("idle")
        self.home.set_voice_active(False)
        self.home.set_voice_level(0.08)
        self.home.input_box.setPlaceholderText("Type in the Jarvis chat box, not PowerShell terminal.")
        self.home.listen_btn.setEnabled(True)
        self.home.listen_btn.setText("MIC")
        if hasattr(self.home, "_agent_voice"):
            self.home._agent_voice.set_status("READY" if status_text == "Ready" else "IDLE", "green" if status_text == "Ready" else "purple")

    def _on_voice_loop_finished(self) -> None:
        with self._voice_state_lock:
            self._is_listening = False
        self._voice_thread = None
        self._voice_worker = None
        self._reset_voice_ui("Ready")
        self.voice_mode.mark_ready()

    def _stop_voice_worker(self) -> None:
        self._stop_voice_loop(wait=False)

    def _show_voice_mode(self) -> None:
        index = self.stack.indexOf(self.voice_mode)
        if index >= 0:
            self._nav_group.blockSignals(True)
            button = self._nav_group.button(index)
            if button:
                button.setChecked(True)
            self._nav_group.blockSignals(False)
            self.stack.setCurrentIndex(index)

    def _return_to_dashboard(self) -> None:
        self._stop_voice_loop(wait=True)
        self._select_nav(0)

    def closeEvent(self, event) -> None:  # noqa: N802
        if not self._stop_voice_loop(wait=True):
            event.ignore()
            return
        super().closeEvent(event)

    def _preview_voice(self) -> None:
        text = self.voice.preview_text.text().strip()
        if text:
            warn = self.controller.preview_tts(text)
            if warn:
                self.home.append_log(f"JARVIS: {warn}")

    def _test_bangla_voice(self) -> None:
        msg = self.controller.test_bangla_tts()
        if msg:
            self.home.append_log(f"JARVIS: {msg}")

    def _apply_voice(self) -> None:
        voice_id = self.voice.voice_combo.currentData()
        rate = self.voice.rate_spin.value()
        if voice_id:
            self.controller.tts.set_voice(str(voice_id))
        self.controller.tts.set_rate(rate)
        self.controller.save_voice_preferences(str(voice_id or ""), rate)
        self.controller.apply_speech_preferences(
            stt_language=str(self.voice.stt_lang_combo.currentData() or "bn-BD"),
            response_language=str(self.voice.response_lang_combo.currentData() or "auto"),
            voice_reply_enabled=self.voice.voice_reply_check.isChecked(),
            tts_auto_bengali_voice=self.voice.auto_bn_voice_check.isChecked(),
            wake_word_enabled=self.voice.wake_word_check.isChecked(),
            noise_reduction_enabled=self.voice.noise_reduction_check.isChecked(),
            mic_sensitivity=self.voice.mic_sensitivity_spin.value(),
            bengali_tts_speed=str(self.voice.bengali_tts_speed_combo.currentData() or "normal"),
        )
        self._sync_voice_tab_from_controller()
        self.home.append_log("JARVIS: Voice settings applied.")

    def _calibrate_ambient_noise(self) -> None:
        try:
            message = self.controller.calibrate_ambient_noise()
        except Exception as exc:
            message = f"Ambient calibration failed: {exc}"
        self.voice.tts_status_label.setText(message)
        self.home.append_log(f"JARVIS: {message}")

    def _ocr_from_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path:
            text = self.controller.ocr_file(path)
            self.vision.output.setPlainText(text)

    def _capture_camera_frame(self) -> None:
        try:
            captured = capture_single_frame()
        except Exception as exc:
            captured = f"Camera capture failed: {exc}"
        self.vision.output.append(f"Captured: {captured}")
        self.vision.path_input.setText(captured if "data/" in captured else "")

    def _ocr_last_capture(self) -> None:
        path = self.vision.path_input.text().strip()
        if not path:
            QMessageBox.information(self, "Vision", "No capture path available.")
            return
        text = self.controller.ocr_file(path)
        self.vision.output.setPlainText(text)

    def _refresh_alarms(self) -> None:
        self.scheduler.listing.clear()
        alarms = self.controller.alarms.list_all()
        for alarm in alarms:
            self.scheduler.listing.addItem(f"{alarm['id']} | [{alarm['status']}] {alarm['title']} at {alarm['due_at']} ({alarm['recurrence']})")
        self._refresh_tasks()

    def _add_alarm_from_scheduler(self) -> None:
        title = self.scheduler.alarm_title_input.text().strip()
        due_at = self.scheduler.alarm_time_input.text().strip()
        recurrence = self.scheduler.alarm_recurrence_input.text().strip()
        result = self.controller.add_alarm(title, due_at, recurrence)
        self.home.append_log(f"JARVIS: {result}")
        self._refresh_alarms()

    def _selected_alarm_id(self) -> int | None:
        item = self.scheduler.listing.currentItem()
        if not item:
            return None
        head = item.text().split("|", 1)[0].strip()
        return int(head) if head.isdigit() else None

    def _delete_selected_alarm(self) -> None:
        alarm_id = self._selected_alarm_id()
        if alarm_id is None:
            QMessageBox.information(self, "Scheduler", "Select an alarm first.")
            return
        result = self.controller.delete_alarm(alarm_id)
        self.home.append_log(f"JARVIS: {result}")
        self._refresh_alarms()

    def _mark_selected_alarm_done(self) -> None:
        alarm_id = self._selected_alarm_id()
        if alarm_id is None:
            QMessageBox.information(self, "Scheduler", "Select an alarm first.")
            return
        result = self.controller.mark_alarm_done(alarm_id)
        self.home.append_log(f"JARVIS: {result}")
        self._refresh_alarms()

    def _start_focus_timer(self) -> None:
        value = self.scheduler.focus_input.text().strip()
        minutes = int(value) if value.isdigit() else 25
        result = self.controller.start_focus_timer(minutes)
        self.home.append_log(f"JARVIS: {result}")
        self._refresh_tasks()

    def _add_task(self) -> None:
        task = self.scheduler.task_input.text().strip()
        result = self.controller.add_task(task)
        self.scheduler.task_input.clear()
        self.home.append_log(f"JARVIS: {result}")
        self._refresh_tasks()

    def _refresh_tasks(self) -> None:
        self.scheduler.task_listing.clear()
        for task in self.controller.list_tasks():
            self.scheduler.task_listing.addItem(task)

    def _select_nav(self, index: int) -> None:
        button = self._nav_group.button(index)
        if button:
            button.setChecked(True)
        self.stack.setCurrentIndex(index)
