from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.components import JarvisOrbPanel, ProgressBarWidget
from app.ui.theme import (
    BG_NEURAL_DEEP,
    MONO_FAMILY,
    NEURAL_BLUE,
    NEURAL_CYAN,
    NEURAL_GREEN,
    NEURAL_PURPLE,
    NEURAL_TEXT_MUTED,
    NEURAL_TEXT_PRIMARY,
    NEURAL_TEXT_SECONDARY,
)


class AutomationPage(QWidget):
    page_title = "Agents"
    page_subtitle = "Manage and monitor all active neural agents."

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("PageSurface")
        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet(f"background: {BG_NEURAL_DEEP};")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(22, 28, 22, 22)
        outer.setSpacing(22)

        main = QVBoxLayout()
        main.setSpacing(16)
        main.setContentsMargins(0, 0, 0, 0)
        main.addWidget(self._header())
        main.addLayout(self._stats_row())
        main.addWidget(self._agents_panel(), 1)

        outer.addLayout(main, 1)
        outer.addWidget(self._right_rail(), 0)

    def _header(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("background: transparent; border: none;")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        text = QVBoxLayout()
        text.setSpacing(6)
        title = QLabel("AGENTS")
        title.setStyleSheet(f"color: {NEURAL_TEXT_PRIMARY}; font-family: {MONO_FAMILY}; font-size: 23px; font-weight: 900;")
        subtitle = QLabel("Manage and monitor all active neural agents.")
        subtitle.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {MONO_FAMILY}; font-size: 12px;")
        text.addWidget(title)
        text.addWidget(subtitle)
        add = QPushButton("+  ADD AGENT")
        add.setCursor(Qt.CursorShape.PointingHandCursor)
        add.setFixedSize(150, 44)
        add.setStyleSheet(f"""
            QPushButton {{
                background: rgba(47, 140, 255, 0.18);
                border: 1px solid rgba(47, 140, 255, 0.78);
                border-radius: 8px;
                color: {NEURAL_CYAN};
                font-family: {MONO_FAMILY};
                font-size: 13px;
                font-weight: 900;
            }}
            QPushButton:hover {{ background: rgba(47, 140, 255, 0.28); }}
        """)
        lay.addLayout(text, 1)
        lay.addWidget(add, 0, Qt.AlignmentFlag.AlignTop)
        return frame

    def _stats_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(14)
        for icon, value, label, meta, tone in (
            ("☷", "3", "ACTIVE AGENTS", "All systems operational", "green"),
            ("▧", "12", "TASKS COMPLETED", "+3 today", "blue"),
            ("◴", "98%", "SUCCESS RATE", "Excellent", "green"),
            ("▴", "245", "TOTAL ACTIONS", "+18 today", "blue"),
        ):
            row.addWidget(self._stat_card(icon, value, label, meta, tone))
        return row

    def _stat_card(self, icon: str, value: str, label: str, meta: str, tone: str) -> QFrame:
        color = NEURAL_GREEN if tone == "green" else NEURAL_BLUE
        card = QFrame()
        card.setFixedHeight(108)
        card.setStyleSheet(f"""
            QFrame {{
                background: rgba(5, 14, 35, 0.82);
                border: 1px solid rgba(47, 140, 255, 0.28);
                border-radius: 10px;
            }}
            QLabel {{ background: transparent; border: none; }}
        """)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(16)
        badge = QLabel(icon)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(58, 58)
        badge.setStyleSheet(f"color: {color}; border: 1px solid rgba(47,140,255,0.35); border-radius: 29px; background: rgba(47,140,255,0.12); font-size: 27px;")
        text = QVBoxLayout()
        text.setSpacing(4)
        v = QLabel(value)
        v.setStyleSheet(f"color: {NEURAL_TEXT_PRIMARY}; font-family: {MONO_FAMILY}; font-size: 26px; font-weight: 900;")
        l = QLabel(label)
        l.setStyleSheet(f"color: {NEURAL_TEXT_PRIMARY}; font-family: {MONO_FAMILY}; font-size: 11px; font-weight: 900;")
        m = QLabel(meta)
        m.setStyleSheet(f"color: {color}; font-family: {MONO_FAMILY}; font-size: 11px; font-weight: 800;")
        text.addWidget(v)
        text.addWidget(l)
        text.addWidget(m)
        lay.addWidget(badge)
        lay.addLayout(text, 1)
        return card

    def _agents_panel(self) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background: rgba(4, 12, 31, 0.70);
                border: 1px solid rgba(47, 140, 255, 0.28);
                border-radius: 10px;
            }}
            QLabel {{ background: transparent; border: none; }}
        """)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 8)
        lay.setSpacing(6)
        lay.addLayout(self._filters())
        rows = (
            ("●", "☷", "Task Agent", "ACTIVE", "Handles task management, scheduling, and automation.", ("Automation", "Scheduling", "Workflows"), "8", "99%", "2m ago", "green"),
            ("●", "▤", "File Agent", "ACTIVE", "Manages files, searches, and data extraction.", ("Search", "Extract", "Organize"), "6", "97%", "1m ago", "blue"),
            ("●", "✈", "Comm Agent", "IDLE", "Handles communication across platforms.", ("Email", "WhatsApp", "Notifications"), "0", "-", "15m ago", "purple"),
            ("●", "✉", "Email Agent", "OFFLINE", "Drafts, sends, and manages email communications.", ("Email", "Draft", "Templates"), "0", "-", "2h ago", "muted"),
        )
        for row in rows:
            lay.addWidget(self._agent_row(*row))
        lay.addStretch(1)
        return panel

    def _filters(self) -> QHBoxLayout:
        wrap = QHBoxLayout()
        wrap.setContentsMargins(18, 10, 12, 10)
        wrap.setSpacing(12)
        for text, active in (("ALL AGENTS", True), ("TASK AGENTS", False), ("FILE AGENTS", False), ("COMM AGENTS", False), ("SYSTEM AGENTS", False)):
            tab = QLabel(text)
            tab.setFixedHeight(36)
            tab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tab.setStyleSheet(
                f"color: {NEURAL_CYAN if active else NEURAL_TEXT_SECONDARY}; "
                f"font-family: {MONO_FAMILY}; font-size: 11px; font-weight: 900; "
                f"border-bottom: {'2px solid ' + NEURAL_BLUE if active else '1px solid transparent'};"
            )
            wrap.addWidget(tab)
        wrap.addStretch(1)
        search = QLineEdit()
        search.setPlaceholderText("Search agents...")
        search.setFixedSize(230, 44)
        search.setStyleSheet(self._input_style())
        status = QComboBox()
        status.addItems(["Status: All", "Active", "Idle", "Offline"])
        status.setFixedSize(150, 44)
        status.setStyleSheet(self._input_style())
        wrap.addWidget(search)
        wrap.addWidget(status)
        return wrap

    def _agent_row(self, dot: str, icon: str, name: str, state: str, desc: str, tags: tuple[str, ...], tasks: str, success: str, active: str, tone: str) -> QFrame:
        color = {"green": NEURAL_GREEN, "blue": NEURAL_BLUE, "purple": NEURAL_PURPLE, "muted": "#596782"}.get(tone, NEURAL_BLUE)
        row = QFrame()
        row.setFixedHeight(118)
        row.setStyleSheet(f"""
            QFrame {{
                background: rgba(5, 14, 35, 0.82);
                border: 1px solid rgba(47, 140, 255, 0.25);
                border-radius: 9px;
            }}
            QLabel {{ background: transparent; border: none; }}
        """)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(22, 14, 22, 14)
        lay.setSpacing(20)

        orb = QLabel(icon)
        orb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        orb.setFixedSize(70, 70)
        orb.setStyleSheet(f"color: {color}; border: 2px solid {color}; border-radius: 35px; background: rgba(47,140,255,0.08); font-size: 31px;")

        info = QVBoxLayout()
        top = QHBoxLayout()
        title = QLabel(name)
        title.setStyleSheet(f"color: {NEURAL_TEXT_PRIMARY}; font-family: {MONO_FAMILY}; font-size: 15px; font-weight: 900;")
        badge = QLabel(state)
        badge.setStyleSheet(f"color: {color}; background: rgba(25,245,166,0.10); border-radius: 5px; padding: 4px 8px; font-family: {MONO_FAMILY}; font-size: 10px; font-weight: 900;")
        top.addWidget(title)
        top.addWidget(badge)
        top.addStretch(1)
        d = QLabel(desc)
        d.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {MONO_FAMILY}; font-size: 11px;")
        tag_row = QHBoxLayout()
        tag_row.setSpacing(8)
        for tag in tags:
            tag_lbl = QLabel(tag)
            tag_lbl.setStyleSheet(f"color: {NEURAL_CYAN}; background: rgba(47,140,255,0.14); border: 1px solid rgba(47,140,255,0.20); border-radius: 5px; padding: 4px 10px; font-family: {MONO_FAMILY}; font-size: 10px;")
            tag_row.addWidget(tag_lbl)
        tag_row.addStretch(1)
        info.addLayout(top)
        info.addWidget(d)
        info.addLayout(tag_row)

        lay.addWidget(orb)
        lay.addLayout(info, 1)
        lay.addWidget(self._mini_metric("TASKS", tasks), 0)
        lay.addWidget(self._mini_metric("SUCCESS RATE", success, color), 0)
        lay.addWidget(self._mini_metric("LAST ACTIVE", active), 0)
        menu = QLabel("⋮")
        menu.setStyleSheet(f"color: {NEURAL_BLUE}; font-size: 26px; font-weight: 900;")
        lay.addWidget(menu)
        return row

    def _mini_metric(self, label: str, value: str, color: str = NEURAL_TEXT_PRIMARY) -> QFrame:
        box = QFrame()
        box.setFixedWidth(120)
        box.setStyleSheet("background: transparent; border: none;")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        l = QLabel(label)
        l.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {MONO_FAMILY}; font-size: 10px;")
        v = QLabel(value)
        v.setStyleSheet(f"color: {color}; font-family: {MONO_FAMILY}; font-size: 18px; font-weight: 900;")
        lay.addWidget(l)
        lay.addWidget(v)
        return box

    def _right_rail(self) -> QFrame:
        rail = QFrame()
        rail.setFixedWidth(320)
        rail.setStyleSheet("background: transparent; border: none;")
        lay = QVBoxLayout(rail)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)
        lay.addWidget(JarvisOrbPanel(), 1)
        lay.addWidget(self._overview_card())
        lay.addWidget(self._system_info_card())
        return rail

    def _overview_card(self) -> QFrame:
        card = self._side_card("AGENT OVERVIEW", 156)
        lay = card.layout()
        row = QHBoxLayout()
        donut = QLabel("◔")
        donut.setAlignment(Qt.AlignmentFlag.AlignCenter)
        donut.setFixedSize(92, 92)
        donut.setStyleSheet(f"color: {NEURAL_GREEN}; font-size: 70px; border: none;")
        legend = QVBoxLayout()
        for name, count, color in (("Active", "3 (60%)", NEURAL_GREEN), ("Idle", "1 (20%)", NEURAL_PURPLE), ("Offline", "1 (20%)", "#596782")):
            line = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 12px;")
            n = QLabel(name)
            n.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {MONO_FAMILY}; font-size: 11px;")
            c = QLabel(count)
            c.setStyleSheet(f"color: {NEURAL_TEXT_PRIMARY}; font-family: {MONO_FAMILY}; font-size: 11px; font-weight: 900;")
            line.addWidget(dot)
            line.addWidget(n)
            line.addStretch(1)
            line.addWidget(c)
            legend.addLayout(line)
        row.addWidget(donut)
        row.addLayout(legend, 1)
        lay.addLayout(row)
        return card

    def _system_info_card(self) -> QFrame:
        card = self._side_card("SYSTEM INFO", 252)
        lay = card.layout()
        lay.addWidget(self._metric("CPU USAGE", "22%", 22))
        lay.addWidget(self._metric("MEMORY USAGE", "2.1 GB / 16 GB", 13))
        lay.addWidget(self._info_line("UPTIME", "02:14:36"))
        lay.addWidget(self._info_line("CONNECTION", "Secure", NEURAL_GREEN))
        return card

    def _side_card(self, title: str, height: int) -> QFrame:
        card = QFrame()
        card.setFixedHeight(height)
        card.setStyleSheet(f"""
            QFrame {{
                background: rgba(5, 14, 35, 0.82);
                border: 1px solid rgba(47, 140, 255, 0.28);
                border-radius: 10px;
            }}
            QLabel {{ background: transparent; border: none; }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 16, 18, 14)
        lay.setSpacing(10)
        t = QLabel(title)
        t.setStyleSheet(f"color: {NEURAL_CYAN}; font-family: {MONO_FAMILY}; font-size: 14px; font-weight: 900;")
        lay.addWidget(t)
        return card

    def _metric(self, label: str, value: str, percent: int) -> QFrame:
        box = QFrame()
        box.setStyleSheet("background: transparent; border: none;")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        l = QLabel(label)
        l.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {MONO_FAMILY}; font-size: 10px;")
        v = QLabel(value)
        v.setStyleSheet(f"color: {NEURAL_CYAN}; font-family: {MONO_FAMILY}; font-size: 11px; font-weight: 900;")
        row.addWidget(l)
        row.addStretch(1)
        row.addWidget(v)
        lay.addLayout(row)
        lay.addWidget(ProgressBarWidget(percent, "blue"))
        return box

    def _info_line(self, label: str, value: str, color: str = NEURAL_TEXT_PRIMARY) -> QFrame:
        row = QFrame()
        row.setStyleSheet("background: transparent; border: none;")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        l = QLabel(label)
        v = QLabel(value)
        l.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {MONO_FAMILY}; font-size: 10px;")
        v.setStyleSheet(f"color: {color}; font-family: {MONO_FAMILY}; font-size: 11px; font-weight: 900;")
        lay.addWidget(l)
        lay.addStretch(1)
        lay.addWidget(v)
        return row

    def _input_style(self) -> str:
        return f"""
            QLineEdit, QComboBox {{
                background: rgba(2, 10, 27, 0.70);
                border: 1px solid rgba(47, 140, 255, 0.35);
                border-radius: 8px;
                color: {NEURAL_TEXT_SECONDARY};
                font-family: {MONO_FAMILY};
                font-size: 12px;
                padding: 0 12px;
            }}
            QComboBox::drop-down {{ border: none; width: 28px; }}
        """
