from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QVBoxLayout, QWidget

from app.ui.theme import BG_NEURAL_DEEP


class SchedulerPage(QWidget):
    page_title = "Scheduler"
    page_subtitle = "Alarms, focus timers and task list."

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("PageSurface")
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(f"background: {BG_NEURAL_DEEP};")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 28, 28, 28)
        lay.setSpacing(12)
        title = QLabel("SCHEDULER")
        title.setObjectName("NeuralPageTitle")
        lay.addWidget(title)

        alarm_row = QHBoxLayout()
        self.alarm_title_input = QLineEdit()
        self.alarm_title_input.setPlaceholderText("Alarm title")
        self.alarm_time_input = QLineEdit()
        self.alarm_time_input.setPlaceholderText("HH:MM")
        self.alarm_recurrence_input = QLineEdit("none")
        self.add_alarm_btn = QPushButton("Add")
        self.add_alarm_btn.setObjectName("NeuralPrimaryButton")
        alarm_row.addWidget(self.alarm_title_input)
        alarm_row.addWidget(self.alarm_time_input)
        alarm_row.addWidget(self.alarm_recurrence_input)
        alarm_row.addWidget(self.add_alarm_btn)
        lay.addLayout(alarm_row)

        self.listing = QListWidget()
        lay.addWidget(self.listing, 1)
        alarm_actions = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.delete_alarm_btn = QPushButton("Delete")
        self.done_alarm_btn = QPushButton("Done")
        for btn in (self.refresh_btn, self.delete_alarm_btn, self.done_alarm_btn):
            btn.setObjectName("NeuralSecondaryButton")
            alarm_actions.addWidget(btn)
        lay.addLayout(alarm_actions)

        focus_row = QHBoxLayout()
        self.focus_input = QLineEdit("25")
        self.start_focus_btn = QPushButton("Start Focus")
        self.start_focus_btn.setObjectName("NeuralSecondaryButton")
        focus_row.addWidget(self.focus_input)
        focus_row.addWidget(self.start_focus_btn)
        lay.addLayout(focus_row)

        task_row = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Task")
        self.add_task_btn = QPushButton("Add Task")
        self.list_task_btn = QPushButton("List Tasks")
        self.add_task_btn.setObjectName("NeuralPrimaryButton")
        self.list_task_btn.setObjectName("NeuralSecondaryButton")
        task_row.addWidget(self.task_input)
        task_row.addWidget(self.add_task_btn)
        task_row.addWidget(self.list_task_btn)
        lay.addLayout(task_row)
        self.task_listing = QListWidget()
        lay.addWidget(self.task_listing, 1)
