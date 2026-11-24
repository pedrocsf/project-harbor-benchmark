import math
from collections.abc import Mapping
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen

from domain.explanations.walkthrough_details import NormalizationDetails
from domain.scoring.text_normalization import DEFAULT_NORMALIZATION, NormalizationOptions
from presentation.views.branding import (
    BORDER_COLOR,
    DISABLED_TEXT_COLOR,
    LABEL_TEXT_COLOR,
    PRIMARY_COLOR,
    PRIMARY_HOVER_COLOR,
    SECONDARY_TEXT_COLOR,
    STRONG_BORDER_COLOR,
    SUCCESS_COLOR,
    SURFACE_COLOR,
    TEXT_COLOR,
    WARNING_COLOR,
)
from presentation.views.metric_explorer.painting import (
    CHIP_RADIUS,
    clamp_unit,
    draw_bar,
    draw_card,
    draw_text,
    draw_value,
    ease_out_cubic,
    lerp,
    mix_colors,
    monospace_font,
    text_font,
    with_alpha,
)

CAPTION_HEIGHT = 16.0
CHIP_BORDER_WIDTH = 1.0
CHIP_DASH_PATTERN = (4.0, 3.0)
CHIP_APPEAR_SCALE = 0.82
PRIMARY_TINT_ALPHA = 0.18
SUCCESS_TINT_ALPHA = 0.16
WARNING_TINT_ALPHA = 0.2
EMPTY_TOKENS_TEXT = "no tokens"
COUNTER_HEIGHT = 62.0
COUNTER_GAP = 10.0
COUNTER_PADDING = 14.0
COUNTER_LABEL_SIZE = 11
COUNTER_LABEL_HEIGHT = 16.0
COUNTER_VALUE_SIZE = 22
COUNTER_VALUE_HEIGHT = 28.0
COUNTER_RADIUS = 10.0
COUNTER_GLOW_WIDTH = 4.0
COUNTER_GLOW_ALPHA = 0.25
BAR_HEIGHT = 22.0
BAR_GAP = 8.0
DIMMED_OPACITY = 0.45
PENDING_VALUE_TEXT = "–"
PARAMETERS_HINT = "Change them with “Parameters…”."
ENABLED_OPTIONS_FORMAT = "On: {items}."
DISABLED_OPTIONS_FORMAT = "Off: {items}."
OPTION_SEPARATOR = ", "
COLLAPSE_SPACES_LABEL = "collapse spaces"
LOWERCASE_LABEL = "lowercase"
STRIP_ACCENTS_LABEL = "strip accents"
REMOVE_PUNCTUATION_LABEL = "drop punctuation"
ARTICLE_LABELS = {
    "english": "drop English articles",
    "portuguese": "drop Portuguese articles",
    "english_portuguese": "drop English and Portuguese articles",
}
NO_ARTICLES_LABEL = "drop articles"
NO_ARTICLES_NAME = "none"
FUNCTION_NAMES = (
    ("collapse", None),
    ("drop_articles", "articles"),
    ("drop_punct", "remove_punctuation"),
    ("strip_accents", "strip_accents"),
    ("lower", "lowercase"),
)
FORMULA_BREAK = "<br>&nbsp;&nbsp;"
FORMULA_HEAD_FUNCTIONS = 2
NORMALIZATION_FORMULA = "n(x) = {expression}"
SCORE_FORMAT = "{:.3f}"
NOTE_SIZE = 12
VERDICT_MARK_STROKE = 2.2
VERDICT_MARK_SCALE = 0.4
VERDICT_APPEAR_SCALE = 0.8
VERDICT_HEIGHT = 44.0
VERDICT_MARK_SIZE = 40.0
VERDICT_GAP = 12.0
VERDICT_SCORE_SIZE = 24
VERDICT_SCORE_FORMAT = "score = {:g}"
VERDICT_MESSAGE_SIZE = 13
HIGHLIGHT_FORMAT = '<span style="color: {color}; font-weight: 600">{text}</span>'
QUOTE_FORMAT = "“{}”"
MAXIMUM_QUOTED_ITEMS = 3
MORE_ITEMS_FORMAT = "{count} more"


