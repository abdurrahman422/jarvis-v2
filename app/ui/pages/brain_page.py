from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.ui.components import JarvisOrbPanel, ProgressBarWidget
from app.services.analytics_service import AnalyticsService
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


class LineChartWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(165)
        self._values: list[int] = []

    def set_values(self, values: list[int]) -> None:
        self._values = [max(0, int(v)) for v in values]
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = self.rect().adjusted(34, 12, -12, -22)
            painter.setPen(QPen(QColor(47, 140, 255, 42), 1))
            for i in range(5):
                y = rect.top() + rect.height() * i / 4
                painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            for i in range(7):
                x = rect.left() + rect.width() * i / 6
                painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            if not self._values or sum(self._values) == 0:
                painter.setPen(QColor(NEURAL_TEXT_SECONDARY))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No analytics data yet")
                return
            max_v = max(self._values) or 1
            points = [
                QPointF(
                    rect.left() + rect.width() * i / max(len(self._values) - 1, 1),
                    rect.bottom() - rect.height() * value / max_v,
                )
                for i, value in enumerate(self._values)
            ]
            path = QPainterPath(points[0])
            for point in points[1:]:
                path.lineTo(point)
            fill = QPainterPath(path)
            fill.lineTo(points[-1].x(), rect.bottom())
            fill.lineTo(points[0].x(), rect.bottom())
            fill.closeSubpath()
            painter.fillPath(fill, QColor(47, 140, 255, 38))
            painter.setPen(QPen(QColor(0, 145, 255, 230), 2))
            painter.drawPath(path)
            painter.setBrush(QColor(0, 245, 255))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(points[-2], 4, 4)
        finally:
            painter.end()


