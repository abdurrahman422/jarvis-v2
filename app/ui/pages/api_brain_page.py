from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.ui.components import NeuralCommandBar
from app.ui.theme import BG_NEURAL_DEEP, MONO_FAMILY, NEURAL_TEXT_PRIMARY, NEURAL_TEXT_SECONDARY


class ApiBrainPage(QWidget):
    settings_changed = Signal()

    page_title = "Offline Brain"
    page_subtitle = "Local rules, optional trained Qwen, and offline fallback."

    def __init__(self, get_setting=None, set_setting=None, test_callback=None) -> None:
        super().__init__()
        self._get_setting = get_setting
        self._set_setting = set_setting
        self._test_callback = test_callback
        self.setObjectName("PageSurface")
        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet(f"background: {BG_NEURAL_DEEP};")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 14, 14, 10)
        outer.setSpacing(12)

        title = QLabel("OFFLINE BRAIN MANAGER")
        title.setStyleSheet(
            f"color: {NEURAL_TEXT_PRIMARY}; font-family: {MONO_FAMILY}; font-size: 26px; font-weight: 900;"
        )
        subtitle = QLabel("Jarvis is running locally: rules/tools -> trained Qwen -> local fallback.")
        subtitle.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {MONO_FAMILY}; font-size: 13px;")

        status = QLabel(
            "OFFLINE_MODE=false by default\n"
            "Google Speech Recognition is used for microphone commands.\n"
            "Set QWEN_LORA_PATH in .env to enable optional local brain models."
        )
        status.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        status.setWordWrap(True)
        status.setStyleSheet(
            f"color: {NEURAL_TEXT_PRIMARY}; font-family: {MONO_FAMILY}; font-size: 14px; line-height: 1.5;"
        )

        outer.addWidget(title)
        outer.addWidget(subtitle)
        outer.addWidget(status, 1)

        command = NeuralCommandBar()
        self.input_box = command.input_box
        self.send_btn = command.send_btn
        self.listen_btn = command.listen_btn
        self.clear_btn = command.clear_btn
        self.clear_btn.clicked.connect(self.input_box.clear)
        self.send_btn.clicked.connect(self._run_manager_command)
        command.setFixedHeight(72)
        self.input_box.setFixedHeight(44)
        self.clear_btn.setFixedSize(36, 40)
        self.send_btn.setFixedSize(58, 40)
        self.listen_btn.setFixedSize(46, 46)
        outer.addWidget(command)

    def _run_manager_command(self) -> None:
        text = self.input_box.toPlainText().strip()
        if self._test_callback is not None:
            self._test_callback(text or "offline brain status")

    def refresh(self) -> None:
        return