@dataclass(frozen=True)
class ChipMetrics:
    font_size: int
    height: float
    padding: float
    gap: float
    minimum_width: float


CHIP_SIZES = (
    ChipMetrics(13, 34.0, 12.0, 8.0, 44.0),
    ChipMetrics(12, 30.0, 9.0, 6.0, 36.0),
    ChipMetrics(11, 26.0, 7.0, 5.0, 28.0),
)


@dataclass(frozen=True)
class ChipStyle:
    fill: QColor
    border: QColor
    text: QColor
    dashed: bool = False
    bold: bool = False


class ChipState(Enum):
    NEUTRAL = "neutral"
    DIMMED = "dimmed"
    MATCHED = "matched"
    MISSING = "missing"
    SUCCESS = "success"
    FAILURE = "failure"


def _style_table() -> dict[ChipState, ChipStyle]:
    surface = QColor(SURFACE_COLOR)
    return {
        ChipState.NEUTRAL: ChipStyle(surface, QColor(BORDER_COLOR), QColor(LABEL_TEXT_COLOR)),
        ChipState.DIMMED: ChipStyle(surface, QColor(BORDER_COLOR), QColor(DISABLED_TEXT_COLOR)),
        ChipState.MATCHED: ChipStyle(with_alpha(PRIMARY_COLOR, PRIMARY_TINT_ALPHA), QColor(PRIMARY_COLOR), QColor(TEXT_COLOR), bold=True),
        ChipState.MISSING: ChipStyle(surface, QColor(WARNING_COLOR), QColor(WARNING_COLOR), dashed=True),
        ChipState.SUCCESS: ChipStyle(with_alpha(SUCCESS_COLOR, SUCCESS_TINT_ALPHA), QColor(SUCCESS_COLOR), QColor(TEXT_COLOR), bold=True),
        ChipState.FAILURE: ChipStyle(with_alpha(WARNING_COLOR, WARNING_TINT_ALPHA), QColor(WARNING_COLOR), QColor(TEXT_COLOR), bold=True),
    }


_STYLES: dict[ChipState, ChipStyle] = {}


def chip_style(state: ChipState) -> ChipStyle:
    if not _STYLES:
        _STYLES.update(_style_table())
    return _STYLES[state]


def blend_styles(first: ChipState, second: ChipState, fraction: float) -> ChipStyle:
    start, end = chip_style(first), chip_style(second)
    weight = clamp_unit(fraction)
    if weight <= 0:
        return start
    if weight >= 1:
        return end
    return ChipStyle(
        mix_colors(start.fill, end.fill, weight),
        mix_colors(start.border, end.border, weight),
        mix_colors(start.text, end.text, weight),
        end.dashed if weight >= 0.5 else start.dashed,
        end.bold if weight >= 0.5 else start.bold,
    )


def chip_font(metrics: ChipMetrics, bold: bool) -> QFont:
    return text_font(metrics.font_size, QFont.Weight.DemiBold if bold else QFont.Weight.Normal)


def chip_width(text: str, metrics: ChipMetrics, maximum_width: float) -> float:
    advance = QFontMetricsF(chip_font(metrics, True)).horizontalAdvance(text)
    return min(maximum_width, max(metrics.minimum_width, advance + 2 * metrics.padding))


@dataclass(frozen=True)
class FlowLayout:
    rects: tuple[QRectF, ...]
    row_count: int
    height: float


