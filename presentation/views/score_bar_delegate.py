from PySide6.QtCore import QEasingCurve, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QTableWidget

from presentation.views.animations import SCORE_REVEAL_MILLISECONDS, motion_enabled, row_reveal_progress
from presentation.views.branding import BORDER_COLOR, SUCCESS_COLOR, WARNING_COLOR

SCORE_FRACTION_ROLE = Qt.ItemDataRole.UserRole + 1
SUCCESS_THRESHOLD = 0.5
BAR_HEIGHT = 6
BAR_RADIUS = BAR_HEIGHT / 2
HORIZONTAL_PADDING = 12
VALUE_WIDTH = 48
VALUE_GAP = 10
DISABLED_OPACITY = 0.4


class ScoreBarDelegate(QStyledItemDelegate):
    def __init__(self, table: QTableWidget):
        super().__init__(table)
        self._table = table
        self._reveal = 1.0
        self._animation = QVariantAnimation(self)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setDuration(SCORE_REVEAL_MILLISECONDS)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.valueChanged.connect(self._on_reveal_changed)

    def start_reveal(self) -> None:
        self._animation.stop()
        if not motion_enabled():
            self._reveal = 1.0
            return
        self._reveal = 0.0
        self._animation.start()

    def _on_reveal_changed(self, value: float) -> None:
        self._reveal = float(value)
        self._table.viewport().update()

    def paint(self, painter: QPainter, option, index) -> None:
        fraction = index.data(SCORE_FRACTION_ROLE)
        if fraction is None:
            super().paint(painter, option, index)
            return
        is_enabled = bool(option.state & QStyle.StateFlag.State_Enabled)
        color = QColor(SUCCESS_COLOR if fraction >= SUCCESS_THRESHOLD else WARNING_COLOR)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(1.0 if is_enabled else DISABLED_OPACITY)
        rect = option.rect.adjusted(HORIZONTAL_PADDING, 0, -HORIZONTAL_PADDING, 0)
        value_rect = QRectF(rect.right() - VALUE_WIDTH, rect.top(), VALUE_WIDTH, rect.height())
        track_width = rect.width() - VALUE_WIDTH - VALUE_GAP
        track_top = rect.center().y() - BAR_HEIGHT / 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(BORDER_COLOR))
        painter.drawRoundedRect(QRectF(rect.left(), track_top, track_width, BAR_HEIGHT), BAR_RADIUS, BAR_RADIUS)
        painter.setBrush(color)
        filled_width = track_width * max(0.0, min(1.0, fraction)) * row_reveal_progress(self._reveal, index.row())
        painter.drawRoundedRect(QRectF(rect.left(), track_top, filled_width, BAR_HEIGHT), BAR_RADIUS, BAR_RADIUS)
        painter.setPen(color)
        painter.drawText(value_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, index.data(Qt.ItemDataRole.DisplayRole))
        painter.restore()
