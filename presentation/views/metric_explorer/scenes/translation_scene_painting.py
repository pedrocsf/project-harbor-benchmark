import string
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QFont, QFontMetricsF, QPainter, QPen

from domain.explanations.timeline import TimelinePosition
from presentation.views.branding import (
    BORDER_COLOR,
    DISABLED_TEXT_COLOR,
    LABEL_TEXT_COLOR,
    PRIMARY_COLOR,
    SECONDARY_TEXT_COLOR,
    SURFACE_COLOR,
    TEXT_COLOR,
)
from presentation.views.metric_explorer.painting import (
    CHIP_TEXT_SIZE,
    clamp_unit,
    draw_card,
    draw_chip,
    draw_text,
    ease_out_cubic,
    mix_colors,
    monospace_font,
    text_font,
    to_color,
    with_alpha,
)

SCORE_FORMAT = "{:.3f}"
MORE_BADGE_FORMAT = "+{count}"
MORE_BADGE_WIDTH = 34.0
WINDOW_BORDER_WIDTH = 2.0
WINDOW_RADIUS = 6.0
WINDOW_MARGIN = 2.0
DIVIDER_WIDTH = 1.0
DASH_PATTERN = (4.0, 3.0)
CELL_TEXT_SIZE = 14
CELL_RADIUS = 4.0
CELL_MATCH_ALPHA = 0.3
CHIP_HORIZONTAL_PADDING = 18.0
BADGE_TEXT_SIZE = 11
EMPTY_TEXT_SIZE = 12
PUNCTUATION_MARKS = frozenset(string.punctuation)
NO_WINDOW = -1
SPACE_GLYPH = "␣"


@dataclass(frozen=True)
class StripLayout:
    unit_rects: tuple[QRectF, ...]
    badge_rect: QRectF | None
    hidden_count: int
    bottom: float


@dataclass(frozen=True)
class SweepFrame:
    window_index: int
    covered_units: frozenset[int]
    matched_count: int


def parameter_flag(parameters: Mapping[str, object], key: str, default: bool = False) -> bool:
    return bool(parameters.get(key, default))


def format_score(value: float) -> str:
    return SCORE_FORMAT.format(value)


def stage_progress(position: TimelinePosition, step_index: int) -> float:
    if position.step_index > step_index:
        return 1.0
    if position.step_index < step_index:
        return 0.0
    return clamp_unit(position.step_progress)


def count_up(value: float, progress: float) -> float:
    return value * ease_out_cubic(progress)


def ngrams(units: Sequence[str], order: int) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(units[start : start + order]) for start in range(len(units) - order + 1))


@lru_cache(maxsize=512)
def clipped_match_flags(answer_units: tuple[str, ...], reference_units: tuple[str, ...], order: int) -> tuple[bool, ...]:
    if order <= 0:
        raise ValueError(f"An n-gram order must be positive: {order!r}")
    available = Counter(ngrams(reference_units, order))
    flags = []
    for gram in ngrams(answer_units, order):
        is_match = available[gram] > 0
        if is_match:
            available[gram] -= 1
        flags.append(is_match)
    return tuple(flags)


def characters_without_spaces(text: str, lowercase: bool = False) -> tuple[str, ...]:
    return tuple("".join(_cased(text, lowercase).split()))


def characters_with_spaces(text: str, lowercase: bool = False) -> tuple[str, ...]:
    return tuple(_cased(text, lowercase))


def space_visible_labels(characters: Sequence[str]) -> tuple[str, ...]:
    return tuple(SPACE_GLYPH if character.isspace() else character for character in characters)


def _cased(text: str, lowercase: bool) -> str:
    return text.lower() if lowercase else text


def chrf_words(text: str, lowercase: bool = False) -> tuple[str, ...]:
    words: list[str] = []
    for word in _cased(text, lowercase).split():
        words.extend(_split_edge_punctuation(word))
    return tuple(words)


def _split_edge_punctuation(word: str) -> list[str]:
    if len(word) == 1:
        return [word]
    if word[-1] in PUNCTUATION_MARKS:
        return [word[:-1], word[-1]]
    if word[0] in PUNCTUATION_MARKS:
        return [word[0], word[1:]]
    return [word]


def sweep_frame(flags: tuple[bool, ...], order: int, progress: float, visible_windows: int) -> SweepFrame:
    window_count = min(len(flags), visible_windows)
    if progress >= 1.0 or window_count <= 0:
        return SweepFrame(NO_WINDOW, _covered(flags, order, len(flags)), sum(flags))
    window_index = min(int(clamp_unit(progress) * window_count), window_count - 1)
    seen = window_index + 1
    return SweepFrame(window_index, _covered(flags, order, seen), sum(flags[:seen]))


def _covered(flags: tuple[bool, ...], order: int, seen: int) -> frozenset[int]:
    return frozenset(unit for start in range(seen) if flags[start] for unit in range(start, start + order))


def chip_widths(labels: Sequence[str], maximum_width: float) -> tuple[float, ...]:
    metrics = QFontMetricsF(text_font(CHIP_TEXT_SIZE, QFont.Weight.DemiBold))
    return tuple(min(maximum_width, metrics.horizontalAdvance(label) + CHIP_HORIZONTAL_PADDING) for label in labels)