def flow_layout(widths: Sequence[float], maximum_width: float, metrics: ChipMetrics) -> FlowLayout:
    rects = []
    cursor_x, cursor_y, row_count = 0.0, 0.0, 1
    for width in widths:
        if cursor_x > 0 and cursor_x + width > maximum_width:
            cursor_x = 0.0
            cursor_y += metrics.height + metrics.gap
            row_count += 1
        rects.append(QRectF(cursor_x, cursor_y, width, metrics.height))
        cursor_x += width + metrics.gap
    return FlowLayout(tuple(rects), row_count, cursor_y + metrics.height)


def layout_tokens(tokens: Sequence[str], maximum_width: float, metrics: ChipMetrics) -> FlowLayout:
    return flow_layout([chip_width(token, metrics, maximum_width) for token in tokens], maximum_width, metrics)


def choose_chip_metrics(token_groups: Sequence[Sequence[str]], maximum_width: float, height_budget: float) -> ChipMetrics:
    layouts = [(metrics, [layout_tokens(group, maximum_width, metrics) for group in token_groups]) for metrics in CHIP_SIZES]
    for metrics, group_layouts in layouts:
        if all(layout.row_count == 1 for layout in group_layouts) and sum(layout.height for layout in group_layouts) <= height_budget:
            return metrics
    for metrics, group_layouts in layouts:
        if sum(layout.height for layout in group_layouts) <= height_budget:
            return metrics
    return CHIP_SIZES[-1]


def offset_rects(rects: Sequence[QRectF], origin: QPointF) -> tuple[QRectF, ...]:
    return tuple(rect.translated(origin) for rect in rects)


def elided(text: str, font: QFont, width: float) -> str:
    return QFontMetricsF(font).elidedText(text, Qt.TextElideMode.ElideRight, max(0.0, width))


def _chip_pen(style: ChipStyle) -> QPen:
    pen = QPen(style.border, CHIP_BORDER_WIDTH)
    if style.dashed:
        pen.setDashPattern(list(CHIP_DASH_PATTERN))
    return pen


def paint_chip(painter: QPainter, rect: QRectF, text: str, style: ChipStyle, metrics: ChipMetrics, appear: float = 1.0) -> None:
    visible = clamp_unit(appear)
    if visible <= 0:
        return
    inset = CHIP_BORDER_WIDTH / 2
    inner = rect.adjusted(inset, inset, -inset, -inset)
    scale = lerp(CHIP_APPEAR_SCALE, 1.0, ease_out_cubic(visible))
    painter.save()
    painter.setOpacity(painter.opacity() * visible)
    center = rect.center()
    painter.translate(center)
    painter.scale(scale, scale)
    painter.translate(-center)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(SURFACE_COLOR)))
    painter.drawRoundedRect(inner, CHIP_RADIUS, CHIP_RADIUS)
    painter.setBrush(QBrush(style.fill))
    painter.setPen(_chip_pen(style))
    painter.drawRoundedRect(inner, CHIP_RADIUS, CHIP_RADIUS)
    font = chip_font(metrics, style.bold)
    label = elided(text, font, rect.width() - metrics.padding)
    draw_text(painter, rect, label, style.text, font, Qt.AlignmentFlag.AlignCenter)
    painter.restore()


def paint_empty_slot(painter: QPainter, rect: QRectF, metrics: ChipMetrics, text: str = EMPTY_TOKENS_TEXT, color: str = STRONG_BORDER_COLOR) -> None:
    pen = QPen(QColor(color), CHIP_BORDER_WIDTH)
    pen.setDashPattern(list(CHIP_DASH_PATTERN))
    inset = CHIP_BORDER_WIDTH / 2
    painter.save()
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(pen)
    painter.drawRoundedRect(rect.adjusted(inset, inset, -inset, -inset), CHIP_RADIUS, CHIP_RADIUS)
    painter.restore()
    if text:
        font = chip_font(metrics, False)
        draw_text(painter, rect, elided(text, font, rect.width() - metrics.padding), DISABLED_TEXT_COLOR, font, Qt.AlignmentFlag.AlignCenter)