class DonutWidget(QWidget):
    def __init__(self, center_text: str, subtitle: str = "", segments: tuple[tuple[int, str], ...] | None = None) -> None:
        super().__init__()
        self.setMinimumSize(150, 150)
        self.center_text = center_text
        self.subtitle = subtitle
        self.segments = segments or ((42, NEURAL_BLUE), (28, NEURAL_GREEN), (18, NEURAL_PURPLE), (12, "#f5a524"))

    def set_data(self, center_text: str, subtitle: str = "", segments: tuple[tuple[int, str], ...] | None = None) -> None:
        self.center_text = center_text
        self.subtitle = subtitle
        self.segments = segments or ()
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            side = min(self.width(), self.height()) - 16
            rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
            if self.segments:
                start = 90 * 16
                for value, color in self.segments:
                    span = int(-value / 100 * 360 * 16)
                    painter.setPen(QPen(QColor(color), 18, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
                    painter.drawArc(rect, start, span)
                    start += span
            else:
                painter.setPen(QPen(QColor(47, 140, 255, 44), 18, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
                painter.drawArc(rect, 90 * 16, -360 * 16)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(5, 14, 35))
            painter.drawEllipse(rect.adjusted(23, 23, -23, -23))
            painter.setPen(QColor(NEURAL_TEXT_PRIMARY))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.center_text)
            if self.subtitle:
                sub = QRectF(rect.left(), rect.center().y() + 12, rect.width(), 24)
                painter.setPen(QColor(NEURAL_TEXT_SECONDARY))
                painter.drawText(sub, Qt.AlignmentFlag.AlignCenter, self.subtitle)
        finally:
            painter.end()


class GaugeWidget(QWidget):
    def __init__(self, value: int = 98) -> None:
        super().__init__()
        self.value = value
        self.setMinimumHeight(170)

    def set_value(self, value: int) -> None:
        self.value = max(0, min(int(value), 100))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(30, 36, self.width() - 60, self.height() * 1.25)
            painter.setPen(QPen(QColor(47, 140, 255, 44), 18, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            painter.drawArc(rect, 180 * 16, -180 * 16)
            painter.setPen(QPen(QColor(25, 245, 166), 18, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(rect, 180 * 16, int(-180 * 16 * self.value / 100))
            painter.setPen(QColor(NEURAL_TEXT_PRIMARY))
            painter.drawText(self.rect().adjusted(0, 42, 0, -35), Qt.AlignmentFlag.AlignCenter, f"{self.value}%")
            painter.setPen(QColor(NEURAL_GREEN))
            label = "No analytics data yet" if self.value == 0 else "Success rate"
            painter.drawText(self.rect().adjusted(0, 86, 0, -20), Qt.AlignmentFlag.AlignCenter, label)
        finally:
            painter.end()


class BrainPage(QWidget):
    page_title = "Analytics"
    page_subtitle = "Real-time insights and performance overview."

    def __init__(self, analytics_service: AnalyticsService | None = None) -> None:
        super().__init__()
        self.setObjectName("PageSurface")
        self.analytics_service = analytics_service or AnalyticsService()
        self.log = QTextEdit()
        self.log.hide()
        self._stat_labels: dict[str, QLabel] = {}
        self._stat_delta_labels: dict[str, QLabel] = {}
        self._legend_layouts: dict[str, QVBoxLayout] = {}
        self._top_actions_layout: QVBoxLayout | None = None
        self._feed_layout: QVBoxLayout | None = None
        self._system_labels: dict[str, QLabel] = {}
        self._performance_labels: dict[str, QLabel] = {}
        self._line_chart: LineChartWidget | None = None
        self._activity_donut: DonutWidget | None = None
        self._category_donut: DonutWidget | None = None
        self._success_gauge: GaugeWidget | None = None
        self._init_ui()
        self.refresh()
        self._metrics_timer = QTimer(self)
        self._metrics_timer.timeout.connect(self.refresh)
        self._metrics_timer.start(5000)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()

    def _init_ui(self) -> None:
        self.setStyleSheet(f"background: {BG_NEURAL_DEEP};")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(22, 26, 22, 22)
        outer.setSpacing(22)
        outer.addLayout(self._main_content(), 1)
        outer.addWidget(self._right_rail(), 0)
        outer.addWidget(self.log)

    def _main_content(self) -> QVBoxLayout:
        main = QVBoxLayout()
        main.setSpacing(12)
        main.addWidget(self._header())
        main.addLayout(self._range_row())
        main.addLayout(self._stats_row())
        charts = QGridLayout()
        charts.setHorizontalSpacing(12)
        charts.setVerticalSpacing(12)
        charts.addWidget(self._line_card(), 0, 0, 1, 2)
        charts.addWidget(self._activity_card(), 0, 2)
        charts.addWidget(self._category_card(), 1, 0)
        charts.addWidget(self._success_card(), 1, 1)
        charts.addWidget(self._top_agents_card(), 1, 2)
        charts.addWidget(self._feed_card(), 2, 0, 1, 3)
        main.addLayout(charts, 1)
        return main

    def _header(self) -> QFrame:
        box = QFrame()
        box.setStyleSheet("background: transparent; border: none;")
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        text = QVBoxLayout()
        title = QLabel("ANALYTICS")
        subtitle = QLabel("Real-time insights and performance overview.")
        title.setStyleSheet(f"color: {NEURAL_TEXT_PRIMARY}; font-family: {MONO_FAMILY}; font-size: 23px; font-weight: 900;")
        subtitle.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {MONO_FAMILY}; font-size: 12px;")
        text.addWidget(title)
        text.addWidget(subtitle)
        export = QPushButton("EXPORT REPORT")
        export.setFixedSize(158, 38)
        export.setStyleSheet(self._button_style())
        lay.addLayout(text, 1)
        lay.addWidget(export, 0, Qt.AlignmentFlag.AlignBottom)
        return box

    def _range_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(0)
        for label, active in (("LIVE", False), ("1H", False), ("6H", False), ("24H", True), ("7D", False), ("30D", False), ("90D", False), ("CUSTOM", False)):
            btn = QPushButton(label)
            btn.setFixedSize(82 if label != "CUSTOM" else 108, 36)
            btn.setStyleSheet(f"background: {'rgba(47,140,255,0.22)' if active else 'rgba(2,10,27,0.62)'}; border: 1px solid rgba(47,140,255,0.28); color: {NEURAL_GREEN if label == 'LIVE' else NEURAL_TEXT_SECONDARY}; font-family: {MONO_FAMILY}; font-size: 11px; font-weight: 900;")
            row.addWidget(btn)
        row.addStretch(1)
        return row

    def _stats_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)
        for key, icon, title, color in (
            ("total_work", "L", "TOTAL TASKS", NEURAL_BLUE),
            ("completed", "C", "COMPLETED", NEURAL_GREEN),
            ("pending", "P", "PENDING", "#f59e0b"),
            ("failed", "F", "FAILED", NEURAL_PURPLE),
        ):
            row.addWidget(self._stat_card(key, icon, title, color))
        return row

    def _stat_card(self, key: str, icon: str, title: str, color: str) -> QFrame:
        card = self._card(108)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(18, 16, 18, 16)
        badge = QLabel(icon)
        badge.setFixedSize(56, 56)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"color: {color}; border: 1px solid rgba(47,140,255,0.34); border-radius: 28px; background: rgba(47,140,255,0.12); font-size: 22px; font-weight: 900;")
        text = QVBoxLayout()
        title_widget = QLabel(title)
        value_widget = QLabel("0")
        delta_widget = QLabel("No analytics data yet")
        title_widget.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {MONO_FAMILY}; font-size: 10px;")
        value_widget.setStyleSheet(f"color: {NEURAL_TEXT_PRIMARY}; font-family: {MONO_FAMILY}; font-size: 24px; font-weight: 900;")
        delta_widget.setStyleSheet(f"color: {color}; font-family: {MONO_FAMILY}; font-size: 11px;")
        text.addWidget(title_widget)
        text.addWidget(value_widget)
        text.addWidget(delta_widget)
        self._stat_labels[key] = value_widget
        self._stat_delta_labels[key] = delta_widget
        lay.addWidget(badge)
        lay.addLayout(text)
        return card

    def _line_card(self) -> QFrame:
        card = self._titled_card("TASKS OVER TIME")
        self._line_chart = LineChartWidget()
        card.layout().addWidget(self._line_chart)
        return card

    def _activity_card(self) -> QFrame:
        card = self._titled_card("AGENT ACTIVITY")
        body = QHBoxLayout()
        self._activity_donut = DonutWidget("0", "AGENTS", ())
        body.addWidget(self._activity_donut)
        legend = QVBoxLayout()
        self._legend_layouts["activity"] = legend
        legend.addWidget(self._empty_label())
        body.addLayout(legend)
        card.layout().addLayout(body)
        return card

    def _category_card(self) -> QFrame:
        card = self._titled_card("TASKS BY CATEGORY")
        body = QHBoxLayout()
        self._category_donut = DonutWidget("0", "TOTAL", ())
        body.addWidget(self._category_donut)
        legend = QVBoxLayout()
        self._legend_layouts["categories"] = legend
        legend.addWidget(self._empty_label())
        body.addLayout(legend)
        card.layout().addLayout(body)
        return card

    def _success_card(self) -> QFrame:
        card = self._titled_card("SUCCESS RATE")
        self._success_gauge = GaugeWidget(0)
        card.layout().addWidget(self._success_gauge)
        return card

    def _top_agents_card(self) -> QFrame:
        card = self._titled_card("TOP PERFORMING AGENTS")
        self._top_actions_layout = card.layout()
        card.layout().addWidget(self._empty_label())
        return card

    def _feed_card(self) -> QFrame:
        card = self._titled_card("ACTIVITY FEED")
        self._feed_layout = card.layout()
        card.layout().addWidget(self._empty_label())
        return card

    def _right_rail(self) -> QFrame:
        rail = QFrame()
        rail.setFixedWidth(300)
        rail.setStyleSheet("background: transparent; border: none;")
        lay = QVBoxLayout(rail)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)
        lay.addWidget(JarvisOrbPanel(), 1)
        lay.addWidget(self._performance_card())
        lay.addWidget(self._system_card())
        return rail

    def _performance_card(self) -> QFrame:
        card = self._titled_card("PERFORMANCE OVERVIEW", 270)
        for key, label, color in (("cpu", "CPU USAGE", NEURAL_BLUE), ("memory", "MEMORY USAGE", NEURAL_PURPLE), ("disk", "DISK USAGE", NEURAL_GREEN)):
            wave = QLabel(f"{label}        0%\nNo analytics data yet")
            wave.setStyleSheet(f"color: {color}; font-family: {MONO_FAMILY}; font-size: 11px;")
            self._performance_labels[key] = wave
            card.layout().addWidget(wave)
        return card

    def _system_card(self) -> QFrame:
        card = self._titled_card("SYSTEM INFO", 214)
        for key, label, color in (("uptime", "UPTIME", NEURAL_TEXT_PRIMARY), ("connection", "CONNECTION", NEURAL_GREEN), ("data_sync", "DATA SYNC", NEURAL_GREEN), ("last_sync", "LAST SYNC", NEURAL_CYAN)):
            row = QHBoxLayout()
            l = QLabel(label)
            v = QLabel("0")
            l.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {MONO_FAMILY}; font-size: 10px;")
            v.setStyleSheet(f"color: {color}; font-family: {MONO_FAMILY}; font-size: 11px; font-weight: 900;")
            row.addWidget(l)
            row.addStretch(1)
            row.addWidget(v)
            self._system_labels[key] = v
            card.layout().addLayout(row)
        return card

    def _titled_card(self, title: str, height: int | None = None) -> QFrame:
        card = self._card(height)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 12)
        lay.setSpacing(10)
        head = QLabel(title)
        head.setStyleSheet(f"color: {NEURAL_CYAN}; font-family: {MONO_FAMILY}; font-size: 12px; font-weight: 900;")
        lay.addWidget(head)
        return card

    def _card(self, height: int | None = None) -> QFrame:
        card = QFrame()
        if height:
            card.setFixedHeight(height)
        card.setStyleSheet("QFrame { background: rgba(5,14,35,0.82); border: 1px solid rgba(47,140,255,0.28); border-radius: 10px; } QLabel { background: transparent; border: none; }")
        return card

    def _legend(self, name: str, pct: str, color: str) -> QFrame:
        row = QFrame()
        row.setStyleSheet("background: transparent; border: none;")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        dot = QLabel("o")
        n = QLabel(name)
        p = QLabel(pct)
        dot.setStyleSheet(f"color: {color}; font-size: 12px;")
        n.setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {MONO_FAMILY}; font-size: 11px;")
        p.setStyleSheet(f"color: {NEURAL_TEXT_PRIMARY}; font-family: {MONO_FAMILY}; font-size: 11px; font-weight: 900;")
        lay.addWidget(dot)
        lay.addWidget(n)
        lay.addStretch(1)
        lay.addWidget(p)
        return row

    def refresh(self) -> None:
        try:
            data = self.analytics_service.get_dashboard()
        except Exception as exc:
            self._show_error_state(str(exc))
            return

        summary = data["summary"]
        self._set_stat("total_work", summary["total_work"], f"{summary['total_chats']} chats logged")
        self._set_stat("completed", summary["completed"], f"{summary['automation_actions']} actions processed")
        self._set_stat("pending", summary["pending"], f"{summary['voice_commands']} voice commands")
        self._set_stat("failed", summary["failed"], f"{summary['api_calls']} API calls")

        if self._line_chart:
            self._line_chart.set_values(data["hourly_usage"])

        colors = (NEURAL_GREEN, NEURAL_BLUE, NEURAL_PURPLE, "#f59e0b", NEURAL_CYAN)
        activity = data["agent_activity"]
        activity_segments = tuple((item["percent"], colors[i % len(colors)]) for i, item in enumerate(activity))
        if self._activity_donut:
            self._activity_donut.set_data(str(len(activity)), "AGENTS", activity_segments)
        self._fill_legend("activity", activity, colors)

        categories = data["categories"]
        category_segments = tuple((item["percent"], colors[i % len(colors)]) for i, item in enumerate(categories))
        if self._category_donut:
            self._category_donut.set_data(self._fmt(summary["total_work"]), "TOTAL", category_segments)
        self._fill_legend("categories", categories, colors)

        if self._success_gauge:
            self._success_gauge.set_value(summary["success_rate"])

        self._fill_top_actions(data["top_actions"], colors)
        self._fill_feed(data["recent_activity"])
        self._update_system(data["system"])

    def _set_stat(self, key: str, value: int, detail: str) -> None:
        if key in self._stat_labels:
            self._stat_labels[key].setText(self._fmt(value))
        if key in self._stat_delta_labels:
            self._stat_delta_labels[key].setText(detail if value else "No analytics data yet")

    def _fill_legend(self, key: str, items: list[dict], colors: tuple[str, ...]) -> None:
        layout = self._legend_layouts.get(key)
        if layout is None:
            return
        self._clear_layout(layout)
        if not items:
            layout.addWidget(self._empty_label())
            return
        for i, item in enumerate(items[:5]):
            layout.addWidget(self._legend(item["name"], f"{item['percent']}%", colors[i % len(colors)]))

    def _fill_top_actions(self, actions: list[dict], colors: tuple[str, ...]) -> None:
        layout = self._top_actions_layout
        if layout is None:
            return
        while layout.count() > 1:
            item = layout.takeAt(1)
            self._dispose_item(item)
        if not actions:
            layout.addWidget(self._empty_label())
            return
        for i, item in enumerate(actions[:3], 1):
            color = colors[(i - 1) % len(colors)]
            row = QHBoxLayout()
            num = QLabel(str(i))
            num.setFixedSize(26, 26)
            num.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num.setStyleSheet("color: #94a3b8; border: 1px solid rgba(47,140,255,0.30); border-radius: 5px;")
            name_lbl = QLabel(item["name"])
            pct_lbl = QLabel(f"{item['success_rate']}%")
            name_lbl.setStyleSheet(f"color: {NEURAL_TEXT_PRIMARY}; font-family: {MONO_FAMILY}; font-size: 12px;")
            pct_lbl.setStyleSheet(f"color: {color}; font-family: {MONO_FAMILY}; font-size: 11px; font-weight: 900;")
            row.addWidget(num)
            row.addWidget(name_lbl)
            row.addStretch(1)
            row.addWidget(pct_lbl)
            layout.addLayout(row)
            layout.addWidget(ProgressBarWidget(item["success_rate"], "blue"))

    def _fill_feed(self, rows: list[dict]) -> None:
        layout = self._feed_layout
        if layout is None:
            return
        while layout.count() > 1:
            item = layout.takeAt(1)
            self._dispose_item(item)
        if not rows:
            layout.addWidget(self._empty_label())
            return
        for row_data in rows[:4]:
            status = row_data["status"]
            color = NEURAL_PURPLE if status == "ERROR" else NEURAL_GREEN
            time_text = self._time_part(row_data["time"])
            message = row_data["message"] or row_data["action"]
            row = QHBoxLayout()
            for widget in (QLabel(f"[{time_text}]"), QLabel("o"), QLabel(message)):
                row.addWidget(widget)
            row.itemAt(0).widget().setStyleSheet(f"color: {NEURAL_TEXT_MUTED}; font-family: {MONO_FAMILY}; font-size: 11px;")
            row.itemAt(1).widget().setStyleSheet(f"color: {color}; font-size: 13px;")
            row.itemAt(2).widget().setStyleSheet(f"color: {NEURAL_TEXT_SECONDARY}; font-family: {MONO_FAMILY}; font-size: 11px;")
            row.addStretch(1)
            s = QLabel(status)
            s.setStyleSheet(f"color: {color}; border: 1px solid {color}; border-radius: 5px; padding: 4px 10px; font-family: {MONO_FAMILY}; font-size: 10px;")
            row.addWidget(s)
            layout.addLayout(row)

    def _update_system(self, system: dict) -> None:
        if "cpu" in self._performance_labels:
            self._performance_labels["cpu"].setText(f"CPU USAGE        {system['cpu_percent']}%\n{self._sparkline(system['cpu_percent'], NEURAL_BLUE)}")
        if "memory" in self._performance_labels:
            self._performance_labels["memory"].setText(
                f"MEMORY USAGE     {system['memory_used_gb']} GB / {system['memory_total_gb']} GB\n{self._sparkline(system['memory_percent'], NEURAL_PURPLE)}"
            )
        if "disk" in self._performance_labels:
            self._performance_labels["disk"].setText(
                f"DISK USAGE       {system['disk_used_gb']} GB / {system['disk_total_gb']} GB\n{self._sparkline(system['disk_percent'], NEURAL_GREEN)}"
            )
        mapping = {
            "uptime": system["boot_uptime"],
            "connection": system["connection"],
            "data_sync": system["data_sync"],
            "last_sync": system["last_sync"],
        }
        for key, value in mapping.items():
            if key in self._system_labels:
                self._system_labels[key].setText(str(value))

    def _show_error_state(self, message: str) -> None:
        for key in self._stat_labels:
            self._set_stat(key, 0, "No analytics data yet")
        if self._line_chart:
            self._line_chart.set_values([])
        if self._feed_layout:
            self._clear_layout(self._feed_layout, keep_first=True)
            self._feed_layout.addWidget(self._empty_label(f"Analytics unavailable: {message}"))

    def _empty_label(self, text: str = "No analytics data yet") -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"color: {NEURAL_TEXT_MUTED}; font-family: {MONO_FAMILY}; font-size: 11px;")
        return label

    def _clear_layout(self, layout: QVBoxLayout, keep_first: bool = False) -> None:
        start = 1 if keep_first else 0
        while layout.count() > start:
            item = layout.takeAt(start)
            self._dispose_item(item)

    def _dispose_item(self, item) -> None:
        widget = item.widget()
        child_layout = item.layout()
        if widget:
            widget.deleteLater()
        elif child_layout:
            self._clear_layout(child_layout)

    def _fmt(self, value: int) -> str:
        return f"{int(value):,}"

    def _time_part(self, value: str) -> str:
        if not value:
            return "--:--:--"
        return value.split(" ")[-1][:8]

    def _sparkline(self, percent: int, color: str) -> str:
        filled = max(0, min(16, round(int(percent) / 100 * 16)))
        return "█" * filled + "░" * (16 - filled)

    def _button_style(self) -> str:
        return f"background: rgba(47,140,255,0.10); border: 1px solid rgba(47,140,255,0.42); border-radius: 7px; color: {NEURAL_CYAN}; font-family: {MONO_FAMILY}; font-size: 11px; font-weight: 900;"
