from collections.abc import Sequence
from dataclasses import dataclass

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QFont, QPainter, QPen

from domain.explanations.timeline import TimelinePosition
from presentation.views.branding import (
    DISABLED_TEXT_COLOR,
    LABEL_TEXT_COLOR,
    PRIMARY_COLOR,
    SECONDARY_TEXT_COLOR,
    STRONG_BORDER_COLOR,
    TEXT_COLOR,
)
from presentation.views.metric_explorer.painting import (
    clamp_unit,
    draw_caption,
    draw_text,
    draw_value,
    ease_out_cubic,
    lerp,
    text_font,
    with_alpha,
)
from presentation.views.metric_explorer.scenes.semantic_scene_painting import elide_text
from presentation.views.metric_explorer.scenes.token_scene_painting import (
    BAR_HEIGHT,
    CAPTION_HEIGHT,
    COUNTER_HEIGHT,
    ChipStyle,
    bar_fill,
    counter_rects,
    paint_counter,
    paint_score_bar,
    pulse,
    staggered,
)

CARD_RADIUS = 10.0
CARD_PADDING = 12.0
CARD_GAP = 8.0
MAXIMUM_CARD_HEIGHT = 54.0
MINIMUM_CARD_HEIGHT = 34.0
BADGE_SIZE = 26.0
BADGE_TEXT_SIZE = 12
TITLE_TEXT_SIZE = 11
BODY_TEXT_SIZE = 13
TRAILING_TEXT_SIZE = 13
TRAILING_WIDTH = 120.0
TITLE_HEIGHT = 15.0
SECTION_GAP = 10.0
BOTTOM_GAP = 12.0
APPEAR_SHIFT = 10.0
ITEM_SHARE = 0.45
HIDDEN_ROWS_FORMAT = "+{count} more not shown"
CUTOFF_LABEL_FORMAT = "k = {k}"
CUTOFF_DASH = (5.0, 4.0)
CUTOFF_LABEL_WIDTH = 60.0
COUNTER_COUNT = 2
COUNTER_PULSE_CYCLES = 2.0


@dataclass(frozen=True)
class CardContent:
    badge: str
    title: str
    body: str
    trailing: str = ""
    trailing_color: str = TEXT_COLOR


@dataclass(frozen=True)
class SceneFrame:
    content: QRectF
    counters: tuple[QRectF, ...]
    bar: QRectF


def scene_frame(area: QRectF) -> SceneFrame:
    bar = QRectF(area.left(), area.bottom() - BAR_HEIGHT, area.width(), BAR_HEIGHT)
    counters_top = bar.top() - BOTTOM_GAP - COUNTER_HEIGHT
    counters = counter_rects(area, counters_top, COUNTER_COUNT)
    content = QRectF(area.left(), area.top(), area.width(), max(0.0, counters_top - BOTTOM_GAP - area.top()))
    return SceneFrame(content, counters, bar)


