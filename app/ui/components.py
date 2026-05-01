"""Reusable premium UI building blocks for Jarvis desktop."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QConicalGradient, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QWidget,
    QVBoxLayout,
)

from app.ui.theme import (
    ACCENT_PRIMARY,
    ACCENT_SECONDARY,
    ERROR,
    SPACE_2,
    SPACE_3,
    SUCCESS,
    WARNING,
)

from app.ui.theme import (
    NEURAL_CYAN,
    NEURAL_BLUE,
    NEURAL_PURPLE,
    NEURAL_GREEN,
    NEURAL_TEXT_PRIMARY,
    NEURAL_TEXT_SECONDARY,
    NEURAL_TEXT_MUTED,
    BG_NEURAL_CORE,
    BG_NEURAL_SURFACE,
    BG_NEURAL_PANEL,
    BG_NEURAL_CARD,
    BG_NEURAL_DEEP,
    MONO_FAMILY,
)


class PremiumCard(QFrame):
    def __init__(
        self,
        title: str | None = None,
        subtitle: str | None = None,
        tone: str = "default",
        object_name: str | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName(
            object_name
            or {
                "accent": "AccentCard",
                "feature": "FeatureCard",
            }.get(tone, "PremiumCard")
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(SPACE_3)

        if title:
            t = QLabel(title)
            t.setObjectName("CardTitle")
            t.setWordWrap(True)
            outer.addWidget(t)

        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("PageSubtitle")
            s.setWordWrap(True)
            outer.addWidget(s)

        self.body_layout = QVBoxLayout()
        self.body_layout.setSpacing(SPACE_3)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        outer.addLayout(self.body_layout)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(14 if tone == "accent" else 10)
        shadow.setOffset(0, 2)
        shadow.setColor(
            QColor(28, 201, 255, 20) if tone == "accent" else QColor(4, 10, 22, 42)
        )
        self.setGraphicsEffect(shadow)

    def add_widget(self, widget) -> None:
        self.body_layout.addWidget(widget)


class HeroPanel(QFrame):
    def __init__(self, kicker: str, title: str, subtitle: str) -> None:
        super().__init__()
        self.setObjectName("HeroPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(SPACE_3)

        k = QLabel(kicker)
        k.setObjectName("HeroKicker")

        t = QLabel(title)
        t.setObjectName("HeroTitle")
        t.setWordWrap(True)

        s = QLabel(subtitle)
        s.setObjectName("HeroSubtitle")
        s.setWordWrap(True)

        lay.addWidget(k)
        lay.addWidget(t)
        lay.addWidget(s)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(40, 170, 255, 28))
        self.setGraphicsEffect(shadow)


class StatMiniCard(QFrame):
    def __init__(
        self,
        label: str,
        value_placeholder: str = "-",
        detail: str = "",
        accent: str = "default",
    ) -> None:
        super().__init__()
        self.setObjectName("StatCard")
        self.setProperty("accent", accent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(92)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(4)

        self._label = QLabel(label)
        self._label.setObjectName("CardTitle")
        self._label.setWordWrap(True)

        self._value = QLabel(value_placeholder)
        self._value.setObjectName("StatValue")
        self._value.setWordWrap(True)

        self._detail = QLabel(detail)
        self._detail.setObjectName("SectionMeta")
        self._detail.setWordWrap(True)

        lay.addWidget(self._label)
        lay.addWidget(self._value)
        if detail:
            lay.addWidget(self._detail)
        lay.addStretch()

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 3)
        glow_map = {
            "primary": QColor(44, 190, 255, 22),
            "secondary": QColor(146, 120, 255, 18),
            "success": QColor(53, 211, 153, 18),
        }
        shadow.setColor(glow_map.get(accent, QColor(4, 10, 22, 54)))
        self.setGraphicsEffect(shadow)

        self.style().unpolish(self)
        self.style().polish(self)

    def set_value(self, text: str) -> None:
        self._value.setText(text)


class StatusChip(QFrame):
    def __init__(
        self,
        text: str,
        accent_text: str | None = None,
        tone: str = "primary",
    ) -> None:
        super().__init__()
        self.setObjectName("InfoPanel")
        self.setProperty("tone", tone)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        color = {
            "primary": ACCENT_PRIMARY,
            "violet": ACCENT_SECONDARY,
            "success": SUCCESS,
            "warning": WARNING,
            "danger": ERROR,
        }.get(tone, ACCENT_PRIMARY)
        self._accent_style = f"color: {color}; font-weight: 800; font-size: 11px;"

        lay = QHBoxLayout(self)
        lay.setContentsMargins(11, 8, 11, 8)
        lay.setSpacing(8)

        dot = QLabel("o")
        dot.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 800;")

        self.label = QLabel(text)
        self.label.setObjectName("MutedLabel")
        self.label.setWordWrap(True)

        lay.addWidget(dot)
        lay.addWidget(self.label)

        self.accent_label: QLabel | None = None
        if accent_text:
            self.accent_label = QLabel(accent_text)
            self.accent_label.setStyleSheet(self._accent_style)
            lay.addWidget(self.accent_label)

        lay.addStretch()
        self.style().unpolish(self)
        self.style().polish(self)

    def set_text(self, text: str) -> None:
        self.label.setText(text)

    def set_accent_text(self, text: str) -> None:
        if self.accent_label is None:
            self.accent_label = QLabel(text)
            self.accent_label.setStyleSheet(self._accent_style)
            self.layout().insertWidget(2, self.accent_label)
        else:
            self.accent_label.setText(text)

    def set_value(self, text: str) -> None:
        self.set_accent_text(text)


class ShellTopBar(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("TopBar")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(14)

        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(2)

        self.title = QLabel("Jarvis")
        self.title.setObjectName("TopBarTitle")
        self.title.setWordWrap(True)

        self.subtitle = QLabel("Premium desktop assistant")
        self.subtitle.setObjectName("TopBarSubtitle")
        self.subtitle.setWordWrap(True)

        title_col.addWidget(self.title)
        title_col.addWidget(self.subtitle)

        self.primary_chip = StatusChip("Local-first", "ACTIVE", tone="success")
        self.secondary_chip = StatusChip("Voice and automation ready", tone="violet")

        lay.addLayout(title_col, stretch=1)
        lay.addWidget(self.primary_chip)
        lay.addWidget(self.secondary_chip)

    def set_page(self, title: str, subtitle: str) -> None:
        self.title.setText(title)
        self.subtitle.setText(subtitle)


def page_header(
    title: str,
    subtitle: str | None = None,
    eyebrow: str = "Assistant Workspace",
) -> QFrame:
    box = QFrame()
    box.setStyleSheet("background: transparent; border: none;")

    v = QVBoxLayout(box)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(2)

    e = QLabel(eyebrow)
    e.setObjectName("PageEyebrow")
    e.setWordWrap(True)

    t = QLabel(title)
    t.setObjectName("PageTitle")
    t.setWordWrap(True)

    v.addWidget(e)
    v.addWidget(t)

    if subtitle:
        s = QLabel(subtitle)
        s.setObjectName("PageSubtitle")
        s.setWordWrap(True)
        v.addWidget(s)

    return box


def compact_panel(title: str, body: str, tone: str = "default") -> QFrame:
    panel = QFrame()
    panel.setObjectName("CompactPanel")
    if tone != "default":
        panel.setProperty("tone", tone)

    lay = QVBoxLayout(panel)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(SPACE_2)

    t = QLabel(title)
    t.setObjectName("CardTitle")
    t.setWordWrap(True)

    b = QLabel(body)
    b.setObjectName("PageSubtitle")
    b.setWordWrap(True)

    lay.addWidget(t)
    lay.addWidget(b)
    return panel


def utility_button(text: str, object_name: str = "GhostButton") -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName(object_name)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


class NeuralCard(QFrame):
    def __init__(
        self,
        title: str | None = None,
        subtitle: str | None = None,
        neural: str = "cyan",
    ) -> None:
        super().__init__()
        self.setObjectName("NeuralCard")
        self.setProperty("neural", neural)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(SPACE_3)

        if title:
            t = QLabel(title)
            t.setObjectName("NeuralPageTitle")
            t.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {NEURAL_TEXT_PRIMARY};")
            t.setWordWrap(True)
            outer.addWidget(t)

        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("NeuralPageSubtitle")
            s.setWordWrap(True)
            outer.addWidget(s)

        self.body_layout = QVBoxLayout()
        self.body_layout.setSpacing(SPACE_3)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        outer.addLayout(self.body_layout)

        glow_color = NEURAL_CYAN if neural == "cyan" else NEURAL_PURPLE
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(glow_color).lighter(200).darker(150))
        self.setGraphicsEffect(shadow)

    def add_widget(self, widget) -> None:
        self.body_layout.addWidget(widget)


class NeuralStatusOrb(QFrame):
    def __init__(
        self,
        label: str = "Status",
        status: str = "ONLINE",
        tone: str = "cyan",
    ) -> None:
        super().__init__()
        self.setObjectName("NeuralStatusOrb")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        color = {
            "cyan": NEURAL_CYAN,
            "purple": NEURAL_PURPLE,
            "green": NEURAL_GREEN,
        }.get(tone, NEURAL_CYAN)

        self.setStyleSheet(f"""
            background: {BG_NEURAL_DEEP};
            border: 1px solid rgba(0,245,255,0.1);
            border-radius: 10px;
        """)

        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(12)
        glow.setOffset(0, 2)
        glow.setColor(QColor(0, 30, 50))
        self.setGraphicsEffect(glow)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)

        indicator = QFrame()
        indicator.setFixedSize(8, 8)
        indicator.setStyleSheet(
            f"background: {color}; border-radius: 4px;"
        )
        indicator.setGraphicsEffect(
            self._make_glow_effect(color)
        )

        text = QLabel(label)
        text.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")

        status_label = QLabel(status)
        status_label.setObjectName("NeuralOrbGlow")
        status_label.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 10px;")

        lay.addWidget(indicator)
        lay.addWidget(text)
        lay.addStretch()
        lay.addWidget(status_label)

        self._indicator = indicator
        self._status_label = status_label

    def _make_glow_effect(self, color: str):
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(10)
        effect.setOffset(0, 0)
        effect.setColor(QColor(color))
        return effect

    def set_status(self, status: str, tone: str = "cyan") -> None:
        """Update the status text and color."""
        color = {
            "cyan": NEURAL_CYAN,
            "purple": NEURAL_PURPLE,
            "green": NEURAL_GREEN,
        }.get(tone, NEURAL_CYAN)

        self._status_label.setText(status)
        self._status_label.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 9px;")
        self._indicator.setStyleSheet(f"background: {color}; border-radius: 3px;")

    def set_value(self, value: str) -> None:
        """Compatibility method - same as set_status."""
        self.set_status(value, "cyan")


class NeuralComposer(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("NeuralComposer")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(12)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        label = QLabel("NEURAL INPUT")
        label.setStyleSheet(
            f"color: {NEURAL_CYAN}; font-size: 10px; font-weight: 700; letter-spacing: 2px;"
        )

        header.addWidget(label)
        header.addStretch()

        self.status = QLabel("READY")
        self.status.setStyleSheet(
            f"color: {NEURAL_GREEN}; font-size: 10px; font-weight: 700;"
        )
        header.addWidget(self.status)

        lay.addLayout(header)

        self.input_area = QFrame()
        self.input_area.setObjectName("NeuralInput")
        from PySide6.QtWidgets import QVBoxLayout as QVBoxLayoutInner
        inner = QVBoxLayoutInner(self.input_area)
        inner.setContentsMargins(0, 0, 0, 0)
        self._input_widget = None

        lay.addWidget(self.input_area)

    def set_input_widget(self, widget) -> None:
        if self._input_widget:
            self.input_area.layout().removeWidget(self._input_widget)
        self._input_widget = widget
        if widget:
            self.input_area.layout().addWidget(widget)

    def set_status(self, text: str) -> None:
        self.status.setText(text)


class NeuralNavButton(QPushButton):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.setObjectName("NeuralNavButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(44)


def _neural_color(tone: str) -> str:
    return {
        "cyan": NEURAL_CYAN,
        "blue": NEURAL_BLUE,
        "purple": NEURAL_PURPLE,
        "green": NEURAL_GREEN,
    }.get(tone, NEURAL_CYAN)


def _shadow(widget, color: str, blur: int = 28, alpha: int = 70) -> None:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, 0)
    qcolor = QColor(color)
    qcolor.setAlpha(alpha)
    effect.setColor(qcolor)
    widget.setGraphicsEffect(effect)


class NeuralButton(QPushButton):
    def __init__(self, text: str, icon: str = "", tone: str = "cyan") -> None:
        super().__init__(f"{icon}  {text}" if icon else text)
        self.tone = tone
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(48)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        color = _neural_color(tone)
        self.setStyleSheet(f"""
            QPushButton {{
                background: rgba(3, 14, 33, 0.78);
                border: 1px solid {color};
                border-radius: 10px;
                color: {NEURAL_TEXT_PRIMARY};
                font-family: {MONO_FAMILY};
                font-size: 12px;
                font-weight: 800;
                padding: 12px 18px;
                text-align: center;
            }}
            QPushButton:hover {{
                background: rgba(12, 28, 58, 0.92);
                color: {color};
                border: 1px solid {color};
            }}
            QPushButton:pressed {{
                background: rgba(0, 245, 255, 0.12);
            }}
        """)
        _shadow(self, color, 20, 34)


class NeuralSidebarButton(QPushButton):
    def __init__(self, icon: str, tooltip: str = "") -> None:
        super().__init__(icon)
        self.setObjectName("NeuralSidebarButton")
        self.setToolTip(tooltip)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(48, 48)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 12px;
                color: {NEURAL_TEXT_MUTED};
                font-family: {MONO_FAMILY};
                font-size: 19px;
                font-weight: 800;
            }}
            QPushButton:hover {{
                background: rgba(47, 140, 255, 0.12);
                border: 1px solid rgba(47, 140, 255, 0.32);
                color: {NEURAL_BLUE};
            }}
            QPushButton:checked {{
                background: rgba(47, 140, 255, 0.18);
                border: 1px solid rgba(0, 245, 255, 0.45);
                color: {NEURAL_CYAN};
            }}
        """)


