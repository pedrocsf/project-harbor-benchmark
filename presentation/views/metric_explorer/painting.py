import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QApplication

from presentation.views.branding import (
    BORDER_COLOR,
    DISABLED_TEXT_COLOR,
    MONOSPACE_FONT_FAMILIES,
    PRIMARY_COLOR,
    SECONDARY_TEXT_COLOR,
    SURFACE_COLOR,
    TEXT_COLOR,
)

ColorLike = QColor | str

CHIP_RADIUS = 8.0
CHIP_TEXT_SIZE = 13
CHIP_MATCHED_FILL_ALPHA = 0.18
CHIP_BORDER_WIDTH = 1.0
BAR_LABEL_WIDTH = 70.0
BAR_VALUE_WIDTH = 52.0
BAR_GAP = 12.0
BAR_TRACK_HEIGHT = 10.0
BAR_LABEL_SIZE = 12
BAR_VALUE_SIZE = 13
CAPTION_SIZE = 11
CAPTION_LETTER_SPACING = 0.9
ARROW_HEAD_LENGTH = 9.0
ARROW_HEAD_ANGLE_DEGREES = 28.0
LINK_SAMPLES = 40
DEFAULT_LINE_WIDTH = 2.0
DEFAULT_CARD_RADIUS = 10.0


def clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, value))


def lerp(start: float, end: float, fraction: float) -> float:
    return start + (end - start) * fraction


def ease_out_cubic(progress: float) -> float:
    remaining = 1.0 - clamp_unit(progress)
    return 1.0 - remaining**3


def ease_in_out(progress: float) -> float:
    value = clamp_unit(progress)
    if value < 0.5:
        return 4 * value**3
    return 1.0 - (-2 * value + 2) ** 3 / 2


def segment_progress(progress: float, start: float, end: float) -> float:
    if end <= start:
        raise ValueError(f"A segment must end after it starts: {start!r} to {end!r}")
    return clamp_unit((progress - start) / (end - start))


def to_color(color: ColorLike) -> QColor:
    return QColor(color)


def with_alpha(color: ColorLike, alpha: float) -> QColor:
    result = to_color(color)
    result.setAlphaF(clamp_unit(alpha) * result.alphaF())
    return result


def mix_colors(first: ColorLike, second: ColorLike, fraction: float) -> QColor:
    start, end = to_color(first), to_color(second)
    weight = clamp_unit(fraction)
    return QColor.fromRgbF(
        lerp(start.redF(), end.redF(), weight),
        lerp(start.greenF(), end.greenF(), weight),
        lerp(start.blueF(), end.blueF(), weight),
        lerp(start.alphaF(), end.alphaF(), weight),
    )


