from PySide6.QtCore import QElapsedTimer, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from presentation.views.branding import PRIMARY_COLOR, STRONG_BORDER_COLOR

SPINNER_SIZE = 14
LINE_WIDTH = 2.0
ARC_SPAN_DEGREES = 90
FULL_TURN_DEGREES = 360
QT_ANGLE_UNITS_PER_DEGREE = 16
ROTATION_MILLISECONDS = 900
FRAME_MILLISECONDS = 16


class SpinnerIndicator(QWidget):
    def __init__(self, size: int = SPINNER_SIZE):
        super().__init__()
        self.setFixedSize(size, size)
        self._clock = QElapsedTimer()
        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self.update)

    def showEvent(self, event) -> None:
        self._clock.start()
        self._frame_timer.start(FRAME_MILLISECONDS)
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        self._frame_timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        inset = LINE_WIDTH / 2
        rect = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
        painter.setPen(QPen(QColor(STRONG_BORDER_COLOR), LINE_WIDTH))
        painter.drawEllipse(rect)
        pen = QPen(QColor(PRIMARY_COLOR), LINE_WIDTH, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        progress = (self._clock.elapsed() % ROTATION_MILLISECONDS) / ROTATION_MILLISECONDS
        start_angle = -progress * FULL_TURN_DEGREES
        painter.drawArc(
            rect,
            int(start_angle * QT_ANGLE_UNITS_PER_DEGREE),
            -ARC_SPAN_DEGREES * QT_ANGLE_UNITS_PER_DEGREE,
        )