def empty_slot_width(metrics: ChipMetrics, maximum_width: float) -> float:
    return chip_width(EMPTY_TOKENS_TEXT, metrics, maximum_width) + 2 * metrics.padding


def staggered(progress: float, index: int, count: int, item_share: float) -> float:
    if count <= 1:
        return clamp_unit(progress)
    share = clamp_unit(item_share)
    start = index * (1.0 - share) / (count - 1)
    return clamp_unit((progress - start) / share) if share > 0 else float(progress >= start)


def pulse(progress: float, cycles: float) -> float:
    return 0.5 - 0.5 * math.cos(2 * math.pi * cycles * clamp_unit(progress))


def counter_rects(area: QRectF, top: float, count: int) -> tuple[QRectF, ...]:
    width = (area.width() - COUNTER_GAP * (count - 1)) / count
    return tuple(QRectF(area.left() + index * (width + COUNTER_GAP), top, width, COUNTER_HEIGHT) for index in range(count))


def paint_counter(painter: QPainter, rect: QRectF, label: str, value_text: str, value_color: str | QColor, glow: float = 0.0) -> None:
    draw_card(painter, rect, SURFACE_COLOR, None, COUNTER_RADIUS)
    if glow > 0:
        painter.save()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(with_alpha(PRIMARY_COLOR, COUNTER_GLOW_ALPHA * clamp_unit(glow)), COUNTER_GLOW_WIDTH))
        half = COUNTER_GLOW_WIDTH / 2
        painter.drawRoundedRect(rect.adjusted(half, half, -half, -half), COUNTER_RADIUS - half, COUNTER_RADIUS - half)
        painter.restore()
    content = rect.adjusted(COUNTER_PADDING, 0, -COUNTER_PADDING, 0)
    label_top = rect.center().y() - (COUNTER_LABEL_HEIGHT + COUNTER_VALUE_HEIGHT) / 2
    label_font = text_font(COUNTER_LABEL_SIZE)
    draw_text(painter, QRectF(content.left(), label_top, content.width(), COUNTER_LABEL_HEIGHT), elided(label, label_font, content.width()), SECONDARY_TEXT_COLOR, label_font)
    draw_value(painter, QRectF(content.left(), label_top + COUNTER_LABEL_HEIGHT, content.width(), COUNTER_VALUE_HEIGHT), value_text, value_color, COUNTER_VALUE_SIZE)


def bars_height(count: int) -> float:
    return count * BAR_HEIGHT + (count - 1) * BAR_GAP


def paint_score_bar(painter: QPainter, rect: QRectF, label: str, value: float, fill: float, reached: bool) -> None:
    painter.save()
    if not reached:
        painter.setOpacity(painter.opacity() * DIMMED_OPACITY)
        draw_bar(painter, rect, 0.0, PRIMARY_COLOR, label, PENDING_VALUE_TEXT)
        painter.restore()
        return
    shown = clamp_unit(fill)
    draw_bar(painter, rect, value * shown, PRIMARY_COLOR, label, SCORE_FORMAT.format(value * shown))
    painter.restore()


def bar_fill(step_index: int, bar_step: int, progress: float) -> tuple[float, bool]:
    if step_index < bar_step:
        return 0.0, False
    if step_index > bar_step:
        return 1.0, True
    return ease_out_cubic(progress), True


def paint_note(painter: QPainter, rect: QRectF, text: str, opacity: float = 1.0, color: str = SECONDARY_TEXT_COLOR) -> None:
    if opacity <= 0 or not text:
        return
    painter.save()
    painter.setOpacity(painter.opacity() * clamp_unit(opacity))
    draw_text(painter, rect, text, color, text_font(NOTE_SIZE), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, wrap=True)
    painter.restore()


def _wrapped_height(text: str, width: float, size: int) -> float:
    metrics = QFontMetricsF(text_font(size))
    bounds = metrics.boundingRect(QRectF(0, 0, max(1.0, width), 10_000), int(Qt.TextFlag.TextWordWrap), text)
    return math.ceil(bounds.height())