class NeuralResourceCard(QFrame):
    def __init__(self, title: str, value: str, detail: str = "", tone: str = "blue") -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        color = _neural_color(tone)
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(4, 12, 28, 0.78);
                border: 1px solid rgba(47, 140, 255, 0.28);
                border-radius: 10px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        label = QLabel(title.upper())
        label.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {MONO_FAMILY}; font-size: 10px; font-weight: 800;")
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color: {color}; font-family: {MONO_FAMILY}; font-size: 16px; font-weight: 900;")
        row.addWidget(label)
        row.addStretch(1)
        row.addWidget(self.value_label)

        self.bar = QFrame()
        self.bar.setFixedHeight(5)
        self.bar.setStyleSheet(f"background: rgba(47, 140, 255, 0.18); border: none; border-radius: 2px;")
        self.detail_label = QLabel(detail)
        self.detail_label.setStyleSheet(f"color: {NEURAL_TEXT_MUTED}; font-family: {MONO_FAMILY}; font-size: 10px; border: none;")

        lay.addLayout(row)
        lay.addWidget(self.bar)
        if detail:
            lay.addWidget(self.detail_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class NeuralAgentRow(QFrame):
    def __init__(self, name: str, status: str = "ACTIVE", tone: str = "green") -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        color = _neural_color(tone)
        self._tone = tone
        self.setStyleSheet("background: transparent; border: none;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 6)
        lay.setSpacing(10)
        self.dot = QFrame()
        self.dot.setFixedSize(18, 18)
        self.dot.setStyleSheet(f"background: transparent; border: 3px solid {color}; border-radius: 9px;")
        label = QLabel(name)
        label.setStyleSheet(f"color: {NEURAL_TEXT_PRIMARY}; font-family: {MONO_FAMILY}; font-size: 13px; font-weight: 700;")
        self.status_label = QLabel(status)
        self.status_label.setStyleSheet(f"color: {color}; font-family: {MONO_FAMILY}; font-size: 10px; font-weight: 900;")
        lay.addWidget(self.dot)
        lay.addWidget(label)
        lay.addStretch(1)
        lay.addWidget(self.status_label)

    def set_status(self, status: str, tone: str | None = None) -> None:
        color = _neural_color(tone or self._tone)
        self.status_label.setText(status)
        self.status_label.setStyleSheet(f"color: {color}; font-family: {MONO_FAMILY}; font-size: 10px; font-weight: 900;")
        self.dot.setStyleSheet(f"background: transparent; border: 3px solid {color}; border-radius: 9px;")


class StatusChip(QFrame):
    def __init__(self, text: str, accent_text: str | None = None, tone: str = "green") -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._tone = tone
        color = _neural_color(tone)
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(0, 245, 255, 0.06);
                border: 1px solid rgba(0, 245, 255, 0.22);
                border-radius: 12px;
            }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(8)
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color}; font-size: 12px; border: none;")
        self.label = QLabel(text)
        self.label.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {MONO_FAMILY}; font-size: 10px; font-weight: 800; border: none;")
        self.accent_label = QLabel(accent_text or "")
        self.accent_label.setStyleSheet(f"color: {color}; font-family: {MONO_FAMILY}; font-size: 10px; font-weight: 900; border: none;")
        lay.addWidget(dot)
        lay.addWidget(self.label)
        if accent_text:
            lay.addWidget(self.accent_label)

    def set_text(self, text: str) -> None:
        self.label.setText(text)

    def set_accent_text(self, text: str) -> None:
        self.accent_label.setText(text)
        if self.accent_label.parent() is None:
            self.layout().addWidget(self.accent_label)

    def set_value(self, text: str) -> None:
        self.set_accent_text(text)