def text_font(pixel_size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    font = QFont(QApplication.font())
    font.setPixelSize(pixel_size)
    font.setWeight(weight)
    return font


def monospace_font(pixel_size: int, weight: QFont.Weight = QFont.Weight.DemiBold) -> QFont:
    font = QFont()
    font.setFamilies(list(MONOSPACE_FONT_FAMILIES))
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPixelSize(pixel_size)
    font.setWeight(weight)
    return font


def draw_text(
    painter: QPainter,
    rect: QRectF,
    text: str,
    color: ColorLike,
    font: QFont,
    alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
    wrap: bool = False,
) -> None:
    flags = int(alignment) | (int(Qt.TextFlag.TextWordWrap) if wrap else 0)
    painter.save()
    painter.setFont(font)
    painter.setPen(to_color(color))
    painter.drawText(rect, flags, text)
    painter.restore()


def draw_card(
    painter: QPainter,
    rect: QRectF,
    fill: ColorLike = SURFACE_COLOR,
    border: ColorLike | None = None,
    radius: float = DEFAULT_CARD_RADIUS,
) -> None:
    painter.save()
    painter.setBrush(QBrush(to_color(fill)))
    painter.setPen(QPen(to_color(border), CHIP_BORDER_WIDTH) if border is not None else Qt.PenStyle.NoPen)
    painter.drawRoundedRect(rect, radius, radius)
    painter.restore()


def draw_chip(painter: QPainter, rect: QRectF, text: str, highlighted: float) -> None:
    weight = clamp_unit(highlighted)
    fill = mix_colors(SURFACE_COLOR, with_alpha(PRIMARY_COLOR, CHIP_MATCHED_FILL_ALPHA), weight)
    border = mix_colors(BORDER_COLOR, PRIMARY_COLOR, weight)
    text_color = mix_colors(DISABLED_TEXT_COLOR, TEXT_COLOR, weight)
    inner_rect = rect.adjusted(CHIP_BORDER_WIDTH / 2, CHIP_BORDER_WIDTH / 2, -CHIP_BORDER_WIDTH / 2, -CHIP_BORDER_WIDTH / 2)
    painter.save()
    painter.setBrush(QBrush(to_color(SURFACE_COLOR)))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(inner_rect, CHIP_RADIUS, CHIP_RADIUS)
    painter.setBrush(QBrush(fill))
    painter.setPen(QPen(border, CHIP_BORDER_WIDTH))
    painter.drawRoundedRect(inner_rect, CHIP_RADIUS, CHIP_RADIUS)
    painter.restore()
    font_weight = QFont.Weight.DemiBold if weight >= 0.5 else QFont.Weight.Normal
    draw_text(painter, rect, text, text_color, text_font(CHIP_TEXT_SIZE, font_weight), Qt.AlignmentFlag.AlignCenter)


def draw_bar(painter: QPainter, rect: QRectF, fraction: float, color: ColorLike, label: str, value_text: str) -> None:
    label_rect = QRectF(rect.left(), rect.top(), BAR_LABEL_WIDTH, rect.height())
    value_rect = QRectF(rect.right() - BAR_VALUE_WIDTH, rect.top(), BAR_VALUE_WIDTH, rect.height())
    track_left = label_rect.right() + BAR_GAP
    track_width = max(0.0, value_rect.left() - BAR_GAP - track_left)
    track_rect = QRectF(track_left, rect.center().y() - BAR_TRACK_HEIGHT / 2, track_width, BAR_TRACK_HEIGHT)
    radius = BAR_TRACK_HEIGHT / 2
    draw_text(painter, label_rect, label, TEXT_COLOR, text_font(BAR_LABEL_SIZE, QFont.Weight.DemiBold))
    draw_card(painter, track_rect, SURFACE_COLOR, None, radius)
    fill_width = track_width * clamp_unit(fraction)
    if fill_width > 0:
        draw_card(painter, QRectF(track_rect.left(), track_rect.top(), max(fill_width, BAR_TRACK_HEIGHT), BAR_TRACK_HEIGHT), color, None, radius)
    draw_value(painter, value_rect, value_text, TEXT_COLOR, BAR_VALUE_SIZE, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)


def draw_arrow(painter: QPainter, start: QPointF, end: QPointF, color: ColorLike, width: float = DEFAULT_LINE_WIDTH) -> None:
    angle = math.atan2(end.y() - start.y(), end.x() - start.x())
    spread = math.radians(ARROW_HEAD_ANGLE_DEGREES)
    head = QPolygonF(
        [
            end,
            QPointF(end.x() - ARROW_HEAD_LENGTH * math.cos(angle - spread), end.y() - ARROW_HEAD_LENGTH * math.sin(angle - spread)),
            QPointF(end.x() - ARROW_HEAD_LENGTH * math.cos(angle + spread), end.y() - ARROW_HEAD_LENGTH * math.sin(angle + spread)),
        ]
    )
    painter.save()
    painter.setPen(QPen(to_color(color), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.drawLine(start, end)
    painter.setBrush(QBrush(to_color(color)))
    painter.drawPolygon(head)
    painter.restore()


def draw_link(
    painter: QPainter,
    start: QPointF,
    end: QPointF,
    progress: float,
    color: ColorLike,
    width: float = DEFAULT_LINE_WIDTH,
) -> None:
    visible = clamp_unit(progress)
    if visible <= 0:
        return
    middle_y = (start.y() + end.y()) / 2
    curve = QPainterPath(start)
    curve.cubicTo(QPointF(start.x(), middle_y), QPointF(end.x(), middle_y), end)
    sample_count = max(2, math.ceil(LINK_SAMPLES * visible))
    partial = QPainterPath(start)
    for sample in range(1, sample_count + 1):
        partial.lineTo(curve.pointAtPercent(visible * sample / sample_count))
    painter.save()
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(to_color(color), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.drawPath(partial)
    painter.restore()


def caption_font() -> QFont:
    font = text_font(CAPTION_SIZE, QFont.Weight.DemiBold)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, CAPTION_LETTER_SPACING)
    return font


def draw_caption(painter: QPainter, position: QPointF | QRectF, text: str, color: ColorLike = SECONDARY_TEXT_COLOR) -> None:
    font = caption_font()
    caption = text.upper()
    if isinstance(position, QRectF):
        draw_text(painter, position, caption, color, font)
        return
    painter.save()
    painter.setFont(font)
    painter.setPen(to_color(color))
    painter.drawText(QPointF(position.x(), position.y() + painter.fontMetrics().ascent()), caption)
    painter.restore()


def draw_value(
    painter: QPainter,
    rect: QRectF,
    text: str,
    color: ColorLike,
    size: int,
    alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
) -> None:
    draw_text(painter, rect, text, color, monospace_font(size), alignment)
