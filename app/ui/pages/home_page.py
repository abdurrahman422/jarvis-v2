from __future__ import annotations

from datetime import datetime
from html import escape

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from app.ui.components import JarvisOrbPanel, NeuralAgentRow, NeuralBrainWidget, NeuralCommandBar, ProgressBarWidget
from app.ui.theme import (
    BG_NEURAL_CORE,
    BG_NEURAL_DEEP,
    BG_NEURAL_PANEL,
    FONT_DISPLAY,
    FONT_MONO,
    FONT_UI,
    MONO_FAMILY,
    NEURAL_BLUE,
    NEURAL_CYAN,
    NEURAL_GREEN,
    NEURAL_PURPLE,
    NEURAL_TEXT_MUTED,
    NEURAL_TEXT_PRIMARY,
    NEURAL_TEXT_SECONDARY,
)


class HomePage(QWidget):
    page_title = "Dashboard"
    page_subtitle = "Command center for Jarvis."

    def __init__(self, controller=None, get_setting=None) -> None:
        super().__init__()
        self.controller = controller
        self._get_setting = get_setting
        self.quick_buttons: list[QPushButton] = []
        self.setObjectName("PageSurface")
        self._build_ui()
        self._start_resource_timer()

    def _build_ui(self) -> None:
        self.setStyleSheet(f"background: {BG_NEURAL_DEEP};")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(22, 28, 10, 10)
        outer.setSpacing(18)

        outer.addWidget(self._left_rail(), 0)
        outer.addWidget(self._center_workspace(), 1)
        outer.addWidget(self._right_orb(), 0)

    def _left_rail(self) -> QWidget:
        rail = QWidget()
        rail.setFixedWidth(290)
        lay = QVBoxLayout(rail)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(18)

        lay.addWidget(self._section_title("SYSTEM CARDS"))
        self.cpu_card = self._resource_card("CPU", "N/A", "blue")
        self.ram_card = self._resource_card("RAM", "N/A", "blue")
        self.battery_card = self._resource_card("BATTERY", "N/A", "green")
        self.storage_card = self._resource_card("STORAGE", "N/A", "purple")
        lay.addWidget(self.cpu_card)
        lay.addWidget(self.ram_card)
        lay.addWidget(self.battery_card)
        lay.addWidget(self.storage_card)

        lay.addSpacing(8)
        lay.addWidget(self._section_title("ACTIVE AGENTS"))
        agents = self._panel()
        agents_lay = QVBoxLayout(agents)
        agents_lay.setContentsMargins(18, 10, 18, 10)
        agents_lay.setSpacing(0)
        self._agent_brain = NeuralAgentRow("Task Agent", "ACTIVE", "green")
        self._agent_file = NeuralAgentRow("File Agent", "ACTIVE", "green")
        self._agent_voice = NeuralAgentRow("Comm Agent", "IDLE", "purple")
        agents_lay.addWidget(self._agent_brain)
        agents_lay.addWidget(self._divider())
        agents_lay.addWidget(self._agent_file)
        agents_lay.addWidget(self._divider())
        agents_lay.addWidget(self._agent_voice)
        lay.addWidget(agents)

        lay.addSpacing(8)
        neural = self._panel()
        neural_lay = QVBoxLayout(neural)
        neural_lay.setContentsMargins(18, 14, 18, 12)
        neural_lay.setSpacing(8)
        top = QHBoxLayout()
        top.addWidget(self._section_title("NEURAL LINK"))
        arrow = QLabel(">")
        arrow.setStyleSheet(f"color: {NEURAL_BLUE}; font-family: {FONT_DISPLAY}; font-size: 20px;")
        top.addWidget(arrow)
        neural_lay.addLayout(top)
        neural_lay.addWidget(NeuralBrainWidget(), 1)
        secure = QLabel("SECURE")
        secure.setAlignment(Qt.AlignmentFlag.AlignRight)
        secure.setStyleSheet(f"color: {NEURAL_GREEN}; font-family: {FONT_MONO}; font-size: 10px; font-weight: 900; letter-spacing: 0.8px;")
        neural_lay.addWidget(secure)
        lay.addWidget(neural, 1)

        shield = self._panel(border="rgba(47, 140, 255, 0.65)")
        shield_lay = QHBoxLayout(shield)
        shield_lay.setContentsMargins(18, 12, 18, 12)
        shield_lay.setSpacing(12)
        shield_icon = QLabel("[]")
        shield_icon.setStyleSheet(f"color: {NEURAL_BLUE}; font-family: {FONT_MONO}; font-size: 18px; font-weight: 900;")
        shield_text = QLabel("NEURAL LINK SECURE\nENCRYPTION: AES-256")
        shield_text.setStyleSheet(f"color: {NEURAL_BLUE}; font-family: {FONT_DISPLAY}; font-size: 12px; font-weight: 800;")
        shield_lay.addWidget(shield_icon)
        shield_lay.addWidget(shield_text, 1)
        shield_lay.addWidget(QLabel(">"))
        lay.addWidget(shield)

        return rail

    def _center_workspace(self) -> QWidget:
        center = QFrame()
        center.setStyleSheet(f"""
            QFrame {{
                background: rgba(2, 7, 19, 0.48);
                border: 1px solid rgba(47, 140, 255, 0.20);
                border-radius: 14px;
            }}
        """)
        lay = QVBoxLayout(center)
        lay.setContentsMargins(22, 26, 22, 32)
        lay.setSpacing(18)

        tools = QGridLayout()
        tools.setHorizontalSpacing(22)
        tools.setVerticalSpacing(12)
        tools.addWidget(self._quick_button("Volume Down", "ভলিউম কম", "blue"), 0, 0)
        tools.addWidget(self._quick_button("Mute", "মিউট", "purple"), 0, 1)
        tools.addWidget(self._quick_button("Screenshot", "স্ক্রিনশট", "green"), 0, 2)
        tools.addWidget(self._quick_button("Downloads", "ডাউনলোড ফোল্ডার ওপেন", "blue", compact=True), 0, 3)
        lay.addLayout(tools)

        self.terminal_line = QLabel(self._terminal_line())
        self.terminal_line.setStyleSheet(f"color: {NEURAL_BLUE}; font-family: {FONT_MONO}; font-size: 15px; font-style: italic;")
        lay.addWidget(self.terminal_line)

        self.activity_card = self._activity_card()
        lay.addWidget(self.activity_card)

        self.log = QTextEdit()
        self.log.setObjectName("PlainLog")
        self.log.setReadOnly(True)
        self.log.setFixedHeight(150)
        self.log.setPlaceholderText("Command history")
        self.log.hide()
        lay.addWidget(self.log)

        lay.addStretch(1)

        actions = QHBoxLayout()
        actions.setSpacing(14)
        actions.addWidget(self._quick_button("YouTube", "ইউটিউব ওপেন", "blue", small=True))
        actions.addWidget(self._quick_button("Weather", "আবহাওয়া", "green", small=True))
        actions.addWidget(self._quick_button("Google Search", "গুগলে সার্চ করো Jarvis", "purple", small=True))
        actions.addWidget(self._quick_button("Desktop", "ডেক্সটপ ওপেন", "blue", small=True))
        actions.addStretch(1)
        lay.addLayout(actions)

        command_bar = NeuralCommandBar()
        self.input_box = command_bar.input_box
        self.input_box.setPlaceholderText("Type in the Jarvis chat box, not PowerShell terminal.")
        self.send_btn = command_bar.send_btn
        self.listen_btn = command_bar.listen_btn
        command_bar.clear_btn.clicked.connect(self.input_box.clear)
        lay.addWidget(command_bar)

        self.input_hint = QLabel("Type in the Jarvis chat box, not PowerShell terminal.")
        self.input_hint.setStyleSheet(f"color: {NEURAL_TEXT_MUTED}; font-family: {FONT_UI}; font-size: 12px;")
        lay.addWidget(self.input_hint)

        self.status = QLabel("Ready")
        self.status.hide()
        lay.addWidget(self.status)
        return center

    def _right_orb(self) -> QWidget:
        wrap = QWidget()
        wrap.setFixedWidth(260)
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 44, 0, 164)
        lay.setSpacing(0)
        self.orb = JarvisOrbPanel()
        lay.addWidget(self.orb, 1)
        return wrap

    def _activity_card(self) -> QFrame:
        card = self._panel(border="rgba(47, 140, 255, 0.44)")
        card.setMinimumHeight(170)
        card.setStyleSheet(card.styleSheet() + f"""
            QFrame {{
                border-left: 3px solid {NEURAL_CYAN};
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(28, 22, 24, 18)
        lay.setSpacing(12)
        top = QHBoxLayout()
        title = QLabel("LATEST COMMAND")
        title.setStyleSheet(f"color: {NEURAL_BLUE}; font-family: {FONT_DISPLAY}; font-size: 14px; font-weight: 900; letter-spacing: 0.8px;")
        self.activity_time = QLabel(datetime.now().strftime("%I:%M:%S %p").lstrip("0"))
        self.activity_time.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {FONT_MONO}; font-size: 10px;")
        ok = QLabel("OK")
        ok.setStyleSheet(f"color: {NEURAL_GREEN}; font-family: {FONT_MONO}; font-size: 11px; font-weight: 900;")
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(self.activity_time)
        top.addWidget(ok)
        self.activity_text = QLabel("No command yet.")
        self.activity_text.setWordWrap(True)
        self.activity_text.setStyleSheet(f"color: {NEURAL_TEXT_PRIMARY}; font-family: {FONT_UI}; font-size: 19px; font-weight: 600; font-style: italic;")
        self.activity_status = QLabel("STATUS: Ready for text, voice, and system actions.")
        self.activity_status.setStyleSheet(f"""
            color: {NEURAL_BLUE};
            background: rgba(47, 140, 255, 0.12);
            border: 1px solid rgba(47, 140, 255, 0.34);
            border-radius: 7px;
            padding: 10px 12px;
            font-family: {FONT_MONO};
            font-size: 13px;
            font-weight: 800;
        """)
        lay.addLayout(top)
        lay.addWidget(self.activity_text)
        lay.addWidget(self.activity_status, alignment=Qt.AlignmentFlag.AlignLeft)
        meta = QHBoxLayout()
        meta.setSpacing(10)
        self.route_kind_label = self._meta_chip("ROUTE", "-")
        self.action_label = self._meta_chip("ACTION", "-")
        self.success_label = self._meta_chip("RESULT", "READY")
        meta.addWidget(self.route_kind_label)
        meta.addWidget(self.action_label)
        meta.addWidget(self.success_label)
        meta.addStretch(1)
        lay.addLayout(meta)
        return card

    def _resource_card(self, title: str, value: str, tone: str) -> QFrame:
        card = self._panel()
        card.setFixedHeight(86)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 14, 18, 12)
        lay.setSpacing(8)
        row = QHBoxLayout()
        icon = QLabel("[#]")
        icon.setStyleSheet(f"color: {NEURAL_BLUE}; font-family: {FONT_MONO}; font-size: 18px; font-weight: 900;")
        label = QLabel(title)
        label.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {FONT_DISPLAY}; font-size: 10px; font-weight: 800; letter-spacing: 0.7px;")
        value_label = QLabel(value)
        value_label.setObjectName("value")
        value_label.setStyleSheet(f"color: {NEURAL_BLUE}; font-family: {FONT_MONO}; font-size: 15px; font-weight: 900;")
        row.addWidget(icon)
        row.addWidget(label)
        row.addStretch(1)
        row.addWidget(value_label)
        progress = ProgressBarWidget(int(value.strip("%")) if value.endswith("%") else 0, tone)
        progress.setObjectName("progress")
        lay.addLayout(row)
        lay.addWidget(progress)
        card.value_label = value_label
        card.progress = progress
        return card

    def _tool_button(self, text: str, tone: str, compact: bool = False, small: bool = False) -> QPushButton:
        color = {"green": NEURAL_GREEN, "purple": NEURAL_PURPLE}.get(tone, NEURAL_BLUE)
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(48 if small else 58)
        if compact:
            btn.setFixedWidth(150)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(5, 14, 35, 0.82);
                border: 1px solid {color};
                border-radius: 10px;
                color: {NEURAL_TEXT_PRIMARY};
                font-family: {FONT_DISPLAY};
                font-size: {11 if small else 13}px;
                font-weight: 900;
                padding: 10px 18px;
            }}
            QPushButton:hover {{
                background: rgba(10, 24, 55, 0.95);
                color: {color};
            }}
        """)
        return btn

    def _quick_button(self, text: str, command: str, tone: str, compact: bool = False, small: bool = False) -> QPushButton:
        btn = self._tool_button(text, tone, compact=compact, small=small)
        btn.setToolTip(command)
        btn.setProperty("command", command)
        self.quick_buttons.append(btn)
        return btn

    def _meta_chip(self, label: str, value: str) -> QLabel:
        chip = QLabel(f"{label}: {value}")
        chip.setStyleSheet(f"""
            color: {NEURAL_CYAN};
            background: rgba(0, 245, 255, 0.07);
            border: 1px solid rgba(0, 245, 255, 0.18);
            border-radius: 7px;
            padding: 7px 9px;
            font-family: {FONT_MONO};
            font-size: 11px;
            font-weight: 900;
        """)
        return chip

    def _panel(self, border: str = "rgba(47, 140, 255, 0.34)") -> QFrame:
        panel = QFrame()
        panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        panel.setStyleSheet(f"""
            QFrame {{
                background: rgba(5, 14, 35, 0.72);
                border: 1px solid {border};
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
        label.setStyleSheet(f"color: {NEURAL_BLUE}; font-family: {FONT_DISPLAY}; font-size: 13px; font-weight: 900; letter-spacing: 0.9px;")
        return label

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: rgba(47, 140, 255, 0.16); border: none;")
        return line

    def _terminal_line(self) -> str:
        return f"[{datetime.now().strftime('%I:%M:%S %p').lstrip('0')}] CPA Engine v1.0 connected to Windows Kernel."

    def _start_resource_timer(self) -> None:
        self._resource_timer = QTimer(self)
        self._resource_timer.timeout.connect(self._update_resources)
        self._resource_timer.start(2500)
        self._update_resources()

    def _update_resources(self) -> None:
        self.terminal_line.setText(self._terminal_line())
        self.activity_time.setText(datetime.now().strftime("%I:%M:%S %p").lstrip("0"))
        try:
            import psutil

            cpu = int(psutil.cpu_percent(interval=None))
            mem = psutil.virtual_memory()
            ram = int(mem.percent)
            self.cpu_card.value_label.setText(f"{cpu}%")
            self.cpu_card.progress.set_value(cpu)
            self.ram_card.value_label.setText(f"{ram}%")
            self.ram_card.progress.set_value(ram)
            battery = psutil.sensors_battery()
            if battery:
                battery_value = int(battery.percent)
                self.battery_card.value_label.setText(f"{battery_value}%")
                self.battery_card.progress.set_value(battery_value)
            else:
                self.battery_card.value_label.setText("N/A")
            import shutil
            from pathlib import Path

            usage = shutil.disk_usage(Path.home().anchor)
            storage = int((usage.used / usage.total) * 100) if usage.total else 0
            self.storage_card.value_label.setText(f"{storage}%")
            self.storage_card.progress.set_value(storage)
        except Exception:
            self.cpu_card.value_label.setText("N/A")
            self.ram_card.value_label.setText("N/A")
            self.battery_card.value_label.setText("N/A")
            self.storage_card.value_label.setText("N/A")

    def append_log(self, text: str) -> None:
        self.log.show()
        self.log.append(text)
        if text.startswith("You:"):
            self.activity_text.setText(f'"{text[4:].strip()}"')
            self.activity_status.setText("STATUS: Command queued for Jarvis.")
        elif text.startswith("Jarvis:") or text.startswith("JARVIS:"):
            self.activity_status.setText(f"STATUS: {text.split(':', 1)[1].strip()}")

    def set_command_result(self, payload: dict) -> None:
        recognized = str(payload.get("recognized_text") or payload.get("heard") or "")
        response = str(payload.get("response") or "")
        route = str(payload.get("type") or payload.get("intent") or "-")
        action = str(payload.get("action") or "-")
        success = payload.get("success")
        self.activity_text.setText(f'"{recognized}"' if recognized else "Command completed.")
        self.activity_status.setText(f"RESPONSE: {response}" if response else "RESPONSE: -")
        self.route_kind_label.setText(f"ROUTE: {route}")
        self.action_label.setText(f"ACTION: {action}")
        if success is True:
            self.success_label.setText("RESULT: OK")
        elif success is False:
            self.success_label.setText("RESULT: ERROR")
        else:
            self.success_label.setText("RESULT: DONE")

    def append_search_results(self, payload: dict) -> None:
        self.log.show()
        query = escape(str(payload.get("query") or payload.get("search_query") or ""))
        summary = escape(str(payload.get("response") or ""))
        search_url = escape(str(payload.get("search_url") or ""))
        rows = [
            "<div style='margin-top:8px; padding:10px; border:1px solid rgba(47,140,255,0.45); border-radius:6px;'>",
            f"<div style='font-weight:700; color:#00f5ff;'>Search: {query}</div>",
            f"<div style='margin-top:4px; color:#e5edf7;'>Answer: {summary}</div>",
        ]
        if search_url:
            rows.append(f"<div style='margin-top:4px;'><a href='{search_url}'>Open in browser</a></div>")
        results = payload.get("results") or []
        if results:
            rows.append("<div style='margin-top:8px; font-weight:700;'>Results</div>")
        for index, item in enumerate(results, start=1):
            title = escape(str(item.get("title") or "Untitled"))
            snippet = escape(str(item.get("snippet") or ""))
            url = escape(str(item.get("url") or ""))
            rows.append("<div style='margin-top:8px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.12);'>")
            rows.append(f"<div style='font-weight:700;'>{index}. {title}</div>")
            if snippet:
                rows.append(f"<div style='color:#b8c7d9;'>{snippet}</div>")
            if url:
                rows.append(f"<div><a href='{url}'>{url}</a></div>")
            rows.append("</div>")
        rows.append("</div>")
        self.log.append("".join(rows))
        self.activity_status.setText(f"STATUS: Showing web search results for {query}")

    def set_orb_state(self, state: str) -> None:
        colors = {
            "idle": NEURAL_CYAN,
            "thinking": NEURAL_PURPLE,
            "listening": NEURAL_GREEN,
        }
        if hasattr(self.orb, "set_state"):
            self.orb.set_state(state.upper(), colors.get(state, NEURAL_CYAN))

    def set_voice_active(self, active: bool) -> None:
        self.set_orb_state("listening" if active else "idle")
        self._agent_voice.set_status("LISTENING" if active else "IDLE", "cyan" if active else "purple")

    def set_voice_level(self, level: float) -> None:
        if hasattr(self.orb, "set_voice_level"):
            self.orb.set_voice_level(level)
