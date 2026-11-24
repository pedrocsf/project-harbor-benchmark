from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from domain.explanations.timeline import TimelinePosition
from presentation.views.branding import BORDER_COLOR, PRIMARY_COLOR

SEGMENT_HEIGHT = 6.0
SEGMENT_GAP = 4.0
TIMELINE_MINIMUM_HEIGHT = 16


class StepTimeline(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._step_count = 1
        self._position = TimelinePosition(0, 0.0, False)
        self.setMinimumHeight(TIMELINE_MINIMUM_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_state(self, step_count: int, position: TimelinePosition) -> None:
        self._step_count = max(1, step_count)
        self._position = position
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        total_gap = SEGMENT_GAP * (self._step_count - 1)
        segment_width = max(0.0, (self.width() - total_gap) / self._step_count)
        top = (self.height() - SEGMENT_HEIGHT) / 2
        radius = SEGMENT_HEIGHT / 2
        for step_index in range(self._step_count):
            left = step_index * (segment_width + SEGMENT_GAP)
            segment = QRectF(left, top, segment_width, SEGMENT_HEIGHT)
            painter.setBrush(QColor(BORDER_COLOR))
            painter.drawRoundedRect(segment, radius, radius)
            fill = self._fill_fraction(step_index)
            if fill <= 0:
                continue
            painter.setBrush(QColor(PRIMARY_COLOR))
            painter.drawRoundedRect(QRectF(left, top, max(segment_width * fill, SEGMENT_HEIGHT), SEGMENT_HEIGHT), radius, radius)

    def _fill_fraction(self, step_index: int) -> float:
        if step_index < self._position.step_index:
            return 1.0
        if step_index == self._position.step_index:
            return self._position.step_progress
        return 0.0