def note_height(text: str, width: float) -> float:
    if not text:
        return 0.0
    return _wrapped_height(text, width, NOTE_SIZE)


def _check_path(center: QPointF, size: float) -> QPainterPath:
    path = QPainterPath(QPointF(center.x() - size, center.y()))
    path.lineTo(QPointF(center.x() - size * 0.3, center.y() + size * 0.7))
    path.lineTo(QPointF(center.x() + size, center.y() - size * 0.6))
    return path


def _cross_path(center: QPointF, size: float) -> QPainterPath:
    path = QPainterPath(QPointF(center.x() - size, center.y() - size))
    path.lineTo(QPointF(center.x() + size, center.y() + size))
    path.moveTo(QPointF(center.x() + size, center.y() - size))
    path.lineTo(QPointF(center.x() - size, center.y() + size))
    return path


def paint_verdict_mark(painter: QPainter, rect: QRectF, is_success: bool) -> None:
    color = SUCCESS_COLOR if is_success else WARNING_COLOR
    tint = SUCCESS_TINT_ALPHA if is_success else WARNING_TINT_ALPHA
    painter.save()
    painter.setBrush(QBrush(with_alpha(color, tint)))
    painter.setPen(QPen(QColor(color), CHIP_BORDER_WIDTH))
    painter.drawEllipse(rect.adjusted(0.5, 0.5, -0.5, -0.5))
    mark_size = rect.width() * VERDICT_MARK_SCALE / 2
    path = _check_path(rect.center(), mark_size) if is_success else _cross_path(rect.center(), mark_size)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(color), VERDICT_MARK_STROKE, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.drawPath(path)
    painter.restore()


@dataclass(frozen=True)
class VerdictLayout:
    mark: QRectF
    message: QRectF
    score: QRectF


def verdict_layout(area: QRectF, top: float, score_text: str, message: str) -> VerdictLayout:
    score_width = QFontMetricsF(monospace_font(VERDICT_SCORE_SIZE)).horizontalAdvance(score_text) + 2
    message_left = area.left() + VERDICT_MARK_SIZE + VERDICT_GAP
    message_width = max(0.0, area.right() - score_width - VERDICT_GAP - message_left)
    height = max(VERDICT_HEIGHT, _wrapped_height(message, message_width, VERDICT_MESSAGE_SIZE))
    mark = QRectF(area.left(), top + (height - VERDICT_MARK_SIZE) / 2, VERDICT_MARK_SIZE, VERDICT_MARK_SIZE)
    score = QRectF(area.right() - score_width, top, score_width, height)
    return VerdictLayout(mark, QRectF(message_left, top, message_width, height), score)


def place_verdict(area: QRectF, preferred_top: float, score_text: str, message: str) -> VerdictLayout:
    height = verdict_layout(area, 0.0, score_text, message).score.height()
    return verdict_layout(area, min(preferred_top, area.bottom() - height), score_text, message)


