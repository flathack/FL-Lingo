"""Custom widgets used by the FL Lingo UI."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class SegmentedProgressBar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._total = 0
        self._localized = 0
        self._done = 0
        self._skipped = 0
        self._manual = 0
        self._terminology = 0
        self._segments = 20
        self.setMinimumHeight(24)

    def set_progress(self, *, total: int, localized: int, done: int, skipped: int, manual: int = 0, terminology: int = 0) -> None:
        self._total = max(0, int(total))
        self._localized = max(0, int(localized))
        self._done = max(0, int(done))
        self._skipped = max(0, int(skipped))
        self._manual = max(0, int(manual))
        self._terminology = max(0, int(terminology))
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        rect = self.rect().adjusted(0, 0, -1, -1)
        if rect.width() <= 0 or rect.height() <= 0:
            return

        painter.fillRect(rect, QColor("#d8d8d8"))
        total = self._total if self._total > 0 else 1
        localized_ratio = min(1.0, self._localized / total)
        auto_ratio = min(1.0, (self._done - self._manual) / total)
        done_ratio = min(1.0, self._done / total)
        terminology_ratio = min(1.0, (self._done + self._terminology) / total)
        covered_ratio = min(1.0, (self._done + self._terminology + self._skipped) / total)
        segment_gap = 2
        segment_width = max(4, int((rect.width() - ((self._segments - 1) * segment_gap)) / self._segments))
        for index in range(self._segments):
            x = rect.x() + index * (segment_width + segment_gap)
            width = segment_width if index < self._segments - 1 else rect.right() - x + 1
            segment_rect = rect.adjusted(x - rect.x(), 0, -(rect.right() - (x + width - 1)), 0)
            segment_end = (index + 1) / self._segments
            if segment_end <= localized_ratio:
                color = QColor("#A855F7")
            elif segment_end <= auto_ratio:
                color = QColor("#4CAF50")
            elif segment_end <= done_ratio:
                color = QColor("#42A5F5")
            elif segment_end <= terminology_ratio:
                color = QColor("#26C6DA")
            elif segment_end <= covered_ratio:
                color = QColor("#E3B341")
            else:
                color = QColor("#C7CCD4")
            painter.fillRect(segment_rect.adjusted(0, 0, -1, 0), color)
        painter.setPen(QPen(QColor("#707070"), 1))
        painter.drawRect(rect)
        painter.end()


class CircularProgressChart(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._total = 0
        self._localized = 0
        self._done = 0
        self._skipped = 0
        self._manual = 0
        self._terminology = 0
        self.setMinimumSize(180, 180)

    def set_progress(self, *, total: int, localized: int, done: int, skipped: int, manual: int = 0, terminology: int = 0) -> None:
        self._total = max(0, int(total))
        self._localized = max(0, int(localized))
        self._done = max(0, int(done))
        self._skipped = max(0, int(skipped))
        self._manual = max(0, int(manual))
        self._terminology = max(0, int(terminology))
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect().adjusted(8, 8, -8, -8)
        if rect.width() <= 0 or rect.height() <= 0:
            return

        size = min(rect.width(), rect.height())
        chart_rect = rect.adjusted(
            (rect.width() - size) // 2,
            (rect.height() - size) // 2,
            -((rect.width() - size) // 2),
            -((rect.height() - size) // 2),
        )
        total = self._total if self._total > 0 else 1
        auto = max(0, self._done - self._localized - self._manual)
        open_count = max(0, total - self._done - self._terminology - self._skipped)
        segments = [
            (self._localized, QColor("#A855F7")),
            (auto, QColor("#4CAF50")),
            (self._manual, QColor("#42A5F5")),
            (self._terminology, QColor("#26C6DA")),
            (self._skipped, QColor("#E3B341")),
            (open_count, QColor("#C7CCD4")),
        ]

        pen_width = max(14, size // 8)
        start_angle = 90 * 16
        for value, color in segments:
            if value <= 0:
                continue
            span_angle = int(round((value / total) * -360 * 16))
            pen = QPen(color, pen_width)
            painter.setPen(pen)
            painter.drawArc(chart_rect, start_angle, span_angle)
            start_angle += span_angle

        inner_margin = pen_width + 8
        inner_rect = chart_rect.adjusted(inner_margin, inner_margin, -inner_margin, -inner_margin)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.palette().window())
        painter.drawEllipse(inner_rect)

        covered = self._done + self._skipped
        percent = int(round((covered / total) * 100)) if self._total > 0 else 0
        painter.setPen(self.palette().text().color())
        font = painter.font()
        font.setBold(True)
        font.setPointSize(max(10, font.pointSize() + 4))
        painter.setFont(font)
        painter.drawText(inner_rect.adjusted(0, -10, 0, -2), Qt.AlignCenter, f"{percent}%")
        font.setBold(False)
        font.setPointSize(max(8, font.pointSize() - 4))
        painter.setFont(font)
        painter.drawText(inner_rect.adjusted(0, 18, 0, 0), Qt.AlignCenter, f"{covered}/{self._total}")
        painter.end()