def layout_flow(widths: Sequence[float], bounds: QRectF, row_height: float, gap: float, max_rows: int) -> StripLayout:
    rects: list[QRectF] = []
    left, row, cursor = bounds.left(), 0, bounds.left()
    for width in widths:
        clamped = min(width, bounds.width())
        if cursor > left and cursor + clamped > bounds.right():
            row, cursor = row + 1, left
        if row >= max_rows:
            break
        rects.append(QRectF(cursor, bounds.top() + row * (row_height + gap), clamped, row_height))
        cursor += clamped + gap
    return _with_badge(rects, len(widths), bounds, row_height, gap)


def _with_badge(rects: list[QRectF], total: int, bounds: QRectF, row_height: float, gap: float) -> StripLayout:
    if len(rects) == total:
        return StripLayout(tuple(rects), None, 0, _bottom(rects, bounds))
    while rects and rects[-1].right() + gap + MORE_BADGE_WIDTH > bounds.right():
        rects.pop()
    badge_left = rects[-1].right() + gap if rects else bounds.left()
    badge_top = rects[-1].top() if rects else bounds.top()
    badge = QRectF(badge_left, badge_top, MORE_BADGE_WIDTH, row_height)
    return StripLayout(tuple(rects), badge, total - len(rects), max(_bottom(rects, bounds), badge.bottom()))


def _bottom(rects: Sequence[QRectF], bounds: QRectF) -> float:
    return max((rect.bottom() for rect in rects), default=bounds.top())


def layout_cells(count: int, bounds: QRectF, preferred_width: float, minimum_width: float) -> StripLayout:
    if count == 0:
        return StripLayout((), None, 0, bounds.bottom())
    cell_width = max(minimum_width, min(preferred_width, bounds.width() / count))
    return layout_flow([cell_width] * count, bounds, bounds.height(), 0.0, 1)


def elide(text: str, font: QFont, width: float) -> str:
    return QFontMetricsF(font).elidedText(text, Qt.TextElideMode.ElideRight, max(0.0, width))


def draw_token_strip(painter: QPainter, layout: StripLayout, labels: Sequence[str], highlights: Sequence[float]) -> None:
    font = text_font(CHIP_TEXT_SIZE, QFont.Weight.DemiBold)
    for index, rect in enumerate(layout.unit_rects):
        draw_chip(painter, rect, elide(labels[index], font, rect.width() - CHIP_HORIZONTAL_PADDING / 2), highlights[index])
    draw_more_badge(painter, layout)


def draw_character_strip(painter: QPainter, layout: StripLayout, characters: Sequence[str], highlights: Sequence[float]) -> None:
    font = monospace_font(CELL_TEXT_SIZE)
    for index, rect in enumerate(layout.unit_rects):
        weight = clamp_unit(highlights[index])
        if weight > 0:
            draw_card(painter, rect.adjusted(1, 1, -1, -1), with_alpha(PRIMARY_COLOR, CELL_MATCH_ALPHA * weight), None, CELL_RADIUS)
        draw_text(painter, rect, characters[index], mix_colors(LABEL_TEXT_COLOR, TEXT_COLOR, weight), font, Qt.AlignmentFlag.AlignCenter)
    draw_more_badge(painter, layout)


def draw_more_badge(painter: QPainter, layout: StripLayout) -> None:
    if layout.badge_rect is None:
        return
    draw_card(painter, layout.badge_rect, SURFACE_COLOR, BORDER_COLOR, CELL_RADIUS)
    text = MORE_BADGE_FORMAT.format(count=layout.hidden_count)
    draw_text(painter, layout.badge_rect, text, SECONDARY_TEXT_COLOR, text_font(BADGE_TEXT_SIZE), Qt.AlignmentFlag.AlignCenter)


def draw_window(painter: QPainter, layout: StripLayout, start: int, order: int) -> None:
    rows: dict[float, QRectF] = {}
    for rect in layout.unit_rects[start : start + order]:
        rows[rect.top()] = rows[rect.top()].united(rect) if rect.top() in rows else QRectF(rect)
    painter.save()
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(to_color(PRIMARY_COLOR), WINDOW_BORDER_WIDTH))
    for rect in rows.values():
        painter.drawRoundedRect(rect.adjusted(-WINDOW_MARGIN, -WINDOW_MARGIN, WINDOW_MARGIN, WINDOW_MARGIN), WINDOW_RADIUS, WINDOW_RADIUS)
    painter.restore()


def draw_empty_strip(painter: QPainter, rect: QRectF, text: str) -> None:
    font = text_font(EMPTY_TEXT_SIZE)
    font.setItalic(True)
    draw_text(painter, rect, text, DISABLED_TEXT_COLOR, font)


def draw_divider(painter: QPainter, left: float, right: float, y: float) -> None:
    painter.save()
    painter.setPen(QPen(to_color(BORDER_COLOR), DIVIDER_WIDTH))
    painter.drawLine(QPointF(left, y), QPointF(right, y))
    painter.restore()


def draw_dashed_line(painter: QPainter, start: QPointF, end: QPointF, color: str, width: float) -> None:
    pen = QPen(to_color(color), width)
    pen.setDashPattern(list(DASH_PATTERN))
    painter.save()
    painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
    painter.setPen(pen)
    painter.drawLine(start, end)
    painter.restore()