def stack_rows(top: float, bottom: float, left: float, width: float, count: int) -> tuple[tuple[QRectF, ...], int]:
    if count <= 0:
        return (), 0
    available = max(0.0, bottom - top)
    height = min(MAXIMUM_CARD_HEIGHT, (available - CARD_GAP * (count - 1)) / count)
    if height >= MINIMUM_CARD_HEIGHT:
        return tuple(QRectF(left, top + index * (height + CARD_GAP), width, height) for index in range(count)), 0
    fitting = max(0, int((available + CARD_GAP) // (MINIMUM_CARD_HEIGHT + CARD_GAP)))
    visible = min(count, fitting)
    rows = tuple(QRectF(left, top + index * (MINIMUM_CARD_HEIGHT + CARD_GAP), width, MINIMUM_CARD_HEIGHT) for index in range(visible))
    return rows, count - visible


def appear_fraction(position: TimelinePosition, step_index: int, item_index: int, item_count: int) -> float:
    if position.step_index > step_index:
        return 1.0
    if position.step_index < step_index:
        return 0.0
    return staggered(position.step_progress, item_index, item_count, ITEM_SHARE)


def paint_card(painter: QPainter, rect: QRectF, content: CardContent, style: ChipStyle, appear: float = 1.0) -> None:
    visible = clamp_unit(appear)
    if visible <= 0:
        return
    painter.save()
    painter.setOpacity(painter.opacity() * visible)
    shifted = rect.translated(0, lerp(APPEAR_SHIFT, 0.0, ease_out_cubic(visible)))
    painter.setBrush(style.fill)
    pen = QPen(style.border, 1.0)
    if style.dashed:
        pen.setDashPattern([4.0, 3.0])
    painter.setPen(pen)
    painter.drawRoundedRect(shifted.adjusted(0.5, 0.5, -0.5, -0.5), CARD_RADIUS, CARD_RADIUS)
    _paint_card_content(painter, shifted, content, style)
    painter.restore()


def _paint_card_content(painter: QPainter, rect: QRectF, content: CardContent, style: ChipStyle) -> None:
    badge_rect = QRectF(rect.left() + CARD_PADDING, rect.center().y() - BADGE_SIZE / 2, BADGE_SIZE, BADGE_SIZE)
    painter.save()
    painter.setBrush(with_alpha(style.border, 0.22))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(badge_rect)
    painter.restore()
    draw_value(painter, badge_rect, content.badge, style.text, BADGE_TEXT_SIZE, Qt.AlignmentFlag.AlignCenter)
    trailing_width = TRAILING_WIDTH if content.trailing else 0.0
    text_left = badge_rect.right() + CARD_PADDING
    text_width = max(0.0, rect.right() - CARD_PADDING - trailing_width - text_left)
    body_font = text_font(BODY_TEXT_SIZE, QFont.Weight.DemiBold if style.bold else QFont.Weight.Normal)
    if content.title and rect.height() >= MAXIMUM_CARD_HEIGHT - 4:
        title_font = text_font(TITLE_TEXT_SIZE)
        title_rect = QRectF(text_left, rect.top() + 7, text_width, TITLE_HEIGHT)
        draw_text(painter, title_rect, elide_text(content.title, title_font, text_width), SECONDARY_TEXT_COLOR, title_font)
        body_rect = QRectF(text_left, title_rect.bottom(), text_width, rect.bottom() - 6 - title_rect.bottom())
    else:
        body_rect = QRectF(text_left, rect.top(), text_width, rect.height())
    draw_text(painter, body_rect, elide_text(content.body, body_font, text_width), style.text, body_font)
    if content.trailing:
        trailing_rect = QRectF(rect.right() - CARD_PADDING - trailing_width, rect.top(), trailing_width, rect.height())
        draw_value(painter, trailing_rect, content.trailing, content.trailing_color, TRAILING_TEXT_SIZE, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)


def paint_hidden_rows(painter: QPainter, top: float, left: float, width: float, hidden_count: int) -> None:
    if hidden_count <= 0:
        return
    rect = QRectF(left, top, width, CAPTION_HEIGHT)
    draw_text(painter, rect, HIDDEN_ROWS_FORMAT.format(count=hidden_count), DISABLED_TEXT_COLOR, text_font(TITLE_TEXT_SIZE))


def paint_cutoff(painter: QPainter, rows: Sequence[QRectF], cutoff: int, opacity: float) -> None:
    if cutoff >= len(rows) or cutoff <= 0 or opacity <= 0:
        return
    line_y = (rows[cutoff - 1].bottom() + rows[cutoff].top()) / 2
    left, right = rows[0].left(), rows[0].right()
    painter.save()
    painter.setOpacity(painter.opacity() * clamp_unit(opacity))
    pen = QPen(with_alpha(PRIMARY_COLOR, 0.9), 1.5)
    pen.setDashPattern(list(CUTOFF_DASH))
    painter.setPen(pen)
    painter.drawLine(int(left), int(line_y), int(right - CUTOFF_LABEL_WIDTH), int(line_y))
    label_rect = QRectF(right - CUTOFF_LABEL_WIDTH + 6, line_y - CAPTION_HEIGHT / 2, CUTOFF_LABEL_WIDTH - 6, CAPTION_HEIGHT)
    draw_value(painter, label_rect, CUTOFF_LABEL_FORMAT.format(k=cutoff), PRIMARY_COLOR, TITLE_TEXT_SIZE, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    painter.restore()


def paint_section_caption(painter: QPainter, rect: QRectF, text: str) -> None:
    draw_caption(painter, rect, text)


def paint_counters(
    painter: QPainter,
    frame: SceneFrame,
    labels: tuple[str, str],
    values: tuple[str, str] | None,
    position: TimelinePosition,
    score_step: int,
) -> None:
    glow = pulse(position.step_progress, COUNTER_PULSE_CYCLES) if position.step_index == score_step else 0.0
    for rect, label, index in zip(frame.counters, labels, range(COUNTER_COUNT)):
        if values is None:
            paint_counter(painter, rect, label, "…", SECONDARY_TEXT_COLOR)
            continue
        color = PRIMARY_COLOR if index == 0 else LABEL_TEXT_COLOR
        paint_counter(painter, rect, label, values[index], color, glow)


def paint_final_bar(painter: QPainter, frame: SceneFrame, label: str, score: float, position: TimelinePosition, score_step: int) -> None:
    fill, reached = bar_fill(position.step_index, score_step, position.step_progress)
    paint_score_bar(painter, frame.bar, label, score, fill, reached)


def short_text(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def caption_rect(left: float, top: float, width: float) -> QRectF:
    return QRectF(left, top, width, CAPTION_HEIGHT)


def section_top(rect: QRectF) -> float:
    return rect.bottom() + SECTION_GAP


def rule_color() -> str:
    return STRONG_BORDER_COLOR
