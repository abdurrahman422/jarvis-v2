from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.components import JarvisOrbPanel, ProgressBarWidget
from app.ui.theme import (
    BG_NEURAL_DEEP,
    FONT_DISPLAY,
    FONT_MONO,
    FONT_UI,
    MONO_FAMILY,
    NEURAL_BLUE,
    NEURAL_CYAN,
    NEURAL_GREEN,
    NEURAL_PURPLE,
    NEURAL_RED,
    NEURAL_TEXT_MUTED,
    NEURAL_TEXT_PRIMARY,
    NEURAL_TEXT_SECONDARY,
)


@dataclass(frozen=True)
class _Choice:
    label: str
    value: str


class SettingsPage(QWidget):
    settings_changed = Signal()
    page_title = "Settings"
    page_subtitle = "Configure and personalize your neural interface experience."

    CATEGORIES = (
        ("General", "general"),
        ("Brain", "ai"),
        ("Voice & Audio", "voice"),
        ("Data & Storage", "data"),
        ("Integrations", "integrations"),
    )

    STARTUP_PAGES = (
        _Choice("Dashboard", "0"),
        _Choice("Voice Mode", "1"),
        _Choice("Commands", "2"),
        _Choice("Automation", "3"),
        _Choice("Brain", "4"),
        _Choice("Scheduler", "5"),
        _Choice("Vision / Terminal", "6"),
        _Choice("Settings", "7"),
    )

    def __init__(self, get_setting=None, set_setting=None, test_callback=None) -> None:
        super().__init__()
        self._get_setting = get_setting
        self._set_setting = set_setting
        self._test_callback = test_callback
        self._category_buttons: dict[str, QPushButton] = {}
        self.setObjectName("PageSurface")
        self._build_ui()
        self._start_snapshot_timer()

    def _build_ui(self) -> None:
        self.setStyleSheet(f"background: {BG_NEURAL_DEEP};")
        root = QHBoxLayout(self)
        root.setContentsMargins(22, 28, 10, 20)
        root.setSpacing(18)

        root.addWidget(self._left_nav(), 0)
        root.addWidget(self._content_panel(), 1)
        root.addWidget(self._right_panel(), 0)

    def _left_nav(self) -> QFrame:
        panel = self._panel()
        panel.setFixedWidth(300)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(16, 20, 16, 16)
        lay.setSpacing(10)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        for index, (label, key) in enumerate(self.CATEGORIES):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(self._category_button_style())
            button.clicked.connect(lambda checked=False, i=index: self._stack.setCurrentIndex(i))
            self._nav_group.addButton(button, index)
            self._category_buttons[key] = button
            lay.addWidget(button)
        self._category_buttons["general"].setChecked(True)

        lay.addStretch(1)
        reset = QPushButton("Reset to Defaults")
        reset.setCursor(Qt.CursorShape.PointingHandCursor)
        reset.setFixedHeight(52)
        reset.setStyleSheet(f"""
            QPushButton {{
                background: rgba(5, 14, 35, 0.82);
                border: 1px solid rgba(236, 72, 153, 0.38);
                border-radius: 9px;
                color: #ff6db7;
                font-family: {FONT_DISPLAY};
                font-size: 12px;
                font-weight: 900;
                text-align: left;
                padding-left: 18px;
            }}
            QPushButton:hover {{
                background: rgba(236, 72, 153, 0.10);
            }}
        """)
        reset.clicked.connect(self._reset_defaults)
        lay.addWidget(reset)
        return panel

    def _content_panel(self) -> QWidget:
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(18)

        title = QLabel("SETTINGS")
        title.setStyleSheet(f"color: {NEURAL_TEXT_PRIMARY}; font-family: {FONT_DISPLAY}; font-size: 22px; font-weight: 900; letter-spacing: 0.4px;")
        subtitle = QLabel("Only active backend-backed settings are editable. Unsupported ideas are hidden or disabled.")
        subtitle.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {FONT_UI}; font-size: 13px; font-weight: 500;")
        lay.addWidget(title)
        lay.addWidget(subtitle)

        content = self._panel()
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(28, 26, 28, 22)
        content_lay.setSpacing(14)
        self._section_header = self._section_title("GENERAL SETTINGS")
        content_lay.addWidget(self._section_header)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent; border: none;")
        self._stack.addWidget(self._general_page())
        self._stack.addWidget(self._ai_page())
        self._stack.addWidget(self._voice_page())
        self._stack.addWidget(self._data_page())
        self._stack.addWidget(self._integrations_page())
        self._stack.currentChanged.connect(self._on_category_changed)
        content_lay.addWidget(self._stack, 1)

        self.status_label = QLabel("Settings are saved automatically.")
        self.status_label.setStyleSheet(f"color: {NEURAL_TEXT_MUTED}; font-family: {FONT_UI}; font-size: 11px;")
        content_lay.addWidget(self.status_label)
        lay.addWidget(content, 1)
        return wrap

    def _general_page(self) -> QWidget:
        page = self._settings_page_container()
        lay = page.layout()
        self.language_combo = self._combo(
            "interface_language",
            "en-US",
            (_Choice("English (US)", "en-US"), _Choice("Bangla", "bn-BD")),
        )
        self.startup_page_combo = self._combo("startup_page", "0", self.STARTUP_PAGES)
        lay.addWidget(self._select_row("Interface Language", "Select your preferred language.", self.language_combo))
        theme = self._segmented_row("Theme Mode", "Dark neural theme is currently active.", "theme_mode", "dark", ("dark",))
        lay.addWidget(theme)
        lay.addWidget(self._select_row("Startup Mode", "Choose what loads on startup.", self.startup_page_combo))
        lay.addWidget(self._toggle_row("Auto Save", "Automatically save your work and data.", "auto_save_enabled", True))
        lay.addStretch(1)
        return page

    def _ai_page(self) -> QWidget:
        page = self._settings_page_container()
        lay = page.layout()
        provider = self._combo(
            "selected_brain",
            "offline_local",
            (
                _Choice("Offline Local", "offline_local"),
                _Choice("Trained Qwen", "trained_qwen"),
            ),
        )
        provider.currentIndexChanged.connect(lambda _: self._save_provider_alias())
        lay.addWidget(self._select_row("Default Brain", "Choose the local brain used for responses.", provider))
        lay.addWidget(self._toggle_row("Context Memory", "Include recent conversation context in AI prompts.", "ai_context_memory_enabled", True))
        lay.addWidget(self._toggle_row("Safe Mode", "Prefer conservative local actions for automation.", "ai_safe_mode_enabled", True))
        test = QPushButton("Test Active Brain")
        test.setCursor(Qt.CursorShape.PointingHandCursor)
        test.setStyleSheet(self._primary_button_style())
        test.clicked.connect(self._test_active_brain)
        lay.addWidget(test)
        lay.addStretch(1)
        return page

    def _voice_page(self) -> QWidget:
        page = self._settings_page_container()
        lay = page.layout()
        stt = self._combo("stt_language", "bn-BD", (_Choice("Bangla", "bn-BD"), _Choice("English (US)", "en-US")))
        response = self._combo("response_language", "auto", (_Choice("Auto", "auto"), _Choice("English", "en"), _Choice("Bangla", "bn")))
        lay.addWidget(self._select_row("Speech Recognition", "Language used by microphone input.", stt))
        lay.addWidget(self._select_row("Reply Language", "Language used for assistant responses.", response))
        lay.addWidget(self._toggle_row("Voice Replies", "Speak assistant replies aloud.", "voice_reply_enabled", True, true_value="true", false_value="false"))
        lay.addWidget(self._toggle_row("Auto Bangla Voice", "Use Bengali voice when Bangla text is detected.", "tts_auto_bengali_voice", True, true_value="1", false_value="0"))
        lay.addWidget(self._toggle_row("Wake Word", "Enable wake-word voice loop mode.", "wake_word_enabled", False, true_value="true", false_value="false"))
        lay.addWidget(self._toggle_row("Noise Reduction", "Use microphone preprocessing before STT.", "noise_reduction_enabled", True, true_value="true", false_value="false"))
        lay.addWidget(self._select_row("Bengali TTS Speed", "Speed used by gTTS fallback.", self._combo("bengali_tts_speed", "normal", (_Choice("Normal", "normal"), _Choice("Faster", "faster")))))
        lay.addWidget(self._select_row("Voice Rate", "Default text-to-speech speed.", self._combo("voice_rate", "170", (_Choice("Slow", "130"), _Choice("Normal", "170"), _Choice("Fast", "210")))))
        lay.addStretch(1)
        return page

    def _security_page(self) -> QWidget:
        page = self._settings_page_container()
        lay = page.layout()
        lay.addWidget(self._toggle_row("Neural Link Guard", "Block dangerous terminal commands.", "safe_terminal_enabled", True))
        lay.addWidget(self._toggle_row("Confirm Automation", "Ask before sensitive desktop actions.", "confirm_automation_enabled", True))
        lay.addWidget(self._toggle_row("Audit Logs", "Record important assistant actions.", "audit_logs_enabled", True))
        lay.addStretch(1)
        return page

    def _data_page(self) -> QWidget:
        page = self._settings_page_container()
        lay = page.layout()
        lay.addWidget(self._toggle_row("Conversation History", "Persist chat history to local database.", "conversation_history_enabled", True))
        lay.addWidget(self._toggle_row("Terminal History", "Save safe terminal command history.", "terminal_history_enabled", True))
        lay.addWidget(self._toggle_row("Analytics", "Collect local usage metrics for charts.", "analytics_enabled", True))
        lay.addWidget(self._select_row("Log Retention", "How long local logs are kept.", self._combo("log_retention_days", "30", (_Choice("7 days", "7"), _Choice("30 days", "30"), _Choice("90 days", "90")))))
        lay.addStretch(1)
        return page

    def _integrations_page(self) -> QWidget:
        page = self._settings_page_container()
        lay = page.layout()
        lay.addWidget(self._disabled_row("WhatsApp Automation", "Coming soon: keep disabled until full UI workflow is connected."))
        lay.addWidget(self._disabled_row("Email Tools", "Coming soon: backend helpers exist, but this settings toggle is not wired."))
        lay.addWidget(self._toggle_row("File Intelligence", "Enable local file search and control.", "file_intelligence_enabled", True))
        lay.addWidget(self._toggle_row("YouTube / Web Open", "Enable alias-based app and website opening.", "youtube_integration_enabled", True))
        lay.addStretch(1)
        return page

    def _appearance_page(self) -> QWidget:
        page = self._settings_page_container()
        lay = page.layout()
        lay.addWidget(self._segmented_row("Accent Color", "Choose the neural accent color.", "accent_color", "cyan", ("cyan", "blue", "purple")))
        lay.addWidget(self._toggle_row("Glass Panels", "Use translucent neural panels.", "glass_panels_enabled", True))
        lay.addWidget(self._toggle_row("Glow Highlights", "Use cyan and purple edge highlights.", "glow_highlights_enabled", True))
        lay.addWidget(self._toggle_row("Dense Sidebar", "Use compact icon navigation.", "dense_sidebar_enabled", False))
        lay.addStretch(1)
        return page

    def _notifications_page(self) -> QWidget:
        page = self._settings_page_container()
        lay = page.layout()
        lay.addWidget(self._toggle_row("Desktop Notices", "Show desktop notifications for completed tasks.", "desktop_notifications_enabled", True))
        lay.addWidget(self._toggle_row("Voice Alerts", "Play voice alerts for important events.", "voice_alerts_enabled", False))
        lay.addWidget(self._toggle_row("Alarm Notices", "Notify when alarms and focus timers complete.", "alarm_notifications_enabled", True))
        lay.addWidget(self._toggle_row("Error Alerts", "Notify when an automation fails.", "error_notifications_enabled", True))
        lay.addStretch(1)
        return page

    def _advanced_page(self) -> QWidget:
        page = self._settings_page_container()
        lay = page.layout()
        lay.addWidget(self._toggle_row("Developer Diagnostics", "Show extra diagnostic output in logs.", "developer_diagnostics_enabled", False))
        lay.addWidget(self._toggle_row("Experimental UI", "Enable recovered experimental interface panels.", "experimental_ui_enabled", False))
        lay.addWidget(self._toggle_row("Startup Health Check", "Run backend checks when Jarvis opens.", "startup_health_check_enabled", True))
        lay.addWidget(self._select_row("Terminal Safety", "Allowed command strictness.", self._combo("terminal_safety_level", "strict", (_Choice("Strict", "strict"), _Choice("Normal", "normal")))))
        lay.addStretch(1)
        return page

    def _right_panel(self) -> QWidget:
        right = QWidget()
        right.setFixedWidth(250)
        lay = QVBoxLayout(right)
        lay.setContentsMargins(0, 32, 0, 36)
        lay.setSpacing(14)
        self.orb = JarvisOrbPanel()
        self.orb.setFixedHeight(390)
        lay.addWidget(self.orb)

        info = self._panel()
        info_lay = QVBoxLayout(info)
        info_lay.setContentsMargins(22, 20, 22, 20)
        info_lay.setSpacing(16)
        info_lay.addWidget(self._section_title("SYSTEM INFO"))
        self.cpu_value = QLabel("0%")
        self.cpu_bar = ProgressBarWidget(0, "blue")
        self.mem_value = QLabel("0%")
        self.mem_bar = ProgressBarWidget(0, "blue")
        self.uptime_value = QLabel("00:00:00")
        self.connection_value = QLabel("Secure")
        info_lay.addLayout(self._metric_row("CPU USAGE", self.cpu_value))
        info_lay.addWidget(self.cpu_bar)
        info_lay.addLayout(self._metric_row("MEMORY USAGE", self.mem_value))
        info_lay.addWidget(self.mem_bar)
        info_lay.addLayout(self._metric_row("UPTIME", self.uptime_value))
        info_lay.addLayout(self._metric_row("CONNECTION", self.connection_value, NEURAL_GREEN))
        lay.addWidget(info)
        lay.addStretch(1)
        return right

    def _settings_page_container(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        return page

    def _select_row(self, title: str, subtitle: str, widget: QWidget) -> QFrame:
        return self._setting_row(title, subtitle, widget)

    def _toggle_row(
        self,
        title: str,
        subtitle: str,
        key: str,
        default: bool,
        true_value: str = "true",
        false_value: str = "false",
    ) -> QFrame:
        current = self._load_bool(key, default, true_value=true_value)
        button = QPushButton()
        button.setCheckable(True)
        button.setChecked(current)
        button.setFixedSize(58, 32)

        def refresh(save: bool = False) -> None:
            checked = button.isChecked()
            button.setText("ON" if checked else "OFF")
            color = NEURAL_GREEN if checked else "rgba(98,124,190,0.45)"
            button.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    border: 1px solid rgba(47,140,255,0.35);
                    border-radius: 16px;
                    color: white;
                    font-family: {FONT_DISPLAY};
                    font-size: 9px;
                    font-weight: 900;
                }}
            """)
            if save:
                self._save_setting(key, true_value if checked else false_value)

        button.clicked.connect(lambda _: refresh(save=True))
        refresh()
        return self._setting_row(title, subtitle, button)

    def _segmented_row(self, title: str, subtitle: str, key: str, default: str, values: tuple[str, ...]) -> QFrame:
        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        group = QButtonGroup(holder)
        group.setExclusive(True)
        current = self._load_setting(key, default)
        for value in values:
            button = QPushButton(value.title())
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setMinimumWidth(96)
            button.setFixedHeight(46)
            button.setStyleSheet(self._segment_button_style())
            button.clicked.connect(lambda checked=False, v=value: self._save_setting(key, v))
            if value == current:
                button.setChecked(True)
            group.addButton(button)
            row.addWidget(button)
        return self._setting_row(title, subtitle, holder)

    def _setting_row(self, title: str, subtitle: str, control: QWidget) -> QFrame:
        row = self._panel()
        row.setFixedHeight(82)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(26, 12, 22, 12)
        lay.setSpacing(16)
        text = QVBoxLayout()
        text.setSpacing(4)
        t = QLabel(title)
        s = QLabel(subtitle)
        t.setStyleSheet(f"color: {NEURAL_TEXT_PRIMARY}; font-family: {FONT_UI}; font-size: 13px; font-weight: 800;")
        s.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {FONT_UI}; font-size: 11px; font-weight: 500;")
        text.addWidget(t)
        text.addWidget(s)
        lay.addLayout(text, 1)
        lay.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
        return row

    def _disabled_row(self, title: str, subtitle: str) -> QFrame:
        button = QPushButton("Coming soon")
        button.setEnabled(False)
        button.setFixedHeight(38)
        button.setStyleSheet(f"""
            QPushButton {{
                background: rgba(100, 116, 139, 0.12);
                border: 1px solid rgba(148, 163, 184, 0.18);
                border-radius: 10px;
                color: {NEURAL_TEXT_MUTED};
                font-family: {FONT_DISPLAY};
                font-size: 11px;
                font-weight: 900;
                padding: 8px 14px;
            }}
        """)
        return self._setting_row(title, subtitle, button)

    def _combo(self, key: str, default: str, choices: tuple[_Choice, ...]) -> QComboBox:
        combo = QComboBox()
        combo.setFixedHeight(50)
        combo.setMinimumWidth(260)
        for choice in choices:
            combo.addItem(choice.label, choice.value)
        value = self._load_setting(key, default)
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.setStyleSheet(f"""
            QComboBox {{
                background: rgba(5, 14, 35, 0.82);
                border: 1px solid rgba(47, 140, 255, 0.36);
                border-radius: 10px;
                color: {NEURAL_TEXT_PRIMARY};
                font-family: {FONT_UI};
                font-size: 13px;
                font-weight: 800;
                padding: 8px 14px;
            }}
            QComboBox:hover {{
                border-color: {NEURAL_CYAN};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 28px;
            }}
        """)
        combo.currentIndexChanged.connect(lambda _: self._save_setting(key, str(combo.currentData())))
        return combo

    def _on_category_changed(self, index: int) -> None:
        label = self.CATEGORIES[index][0].upper()
        self._section_header.setText(f"{label} SETTINGS")

    def _test_active_brain(self) -> None:
        ok = bool(self._test_callback() if self._test_callback else False)
        self.status_label.setText("Active brain connected." if ok else "Active brain is not configured yet.")
        self.status_label.setStyleSheet(f"color: {NEURAL_GREEN if ok else NEURAL_RED}; font-family: {FONT_UI}; font-size: 11px; font-weight: 600;")

    def _save_provider_alias(self) -> None:
        brain = self._load_setting("selected_brain", "offline_local")
        provider = "trained_qwen" if brain == "trained_qwen" else "offline_local"
        self._save_setting("ai_provider", provider)

    def _reset_defaults(self) -> None:
        defaults = {
            "interface_language": "en-US",
            "theme_mode": "dark",
            "startup_page": "0",
            "animations_enabled": "true",
            "sound_effects_enabled": "true",
            "compact_mode": "false",
            "auto_save_enabled": "true",
            "voice_reply_enabled": "true",
            "tts_auto_bengali_voice": "1",
            "stt_language": "bn-BD",
            "response_language": "auto",
            "selected_brain": "offline_local",
            "ai_provider": "offline_local",
        }
        for key, value in defaults.items():
            self._save_setting(key, value, emit=False)
        self.status_label.setText("Defaults restored. Reopen Settings to refresh every control.")
        self.settings_changed.emit()

    def _start_snapshot_timer(self) -> None:
        self._seconds = 0
        self._snapshot_timer = QTimer(self)
        self._snapshot_timer.timeout.connect(self._update_snapshot)
        self._snapshot_timer.start(2000)
        self._update_snapshot()

    def _update_snapshot(self) -> None:
        self._seconds += 2
        try:
            import psutil

            cpu = int(psutil.cpu_percent(interval=None))
            mem = psutil.virtual_memory()
            self.cpu_value.setText(f"{cpu}%")
            self.cpu_bar.set_value(cpu)
            self.mem_value.setText(f"{mem.used / (1024 ** 3):.1f} GB / {mem.total / (1024 ** 3):.0f} GB")
            self.mem_bar.set_value(int(mem.percent))
        except Exception:
            self.cpu_value.setText("N/A")
            self.mem_value.setText("N/A")
        hours = self._seconds // 3600
        minutes = (self._seconds % 3600) // 60
        seconds = self._seconds % 60
        self.uptime_value.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    def _metric_row(self, label: str, value: QLabel, color: str | None = None) -> QHBoxLayout:
        row = QHBoxLayout()
        name = QLabel(label)
        name.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {FONT_DISPLAY}; font-size: 11px; font-weight: 800; letter-spacing: 0.5px;")
        value.setAlignment(Qt.AlignmentFlag.AlignRight)
        value.setStyleSheet(f"color: {color or NEURAL_BLUE}; font-family: {FONT_MONO}; font-size: 12px; font-weight: 900;")
        row.addWidget(name)
        row.addStretch(1)
        row.addWidget(value)
        return row

    def _panel(self) -> QFrame:
        panel = QFrame()
        panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        panel.setStyleSheet(f"""
            QFrame {{
                background: rgba(5, 14, 35, 0.72);
                border: 1px solid rgba(47, 140, 255, 0.34);
                border-radius: 10px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        return panel

    def _section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"color: {NEURAL_CYAN}; font-family: {FONT_DISPLAY}; font-size: 14px; font-weight: 900; letter-spacing: 0.8px;")
        return label

    def _category_button_style(self) -> str:
        return f"""
            QPushButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 9px;
                color: {NEURAL_TEXT_SECONDARY};
                font-family: {FONT_UI};
                font-size: 13px;
                font-weight: 800;
                text-align: left;
                padding: 13px 16px;
            }}
            QPushButton:hover {{
                color: {NEURAL_CYAN};
                background: rgba(47, 140, 255, 0.08);
                border-color: rgba(47, 140, 255, 0.22);
            }}
            QPushButton:checked {{
                color: {NEURAL_CYAN};
                background: rgba(47, 140, 255, 0.18);
                border-color: rgba(47, 140, 255, 0.56);
            }}
        """

    def _segment_button_style(self) -> str:
        return f"""
            QPushButton {{
                background: rgba(5, 14, 35, 0.82);
                border: 1px solid rgba(47, 140, 255, 0.34);
                border-radius: 10px;
                color: {NEURAL_TEXT_PRIMARY};
                font-family: {FONT_DISPLAY};
                font-size: 12px;
                font-weight: 900;
            }}
            QPushButton:checked {{
                background: rgba(47, 140, 255, 0.26);
                border-color: rgba(47, 140, 255, 0.72);
                color: white;
            }}
            QPushButton:hover {{
                border-color: {NEURAL_CYAN};
            }}
        """

    def _primary_button_style(self) -> str:
        return f"""
            QPushButton {{
                background: rgba(0, 245, 255, 0.12);
                border: 1px solid rgba(0, 245, 255, 0.48);
                border-radius: 10px;
                color: {NEURAL_CYAN};
                font-family: {FONT_DISPLAY};
                font-size: 12px;
                font-weight: 900;
                padding: 12px 18px;
            }}
            QPushButton:hover {{
                background: rgba(0, 245, 255, 0.20);
            }}
        """

    def _load_setting(self, key: str, default: str = "") -> str:
        return str(self._get_setting(key, default)) if self._get_setting else default

    def _save_setting(self, key: str, value: str, emit: bool = True) -> None:
        if self._set_setting:
            self._set_setting(key, value)
        if emit:
            self.status_label.setText(f"Saved {key.replace('_', ' ')}.")
            self.status_label.setStyleSheet(f"color: {NEURAL_GREEN}; font-family: {FONT_UI}; font-size: 11px; font-weight: 600;")
            self.settings_changed.emit()

    def _load_bool(self, key: str, default: bool, true_value: str = "true") -> bool:
        value = self._load_setting(key, true_value if default else "false").strip().lower()
        return value in {true_value.lower(), "1", "true", "yes", "enabled", "on"}
