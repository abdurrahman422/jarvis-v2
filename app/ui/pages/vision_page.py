from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services.terminal_service import SafeTerminalService
from app.ui.components import JarvisOrbPanel, ProgressBarWidget
from app.ui.theme import (
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
    NEURAL_RED,
    NEURAL_TEXT_MUTED,
    NEURAL_TEXT_PRIMARY,
    NEURAL_TEXT_SECONDARY,
)


class _TerminalInput(QLineEdit):
    def __init__(self, page: "VisionPage") -> None:
        super().__init__()
        self._page = page

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Up:
            self._page.recall_history(-1)
            return
        if event.key() == Qt.Key.Key_Down:
            self._page.recall_history(1)
            return
        super().keyPressEvent(event)


class VisionPage(QWidget):
    page_title = "Terminal"
    page_subtitle = "Execute safe Jarvis system commands."

    QUICK_COMMANDS = (
        ("System Info", "View system information", "systeminfo"),
        ("Clear Cache", "Clear app cache", "clear cache"),
        ("Neural Link Status", "Check neural connection", "neural link status"),
        ("Logs", "View system logs", "logs"),
        ("Diagnostics", "Run system diagnostics", "diagnostics"),
        ("Memory Clean", "Optimize memory usage", "memory clean"),
    )

    def __init__(self, controller=None) -> None:
        super().__init__()
        self.controller = controller
        self.terminal = SafeTerminalService(controller=controller)
        self._session_id = "Terminal 1"
        self._history: list[str] = []
        self._history_index = 0
        self._session_buffers = {
            "Terminal 1": self._initial_text(),
            "Terminal 2": self._initial_text(),
            "Terminal 3": self._initial_text(),
        }
        self.setObjectName("PageSurface")
        self._build_ui()
        self._start_snapshot_timer()

    def _build_ui(self) -> None:
        self.setStyleSheet(f"background: {BG_NEURAL_DEEP};")
        root = QHBoxLayout(self)
        root.setContentsMargins(22, 18, 10, 20)
        root.setSpacing(18)

        root.addWidget(self._left_panel(), 0)
        root.addWidget(self._terminal_panel(), 1)
        root.addWidget(self._right_panel(), 0)

        # Compatibility with older MainWindow OCR signal wiring.
        self.path_input = QLineEdit()
        self.path_input.hide()
        self.output = self.terminal_output
        self.pick_btn = QPushButton()
        self.capture_btn = QPushButton()
        self.ocr_last_capture_btn = QPushButton()
        for button in (self.pick_btn, self.capture_btn, self.ocr_last_capture_btn):
            button.hide()

    def _left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(292)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        title = QLabel("> TERMINAL")
        title.setStyleSheet(f"color: {NEURAL_TEXT_PRIMARY}; font-family: {FONT_DISPLAY}; font-size: 21px; font-weight: 900; letter-spacing: 0.4px;")
        subtitle = QLabel("> Execute commands and interact with the system.")
        subtitle.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {FONT_UI}; font-size: 13px; font-weight: 500;")
        lay.addWidget(title)
        lay.addWidget(subtitle)

        quick = self._panel()
        quick_lay = QVBoxLayout(quick)
        quick_lay.setContentsMargins(20, 18, 20, 18)
        quick_lay.setSpacing(10)
        quick_lay.addWidget(self._section_title("QUICK COMMANDS"))
        for label, detail, command in self.QUICK_COMMANDS:
            quick_lay.addWidget(self._quick_command(label, detail, command))
        lay.addWidget(quick)

        shortcuts = self._panel()
        short_lay = QVBoxLayout(shortcuts)
        short_lay.setContentsMargins(20, 18, 20, 18)
        short_lay.setSpacing(10)
        short_lay.addWidget(self._section_title("SHORTCUTS"))
        for key, action in (
            ("Ctrl + K", "Clear Terminal"),
            ("Ctrl + L", "Clear Screen"),
            ("Ctrl + Up", "Previous Command"),
            ("Ctrl + Down", "Next Command"),
            ("Ctrl + Enter", "Execute Command"),
        ):
            short_lay.addLayout(self._shortcut_row(key, action))
        lay.addWidget(shortcuts)
        lay.addStretch(1)
        return panel

    def _terminal_panel(self) -> QFrame:
        panel = self._panel()
        panel.setMinimumWidth(720)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(8)
        self.session_buttons: dict[str, QPushButton] = {}
        for session in ("Terminal 1", "Terminal 2", "Terminal 3"):
            button = QPushButton(session.upper())
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, name=session: self.switch_session(name))
            button.setStyleSheet(self._session_button_style())
            self.session_buttons[session] = button
            top.addWidget(button)
        self.session_buttons[self._session_id].setChecked(True)

        add_btn = QPushButton("+")
        add_btn.setFixedWidth(48)
        add_btn.setStyleSheet(self._session_button_style())
        add_btn.clicked.connect(lambda: self.append_terminal("Additional terminal slots are reserved for future sessions."))
        self.clear_btn = QPushButton("CLEAR")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setStyleSheet(self._ghost_button_style())
        self.clear_btn.clicked.connect(self.clear_terminal)
        top.addWidget(add_btn)
        top.addStretch(1)
        top.addWidget(self.clear_btn)
        lay.addLayout(top)

        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setObjectName("PlainLog")
        self.terminal_output.setText(self._session_buffers[self._session_id])
        self.terminal_output.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(1, 6, 18, 0.92);
                border: none;
                border-radius: 10px;
                color: {NEURAL_TEXT_PRIMARY};
                font-family: {FONT_MONO};
                font-size: 13px;
                padding: 18px;
            }}
        """)
        lay.addWidget(self.terminal_output, 1)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        self.command_input = _TerminalInput(self)
        self.command_input.setPlaceholderText("Type a command...")
        self.command_input.returnPressed.connect(self.execute_current_command)
        self.command_input.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(2, 7, 22, 0.92);
                border: 1px solid rgba(0, 245, 255, 0.72);
                border-radius: 10px;
                color: {NEURAL_TEXT_PRIMARY};
                font-family: {FONT_MONO};
                font-size: 16px;
                padding: 14px 18px;
            }}
            QLineEdit:focus {{
                border: 1px solid {NEURAL_CYAN};
            }}
        """)
        self.run_btn = QPushButton("RUN")
        self.run_btn.setFixedSize(70, 56)
        self.run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run_btn.setStyleSheet(self._run_button_style())
        self.run_btn.clicked.connect(self.execute_current_command)
        self.mic_btn = QPushButton("MIC")
        self.mic_btn.setFixedSize(70, 56)
        self.mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_btn.setStyleSheet(self._mic_button_style())
        self.mic_btn.clicked.connect(lambda: self.append_terminal("Voice terminal input is routed through the main dashboard microphone."))
        input_row.addWidget(self.command_input, 1)
        input_row.addWidget(self.run_btn)
        input_row.addWidget(self.mic_btn)
        lay.addLayout(input_row)
        return panel

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
        self.connection_value = QLabel("Unknown")
        info_lay.addLayout(self._metric_row("CPU USAGE", self.cpu_value))
        info_lay.addWidget(self.cpu_bar)
        info_lay.addLayout(self._metric_row("MEMORY USAGE", self.mem_value))
        info_lay.addWidget(self.mem_bar)
        info_lay.addLayout(self._metric_row("UPTIME", self.uptime_value))
        info_lay.addLayout(self._metric_row("CONNECTION", self.connection_value, NEURAL_GREEN))
        lay.addWidget(info)
        lay.addStretch(1)
        return right

    def execute_current_command(self) -> None:
        command = self.command_input.text().strip()
        if not command:
            return
        self.command_input.clear()
        self._history.append(command)
        self._history_index = len(self._history)

        if command.lower() in {"clear", "cls"}:
            self.clear_terminal()
            return

        self.append_terminal(f"\nCPA@neural> {command}", prompt=False)
        output = self.terminal.execute(command, session_id=self._session_id)
        if output:
            self.append_terminal(output, prompt=False)
        self.append_terminal("CPA@neural> ", prompt=False)
        self._sync_session_buffer()
        self._update_snapshot()

    def switch_session(self, session_id: str) -> None:
        self._sync_session_buffer()
        self._session_id = session_id
        for name, button in self.session_buttons.items():
            button.setChecked(name == session_id)
        self.terminal_output.setPlainText(self._session_buffers[session_id])
        self._scroll_to_end()

    def clear_terminal(self) -> None:
        text = self._initial_text()
        self.terminal.clear_session(self._session_id)
        self._session_buffers[self._session_id] = text
        self.terminal_output.setPlainText(text)
        self._scroll_to_end()

    def recall_history(self, direction: int) -> None:
        if not self._history:
            return
        self._history_index = max(0, min(len(self._history) - 1, self._history_index + direction))
        self.command_input.setText(self._history[self._history_index])
        self.command_input.setCursorPosition(len(self.command_input.text()))

    def append_terminal(self, text: str, prompt: bool = True) -> None:
        current = self.terminal_output.toPlainText()
        addition = text if not prompt else f"\n{text}"
        self.terminal_output.setPlainText(current.rstrip() + addition)
        self._scroll_to_end()
        self._sync_session_buffer()

    def _initial_text(self) -> str:
        banner = self.terminal.banner()
        return banner + "\nCPA@neural> "

    def _sync_session_buffer(self) -> None:
        if hasattr(self, "terminal_output"):
            self._session_buffers[self._session_id] = self.terminal_output.toPlainText()

    def _scroll_to_end(self) -> None:
        cursor = self.terminal_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.terminal_output.setTextCursor(cursor)

    def _start_snapshot_timer(self) -> None:
        self._snapshot_timer = QTimer(self)
        self._snapshot_timer.timeout.connect(self._update_snapshot)
        self._snapshot_timer.start(2000)
        self._update_snapshot()

    def _update_snapshot(self) -> None:
        snap = self.terminal.get_system_snapshot()
        cpu = int(snap.get("cpu_percent", 0))
        mem = int(snap.get("memory_percent", 0))
        self.cpu_value.setText(f"{cpu}%")
        self.cpu_bar.set_value(cpu)
        self.mem_value.setText(str(snap.get("memory_text", "unknown")))
        self.mem_bar.set_value(mem)
        self.uptime_value.setText(str(snap.get("uptime", "00:00:00")))
        connection = str(snap.get("connection", "Unknown"))
        self.connection_value.setText("Secure" if connection == "Online" else connection)
        self.connection_value.setStyleSheet(f"color: {NEURAL_GREEN if connection == 'Online' else NEURAL_RED}; font-family: {FONT_MONO}; font-size: 12px; font-weight: 900;")

    def _quick_command(self, title: str, detail: str, command: str) -> QPushButton:
        button = QPushButton(f"{title}\n{detail}")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda checked=False, cmd=command: self._run_quick(cmd))
        button.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                background: rgba(5, 18, 43, 0.82);
                border: 1px solid rgba(47, 140, 255, 0.36);
                border-radius: 7px;
                color: {NEURAL_TEXT_PRIMARY};
                font-family: {FONT_UI};
                font-size: 11px;
                font-weight: 800;
                padding: 10px 14px;
            }}
            QPushButton:hover {{
                border-color: {NEURAL_CYAN};
                background: rgba(7, 27, 62, 0.95);
            }}
        """)
        return button

    def _run_quick(self, command: str) -> None:
        self.command_input.setText(command)
        self.execute_current_command()

    def _shortcut_row(self, key: str, action: str) -> QHBoxLayout:
        row = QHBoxLayout()
        key_label = QLabel(key)
        key_label.setStyleSheet(f"""
            color: {NEURAL_BLUE};
            background: rgba(47, 140, 255, 0.10);
            border: 1px solid rgba(47, 140, 255, 0.24);
            border-radius: 5px;
            padding: 5px 8px;
            font-family: {FONT_MONO};
            font-size: 10px;
            font-weight: 900;
        """)
        action_label = QLabel(action)
        action_label.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {FONT_UI}; font-size: 10px;")
        row.addWidget(key_label)
        row.addWidget(action_label)
        row.addStretch(1)
        return row

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
        label.setStyleSheet(f"color: {NEURAL_CYAN}; font-family: {FONT_DISPLAY}; font-size: 13px; font-weight: 900; letter-spacing: 0.8px;")
        return label

    def _session_button_style(self) -> str:
        return f"""
            QPushButton {{
                background: rgba(5, 14, 35, 0.82);
                border: 1px solid rgba(47, 140, 255, 0.24);
                border-radius: 7px;
                color: {NEURAL_TEXT_SECONDARY};
                font-family: {FONT_DISPLAY};
                font-size: 12px;
                font-weight: 800;
                padding: 11px 18px;
            }}
            QPushButton:checked {{
                color: {NEURAL_TEXT_PRIMARY};
                border-top: 2px solid {NEURAL_CYAN};
            }}
            QPushButton:hover {{
                color: {NEURAL_CYAN};
                border-color: rgba(0, 245, 255, 0.45);
            }}
        """

    def _ghost_button_style(self) -> str:
        return f"""
            QPushButton {{
                background: transparent;
                border: 1px solid transparent;
                color: {NEURAL_TEXT_SECONDARY};
                font-family: {FONT_DISPLAY};
                font-size: 12px;
                font-weight: 900;
                padding: 8px 12px;
            }}
            QPushButton:hover {{
                color: {NEURAL_CYAN};
            }}
        """

    def _run_button_style(self) -> str:
        return f"""
            QPushButton {{
                background: rgba(47, 140, 255, 0.20);
                border: 1px solid rgba(47, 140, 255, 0.65);
                border-radius: 10px;
                color: {NEURAL_CYAN};
                font-family: {FONT_DISPLAY};
                font-size: 12px;
                font-weight: 900;
            }}
            QPushButton:hover {{
                background: rgba(47, 140, 255, 0.34);
            }}
        """

    def _mic_button_style(self) -> str:
        return f"""
            QPushButton {{
                background: rgba(168, 85, 247, 0.24);
                border: 1px solid rgba(168, 85, 247, 0.72);
                border-radius: 10px;
                color: {NEURAL_PURPLE};
                font-family: {FONT_DISPLAY};
                font-size: 12px;
                font-weight: 900;
            }}
            QPushButton:hover {{
                color: white;
                border-color: {NEURAL_CYAN};
            }}
        """
