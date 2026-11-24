from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF

from presentation.views.branding import LABEL_TEXT_COLOR, TEXT_ON_PRIMARY_COLOR

ICON_SIZE = 16
ICON_SCALE = 2
PAUSE_LINE_WIDTH = 2.4
RESTART_LINE_WIDTH = 1.6
RESTART_ARC_START_DEGREES = 135
RESTART_ARC_SPAN_DEGREES = -300


def _paint_icon(draw) -> QIcon:
    pixmap = QPixmap(ICON_SIZE * ICON_SCALE, ICON_SIZE * ICON_SCALE)
    pixmap.setDevicePixelRatio(ICON_SCALE)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    draw(painter)
    painter.end()
    return QIcon(pixmap)


def _round_pen(color: str, width: float) -> QPen:
    return QPen(QColor(color), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)


def pause_icon() -> QIcon:
    def draw(painter: QPainter) -> None:
        painter.setPen(_round_pen(TEXT_ON_PRIMARY_COLOR, PAUSE_LINE_WIDTH))
        painter.drawLine(QPointF(5, 3), QPointF(5, 13))
        painter.drawLine(QPointF(11, 3), QPointF(11, 13))

    return _paint_icon(draw)


def play_icon() -> QIcon:
    def draw(painter: QPainter) -> None:
        painter.setPen(_round_pen(TEXT_ON_PRIMARY_COLOR, RESTART_LINE_WIDTH))
        painter.setBrush(QColor(TEXT_ON_PRIMARY_COLOR))
        painter.drawPolygon(QPolygonF([QPointF(5, 3), QPointF(13, 8), QPointF(5, 13)]))

    return _paint_icon(draw)


def restart_icon() -> QIcon:
    def draw(painter: QPainter) -> None:
        painter.setPen(_round_pen(LABEL_TEXT_COLOR, RESTART_LINE_WIDTH))
        arc = QPainterPath()
        bounds = QRectF(3, 3, 10, 10)
        arc.arcMoveTo(bounds, RESTART_ARC_START_DEGREES)
        arc.arcTo(bounds, RESTART_ARC_START_DEGREES, RESTART_ARC_SPAN_DEGREES)
        painter.drawPath(arc)
        start = arc.pointAtPercent(0)
        painter.drawPolyline([QPointF(start.x(), start.y() - 3), start, QPointF(start.x() + 3, start.y())])

    return _paint_icon(draw)
