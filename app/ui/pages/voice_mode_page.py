from __future__ import annotations

import math
import random
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.ui.theme import (
    BG_NEURAL_CORE,
    BG_NEURAL_DEEP,
    FONT_DISPLAY,
    FONT_MONO,
    FONT_UI,
    NEURAL_BLUE,
    NEURAL_CYAN,
    NEURAL_GREEN,
    NEURAL_PURPLE,
    NEURAL_RED,
    NEURAL_TEXT_MUTED,
    NEURAL_TEXT_PRIMARY,
    NEURAL_TEXT_SECONDARY,
)


class ParticleBulbWidget(QWidget):
    """Pseudo-3D Jarvis voice orb built from small glowing particles."""

    STATE_COLORS = {
        "Idle": QColor(NEURAL_CYAN),
        "Ready": QColor(NEURAL_CYAN),
        "Listening": QColor(NEURAL_GREEN),
        "Processing": QColor(NEURAL_PURPLE),
        "Speaking": QColor(NEURAL_CYAN),
        "Error": QColor(NEURAL_RED),
    }

    def __init__(self, particle_count: int = 500) -> None:
        super().__init__()
        self.setMinimumSize(560, 520)
        self._state = "Idle"
        self._transcript = ""
        self._response_preview = ""
        self._level = 0.08
        self._last_real_level_at = 0.0
        self._phase = 0.0
        self._particles = self._make_particles(particle_count)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def set_state(self, state: str) -> None:
        self._state = state or "Idle"
        self.update()

    def set_level(self, level: float) -> None:
        self._level = max(0.0, min(1.0, float(level)))
        self._last_real_level_at = time.monotonic()
        self.update()

    def set_transcript(self, text: str) -> None:
        self._transcript = (text or "").strip()
        self.update()

    def set_response_preview(self, text: str) -> None:
        self._response_preview = (text or "").strip()
        self.update()

    def _make_particles(self, particle_count: int) -> list[tuple[float, float, float, float, float]]:
        rng = random.Random(42690)
        particles: list[tuple[float, float, float, float, float]] = []
        sphere_count = max(380, int(particle_count * 0.86))
        for _ in range(sphere_count):
            # Fibonacci-ish distribution with a little jitter keeps the orb rich
            # without clumping into visible bands.
            z = rng.uniform(-0.92, 0.92)
            theta = rng.uniform(0, math.tau)
            radius = math.sqrt(max(0.0, 1.0 - z * z))
            x = radius * math.cos(theta)
            y = radius * math.sin(theta) * 0.94
            shell = 0.72 + rng.random() * 0.34
            particles.append((x * shell, y * shell, z * shell, rng.random(), rng.uniform(0.65, 1.25)))

        neck_count = particle_count - sphere_count
        for _ in range(max(0, neck_count)):
            theta = rng.uniform(0, math.tau)
            ring = rng.choice((0.24, 0.36, 0.50, 0.68))
            x = math.cos(theta) * ring
            z = math.sin(theta) * ring * 0.72
            y = rng.uniform(0.80, 1.20)
            particles.append((x, y, z, rng.random(), rng.uniform(0.55, 1.0)))
        return particles[:particle_count]

    def _tick(self) -> None:
        self._phase = (self._phase + 0.018) % math.tau
        self.update()

    def _effective_level(self) -> float:
        if time.monotonic() - self._last_real_level_at < 0.7:
            return self._level
        if self._state == "Listening":
            return 0.22 + 0.18 * (math.sin(self._phase * 5.5) + 1.0) / 2.0
        if self._state == "Speaking":
            return 0.18 + 0.22 * (math.sin(self._phase * 7.0) + 1.0) / 2.0
        if self._state == "Processing":
            return 0.16
        return 0.07

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = self.width(), self.height()
            self._paint_background(painter, w, h)
            self._paint_bulb(painter, w, h)
            self._paint_center_text(painter, w, h)
        finally:
            painter.end()

    def _paint_background(self, painter: QPainter, w: int, h: int) -> None:
        bg = QLinearGradient(0, 0, w, h)
        bg.setColorAt(0, QColor(2, 7, 19))
        bg.setColorAt(0.55, QColor(4, 9, 24))
        bg.setColorAt(1, QColor(12, 8, 32))
        painter.fillRect(self.rect(), bg)

        cx, cy = w / 2, h * 0.49
        radial = QRadialGradient(QPointF(cx, cy), min(w, h) * 0.52)
        radial.setColorAt(0.0, QColor(0, 245, 255, 32))
        radial.setColorAt(0.45, QColor(47, 140, 255, 18))
        radial.setColorAt(0.76, QColor(168, 85, 247, 18))
        radial.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(radial)
        painter.drawEllipse(QPointF(cx, cy), min(w, h) * 0.52, min(w, h) * 0.43)

        painter.setPen(QPen(QColor(0, 245, 255, 30), 1))
        for i in range(7):
            y = h * (0.16 + i * 0.095)
            painter.drawLine(QPointF(w * 0.16, y), QPointF(w * 0.84, y + math.sin(self._phase + i) * 8))

    def _paint_bulb(self, painter: QPainter, w: int, h: int) -> None:
        cx, cy = w / 2, h * 0.46
        base_radius = min(w * 0.31, h * 0.31)
        level = self._effective_level()
        state_color = self.STATE_COLORS.get(self._state, QColor(NEURAL_CYAN))
        pulse = 1.0 + level * 0.18
        spin = self._phase * (1.8 if self._state == "Processing" else 0.68)
        tilt = math.sin(self._phase * 0.7) * 0.14

        self._paint_glow_rings(painter, cx, cy, base_radius, state_color, level)

        projected: list[tuple[float, float, float, float, QColor]] = []
        sin_y, cos_y = math.sin(spin), math.cos(spin)
        sin_x, cos_x = math.sin(tilt), math.cos(tilt)
        for x, y, z, seed, size in self._particles:
            motion = level * 0.075 * math.sin(self._phase * (2.2 + seed) + seed * 18.0)
            px = x * (1.0 + motion)
            py = y * (1.0 + motion * 0.55)
            pz = z * (1.0 + motion)

            rx = px * cos_y - pz * sin_y
            rz = px * sin_y + pz * cos_y
            ry = py * cos_x - rz * sin_x
            rz = py * sin_x + rz * cos_x

            perspective = 1.0 / (1.95 - rz * 0.50)
            projection_scale = 1.45
            sx = cx + rx * base_radius * perspective * pulse * projection_scale
            sy = cy + ry * base_radius * perspective * pulse * projection_scale
            depth = max(0.0, min(1.0, (rz + 1.15) / 2.3))
            alpha = int(82 + 150 * depth)
            if self._state == "Error":
                color = QColor(255, 220, 220, alpha)
            else:
                color = QColor(255, 255, 255, alpha)
            projected.append((depth, sx, sy, size * (0.95 + depth * 1.25), perspective, color))

        projected.sort(key=lambda item: item[0])
        for depth, sx, sy, dot_size, perspective, color in projected:
            glow_alpha = int(color.alpha() * (0.20 + level * 0.45))
            glow_color = QColor(state_color)
            glow_color.setAlpha(glow_alpha)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow_color)
            painter.drawEllipse(QPointF(sx, sy), dot_size * 2.3, dot_size * 2.3)
            painter.setBrush(color)
            painter.drawEllipse(QPointF(sx, sy), dot_size, dot_size)

        self._paint_base(painter, cx, cy + base_radius * 1.08, base_radius, state_color, level)

    def _paint_glow_rings(self, painter: QPainter, cx: float, cy: float, radius: float, color: QColor, level: float) -> None:
        for i in range(5):
            alpha = int(36 - i * 5 + level * 34)
            ring = QColor(color)
            ring.setAlpha(max(8, alpha))
            painter.setPen(QPen(ring, 1.0 + i * 0.22))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            rect = QRectF(cx - radius * (1.0 + i * 0.09), cy - radius * (0.82 + i * 0.06), radius * (2.0 + i * 0.18), radius * (1.64 + i * 0.12))
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(-13 + math.sin(self._phase + i) * 4)
            painter.translate(-cx, -cy)
            painter.drawEllipse(rect)
            painter.restore()

        purple = QColor(NEURAL_PURPLE)
        purple.setAlpha(42 + int(level * 45))
        painter.setPen(QPen(purple, 1.2))
        for i in range(4):
            rect = QRectF(cx - radius * 1.12, cy - radius * 1.02, radius * 2.24, radius * 2.04)
            painter.drawArc(rect, int((self._phase * 1600 + i * 1250) % 5760), 820)

    def _paint_base(self, painter: QPainter, cx: float, base_y: float, radius: float, color: QColor, level: float) -> None:
        painter.setBrush(QColor(0, 45, 120, 82))
        ring = QColor(color)
        ring.setAlpha(135 + int(level * 80))
        painter.setPen(QPen(ring, 1.5))
        painter.drawEllipse(QPointF(cx, base_y), radius * 0.92, radius * 0.17)
        painter.setPen(QPen(QColor(NEURAL_BLUE), 1.2))
        painter.drawEllipse(QPointF(cx, base_y + radius * 0.07), radius * 0.60, radius * 0.09)
        painter.setPen(QPen(QColor(NEURAL_PURPLE), 1.1))
        painter.drawEllipse(QPointF(cx, base_y + radius * 0.11), radius * 0.42, radius * 0.06)

    def _paint_center_text(self, painter: QPainter, w: int, h: int) -> None:
        text = self._transcript.strip()
        if not text:
            return

        max_width = min(360, int(w * 0.55))
        rect = QRectF((w - max_width) / 2, h * 0.40, max_width, 92)
        path = QPainterPath()
        path.addRoundedRect(rect, 18, 18)
        painter.setPen(QPen(QColor(0, 245, 255, 85), 1))
        painter.setBrush(QColor(2, 8, 22, 182))
        painter.drawPath(path)

        font = QFont()
        font.setFamilies([FONT_UI.replace('"', "").split(",")[0]])
        font.setPointSize(13)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(NEURAL_TEXT_PRIMARY))
        painter.drawText(rect.adjusted(18, 12, -18, -12), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)


