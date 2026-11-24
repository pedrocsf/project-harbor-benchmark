import math
from collections.abc import Iterator
from contextlib import contextmanager

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QFont, QFontMetricsF, QPainter, QPen

from domain.explanations.timeline import TimelinePosition
from presentation.views.metric_explorer.painting import ColorLike, clamp_unit, to_color

DASH_PATTERN = (4.0, 4.0)
DEFAULT_BORDER_WIDTH = 1.0
WRAP_CACHE_LIMIT = 512
FULL_TURN = 2 * math.pi

_wrap_cache: dict[tuple[str, str, int, int], tuple[str, ...]] = {}


def step_phase(position: TimelinePosition, step_index: int) -> float:
    if position.step_index > step_index:
        return 1.0
    if position.step_index < step_index:
        return 0.0
    return clamp_unit(position.step_progress)


def is_active_step(position: TimelinePosition, step_index: int) -> bool:
    return position.step_index == step_index


def wave(progress: float, cycles: float) -> float:
    return 0.5 - 0.5 * math.cos(FULL_TURN * cycles * progress)


@contextmanager
def fitted_area(painter: QPainter, area: QRectF, minimum_width: float, minimum_height: float) -> Iterator[QRectF]:
    scale = min(1.0, area.width() / minimum_width, area.height() / minimum_height)
    painter.save()
    painter.setClipRect(area, Qt.ClipOperation.IntersectClip)
    painter.translate(area.topLeft())
    painter.scale(scale, scale)
    try:
        yield QRectF(0.0, 0.0, area.width() / scale, area.height() / scale)
    finally:
        painter.restore()


@contextmanager
def faded(painter: QPainter, opacity: float) -> Iterator[None]:
    painter.save()
    painter.setOpacity(painter.opacity() * clamp_unit(opacity))
    try:
        yield
    finally:
        painter.restore()


@contextmanager
def clipped_to(painter: QPainter, rect: QRectF) -> Iterator[None]:
    painter.save()
    painter.setClipRect(rect, Qt.ClipOperation.IntersectClip)
    try:
        yield
    finally:
        painter.restore()


def draw_outlined_card(
    painter: QPainter,
    rect: QRectF,
    fill: ColorLike,
    border: ColorLike,
    radius: float,
    dashed: bool = False,
) -> None:
    pen = QPen(to_color(border), DEFAULT_BORDER_WIDTH)
    if dashed:
        pen.setDashPattern(list(DASH_PATTERN))
    inset = DEFAULT_BORDER_WIDTH / 2
    painter.save()
    painter.setBrush(QBrush(to_color(fill)))
    painter.setPen(pen)
    painter.drawRoundedRect(rect.adjusted(inset, inset, -inset, -inset), radius, radius)
    painter.restore()


def draw_dashed_line(painter: QPainter, start: QPointF, end: QPointF, color: ColorLike, width: float = DEFAULT_BORDER_WIDTH) -> None:
    pen = QPen(to_color(color), width)
    pen.setDashPattern(list(DASH_PATTERN))
    painter.save()
    painter.setPen(pen)
    painter.drawLine(start, end)
    painter.restore()


def draw_line(painter: QPainter, start: QPointF, end: QPointF, color: ColorLike, width: float = DEFAULT_BORDER_WIDTH) -> None:
    painter.save()
    painter.setPen(QPen(to_color(color), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(start, end)
    painter.restore()


def draw_dot(painter: QPainter, center: QPointF, radius: float, color: ColorLike) -> None:
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(to_color(color)))
    painter.drawEllipse(center, radius, radius)
    painter.restore()


def text_width(text: str, font: QFont) -> float:
    return QFontMetricsF(font).horizontalAdvance(text)


def elide_text(text: str, font: QFont, width: float) -> str:
    return QFontMetricsF(font).elidedText(text, Qt.TextElideMode.ElideRight, max(0.0, width))


def wrap_text(text: str, font: QFont, width: float, maximum_lines: int) -> tuple[str, ...]:
    key = (text, font.key(), round(width), maximum_lines)
    cached = _wrap_cache.get(key)
    if cached is not None:
        return cached
    if len(_wrap_cache) >= WRAP_CACHE_LIMIT:
        _wrap_cache.clear()
    lines = _wrap_words(text, font, width, maximum_lines)
    _wrap_cache[key] = lines
    return lines


def _wrap_words(text: str, font: QFont, width: float, maximum_lines: int) -> tuple[str, ...]:
    metrics = QFontMetricsF(font)
    words = text.split()
    lines: list[str] = []
    current = ""
    for index, word in enumerate(words):
        candidate = f"{current} {word}" if current else word
        if metrics.horizontalAdvance(candidate) <= width or not current:
            current = candidate
            continue
        if len(lines) == maximum_lines - 1:
            remaining = " ".join([current, *words[index:]])
            return (*lines, metrics.elidedText(remaining, Qt.TextElideMode.ElideRight, width))
        lines.append(metrics.elidedText(current, Qt.TextElideMode.ElideRight, width))
        current = word
    if current or not lines:
        lines.append(metrics.elidedText(current, Qt.TextElideMode.ElideRight, width))
    return tuple(lines[:maximum_lines])


def largest_fitting_font(text: str, sizes: tuple[int, ...], width: float, font_factory) -> QFont:
    for size in sizes:
        font = font_factory(size)
        if text_width(text, font) <= width:
            return font
    return font_factory(sizes[-1])