class NeuralCommandBar(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(88)
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(6, 13, 35, 0.94);
                border: 1px solid rgba(0, 245, 255, 0.55);
                border-radius: 22px;
            }}
            QTextEdit {{
                background: rgba(3, 8, 22, 0.78);
                border: none;
                border-radius: 16px;
                color: {NEURAL_TEXT_PRIMARY};
                font-family: {MONO_FAMILY};
                font-size: 15px;
                padding: 13px 16px;
            }}
        """)
        _shadow(self, NEURAL_PURPLE, 32, 85)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(22, 14, 18, 14)
        lay.setSpacing(14)

        spark = QLabel("*")
        spark.setStyleSheet(f"color: {NEURAL_BLUE}; font-size: 28px; font-weight: 900; border: none;")
        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("Type a command or ask anything...")
        self.input_box.setMaximumHeight(58)
        self.send_btn = QPushButton("RUN")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setFixedSize(62, 52)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(47, 140, 255, 0.20);
                border: 1px solid rgba(47, 140, 255, 0.45);
                border-radius: 14px;
                color: {NEURAL_BLUE};
                font-family: {MONO_FAMILY};
                font-size: 12px;
                font-weight: 900;
            }}
            QPushButton:hover {{
                background: rgba(47, 140, 255, 0.32);
                color: {NEURAL_CYAN};
            }}
        """)
        self.listen_btn = QPushButton("MIC")
        self.listen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.listen_btn.setFixedSize(58, 58)
        self.listen_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(168, 85, 247, 0.22);
                border: 1px solid rgba(168, 85, 247, 0.70);
                border-radius: 29px;
                color: white;
                font-family: {MONO_FAMILY};
                font-size: 12px;
                font-weight: 900;
            }}
            QPushButton:hover {{
                background: rgba(168, 85, 247, 0.36);
                border-color: {NEURAL_CYAN};
            }}
        """)
        self.clear_btn = QPushButton("CLR")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setFixedSize(48, 42)
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 12px;
                color: {NEURAL_TEXT_MUTED};
                font-family: {MONO_FAMILY};
                font-size: 10px;
                font-weight: 800;
            }}
            QPushButton:hover {{
                color: {NEURAL_CYAN};
                border-color: rgba(0,245,255,0.28);
            }}
        """)

        lay.addWidget(spark)
        lay.addWidget(self.input_box, 1)
        lay.addWidget(self.clear_btn)
        lay.addWidget(self.send_btn)
        lay.addWidget(self.listen_btn)


class JarvisOrbPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(230)
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(4, 12, 30, 0.82);
                border: 1px solid rgba(47, 140, 255, 0.28);
                border-radius: 16px;
            }}
        """)
        _shadow(self, NEURAL_BLUE, 28, 45)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)

        title = QLabel("JARVIS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {NEURAL_BLUE}; font-family: {MONO_FAMILY}; font-size: 24px; font-weight: 900; border: none;")
        online = QLabel("● ONLINE")
        online.setAlignment(Qt.AlignmentFlag.AlignCenter)
        online.setStyleSheet(f"color: {NEURAL_GREEN}; font-family: {MONO_FAMILY}; font-size: 11px; font-weight: 800; border: none;")

        orb = QFrame()
        orb.setFixedSize(150, 150)
        orb.setStyleSheet(f"""
            background: qradialgradient(cx:0.38, cy:0.35, radius:0.72,
                stop:0 white,
                stop:0.12 {NEURAL_CYAN},
                stop:0.45 rgba(47, 140, 255, 0.78),
                stop:0.72 rgba(168, 85, 247, 0.70),
                stop:1 rgba(3, 8, 22, 0.05));
            border: 2px solid rgba(0,245,255,0.70);
            border-radius: 75px;
        """)
        _shadow(orb, NEURAL_CYAN, 42, 130)
        orb_lay = QVBoxLayout(orb)
        orb_lay.setContentsMargins(0, 0, 0, 0)
        core = QLabel("AI")
        core.setAlignment(Qt.AlignmentFlag.AlignCenter)
        core.setStyleSheet(f"color: white; font-family: {MONO_FAMILY}; font-size: 32px; font-weight: 900; border: none; background: transparent;")
        orb_lay.addWidget(core)

        base = QLabel("━━━━━━")
        base.setAlignment(Qt.AlignmentFlag.AlignCenter)
        base.setStyleSheet(f"color: {NEURAL_BLUE}; font-size: 28px; font-weight: 900; border: none;")
        self.status = QLabel("NEURAL LINK")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet(f"color: {NEURAL_CYAN}; font-family: {MONO_FAMILY}; font-size: 10px; font-weight: 900; letter-spacing: 1px; border: none;")

        voice = QLabel("VOICE STATUS")
        voice.setStyleSheet(f"color: {NEURAL_TEXT_MUTED}; font-family: {MONO_FAMILY}; font-size: 10px; font-weight: 900; border: none;")
        wave = QLabel("▁▃▅▇▆▃▂▅▇▅▃▁")
        wave.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wave.setStyleSheet(f"color: {NEURAL_CYAN}; font-family: {MONO_FAMILY}; font-size: 22px; font-weight: 900; border: none;")
        self.voice_state = QLabel("LISTENING...")
        self.voice_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.voice_state.setStyleSheet(f"color: {NEURAL_TEXT_MUTED}; font-family: {MONO_FAMILY}; font-size: 10px; font-weight: 900; border: none;")

        lay.addWidget(title)
        lay.addWidget(online)
        lay.addSpacing(18)
        lay.addWidget(orb, 0, Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(base)
        lay.addWidget(self.status)
        lay.addStretch(1)
        lay.addWidget(voice)
        lay.addWidget(wave)
        lay.addWidget(self.voice_state)

    def set_state(self, text: str, color: str = NEURAL_CYAN) -> None:
        self.status.setText(text)
        self.status.setStyleSheet(f"color: {color}; font-family: {MONO_FAMILY}; font-size: 10px; font-weight: 900; letter-spacing: 1px; border: none;")


# Reference-matched neural dashboard widgets. These definitions intentionally
# come last so legacy imports keep working while the dashboard gets the new look.
def _tone_color(tone: str) -> str:
    return {
        "cyan": NEURAL_CYAN,
        "blue": NEURAL_BLUE,
        "purple": NEURAL_PURPLE,
        "green": NEURAL_GREEN,
    }.get(tone, NEURAL_BLUE)


def _glow(widget, color: str, blur: int = 22, alpha: int = 54) -> None:
    # Intentionally disabled for the neural dashboard. Applying graphics effects
    # to widgets that contain custom paintEvent children can make Qt repaint the
    # subtree through an offscreen pixmap and trigger repeated QPainter warnings.
    widget.setGraphicsEffect(None)


class ProgressBarWidget(QWidget):
    def __init__(self, value: int = 0, tone: str = "blue") -> None:
        super().__init__()
        self.value = max(0, min(100, value))
        self.tone = tone
        self.setFixedHeight(8)

    def set_value(self, value: int) -> None:
        self.value = max(0, min(100, value))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(0, 2, self.width(), 4)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(22, 45, 88, 150))
            painter.drawRoundedRect(rect, 2, 2)
            fill = QRectF(0, 2, max(8, self.width() * self.value / 100), 4)
            grad = QLinearGradient(fill.topLeft(), fill.topRight())
            grad.setColorAt(0, QColor(NEURAL_BLUE))
            grad.setColorAt(1, QColor(_tone_color(self.tone)))
            painter.setBrush(grad)
            painter.drawRoundedRect(fill, 2, 2)
        finally:
            painter.end()


class NeuralBrainWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(120)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setGraphicsEffect(None)
        self._phase = 0.0
        self._nodes = [
            (0.23, 0.62, 0.15), (0.30, 0.50, 0.72), (0.41, 0.42, 0.35),
            (0.52, 0.36, 0.91), (0.64, 0.43, 0.18), (0.72, 0.54, 0.58),
            (0.77, 0.66, 0.04), (0.64, 0.73, 0.81), (0.49, 0.70, 0.27),
            (0.36, 0.67, 0.66), (0.29, 0.58, 0.47), (0.47, 0.54, 0.10),
            (0.58, 0.58, 0.76), (0.55, 0.26, 0.38), (0.40, 0.29, 0.86),
        ]
        self._links = [
            (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6),
            (6, 7), (7, 8), (8, 9), (9, 10), (10, 0),
            (1, 11), (11, 12), (12, 5), (2, 11), (8, 11),
            (3, 13), (13, 4), (13, 14), (14, 2), (9, 12),
        ]
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

    def _tick(self) -> None:
        self._phase = (self._phase + 0.055) % (math.tau * 1000)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            w, h = self.width(), self.height()
            points = [QPointF(w * x, h * y) for x, y, _ in self._nodes]

            brain = QPainterPath()
            brain.moveTo(w * 0.18, h * 0.62)
            brain.cubicTo(w * 0.12, h * 0.36, w * 0.35, h * 0.18, w * 0.50, h * 0.24)
            brain.cubicTo(w * 0.70, h * 0.14, w * 0.88, h * 0.34, w * 0.82, h * 0.58)
            brain.cubicTo(w * 0.80, h * 0.78, w * 0.55, h * 0.86, w * 0.35, h * 0.76)
            brain.cubicTo(w * 0.23, h * 0.73, w * 0.15, h * 0.68, w * 0.18, h * 0.62)
            painter.setPen(QPen(QColor(0, 245, 255, 92), 1.15))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(brain)

            painter.setPen(QPen(QColor(0, 150, 255, 34), 1))
            for x, y, seed in self._nodes[::2]:
                painter.drawPoint(QPointF(w * (x + math.sin(seed * 9) * 0.18), h * (y - 0.22)))

            for idx, (a, b) in enumerate(self._links):
                glow = 0.45 + 0.55 * ((math.sin(self._phase + idx * 0.7) + 1.0) / 2.0)
                color = QColor(0, 245, 255, int(42 + 70 * glow))
                painter.setPen(QPen(color, 0.9))
                painter.drawLine(points[a], points[b])

            for idx, point in enumerate(points):
                seed = self._nodes[idx][2]
                pulse = (math.sin(self._phase * 1.65 + seed * math.tau) + 1.0) / 2.0
                radius = 2.0 + pulse * 1.6
                glow_radius = radius + 4.5
                glow = QColor(0, 245, 255, int(34 + pulse * 42))
                core = QColor(0, 245, 255, int(170 + pulse * 70))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(glow)
                painter.drawEllipse(point, glow_radius, glow_radius)
                painter.setBrush(core)
                painter.drawEllipse(point, radius, radius)
        finally:
            painter.end()


class OrbWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(190, 210)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = self.width(), self.height()
            cx, cy = w / 2, h * 0.46
            radius = min(w * 0.34, h * 0.30)
            for i, alpha in enumerate((38, 26, 16)):
                painter.setPen(QPen(QColor(0, 160, 255, alpha), 1))
                painter.drawEllipse(QPointF(cx, cy), radius + i * 16, (radius + i * 16) * 0.86)
            grad = QRadialGradient(QPointF(cx - radius * 0.35, cy - radius * 0.35), radius * 1.35)
            grad.setColorAt(0.0, QColor(255, 255, 255, 235))
            grad.setColorAt(0.12, QColor(0, 245, 255, 230))
            grad.setColorAt(0.44, QColor(26, 114, 255, 235))
            grad.setColorAt(0.72, QColor(151, 69, 255, 230))
            grad.setColorAt(1.0, QColor(3, 6, 20, 80))
            painter.setPen(QPen(QColor(0, 245, 255, 190), 1.4))
            painter.setBrush(grad)
            painter.drawEllipse(QPointF(cx, cy), radius, radius)
            painter.setPen(QPen(QColor(0, 245, 255, 105), 1))
            for i in range(10):
                rect = QRectF(cx - radius * (0.95 + i * 0.015), cy - radius * (0.35 + i * 0.035),
                              radius * (1.9 + i * 0.03), radius * (0.7 + i * 0.07))
                painter.save()
                painter.translate(cx, cy)
                painter.rotate(13)
                painter.translate(-cx, -cy)
                painter.drawEllipse(rect)
                painter.restore()
            painter.setPen(QPen(QColor(140, 88, 255, 125), 1))
            for i in range(8):
                painter.drawArc(QRectF(cx - radius * 1.1, cy - radius * 1.1, radius * 2.2, radius * 2.2),
                                i * 410, 520)
            painter.setPen(QPen(QColor(0, 125, 255, 130), 1))
            for i in range(12):
                x1 = cx + (i % 4 - 1.5) * radius * 0.38
                y1 = cy + ((i * 7) % 5 - 2) * radius * 0.28
                x2 = cx + (((i + 1) * 5) % 5 - 2) * radius * 0.35
                y2 = cy + (((i + 2) * 3) % 5 - 2) * radius * 0.30
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
                painter.setBrush(QColor(0, 245, 255, 180))
                painter.drawEllipse(QPointF(x1, y1), 2, 2)
            base_y = h * 0.84
            painter.setBrush(QColor(0, 50, 130, 70))
            painter.setPen(QPen(QColor(0, 125, 255, 170), 1))
            painter.drawEllipse(QPointF(cx, base_y), radius * 1.16, radius * 0.24)
            painter.setPen(QPen(QColor(0, 245, 255, 170), 2))
            painter.drawEllipse(QPointF(cx, base_y - 3), radius * 0.82, radius * 0.16)
            painter.setPen(QPen(QColor(132, 75, 255, 180), 1.4))
            painter.drawEllipse(QPointF(cx + 8, base_y - 1), radius * 0.58, radius * 0.11)
        finally:
            painter.end()


class WaveformWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(42)
        self._level = 0.12
        self._phase = 0.0
        self._values = [8, 14, 5, 18, 25, 12, 30, 16, 23, 11, 20, 26, 14, 19, 10, 23, 17, 28, 12, 20, 15, 24, 9, 18]

    def set_level(self, level: float) -> None:
        self._level = max(0.0, min(1.0, float(level)))
        self._phase = (self._phase + 0.35) % math.tau
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = self.width(), self.height()
            step = w / len(self._values)
            for i, value in enumerate(self._values):
                x = i * step + step / 2
                pulse = 0.35 + self._level * 1.25
                wave = 0.72 + 0.28 * math.sin(self._phase + i * 0.65)
                height = max(3.0, min(h - 4.0, value * pulse * wave))
                color = QColor(NEURAL_CYAN) if i < len(self._values) * 0.55 else QColor(NEURAL_PURPLE)
                color.setAlpha(225)
                painter.setPen(QPen(color, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawLine(QPointF(x, h / 2 - height / 2), QPointF(x, h / 2 + height / 2))
        finally:
            painter.end()


class NeuralButton(QPushButton):
    def __init__(self, text: str, icon: str = "", tone: str = "blue") -> None:
        super().__init__(f"{icon}  {text}" if icon else text)
        color = _tone_color(tone)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(46)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"""
            QPushButton {{
                background: rgba(4, 15, 38, 0.76);
                border: 1px solid {color};
                border-radius: 10px;
                color: {NEURAL_TEXT_PRIMARY};
                font-family: {MONO_FAMILY};
                font-size: 12px;
                font-weight: 900;
                padding: 10px 16px;
            }}
            QPushButton:hover {{
                background: rgba(8, 27, 63, 0.94);
                color: {color};
            }}
        """)


class NeuralResourceCard(QFrame):
    def __init__(self, title: str, value: str, detail: str = "", tone: str = "blue") -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(72)
        self._tone = tone
        color = _tone_color(tone)
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(5, 14, 35, 0.84);
                border: 1px solid rgba(47, 140, 255, 0.32);
                border-radius: 10px;
            }}
            QLabel {{ border: none; background: transparent; }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)
        icon = QLabel("▣")
        icon.setStyleSheet(f"color: {color}; font-family: {MONO_FAMILY}; font-size: 22px; font-weight: 900;")
        info = QVBoxLayout()
        info.setSpacing(4)
        row = QHBoxLayout()
        row.setSpacing(8)
        label = QLabel(title.upper())
        label.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {MONO_FAMILY}; font-size: 10px; font-weight: 800;")
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color: {NEURAL_BLUE}; font-family: {MONO_FAMILY}; font-size: 17px; font-weight: 900;")
        row.addWidget(label)
        row.addStretch(1)
        row.addWidget(self.value_label)
        self.detail_label = QLabel(detail)
        self.detail_label.setStyleSheet(f"color: {NEURAL_TEXT_PRIMARY}; font-family: {MONO_FAMILY}; font-size: 11px;")
        self.progress = ProgressBarWidget(72 if "CPU" in title.upper() else 13, tone)
        info.addLayout(row)
        if detail:
            info.addWidget(self.detail_label)
        info.addWidget(self.progress)
        lay.addWidget(icon)
        lay.addLayout(info, 1)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)
        try:
            self.progress.set_value(int(float(value.strip("%"))))
        except ValueError:
            pass


class NeuralAgentRow(QFrame):
    def __init__(self, name: str, status: str = "ACTIVE", tone: str = "green") -> None:
        super().__init__()
        self.setStyleSheet("QFrame { background: transparent; border: none; } QLabel { background: transparent; border: none; }")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 8)
        lay.setSpacing(10)
        color = _tone_color(tone)
        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color: {color}; font-size: 18px;")
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet(f"color: {NEURAL_TEXT_PRIMARY}; font-family: {MONO_FAMILY}; font-size: 13px; font-weight: 700;")
        self.status_label = QLabel(status)
        self.status_label.setStyleSheet(f"color: {color}; font-family: {MONO_FAMILY}; font-size: 10px; font-weight: 900;")
        lay.addWidget(self.dot)
        lay.addWidget(self.name_label)
        lay.addStretch(1)
        lay.addWidget(self.status_label)

    def set_status(self, status: str, tone: str = "green") -> None:
        color = _tone_color(tone)
        self.status_label.setText(status)
        self.status_label.setStyleSheet(f"color: {color}; font-family: {MONO_FAMILY}; font-size: 10px; font-weight: 900;")
        self.dot.setStyleSheet(f"color: {color}; font-size: 18px;")


class StatusChip(QFrame):
    def __init__(self, text: str, accent_text: str | None = None, tone: str = "green") -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        color = _tone_color(tone)
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(7, 23, 54, 0.82);
                border: 1px solid rgba(47, 140, 255, 0.48);
                border-radius: 10px;
            }}
            QLabel {{ border: none; background: transparent; }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(9)
        dot = QLabel("◇")
        dot.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: 900;")
        self.label = QLabel(text)
        self.label.setStyleSheet(f"color: {NEURAL_BLUE}; font-family: {MONO_FAMILY}; font-size: 12px; font-weight: 900;")
        self.accent_label = QLabel(accent_text or "")
        self.accent_label.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {MONO_FAMILY}; font-size: 9px; font-weight: 800;")
        lay.addWidget(dot)
        lay.addWidget(self.label)
        lay.addStretch(1)
        if accent_text:
            lay.addWidget(self.accent_label)

    def set_text(self, text: str) -> None:
        self.label.setText(text)

    def set_accent_text(self, text: str) -> None:
        self.accent_label.setText(text)

    def set_value(self, text: str) -> None:
        self.set_accent_text(text)


class NeuralCommandBar(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(92)
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(5, 12, 32, 0.95);
                border: 1px solid rgba(0, 245, 255, 0.78);
                border-radius: 20px;
            }}
            QTextEdit {{
                background: rgba(2, 7, 22, 0.88);
                border: none;
                border-radius: 13px;
                color: {NEURAL_TEXT_PRIMARY};
                font-family: {MONO_FAMILY};
                font-size: 15px;
                padding: 14px 18px;
            }}
        """)
        _glow(self, NEURAL_PURPLE, 34, 95)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(22, 16, 20, 16)
        lay.setSpacing(16)
        spark = QLabel("✦")
        spark.setStyleSheet(f"color: {NEURAL_BLUE}; font-size: 28px; border: none; background: transparent;")
        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("Type a command or ask anything...")
        self.input_box.setFixedHeight(58)
        self.clear_btn = QPushButton("⋮")
        self.send_btn = QPushButton("RUN")
        self.listen_btn = QPushButton("🎙")
        for button in (self.clear_btn, self.send_btn, self.listen_btn):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setFixedSize(42, 50)
        self.send_btn.setFixedSize(64, 50)
        self.listen_btn.setFixedSize(58, 58)
        self.clear_btn.setStyleSheet(f"background: transparent; border: none; color: {NEURAL_BLUE}; font-size: 24px;")
        self.send_btn.setStyleSheet(f"background: rgba(47,140,255,0.24); border: 1px solid rgba(47,140,255,0.55); border-radius: 12px; color: {NEURAL_CYAN}; font-family: {MONO_FAMILY}; font-size: 12px; font-weight: 900;")
        self.listen_btn.setStyleSheet(f"background: rgba(96,59,255,0.44); border: 1px solid rgba(168,85,247,0.95); border-radius: 29px; color: white; font-size: 24px;")
        lay.addWidget(spark)
        lay.addWidget(self.input_box, 1)
        lay.addWidget(self.send_btn)
        lay.addWidget(self.listen_btn)


class JarvisOrbPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(230)
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(4, 12, 31, 0.80);
                border: 1px solid rgba(47, 140, 255, 0.30);
                border-radius: 14px;
            }}
            QLabel {{ border: none; background: transparent; }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 16)
        lay.setSpacing(10)
        title = QLabel("JARVIS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {NEURAL_BLUE}; font-family: {MONO_FAMILY}; font-size: 24px; font-weight: 900;")
        online = QLabel("● ONLINE")
        online.setAlignment(Qt.AlignmentFlag.AlignCenter)
        online.setStyleSheet(f"color: {NEURAL_GREEN}; font-family: {MONO_FAMILY}; font-size: 11px; font-weight: 800;")
        self.orb = OrbWidget()
        voice = QLabel("VOICE STATUS")
        voice.setStyleSheet(f"color: {NEURAL_TEXT_MUTED}; font-family: {MONO_FAMILY}; font-size: 10px; font-weight: 900;")
        self.wave = WaveformWidget()
        self.voice_state = QLabel("LISTENING...")
        self.voice_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.voice_state.setStyleSheet(f"color: {NEURAL_TEXT_MUTED}; font-family: {MONO_FAMILY}; font-size: 10px; font-weight: 900; letter-spacing: 1px;")
        self.status = QLabel("NEURAL LINK")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet(f"color: {NEURAL_CYAN}; font-family: {MONO_FAMILY}; font-size: 10px; font-weight: 900;")
        lay.addWidget(title)
        lay.addWidget(online)
        lay.addWidget(self.orb, 1)
        lay.addWidget(voice)
        lay.addWidget(self.wave)
        lay.addWidget(self.voice_state)

    def set_state(self, text: str, color: str = NEURAL_CYAN) -> None:
        self.status.setText(text)
        self.voice_state.setText(text)
        self.voice_state.setStyleSheet(f"color: {color}; font-family: {MONO_FAMILY}; font-size: 10px; font-weight: 900; letter-spacing: 1px;")

    def set_voice_level(self, level: float) -> None:
        self.wave.set_level(level)