class VoiceModePage(QWidget):
    back_requested = Signal()
    page_title = "Voice Mode"
    page_subtitle = "Live speech capture and response."

    def __init__(self) -> None:
        super().__init__()
        self._state = "Idle"
        self.setObjectName("PageSurface")
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(f"background: {BG_NEURAL_DEEP};")
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        top = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        eyebrow = QLabel("VOICE COMMAND")
        eyebrow.setStyleSheet(f"color: {NEURAL_CYAN}; font-family: {FONT_DISPLAY}; font-size: 11px; font-weight: 900; letter-spacing: 1.4px;")
        title = QLabel("JARVIS LISTENING CORE")
        title.setStyleSheet(f"color: {NEURAL_TEXT_PRIMARY}; font-family: {FONT_DISPLAY}; font-size: 25px; font-weight: 900; letter-spacing: 0.4px;")
        subtitle = QLabel("Speak naturally. Jarvis will transcribe, process, and reply.")
        subtitle.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {FONT_UI}; font-size: 13px;")
        title_box.addWidget(eyebrow)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        self.state_label = QLabel("IDLE")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setFixedHeight(42)
        self.state_label.setMinimumWidth(140)
        self.state_label.setStyleSheet(self._state_badge_style(NEURAL_CYAN))

        self.back_btn = QPushButton("Back")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setFixedHeight(42)
        self.back_btn.setStyleSheet(self._button_style())
        self.back_btn.clicked.connect(self.back_requested.emit)

        top.addLayout(title_box, 1)
        top.addWidget(self.state_label)
        top.addWidget(self.back_btn)
        root.addLayout(top)

        stage = QFrame()
        stage.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        stage.setStyleSheet(f"""
            QFrame {{
                background: rgba(2, 7, 19, 0.74);
                border: 1px solid rgba(0, 245, 255, 0.22);
                border-radius: 18px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        stage_lay = QVBoxLayout(stage)
        stage_lay.setContentsMargins(18, 18, 18, 18)
        stage_lay.setSpacing(12)
        self.bulb = ParticleBulbWidget(500)
        stage_lay.addWidget(self.bulb, 1)

        self.transcript_label = QLabel("Recognized text will appear here.")
        self.transcript_label.setWordWrap(True)
        self.transcript_label.setStyleSheet(f"""
            color: {NEURAL_TEXT_SECONDARY};
            background: rgba(5, 14, 35, 0.52);
            border: 1px solid rgba(47, 140, 255, 0.18);
            border-radius: 12px;
            padding: 10px 14px;
            font-family: {FONT_UI};
            font-size: 13px;
            font-weight: 600;
        """)
        stage_lay.addWidget(self.transcript_label)

        self.response_label = QLabel("")
        self.response_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.response_label.setWordWrap(True)
        self.response_label.setMinimumHeight(70)
        self.response_label.setStyleSheet(f"""
            color: {NEURAL_TEXT_PRIMARY};
            background: rgba(5, 14, 35, 0.72);
            border: 1px solid rgba(47, 140, 255, 0.24);
            border-radius: 14px;
            padding: 14px 18px;
            font-family: {FONT_UI};
            font-size: 15px;
            font-weight: 600;
        """)
        stage_lay.addWidget(self.response_label)
        root.addWidget(stage, 1)

        bottom = QHBoxLayout()
        self.helper_label = QLabel("Ready for voice input.")
        self.helper_label.setStyleSheet(f"color: {NEURAL_TEXT_MUTED}; font-family: {FONT_MONO}; font-size: 11px; font-weight: 700; letter-spacing: 0.8px;")
        bottom.addWidget(self.helper_label)
        bottom.addStretch(1)
        root.addLayout(bottom)

    def reset_for_listening(self) -> None:
        self.response_label.clear()
        self.transcript_label.setText("Recognized text will appear here.")
        self.bulb.set_transcript("")
        self.bulb.set_response_preview("")
        self.set_state("Listening")
        self.helper_label.setText("Microphone active. Speak now.")

    def set_level(self, level: float) -> None:
        self.bulb.set_level(level)

    def set_transcript(self, text: str) -> None:
        self.bulb.set_transcript(text)
        self.transcript_label.setText(text or "Recognized text will appear here.")
        self.helper_label.setText("Transcript captured.")

    def set_state(self, state: str) -> None:
        self._state = state
        normalized = state or "Idle"
        color = {
            "Idle": NEURAL_CYAN,
            "Ready": NEURAL_CYAN,
            "Listening": NEURAL_GREEN,
            "Processing": NEURAL_PURPLE,
            "Speaking": NEURAL_CYAN,
            "Error": NEURAL_RED,
        }.get(normalized, NEURAL_CYAN)
        self.state_label.setText(normalized.upper())
        self.state_label.setStyleSheet(self._state_badge_style(color))
        self.bulb.set_state(normalized)
        if normalized == "Processing":
            self.helper_label.setText("Processing command...")
        elif normalized == "Speaking":
            self.helper_label.setText("Jarvis is replying.")
        elif normalized in {"Ready", "Idle"}:
            self.helper_label.setText("Ready for voice input.")

    def set_response(self, text: str) -> None:
        self.response_label.setText(text)
        self.bulb.set_response_preview(text)

    def show_error(self, text: str) -> None:
        self._state = "Error"
        self.set_state("Error")
        self.response_label.setText(text)
        self.helper_label.setText("Voice command ended with an error.")

    def mark_ready(self) -> None:
        self.set_state("Ready")

    def _state_badge_style(self, color: str) -> str:
        return f"""
            color: {color};
            background: rgba(5, 14, 35, 0.78);
            border: 1px solid {color};
            border-radius: 12px;
            padding: 8px 14px;
            font-family: {FONT_DISPLAY};
            font-size: 12px;
            font-weight: 900;
            letter-spacing: 1.1px;
        """

    def _button_style(self) -> str:
        return f"""
            QPushButton {{
                background: rgba(47, 140, 255, 0.10);
                border: 1px solid rgba(47, 140, 255, 0.38);
                border-radius: 12px;
                color: {NEURAL_TEXT_PRIMARY};
                font-family: {FONT_DISPLAY};
                font-size: 12px;
                font-weight: 800;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                color: {NEURAL_CYAN};
                border-color: rgba(0, 245, 255, 0.70);
                background: rgba(0, 245, 255, 0.12);
            }}
        """