def paint_verdict(painter: QPainter, layout: VerdictLayout, is_success: bool, message: str, score_text: str, appear: float) -> None:
    visible = clamp_unit(appear)
    if visible <= 0:
        return
    painter.save()
    painter.setOpacity(painter.opacity() * visible)
    scale = lerp(VERDICT_APPEAR_SCALE, 1.0, ease_out_cubic(visible))
    center = layout.mark.center()
    painter.save()
    painter.translate(center)
    painter.scale(scale, scale)
    painter.translate(-center)
    paint_verdict_mark(painter, layout.mark, is_success)
    painter.restore()
    draw_text(painter, layout.message, message, LABEL_TEXT_COLOR, text_font(VERDICT_MESSAGE_SIZE), wrap=True)
    color = SUCCESS_COLOR if is_success else WARNING_COLOR
    draw_value(painter, layout.score, score_text, color, VERDICT_SCORE_SIZE, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    painter.restore()


def quoted_list(items: Sequence[str]) -> str:
    quoted = [QUOTE_FORMAT.format(item) for item in items[:MAXIMUM_QUOTED_ITEMS]]
    hidden = len(items) - len(quoted)
    if hidden > 0:
        quoted.append(MORE_ITEMS_FORMAT.format(count=hidden))
    if len(quoted) == 1:
        return quoted[0]
    return ", ".join(quoted[:-1]) + " and " + quoted[-1]


def highlighted_text(text: str) -> str:
    return HIGHLIGHT_FORMAT.format(color=PRIMARY_HOVER_COLOR, text=text)


def highlighted_value(value: float) -> str:
    return highlighted_text(SCORE_FORMAT.format(value))


def format_score(value: float) -> str:
    return SCORE_FORMAT.format(value)


class LayoutCache:
    def __init__(self, builder: Callable[[object, QRectF], object]):
        self._builder = builder
        self._key: tuple | None = None
        self._value: object = None

    def get(self, walkthrough: object, area: QRectF) -> object:
        key = (walkthrough, area.left(), area.top(), area.width(), area.height())
        if key != self._key:
            self._value = self._builder(walkthrough, area)
            self._key = key
        return self._value


def options_from_parameters(parameters: Mapping) -> NormalizationOptions:
    return NormalizationOptions(
        lowercase=parameters.get("lowercase", DEFAULT_NORMALIZATION.lowercase),
        strip_accents=parameters.get("strip_accents", DEFAULT_NORMALIZATION.strip_accents),
        remove_punctuation=parameters.get("remove_punctuation", DEFAULT_NORMALIZATION.remove_punctuation),
        articles=parameters.get("remove_articles", DEFAULT_NORMALIZATION.articles),
    )


def options_from_normalization(normalization: NormalizationDetails) -> NormalizationOptions:
    return NormalizationOptions(
        lowercase=normalization.lowercase,
        strip_accents=normalization.strip_accents,
        remove_punctuation=normalization.remove_punctuation,
        articles=normalization.articles,
    )


def _option_states(options: NormalizationOptions) -> tuple[tuple[str, bool], ...]:
    return (
        (LOWERCASE_LABEL, options.lowercase),
        (STRIP_ACCENTS_LABEL, options.strip_accents),
        (REMOVE_PUNCTUATION_LABEL, options.remove_punctuation),
        (ARTICLE_LABELS.get(options.articles, NO_ARTICLES_LABEL), options.articles != NO_ARTICLES_NAME),
    )


def normalization_options_text(options: NormalizationOptions) -> str:
    states = _option_states(options)
    enabled = [label for label, is_on in states if is_on] + [COLLAPSE_SPACES_LABEL]
    disabled = [label for label, is_on in states if not is_on]
    parts = [ENABLED_OPTIONS_FORMAT.format(items=OPTION_SEPARATOR.join(enabled))]
    if disabled:
        parts.append(DISABLED_OPTIONS_FORMAT.format(items=OPTION_SEPARATOR.join(disabled)))
    parts.append(PARAMETERS_HINT)
    return " ".join(parts)


def _function_is_active(options: NormalizationOptions, option_name: str | None) -> bool:
    if option_name is None:
        return True
    value = getattr(options, option_name)
    return value != NO_ARTICLES_NAME if option_name == "articles" else bool(value)


def normalization_formula(options: NormalizationOptions) -> str:
    names = [name for name, option in FUNCTION_NAMES if _function_is_active(options, option)]
    head = "".join(f"{name}(" for name in names[:FORMULA_HEAD_FUNCTIONS])
    tail = "".join(f"{name}(" for name in names[FORMULA_HEAD_FUNCTIONS:]) + "x" + ")" * len(names)
    expression = head + FORMULA_BREAK + tail if len(names) > FORMULA_HEAD_FUNCTIONS else head + tail
    return NORMALIZATION_FORMULA.format(expression=expression)
