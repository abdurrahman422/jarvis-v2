from __future__ import annotations

import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme import (
    BG_NEURAL_DEEP,
    BG_NEURAL_PANEL,
    FONT_BANGLA,
    FONT_DISPLAY,
    FONT_UI,
    NEURAL_BLUE,
    NEURAL_CYAN,
    NEURAL_GREEN,
    NEURAL_PURPLE,
    NEURAL_TEXT_MUTED,
    NEURAL_TEXT_PRIMARY,
    NEURAL_TEXT_SECONDARY,
)


class WaveformWidget(QWidget):
    def __init__(self, bars: int = 86, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._bars = bars
        self.setMinimumHeight(30)

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        width = max(1, self.width())
        height = max(1, self.height())
        center = height / 2
        step = width / max(1, self._bars)
        for i in range(self._bars):
            wave = 0.35 + 0.65 * abs(math.sin(i * 0.37) * math.cos(i * 0.13))
            bar_h = max(4, wave * height * 0.74)
            if i % 9 == 0:
                bar_h *= 1.22
            color = QColor(0, 245, 255) if i < self._bars * 0.58 else QColor(168, 85, 247)
            color.setAlpha(170)
            pen = QPen(color, 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            x = i * step + step * 0.5
            painter.drawLine(x, center - bar_h / 2, x, center + bar_h / 2)


class VoiceCard(QFrame):
    def __init__(
        self,
        name: str,
        subtitle: str,
        tags: list[str],
        accent: str,
        selected: bool = False,
        bangla: bool = True,
    ) -> None:
        super().__init__()
        self.setObjectName("VoiceChoiceCard")
        self.setProperty("selected", selected)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(108)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(14)

        avatar = QLabel("●")
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFixedSize(58, 58)
        avatar.setStyleSheet(
            f"border-radius: 29px; background: {accent}; color: rgba(255,255,255,0.72);"
            "font-size: 26px; font-weight: 900;"
        )
        lay.addWidget(avatar)

        text_box = QVBoxLayout()
        text_box.setSpacing(3)
        title = QLabel(name)
        title.setObjectName("VoiceCardTitle")
        title.setStyleSheet(f"font-family: {FONT_BANGLA if bangla else FONT_DISPLAY};")
        sub = QLabel(subtitle)
        sub.setObjectName("VoiceCardSub")
        text_box.addWidget(title)
        text_box.addWidget(sub)

        tag_row = QHBoxLayout()
        tag_row.setSpacing(6)
        for tag in tags:
            chip = QLabel(tag)
            chip.setObjectName("VoiceTag")
            tag_row.addWidget(chip)
        tag_row.addStretch(1)
        text_box.addLayout(tag_row)
        lay.addLayout(text_box, 1)

        action = QLabel("✓" if selected else "▶")
        action.setObjectName("VoiceCardAction")
        action.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action.setFixedSize(36, 36)
        lay.addWidget(action)


class VoicePage(QWidget):
    page_title = "Voice"
    page_subtitle = "Speech recognition and text-to-speech settings."

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("PageSurface")
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(self._stylesheet())
        root = QHBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 16)
        root.setSpacing(26)

        left = QVBoxLayout()
        left.setSpacing(14)
        root.addLayout(left, 7)

        header = QVBoxLayout()
        header.setSpacing(6)
        title = QLabel("VOICE SETTINGS")
        title.setObjectName("VoicePageTitle")
        subtitle = QLabel("Google STT, voice replies, wake word, mic cleanup, and Bengali TTS speed.")
        subtitle.setObjectName("VoiceSubtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        left.addLayout(header)

        self.voice_combo = QComboBox()
        self.voice_combo.setVisible(False)
        left.addWidget(self.voice_combo)

        tabs = QHBoxLayout()
        tabs.setSpacing(8)
        self.bangla_tab = QPushButton("Bangla TTS")
        self.bangla_tab.setObjectName("VoiceTabActive")
        self.english_tab = QPushButton("English SAPI")
        self.english_tab.setObjectName("VoiceTab")
        tabs.addWidget(self.bangla_tab, 1)
        tabs.addWidget(self.english_tab, 1)
        left.addLayout(tabs)

        bangla_title = QLabel("Bengali fallback voice profiles")
        bangla_title.setObjectName("VoiceSectionTitle")
        left.addWidget(bangla_title)

        bangla_grid = QGridLayout()
        bangla_grid.setSpacing(10)
        bangla_grid.addWidget(VoiceCard("আরিয়ান (পুরুষ)", "স্মার্ট, আত্মবিশ্বাসী কণ্ঠস্বর", ["পুরুষ", "মসৃণ", "প্রাকৃতিক"], "#1d9bf0", True), 0, 0)
        bangla_grid.addWidget(VoiceCard("মৈত্রী (মহিলা)", "মিষ্টি, নরম কণ্ঠস্বর", ["মহিলা", "মিষ্টি", "সহজ"], "#f59e0b"), 0, 1)
        bangla_grid.addWidget(VoiceCard("সায়েম (পুরুষ)", "গভীর, ভারী কণ্ঠস্বর", ["পুরুষ", "গভীর", "ভারী"], "#d08a2e"), 1, 0)
        bangla_grid.addWidget(VoiceCard("তানিয়া (মহিলা)", "উষ্ণ, বন্ধুত্বপূর্ণ কণ্ঠস্বর", ["মহিলা", "উষ্ণ", "বন্ধুত্বপূর্ণ"], "#f97388"), 1, 1)
        bangla_grid.addWidget(VoiceCard("রাকিব (তরুণ)", "তরুণ, উদ্যমী কণ্ঠস্বর", ["তরুণ", "উদ্যমী", "প্রাণবন্ত"], "#8b93a6"), 2, 0)
        bangla_grid.addWidget(VoiceCard("ইফিজা (শিশু)", "নরম, মিষ্টি কণ্ঠস্বর", ["শিশু", "নরম", "মিষ্টি"], "#a3e635"), 2, 1)
        left.addLayout(bangla_grid)

        english_title = QLabel("English Voice List")
        english_title.setObjectName("VoiceSectionTitle")
        left.addWidget(english_title)

        english_grid = QGridLayout()
        english_grid.setSpacing(10)
        english_grid.addWidget(VoiceCard("James (Male)", "Clear, Professional Voice", ["Male", "Clear", "Professional"], "#b58b6a", False, False), 0, 0)
        english_grid.addWidget(VoiceCard("Emma (Female)", "Soft, Natural Voice", ["Female", "Soft", "Natural"], "#e7b59f", False, False), 0, 1)
        left.addLayout(english_grid)

        info = QLabel("Jarvis keeps English SAPI separate from Bengali gTTS fallback.")
        info.setObjectName("VoiceInfo")
        left.addWidget(info)
        left.addStretch(1)

        right = QVBoxLayout()
        right.setSpacing(10)
        root.addLayout(right, 5)

        right.addWidget(self._selected_voice_panel())
        right.addWidget(self._voice_test_panel())
        right.addWidget(self._voice_settings_panel())
        right.addStretch(1)

    def _selected_voice_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("VoicePanel")
        panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)
        title = QLabel("Selected Voice")
        title.setObjectName("VoicePanelTitle")
        lay.addWidget(title)

        row = QHBoxLayout()
        avatar = QLabel("●")
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFixedSize(64, 64)
        avatar.setStyleSheet("border-radius: 32px; background: #1d9bf0; color: rgba(255,255,255,0.7); font-size: 28px;")
        row.addWidget(avatar)
        copy = QVBoxLayout()
        self.selected_voice_label = QLabel("আরিয়ান (পুরুষ)")
        self.selected_voice_label.setObjectName("SelectedVoiceName")
        self.selected_voice_meta = QLabel("স্মার্ট, আত্মবিশ্বাসী কণ্ঠস্বর")
        self.selected_voice_meta.setObjectName("VoiceCardSub")
        copy.addWidget(self.selected_voice_label)
        copy.addWidget(self.selected_voice_meta)
        row.addLayout(copy, 1)
        active = QLabel("ACTIVE")
        active.setObjectName("ActiveBadge")
        active.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(active)
        lay.addLayout(row)
        lay.addWidget(WaveformWidget(72))
        return panel

    def _voice_test_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("VoicePanel")
        panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)
        title = QLabel("TTS Preview")
        title.setObjectName("VoicePanelTitle")
        desc = QLabel("Type a command to test how Jarvis will respond.")
        desc.setObjectName("VoiceSubtitle")
        lay.addWidget(title)
        lay.addWidget(desc)
        self.preview_text = QLineEdit("ওপেন ইউটিউব")
        self.preview_text.setMaxLength(100)
        self.preview_text.setObjectName("VoicePreviewInput")
        lay.addWidget(self.preview_text)
        self.preview_btn = QPushButton("Preview Voice")
        self.preview_btn.setObjectName("VoicePrimaryButton")
        lay.addWidget(self.preview_btn)
        ex_row = QHBoxLayout()
        ex = QLabel("Example Response (আরিয়ান কণ্ঠ)")
        ex.setObjectName("VoicePanelTitle")
        ex_row.addWidget(ex, 1)
        self.test_bn_btn = QPushButton("▶")
        self.test_bn_btn.setObjectName("RoundPlayButton")
        self.test_bn_btn.setFixedSize(34, 34)
        ex_row.addWidget(self.test_bn_btn)
        lay.addLayout(ex_row)
        sample = QLabel("জি স্যার! এখনই ইউটিউব খুলছি।")
        sample.setObjectName("ResponseBubble")
        lay.addWidget(sample)
        lay.addWidget(WaveformWidget(78))
        return panel

    def _voice_settings_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("VoicePanel")
        panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)
        title = QLabel("⚙  Voice Settings")
        title.setObjectName("VoicePanelTitle")
        lay.addWidget(title)

        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(80, 260)
        self.rate_spin.setValue(175)
        self._add_slider_row(lay, "R", "Speech Rate", self.rate_spin, 80, 260, 175)
        self.pitch_spin = QSpinBox()
        self.pitch_spin.setRange(0, 100)
        self.pitch_spin.setValue(50)
        pitch_slider = self._add_slider_row(lay, "P", "Pitch", self.pitch_spin, 0, 100, 50)
        pitch_slider.setEnabled(False)
        self.pitch_spin.setEnabled(False)
        self.pitch_spin.setToolTip("Coming soon")
        self.volume_spin = QSpinBox()
        self.volume_spin.setRange(0, 100)
        self.volume_spin.setValue(80)
        volume_slider = self._add_slider_row(lay, "V", "TTS Volume", self.volume_spin, 0, 100, 80)
        volume_slider.setEnabled(False)
        self.volume_spin.setEnabled(False)
        self.volume_spin.setToolTip("Coming soon")

        self.mic_sensitivity_spin = QSpinBox()
        self.mic_sensitivity_spin.setRange(0, 100)
        self.mic_sensitivity_spin.setValue(50)
        self._add_slider_row(lay, "MIC", "Mic Sensitivity", self.mic_sensitivity_spin, 0, 100, 50)

        self.bengali_tts_speed_combo = QComboBox()
        self.bengali_tts_speed_combo.addItem("Bengali TTS speed: Normal", "normal")
        self.bengali_tts_speed_combo.addItem("Bengali TTS speed: Faster", "faster")
        lay.addWidget(self.bengali_tts_speed_combo)

        self.stt_lang_combo = QComboBox()
        self.stt_lang_combo.addItem("Bangla", "bn-BD")
        self.stt_lang_combo.addItem("English (US)", "en-US")
        self.stt_lang_combo.setVisible(True)
        self.response_lang_combo = QComboBox()
        self.response_lang_combo.addItem("Auto", "auto")
        self.response_lang_combo.addItem("English", "en")
        self.response_lang_combo.addItem("Bangla", "bn")
        self.response_lang_combo.setVisible(True)
        lay.addWidget(self.stt_lang_combo)
        lay.addWidget(self.response_lang_combo)

        checks = QGridLayout()
        checks.setHorizontalSpacing(14)
        checks.setVerticalSpacing(10)
        self.auto_bn_voice_check = QCheckBox("Auto-select best voice")
        self.voice_reply_check = QCheckBox("Speak assistant replies")
        self.wake_word_check = QCheckBox("Wake Word Mode")
        self.emotion_check = QCheckBox("Emotion detection (Coming soon)")
        self.noise_reduction_check = QCheckBox("Noise reduction")
        self.auto_bn_voice_check.setChecked(True)
        self.voice_reply_check.setChecked(True)
        self.emotion_check.setChecked(True)
        self.emotion_check.setEnabled(False)
        self.noise_reduction_check.setChecked(True)
        checks.addWidget(self.auto_bn_voice_check, 0, 0)
        checks.addWidget(self.voice_reply_check, 0, 1)
        checks.addWidget(self.wake_word_check, 1, 0)
        checks.addWidget(self.emotion_check, 1, 1)
        checks.addWidget(self.noise_reduction_check, 2, 0)
        lay.addLayout(checks)

        self.tts_status_label = QLabel("TTS status unavailable")
        self.tts_status_label.setObjectName("VoiceStatus")
        lay.addWidget(self.tts_status_label)
        self.ambient_calibrate_btn = QPushButton("Calibrate ambient noise")
        self.ambient_calibrate_btn.setObjectName("VoiceGhostButton")
        lay.addWidget(self.ambient_calibrate_btn)
        self.apply_btn = QPushButton("Apply Voice Settings")
        self.apply_btn.setObjectName("VoiceGhostButton")
        lay.addWidget(self.apply_btn)
        return panel

    def _add_slider_row(self, parent: QVBoxLayout, icon: str, label: str, spin: QSpinBox, minimum: int, maximum: int, value: int) -> QSlider:
        row = QHBoxLayout()
        row.setSpacing(10)
        icon_label = QLabel(icon)
        icon_label.setFixedWidth(24)
        name = QLabel(label)
        name.setObjectName("VoiceSettingLabel")
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)
        spin.setObjectName("VoiceValueBox")
        spin.setFixedWidth(64)
        row.addWidget(icon_label)
        row.addWidget(name)
        row.addWidget(slider, 1)
        row.addWidget(spin)
        parent.addLayout(row)
        return slider

    def _sync_labels(self) -> None:
        name = self.voice_combo.currentText().strip()
        if name:
            self.selected_voice_label.setText(name)
            self.selected_voice_meta.setText("Active system voice")

    def _stylesheet(self) -> str:
        return f"""
        QWidget#PageSurface {{
            background: {BG_NEURAL_DEEP};
        }}
        QLabel#VoicePageTitle {{
            font-family: {FONT_DISPLAY};
            font-size: 26px;
            font-weight: 900;
            color: {NEURAL_TEXT_PRIMARY};
        }}
        QLabel#VoiceSubtitle {{
            color: {NEURAL_TEXT_SECONDARY};
            font-size: 13px;
            font-weight: 600;
        }}
        QLabel#VoiceSectionTitle, QLabel#VoicePanelTitle {{
            font-family: {FONT_DISPLAY};
            font-size: 16px;
            font-weight: 800;
            color: {NEURAL_TEXT_PRIMARY};
        }}
        QPushButton#VoiceTabActive, QPushButton#VoiceTab {{
            min-height: 48px;
            border-radius: 8px;
            font-family: {FONT_DISPLAY};
            font-size: 15px;
            font-weight: 800;
        }}
        QPushButton#VoiceTabActive {{
            color: {NEURAL_CYAN};
            background: rgba(47, 140, 255, 0.18);
            border: 1px solid rgba(47, 140, 255, 0.75);
        }}
        QPushButton#VoiceTab {{
            color: {NEURAL_TEXT_PRIMARY};
            background: rgba(15, 22, 40, 0.86);
            border: 1px solid rgba(80, 110, 170, 0.34);
        }}
        QFrame#VoiceChoiceCard, QFrame#VoicePanel {{
            background: {BG_NEURAL_PANEL};
            border: 1px solid rgba(65, 105, 180, 0.34);
            border-radius: 10px;
        }}
        QFrame#VoiceChoiceCard[selected="true"] {{
            border: 1px solid {NEURAL_BLUE};
            background: rgba(20, 54, 116, 0.36);
        }}
        QLabel#VoiceCardTitle, QLabel#SelectedVoiceName {{
            font-size: 17px;
            font-weight: 900;
            color: {NEURAL_TEXT_PRIMARY};
        }}
        QLabel#SelectedVoiceName {{
            font-family: {FONT_BANGLA};
            font-size: 20px;
        }}
        QLabel#VoiceCardSub {{
            font-family: {FONT_BANGLA};
            font-size: 12px;
            font-weight: 700;
            color: {NEURAL_TEXT_SECONDARY};
        }}
        QLabel#VoiceTag {{
            background: rgba(47, 140, 255, 0.22);
            color: #dbeafe;
            border-radius: 5px;
            padding: 3px 8px;
            font-family: {FONT_BANGLA};
            font-size: 11px;
            font-weight: 800;
        }}
        QLabel#VoiceCardAction {{
            border: 1px solid rgba(148, 163, 184, 0.55);
            border-radius: 18px;
            color: #ffffff;
            font-size: 20px;
            font-weight: 900;
        }}
        QLabel#ActiveBadge {{
            background: #16a34a;
            color: white;
            border-radius: 7px;
            padding: 7px 12px;
            font-weight: 900;
        }}
        QLabel#VoiceInfo {{
            background: rgba(47, 140, 255, 0.16);
            color: {NEURAL_TEXT_PRIMARY};
            border: 1px solid rgba(47, 140, 255, 0.3);
            border-radius: 10px;
            padding: 14px 16px;
            font-weight: 700;
        }}
        QLineEdit#VoicePreviewInput, QLabel#ResponseBubble {{
            background: rgba(4, 8, 18, 0.74);
            border: 1px solid rgba(47, 140, 255, 0.22);
            border-radius: 8px;
            padding: 12px;
            color: {NEURAL_TEXT_PRIMARY};
            font-family: {FONT_BANGLA};
            font-size: 14px;
            font-weight: 800;
            min-height: 38px;
        }}
        QPushButton#VoicePrimaryButton {{
            min-height: 44px;
            border-radius: 8px;
            border: none;
            background: {NEURAL_BLUE};
            color: white;
            font-size: 14px;
            font-weight: 900;
        }}
        QPushButton#RoundPlayButton {{
            border-radius: 17px;
            border: 1px solid rgba(148, 163, 184, 0.55);
            background: transparent;
            color: white;
            font-size: 15px;
        }}
        QLabel#VoiceSettingLabel {{
            color: {NEURAL_TEXT_PRIMARY};
            font-weight: 800;
            min-width: 92px;
        }}
        QSpinBox#VoiceValueBox {{
            background: rgba(5, 8, 16, 0.76);
            border: 1px solid rgba(80, 110, 170, 0.36);
            border-radius: 7px;
            color: {NEURAL_TEXT_PRIMARY};
            padding: 6px;
        }}
        QSlider::groove:horizontal {{
            height: 4px;
            background: rgba(148, 163, 184, 0.20);
            border-radius: 2px;
        }}
        QSlider::sub-page:horizontal {{
            background: {NEURAL_BLUE};
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            width: 14px;
            height: 14px;
            margin: -5px 0;
            border-radius: 7px;
            background: white;
        }}
        QCheckBox {{
            color: {NEURAL_TEXT_PRIMARY};
            font-weight: 700;
            spacing: 8px;
        }}
        QLabel#VoiceStatus {{
            color: {NEURAL_TEXT_MUTED};
            font-size: 11px;
            font-weight: 700;
        }}
        QPushButton#VoiceGhostButton {{
            min-height: 34px;
            border-radius: 8px;
            background: rgba(0, 245, 255, 0.06);
            border: 1px solid rgba(0, 245, 255, 0.18);
            color: {NEURAL_CYAN};
            font-weight: 800;
        }}
        """
