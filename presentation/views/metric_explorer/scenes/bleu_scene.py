import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QFont, QPainter, QPainterPath, QPen

from domain.explanations.metric_walkthrough import MetricWalkthrough
from domain.explanations.timeline import TimelinePosition
from domain.explanations.walkthrough_details import BleuDetails
from presentation.views.branding import (
    BORDER_COLOR,
    DISABLED_TEXT_COLOR,
    LABEL_TEXT_COLOR,
    PRIMARY_COLOR,
    PRIMARY_HOVER_COLOR,
    SECONDARY_TEXT_COLOR,
    STRONG_BORDER_COLOR,
    SURFACE_COLOR,
    TEXT_COLOR,
    WARNING_COLOR,
)
from presentation.views.metric_explorer.painting import (
    clamp_unit,
    draw_caption,
    draw_card,
    draw_text,
    draw_value,
    ease_in_out,
    ease_out_cubic,
    lerp,
    monospace_font,
    segment_progress,
    text_font,
    to_color,
    with_alpha,
)
from presentation.views.metric_explorer.scenes.base_scene import SceneStep, WalkthroughScene
from presentation.views.metric_explorer.scenes.translation_scene_painting import (
    NO_WINDOW,
    StripLayout,
    chip_widths,
    clipped_match_flags,
    count_up,
    draw_dashed_line,
    draw_divider,
    draw_empty_strip,
    draw_token_strip,
    draw_window,
    elide,
    format_score,
    layout_flow,
    stage_progress,
    sweep_frame,
)

DEFAULT_ORDER_COUNT = 4
PRECISION_STEP = 0
MEAN_STEP = 1
PENALTY_STEP = 2
SCORE_STEP = 3
RESULT_ORDERS_PER_LINE = 2
SUBSCRIPT_DIGITS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

STEPS = (
    SceneStep(
        "Precision per n-gram order",
        "Split both texts into tokens{tokenization}, then count answer n-grams of orders 1 to {order_count} also found in the reference, clipped by its counts: {counts}.",
        6.0,
        (0,),
    ),
    SceneStep(
        "Geometric mean",
        "The {orders} combined with a geometric mean, so one weak order pulls the score down.",
        3.5,
        (1,),
    ),
    SceneStep(
        "Brevity penalty",
        "Short answers would get high precision for free, so BLEU scales them down. {lengths}",
        4.0,
        (2,),
    ),
    SceneStep(
        "Final score",
        "Brevity penalty times the geometric mean. This is sentence BLEU; the Corpus BLEU card pools all questions.",
        3.5,
        (1,),
    ),
)
FORMULA_TEMPLATE = (
    "p<sub>n</sub> = clipped matches<sub>n</sub> / answer n-grams<sub>n</sub>, n = 1…{order_count}",
    "BLEU = BP · exp({weight} Σ log p<sub>n</sub>), w<sub>n</sub> = {weight}",
    "BP = 1 if c ≥ r, else e<sup>1 − r/c</sup>",
)
LIMITATION = "Built for corpus-level translation: on single short answers it is noisy, even with smoothing."

PRECISION_CAPTION = "Modified n-gram precision"
EMPTY_ANSWER_TEXT = "(empty answer)"
COUNT_FORMAT = "{matches}/{total}"
TOKENIZER_NAMES = {"13a": "13a", "intl": "international", "char": "character", "none": "whitespace-only"}
TOKENIZATION_FORMAT = " with the {name} tokenizer{case}"
IGNORE_CASE_TEXT = ", ignoring letter case"
SMOOTH_FLOOR_KEY = "floor"
SMOOTH_NONE_KEY = "none"
SMOOTHING_SENTENCES = {
    "exp": " Exponential smoothing keeps {orders} above zero.",
    "floor": " Floor smoothing counts {orders} as {value:g} match instead of 0.",
    "add-k": " Add-k smoothing adds {value:g} to the counts above unigrams, so {orders} stay above zero.",
    "none": " Smoothing is off, so {orders} with no match make BLEU 0.",
}
SMOOTHING_LABELS = {
    "exp": "exponential smoothing",
    "floor": "floor smoothing {value:g}",
    "add-k": "add-k smoothing k = {value:g}",
    "none": "smoothing off",
}
PARAMETERS_HINT = " Change the options with “Parameters…”."
LIMITATION_SMOOTHING_OFF = " Smoothing is off: a single order without matches gives BLEU 0."
LIMITATION_CHARACTERS = " With the character tokenizer, n-grams are runs of letters, not words."
EFFECTIVE_ORDER_SENTENCE = " A {length}-token answer has only {orders}."
EMPTY_PRECISION_SENTENCE = " The answer is empty, so BLEU is 0."
NO_PENALTY_SENTENCE = "c = {c} ≥ r = {r}: no penalty."
PENALTY_SENTENCE = "c = {c} < r = {r}: penalized."
EMPTY_PENALTY_SENTENCE = "c = 0, so BP = 0."
ACTIVE_COUNTER_FORMAT = "{order}-grams · {matches} of {total} match"
LENGTHS_COUNTER_FORMAT = "{c} answer tokens · {r} reference tokens"
NO_NGRAMS_TEXT = "none"
PENDING_COUNT_TEXT = "–"
MISSING_VALUE_TEXT = "—"
ORDER_LABEL_FORMAT = "{order}-gram"
MEAN_LABEL_FORMAT = "GM {value}"
NOTE_SMOOTHED_FORMAT = "{orders}: no matches, {smoothing} instead of 0"
NOTE_UNSMOOTHED_FORMAT = "{orders}: no matches and smoothing is off, so BLEU is 0"
NOTE_EFFECTIVE_FORMAT = "{length}-token answer: only {orders} used"
NOTE_EMPTY_TEXT = "Empty answer: no n-grams, so BLEU is 0"
NOTE_DEFAULT_TEXT = "Clipped: an n-gram counts at most as often as it appears in the reference"
NOTE_SEPARATOR = " · "
PENALTY_CAPTION = "Brevity penalty"
SCORE_CAPTION = "Sentence BLEU"
LENGTHS_FORMAT = "c = {c} · r = {r} tokens"
NO_PENALTY_TEXT = "Not shorter: no penalty."
PENALTY_TEXT = "Shorter: scaled down."
EMPTY_PENALTY_TEXT = "Empty answer: no length."
PENALTY_VALUE_FORMAT = "BP = {value}"
PRODUCT_FORMAT = "{penalty} × {mean}"
SCORE_VALUE_FORMAT = "BLEU = {value}"
CORPUS_NOTE = "Per question. The Corpus BLEU card pools all questions."
AXIS_VALUE_LABEL = "BP"
AXIS_RATIO_LABEL = "c / r"
AXIS_UNIT_LABEL = "1"

SECTION_GAP = 10.0
CAPTION_HEIGHT = 16.0
STRIP_TOP_GAP = 8.0
TOKEN_ROW_HEIGHT = 26.0
TOKEN_GAP = 6.0
TOKEN_MAX_ROWS = 2
COUNTER_GAP = 6.0
COUNTER_HEIGHT = 18.0
COUNTER_TEXT_SIZE = 12
NOTE_HEIGHT = 18.0
NOTE_TEXT_SIZE = 11
BAR_VALUE_HEIGHT = 18.0
BAR_VALUE_SIZE = 13
BAR_LABEL_HEIGHT = 16.0
BAR_LABEL_SIZE = 12
BAR_COUNT_HEIGHT = 14.0
BAR_COUNT_SIZE = 11
BAR_INNER_GAP = 4.0
BAR_MAX_WIDTH = 56.0
BAR_WIDTH_FRACTION = 0.6
BAR_RADIUS = 8.0
MINIMUM_FILL_HEIGHT = 3.0
MEAN_GUTTER_WIDTH = 72.0
MEAN_LABEL_HEIGHT = 20.0
MEAN_LABEL_SIZE = 12
MEAN_DOT_RADIUS = 4.0
MEAN_LINE_WIDTH = 1.5
BAR_CHART_SHARE = 0.58
BAR_CHART_MAX_HEIGHT = 210.0
BOTTOM_MAX_HEIGHT = 170.0
BOTTOM_MIN_HEIGHT = 104.0
CURVE_WIDTH_FRACTION = 0.48
CURVE_MAX_WIDTH = 300.0
CURVE_AXIS_LEFT = 24.0
CURVE_AXIS_BOTTOM = 18.0
CURVE_AXIS_TOP = 8.0
CURVE_AXIS_RIGHT = 8.0
CURVE_LABEL_SIZE = 10
CURVE_LABEL_WIDTH = 40.0
CURVE_LABEL_HEIGHT = 14.0
CURVE_SAMPLES = 90
CURVE_LINE_WIDTH = 2.5
AXIS_LINE_WIDTH = 1.0
RATIO_MAXIMUM = 1.5
MARKER_RADIUS = 5.0
PING_MAXIMUM_RADIUS = 13.0
PING_LINE_WIDTH = 2.0
TEXT_COLUMN_GAP = 16.0
TEXT_LINE_HEIGHT = 18.0
TEXT_SIZE = 12
BIG_VALUE_HEIGHT = 30.0
BIG_VALUE_SIZE = 20
PRODUCT_SIZE = 14
CORPUS_NOTE_HEIGHT = 30.0
CORPUS_NOTE_SIZE = 11
FUTURE_OPACITY = 0.35
INACTIVE_ORDER_OPACITY = 0.45

PRECISION_SWEEP_END = 0.9
SEGMENT_SWEEP_SHARE = 0.75
MEAN_DROP_END = 0.6
MEAN_LINE_START = 0.35
CURVE_DRAW_END = 0.45
MARKER_START = 0.45
MARKER_END = 0.85
SCORE_FADE_END = 0.3
SCORE_COUNT_START = 0.2


@dataclass(frozen=True)
class BarColumn:
    value_rect: QRectF
    track_rect: QRectF
    label_rect: QRectF
    count_rect: QRectF


@dataclass(frozen=True)
class BleuLayout:
    caption_rect: QRectF
    strip_rect: QRectF
    strip: StripLayout
    counter_rect: QRectF
    columns: tuple[BarColumn, ...]
    chart_rect: QRectF
    mean_gutter: QRectF
    note_rect: QRectF
    divider_y: float
    plot_rect: QRectF
    curve: QPainterPath
    text_rect: QRectF


@dataclass(frozen=True)
class OrderState:
    fill: float
    value_text: str
    count_text: str
    revealed: bool


def brevity_penalty_at(ratio: float) -> float:
    if ratio <= 0:
        return 0.0
    if ratio >= 1:
        return 1.0
    return math.exp(1 - 1 / ratio)


def length_ratio(details: BleuDetails) -> float:
    if details.reference_length == 0:
        return RATIO_MAXIMUM
    return min(RATIO_MAXIMUM, details.answer_length / details.reference_length)


def subscript(order: int) -> str:
    return f"p{str(order).translate(SUBSCRIPT_DIGITS)}"


def order_list(orders: tuple[int, ...]) -> str:
    names = [subscript(order) for order in orders]
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def plural_orders(count: int) -> str:
    return f"{count} order" if count == 1 else f"{count} orders"


class BleuScene(WalkthroughScene):
    identifier = "bleu"

    def __init__(self):
        self._layout_key: tuple | None = None
        self._layout: BleuLayout | None = None

    @property
    def steps(self) -> tuple[SceneStep, ...]:
        return STEPS

    @property
    def formula(self) -> tuple[str, ...]:
        return self._formula_lines(DEFAULT_ORDER_COUNT)

    @property
    def limitation(self) -> str:
        return LIMITATION

    def formula_for(self, walkthrough: MetricWalkthrough) -> tuple[str, ...]:
        return self._formula_lines(self._order_count(self._details(walkthrough)))

    def limitation_for(self, walkthrough: MetricWalkthrough) -> str:
        text = LIMITATION
        if walkthrough.parameters.get("smooth_method") == SMOOTH_NONE_KEY:
            text += LIMITATION_SMOOTHING_OFF
        if walkthrough.parameters.get("tokenize") == "char":
            text += LIMITATION_CHARACTERS
        return text

    def _formula_lines(self, order_count: int) -> tuple[str, ...]:
        weight = f"1/{order_count}" if order_count > 1 else "1"
        return tuple(line.format(order_count=order_count, weight=weight) for line in FORMULA_TEMPLATE)

    def _order_count(self, details: BleuDetails) -> int:
        return len(details.precisions) or DEFAULT_ORDER_COUNT

    def step_body(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        details = self._details(walkthrough)
        body = STEPS[step_index].body
        if step_index == PRECISION_STEP:
            return self._precision_body(body, details, walkthrough)
        if step_index == MEAN_STEP:
            return body.format(orders=self._mean_subject(details))
        if step_index == PENALTY_STEP:
            return body.format(lengths=self._penalty_sentence(details))
        return body

    def _precision_body(self, body: str, details: BleuDetails, walkthrough: MetricWalkthrough) -> str:
        text = body.format(
            tokenization=self._tokenization_text(walkthrough),
            order_count=self._order_count(details),
            counts=self._counts_text(details),
        )
        return text + self._precision_remarks(details, walkthrough) + PARAMETERS_HINT

    def _tokenization_text(self, walkthrough: MetricWalkthrough) -> str:
        parameters = walkthrough.parameters
        name = TOKENIZER_NAMES.get(str(parameters.get("tokenize", "13a")), str(parameters.get("tokenize")))
        case = IGNORE_CASE_TEXT if parameters.get("lowercase") else ""
        return TOKENIZATION_FORMAT.format(name=name, case=case)

    def _smoothing_value(self, walkthrough: MetricWalkthrough) -> float:
        key = "floor_value" if walkthrough.parameters.get("smooth_method") == SMOOTH_FLOOR_KEY else "add_k_value"
        return float(walkthrough.parameters.get(key, 0.0))

    def _smoothing_label(self, walkthrough: MetricWalkthrough) -> str:
        method = str(walkthrough.parameters.get("smooth_method", "exp"))
        return SMOOTHING_LABELS.get(method, method).format(value=self._smoothing_value(walkthrough))

    def formula_result(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        details = self._details(walkthrough)
        if step_index == PRECISION_STEP:
            return self._precision_result(details)
        if step_index == MEAN_STEP:
            return f"exp(1/{max(1, details.effective_order)} Σ log p<sub>n</sub>) = {format_score(details.geometric_mean)}"
        if step_index == PENALTY_STEP:
            return self._penalty_result(details)
        return f"= {format_score(details.brevity_penalty)} · {format_score(details.geometric_mean)} = <b>{format_score(details.score)}</b>"

    def paint(self, painter: QPainter, area: QRectF, walkthrough: MetricWalkthrough, position: TimelinePosition) -> None:
        details = self._details(walkthrough)
        layout = self._layout_for(details, area)
        painter.save()
        painter.setClipRect(area, Qt.ClipOperation.IntersectClip)
        self._paint_precision_section(painter, layout, details, position)
        self._paint_mean(painter, layout, details, stage_progress(position, MEAN_STEP))
        self._paint_note(painter, layout, details, walkthrough)
        draw_divider(painter, area.left(), area.right(), layout.divider_y)
        self._paint_penalty_plot(painter, layout, details, position)
        self._paint_text_column(painter, layout, details, position)
        painter.restore()

    def _details(self, walkthrough: MetricWalkthrough) -> BleuDetails:
        if not isinstance(walkthrough.details, BleuDetails):
            raise TypeError(f"BLEU needs BLEU details, got {type(walkthrough.details).__name__}.")
        return walkthrough.details

    def _counts_text(self, details: BleuDetails) -> str:
        if details.effective_order == 0:
            return "there are none"
        pairs = zip(details.matches_by_order[: details.effective_order], details.totals_by_order[: details.effective_order])
        return ", ".join(COUNT_FORMAT.format(matches=matches, total=total) for matches, total in pairs)

    def _precision_remarks(self, details: BleuDetails, walkthrough: MetricWalkthrough) -> str:
        if details.effective_order == 0:
            return EMPTY_PRECISION_SENTENCE
        remarks = ""
        unmatched = self._unmatched_orders(details)
        if details.smoothed_orders:
            method = str(walkthrough.parameters.get("smooth_method", "exp"))
            template = SMOOTHING_SENTENCES.get(method, SMOOTHING_SENTENCES["exp"])
            remarks += template.format(orders=order_list(details.smoothed_orders), value=self._smoothing_value(walkthrough))
        elif unmatched and walkthrough.parameters.get("smooth_method") == SMOOTH_NONE_KEY:
            remarks += SMOOTHING_SENTENCES[SMOOTH_NONE_KEY].format(orders=order_list(unmatched))
        if details.effective_order < self._order_count(details):
            remarks += EFFECTIVE_ORDER_SENTENCE.format(length=details.answer_length, orders=plural_orders(details.effective_order))
        return remarks

    def _unmatched_orders(self, details: BleuDetails) -> tuple[int, ...]:
        return tuple(order for order in range(1, details.effective_order + 1) if details.matches_by_order[order - 1] == 0 and details.totals_by_order[order - 1] > 0)

    def _mean_subject(self, details: BleuDetails) -> str:
        if details.effective_order <= 1:
            return "available precision is"
        return f"{details.effective_order} precisions are"

    def _penalty_sentence(self, details: BleuDetails) -> str:
        if details.answer_length == 0:
            return EMPTY_PENALTY_SENTENCE
        template = NO_PENALTY_SENTENCE if details.answer_length >= details.reference_length else PENALTY_SENTENCE
        return template.format(c=details.answer_length, r=details.reference_length)

    def _precision_result(self, details: BleuDetails) -> str:
        if details.effective_order == 0:
            return "no n-grams, every p<sub>n</sub> = 0"
        lines = []
        for first in range(0, details.effective_order, RESULT_ORDERS_PER_LINE):
            orders = range(first + 1, min(details.effective_order, first + RESULT_ORDERS_PER_LINE) + 1)
            names = ", ".join(f"p<sub>{order}</sub>" for order in orders)
            values = ", ".join(format_score(details.precisions[order - 1]) for order in orders)
            lines.append(f"{names} = {values}")
        return "<br>".join(lines)

    def _penalty_result(self, details: BleuDetails) -> str:
        if details.answer_length == 0 or details.answer_length >= details.reference_length:
            return f"BP = {format_score(details.brevity_penalty)}"
        exponent = f"1 − {details.reference_length}/{details.answer_length}"
        return f"BP = e<sup>{exponent}</sup> = {format_score(details.brevity_penalty)}"

    def _layout_for(self, details: BleuDetails, area: QRectF) -> BleuLayout:
        key = (details, area.left(), area.top(), area.width(), area.height())
        if key != self._layout_key or self._layout is None:
            self._layout = self._build_layout(details, area)
            self._layout_key = key
        return self._layout

    def _build_layout(self, details: BleuDetails, area: QRectF) -> BleuLayout:
        left, width = area.left(), area.width()
        caption_rect = QRectF(left, area.top(), width, CAPTION_HEIGHT)
        strip_height = TOKEN_ROW_HEIGHT * TOKEN_MAX_ROWS + TOKEN_GAP * (TOKEN_MAX_ROWS - 1)
        strip_rect = QRectF(left, caption_rect.bottom() + STRIP_TOP_GAP, width, strip_height)
        strip = layout_flow(chip_widths(details.answer_tokens, width), strip_rect, TOKEN_ROW_HEIGHT, TOKEN_GAP, TOKEN_MAX_ROWS)
        strip_bottom = strip.bottom if strip.unit_rects or strip.badge_rect else strip_rect.top() + TOKEN_ROW_HEIGHT
        counter_rect = QRectF(left, strip_bottom + COUNTER_GAP, width, COUNTER_HEIGHT)
        chart_top = counter_rect.bottom() + SECTION_GAP
        flexible = max(0.0, area.bottom() - chart_top - NOTE_HEIGHT - 2 * SECTION_GAP)
        bottom_height = min(flexible, BOTTOM_MAX_HEIGHT, max(BOTTOM_MIN_HEIGHT, flexible * (1 - BAR_CHART_SHARE)))
        chart_height = min(BAR_CHART_MAX_HEIGHT, flexible - bottom_height)
        chart_rect = QRectF(left, chart_top, max(0.0, width - MEAN_GUTTER_WIDTH), chart_height)
        columns = self._build_columns(chart_rect, self._order_count(details))
        mean_gutter = QRectF(chart_rect.right(), columns[0].track_rect.top(), MEAN_GUTTER_WIDTH, columns[0].track_rect.height())
        note_rect = QRectF(left, chart_rect.bottom(), width, NOTE_HEIGHT)
        divider_y = note_rect.bottom() + SECTION_GAP
        bottom_top = divider_y + SECTION_GAP
        plot_rect = QRectF(left, bottom_top, min(CURVE_MAX_WIDTH, width * CURVE_WIDTH_FRACTION), bottom_height)
        text_left = plot_rect.right() + TEXT_COLUMN_GAP
        text_rect = QRectF(text_left, bottom_top, max(0.0, area.right() - text_left), bottom_height)
        return BleuLayout(
            caption_rect, strip_rect, strip, counter_rect, columns, chart_rect, mean_gutter,
            note_rect, divider_y, plot_rect, self._build_curve(self._plot_inner(plot_rect)), text_rect,
        )

    def _build_columns(self, chart_rect: QRectF, order_count: int) -> tuple[BarColumn, ...]:
        column_width = chart_rect.width() / order_count
        bar_width = min(BAR_MAX_WIDTH, column_width * BAR_WIDTH_FRACTION)
        fixed = BAR_VALUE_HEIGHT + BAR_LABEL_HEIGHT + BAR_COUNT_HEIGHT + 3 * BAR_INNER_GAP
        track_height = max(0.0, chart_rect.height() - fixed)
        columns = []
        for index in range(order_count):
            column_left = chart_rect.left() + index * column_width
            value_rect = QRectF(column_left, chart_rect.top(), column_width, BAR_VALUE_HEIGHT)
            track_top = value_rect.bottom() + BAR_INNER_GAP
            track_rect = QRectF(column_left + (column_width - bar_width) / 2, track_top, bar_width, track_height)
            label_rect = QRectF(column_left, track_rect.bottom() + BAR_INNER_GAP, column_width, BAR_LABEL_HEIGHT)
            count_rect = QRectF(column_left, label_rect.bottom() + BAR_INNER_GAP, column_width, BAR_COUNT_HEIGHT)
            columns.append(BarColumn(value_rect, track_rect, label_rect, count_rect))
        return tuple(columns)

    def _plot_inner(self, plot_rect: QRectF) -> QRectF:
        return plot_rect.adjusted(CURVE_AXIS_LEFT, CURVE_AXIS_TOP, -CURVE_AXIS_RIGHT, -CURVE_AXIS_BOTTOM)

    def _plot_point(self, inner: QRectF, ratio: float, penalty: float) -> QPointF:
        return QPointF(inner.left() + ratio / RATIO_MAXIMUM * inner.width(), inner.bottom() - penalty * inner.height())

    def _build_curve(self, inner: QRectF) -> QPainterPath:
        path = QPainterPath(self._plot_point(inner, 0.0, 0.0))
        for sample in range(1, CURVE_SAMPLES + 1):
            ratio = RATIO_MAXIMUM * sample / CURVE_SAMPLES
            path.lineTo(self._plot_point(inner, ratio, brevity_penalty_at(ratio)))
        return path

    def _segment_bounds(self, details: BleuDetails, order: int) -> tuple[float, float] | None:
        if order > details.effective_order:
            return None
        length = PRECISION_SWEEP_END / details.effective_order
        return (order - 1) * length, order * length

    def _order_flags(self, details: BleuDetails, order: int) -> tuple[bool, ...]:
        return clipped_match_flags(details.answer_tokens, details.reference_tokens, order)

    def _visible_windows(self, layout: BleuLayout, order: int) -> int:
        return max(0, len(layout.strip.unit_rects) - order + 1)

    def _order_state(self, layout: BleuLayout, details: BleuDetails, order: int, progress: float) -> OrderState:
        index = order - 1
        total = details.totals_by_order[index]
        bounds = self._segment_bounds(details, order)
        if bounds is None or total == 0:
            return OrderState(0.0, MISSING_VALUE_TEXT, NO_NGRAMS_TEXT, False)
        local = segment_progress(progress, *bounds)
        if local <= 0:
            return OrderState(0.0, "", COUNT_FORMAT.format(matches=PENDING_COUNT_TEXT, total=total), False)
        sweep = sweep_frame(self._order_flags(details, order), order, local / SEGMENT_SWEEP_SHARE, self._visible_windows(layout, order))
        settle = ease_in_out(segment_progress(local, SEGMENT_SWEEP_SHARE, 1.0))
        fill = lerp(sweep.matched_count / total, details.precisions[index], settle)
        matches = sweep.matched_count if settle < 1 else details.matches_by_order[index]
        return OrderState(fill, format_score(fill), COUNT_FORMAT.format(matches=matches, total=total), True)

    def _active_order(self, details: BleuDetails, progress: float) -> int | None:
        if details.effective_order == 0 or progress >= PRECISION_SWEEP_END:
            return None
        return min(details.effective_order, int(progress / PRECISION_SWEEP_END * details.effective_order) + 1)

    def _paint_precision_section(self, painter: QPainter, layout: BleuLayout, details: BleuDetails, position: TimelinePosition) -> None:
        progress = stage_progress(position, PRECISION_STEP)
        draw_caption(painter, layout.caption_rect, PRECISION_CAPTION)
        active_order = self._active_order(details, progress)
        self._paint_strip(painter, layout, details, progress, active_order)
        self._paint_counter(painter, layout, details, progress, active_order)
        for order in range(1, self._order_count(details) + 1):
            self._paint_bar(painter, layout, details, order, self._order_state(layout, details, order, progress), active_order)

    def _paint_strip(self, painter: QPainter, layout: BleuLayout, details: BleuDetails, progress: float, active_order: int | None) -> None:
        if not details.answer_tokens:
            draw_empty_strip(painter, QRectF(layout.strip_rect.left(), layout.strip_rect.top(), layout.strip_rect.width(), TOKEN_ROW_HEIGHT), EMPTY_ANSWER_TEXT)
            return
        if active_order is None:
            highlights = self._settled_highlights(layout, details, progress)
            draw_token_strip(painter, layout.strip, details.answer_tokens, highlights)
            return
        start, end = self._segment_bounds(details, active_order)
        local = segment_progress(progress, start, end)
        sweep = sweep_frame(self._order_flags(details, active_order), active_order, local / SEGMENT_SWEEP_SHARE, self._visible_windows(layout, active_order))
        highlights = [1.0 if unit in sweep.covered_units else 0.0 for unit in range(len(details.answer_tokens))]
        draw_token_strip(painter, layout.strip, details.answer_tokens, highlights)
        if sweep.window_index != NO_WINDOW:
            draw_window(painter, layout.strip, sweep.window_index, active_order)

    def _settled_highlights(self, layout: BleuLayout, details: BleuDetails, progress: float) -> list[float]:
        unigram = self._coverage(details, 1)
        if details.effective_order <= 1:
            return unigram
        last = self._coverage(details, details.effective_order)
        blend = ease_in_out(segment_progress(progress, PRECISION_SWEEP_END, 1.0))
        return [lerp(previous, final, blend) for previous, final in zip(last, unigram)]

    def _coverage(self, details: BleuDetails, order: int) -> list[float]:
        flags = self._order_flags(details, order)
        covered = {unit for start, flag in enumerate(flags) if flag for unit in range(start, start + order)}
        return [1.0 if unit in covered else 0.0 for unit in range(len(details.answer_tokens))]

    def _paint_counter(self, painter: QPainter, layout: BleuLayout, details: BleuDetails, progress: float, active_order: int | None) -> None:
        font = text_font(COUNTER_TEXT_SIZE)
        if active_order is None:
            text = LENGTHS_COUNTER_FORMAT.format(c=details.answer_length, r=details.reference_length)
            draw_text(painter, layout.counter_rect, elide(text, font, layout.counter_rect.width()), SECONDARY_TEXT_COLOR, font)
            return
        start, end = self._segment_bounds(details, active_order)
        local = segment_progress(progress, start, end)
        sweep = sweep_frame(self._order_flags(details, active_order), active_order, local / SEGMENT_SWEEP_SHARE, self._visible_windows(layout, active_order))
        text = ACTIVE_COUNTER_FORMAT.format(order=active_order, matches=sweep.matched_count, total=details.totals_by_order[active_order - 1])
        draw_text(painter, layout.counter_rect, elide(text, font, layout.counter_rect.width()), LABEL_TEXT_COLOR, text_font(COUNTER_TEXT_SIZE, QFont.Weight.DemiBold))

    def _paint_bar(self, painter: QPainter, layout: BleuLayout, details: BleuDetails, order: int, state: OrderState, active_order: int | None) -> None:
        column = layout.columns[order - 1]
        is_used = order <= details.effective_order
        painter.save()
        painter.setOpacity(1.0 if is_used else INACTIVE_ORDER_OPACITY)
        draw_card(painter, column.track_rect, SURFACE_COLOR, BORDER_COLOR if order == active_order else None, BAR_RADIUS)
        self._paint_fill(painter, column.track_rect, state.fill, self._fill_color(details, order))
        draw_value(painter, column.value_rect, state.value_text, TEXT_COLOR, BAR_VALUE_SIZE, Qt.AlignmentFlag.AlignCenter)
        label_color = TEXT_COLOR if state.revealed or order == active_order else SECONDARY_TEXT_COLOR
        draw_text(painter, column.label_rect, ORDER_LABEL_FORMAT.format(order=order), label_color, text_font(BAR_LABEL_SIZE, QFont.Weight.DemiBold), Qt.AlignmentFlag.AlignCenter)
        draw_text(painter, column.count_rect, state.count_text, SECONDARY_TEXT_COLOR, monospace_font(BAR_COUNT_SIZE, QFont.Weight.Normal), Qt.AlignmentFlag.AlignCenter)
        painter.restore()

    def _fill_color(self, details: BleuDetails, order: int) -> str:
        return STRONG_BORDER_COLOR if order in details.smoothed_orders else PRIMARY_COLOR

    def _paint_fill(self, painter: QPainter, track: QRectF, fraction: float, color: str) -> None:
        if fraction <= 0 or track.height() <= 0:
            return
        height = max(MINIMUM_FILL_HEIGHT, track.height() * clamp_unit(fraction))
        fill_rect = QRectF(track.left(), track.bottom() - height, track.width(), height)
        draw_card(painter, fill_rect, color, None, min(BAR_RADIUS, height / 2))

    def _paint_mean(self, painter: QPainter, layout: BleuLayout, details: BleuDetails, progress: float) -> None:
        if progress <= 0 or details.effective_order == 0:
            return
        track = layout.columns[0].track_rect
        mean_y = track.bottom() - track.height() * clamp_unit(details.geometric_mean)
        drop = ease_in_out(segment_progress(progress, 0.0, MEAN_DROP_END))
        for order in range(1, details.effective_order + 1):
            self._paint_mean_dot(painter, layout.columns[order - 1].track_rect, details.precisions[order - 1], mean_y, drop)
        line = ease_out_cubic(segment_progress(progress, MEAN_LINE_START, 1.0))
        if line <= 0:
            return
        start = QPointF(layout.chart_rect.left(), mean_y)
        end = QPointF(lerp(layout.chart_rect.left(), layout.chart_rect.right(), line), mean_y)
        draw_dashed_line(painter, start, end, PRIMARY_HOVER_COLOR, MEAN_LINE_WIDTH)
        self._paint_mean_label(painter, layout, details, mean_y, line)

    def _paint_mean_dot(self, painter: QPainter, track: QRectF, precision: float, mean_y: float, drop: float) -> None:
        top_y = track.bottom() - track.height() * clamp_unit(precision)
        center = QPointF(track.center().x(), lerp(top_y, mean_y, drop))
        painter.save()
        painter.setPen(QPen(with_alpha(PRIMARY_HOVER_COLOR, 0.6), MEAN_LINE_WIDTH))
        painter.drawLine(QPointF(center.x(), top_y), center)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(to_color(PRIMARY_HOVER_COLOR)))
        painter.drawEllipse(center, MEAN_DOT_RADIUS, MEAN_DOT_RADIUS)
        painter.restore()

    def _paint_mean_label(self, painter: QPainter, layout: BleuLayout, details: BleuDetails, mean_y: float, reveal: float) -> None:
        gutter = layout.mean_gutter
        top = min(max(mean_y - MEAN_LABEL_HEIGHT / 2, gutter.top() - BAR_VALUE_HEIGHT), gutter.bottom() - MEAN_LABEL_HEIGHT)
        rect = QRectF(gutter.left() + BAR_INNER_GAP, top, gutter.width() - BAR_INNER_GAP, MEAN_LABEL_HEIGHT)
        painter.save()
        painter.setOpacity(reveal)
        draw_card(painter, rect, with_alpha(PRIMARY_COLOR, 0.18), PRIMARY_COLOR, MEAN_LABEL_HEIGHT / 2)
        text = MEAN_LABEL_FORMAT.format(value=format_score(details.geometric_mean))
        draw_value(painter, rect, text, TEXT_COLOR, MEAN_LABEL_SIZE, Qt.AlignmentFlag.AlignCenter)
        painter.restore()

    def _paint_note(self, painter: QPainter, layout: BleuLayout, details: BleuDetails, walkthrough: MetricWalkthrough) -> None:
        font = text_font(NOTE_TEXT_SIZE)
        text = elide(self._note_text(details, walkthrough), font, layout.note_rect.width())
        draw_text(painter, layout.note_rect, text, SECONDARY_TEXT_COLOR, font)

    def _note_text(self, details: BleuDetails, walkthrough: MetricWalkthrough) -> str:
        if details.effective_order == 0:
            return NOTE_EMPTY_TEXT
        parts = []
        if details.effective_order < self._order_count(details):
            parts.append(NOTE_EFFECTIVE_FORMAT.format(length=details.answer_length, orders=plural_orders(details.effective_order)))
        if details.smoothed_orders:
            names = ", ".join(subscript(order) for order in details.smoothed_orders)
            parts.append(NOTE_SMOOTHED_FORMAT.format(orders=names, smoothing=self._smoothing_label(walkthrough)))
        elif walkthrough.parameters.get("smooth_method") == SMOOTH_NONE_KEY and self._unmatched_orders(details):
            names = ", ".join(subscript(order) for order in self._unmatched_orders(details))
            parts.append(NOTE_UNSMOOTHED_FORMAT.format(orders=names))
        return NOTE_SEPARATOR.join(parts) if parts else NOTE_DEFAULT_TEXT

    def _paint_penalty_plot(self, painter: QPainter, layout: BleuLayout, details: BleuDetails, position: TimelinePosition) -> None:
        if layout.plot_rect.height() <= CURVE_AXIS_TOP + CURVE_AXIS_BOTTOM:
            return
        progress = stage_progress(position, PENALTY_STEP)
        inner = self._plot_inner(layout.plot_rect)
        painter.save()
        painter.setOpacity(1.0 if position.step_index >= PENALTY_STEP else FUTURE_OPACITY)
        self._paint_axes(painter, inner)
        painter.restore()
        if progress <= 0:
            return
        self._paint_curve(painter, layout, inner, ease_out_cubic(segment_progress(progress, 0.0, CURVE_DRAW_END)))
        self._paint_marker(painter, inner, details, progress)

    def _paint_axes(self, painter: QPainter, inner: QRectF) -> None:
        painter.save()
        painter.setPen(QPen(to_color(BORDER_COLOR), AXIS_LINE_WIDTH))
        painter.drawLine(inner.bottomLeft(), inner.bottomRight())
        painter.drawLine(inner.bottomLeft(), inner.topLeft())
        unit_x = self._plot_point(inner, 1.0, 0.0).x()
        painter.drawLine(QPointF(unit_x, inner.bottom()), QPointF(unit_x, inner.bottom() + BAR_INNER_GAP))
        painter.restore()
        label_font = text_font(CURVE_LABEL_SIZE)
        align_right = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        draw_text(painter, QRectF(inner.left() - CURVE_AXIS_LEFT, inner.top(), CURVE_AXIS_LEFT - BAR_INNER_GAP, CURVE_LABEL_HEIGHT), AXIS_VALUE_LABEL, SECONDARY_TEXT_COLOR, label_font, align_right)
        bottom_rect = QRectF(inner.right() - CURVE_LABEL_WIDTH, inner.bottom() + BAR_INNER_GAP, CURVE_LABEL_WIDTH, CURVE_LABEL_HEIGHT)
        draw_text(painter, bottom_rect, AXIS_RATIO_LABEL, SECONDARY_TEXT_COLOR, label_font, align_right)
        unit_rect = QRectF(unit_x - CURVE_LABEL_WIDTH / 2, inner.bottom() + BAR_INNER_GAP, CURVE_LABEL_WIDTH, CURVE_LABEL_HEIGHT)
        draw_text(painter, unit_rect, AXIS_UNIT_LABEL, SECONDARY_TEXT_COLOR, label_font, Qt.AlignmentFlag.AlignCenter)

    def _paint_curve(self, painter: QPainter, layout: BleuLayout, inner: QRectF, reveal: float) -> None:
        if reveal <= 0:
            return
        painter.save()
        painter.setClipRect(QRectF(inner.left() - CURVE_LINE_WIDTH, inner.top() - CURVE_LINE_WIDTH, inner.width() * reveal + CURVE_LINE_WIDTH, inner.height() + 2 * CURVE_LINE_WIDTH), Qt.ClipOperation.IntersectClip)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(to_color(PRIMARY_COLOR), CURVE_LINE_WIDTH, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(layout.curve)
        painter.restore()

    def _paint_marker(self, painter: QPainter, inner: QRectF, details: BleuDetails, progress: float) -> None:
        travel = segment_progress(progress, MARKER_START, MARKER_END)
        if progress < MARKER_START:
            return
        ratio = lerp(1.0, length_ratio(details), ease_in_out(travel))
        center = self._plot_point(inner, ratio, brevity_penalty_at(ratio))
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(to_color(WARNING_COLOR)))
        painter.drawEllipse(center, MARKER_RADIUS, MARKER_RADIUS)
        ping = segment_progress(progress, MARKER_END, 1.0)
        if 0 < ping < 1:
            radius = lerp(MARKER_RADIUS, PING_MAXIMUM_RADIUS, ease_out_cubic(ping))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(with_alpha(WARNING_COLOR, 1.0 - ping), PING_LINE_WIDTH))
            painter.drawEllipse(center, radius, radius)
        painter.restore()

    def _paint_text_column(self, painter: QPainter, layout: BleuLayout, details: BleuDetails, position: TimelinePosition) -> None:
        if layout.text_rect.width() <= 0 or layout.text_rect.height() <= 0:
            return
        score_progress = stage_progress(position, SCORE_STEP)
        fade = ease_in_out(segment_progress(score_progress, 0.0, SCORE_FADE_END))
        if fade < 1:
            painter.save()
            painter.setOpacity((1.0 - fade) * (1.0 if position.step_index >= PENALTY_STEP else FUTURE_OPACITY))
            self._paint_penalty_text(painter, layout.text_rect, details, stage_progress(position, PENALTY_STEP))
            painter.restore()
        if fade > 0:
            painter.save()
            painter.setOpacity(fade)
            self._paint_score_text(painter, layout.text_rect, details, segment_progress(score_progress, SCORE_COUNT_START, 1.0))
            painter.restore()

    def _paint_penalty_text(self, painter: QPainter, rect: QRectF, details: BleuDetails, progress: float) -> None:
        font = text_font(TEXT_SIZE)
        lines = (
            LENGTHS_FORMAT.format(c=details.answer_length, r=details.reference_length),
            self._penalty_verdict(details),
        )
        top = self._paint_text_caption(painter, rect, PENALTY_CAPTION)
        for index, line in enumerate(lines):
            color = SECONDARY_TEXT_COLOR if index == len(lines) - 1 else LABEL_TEXT_COLOR
            line_rect = QRectF(rect.left(), top + index * TEXT_LINE_HEIGHT, rect.width(), TEXT_LINE_HEIGHT)
            draw_text(painter, line_rect, elide(line, font, rect.width()), color, font)
        value_top = top + len(lines) * TEXT_LINE_HEIGHT
        travel = ease_in_out(segment_progress(progress, MARKER_START, MARKER_END))
        shown = brevity_penalty_at(lerp(1.0, length_ratio(details), travel)) if progress > 0 else None
        value = format_score(shown) if shown is not None else MISSING_VALUE_TEXT
        self._paint_big_value(painter, QRectF(rect.left(), value_top, rect.width(), BIG_VALUE_HEIGHT), PENALTY_VALUE_FORMAT.format(value=value), WARNING_COLOR)

    def _penalty_verdict(self, details: BleuDetails) -> str:
        if details.answer_length == 0:
            return EMPTY_PENALTY_TEXT
        if details.answer_length >= details.reference_length:
            return NO_PENALTY_TEXT
        return PENALTY_TEXT

    def _paint_score_text(self, painter: QPainter, rect: QRectF, details: BleuDetails, progress: float) -> None:
        top = self._paint_text_caption(painter, rect, SCORE_CAPTION)
        product = PRODUCT_FORMAT.format(penalty=format_score(details.brevity_penalty), mean=format_score(details.geometric_mean))
        product_font = monospace_font(PRODUCT_SIZE)
        draw_text(painter, QRectF(rect.left(), top, rect.width(), TEXT_LINE_HEIGHT + BAR_INNER_GAP), elide(product, product_font, rect.width()), LABEL_TEXT_COLOR, product_font)
        value_top = top + TEXT_LINE_HEIGHT + BAR_INNER_GAP
        value = SCORE_VALUE_FORMAT.format(value=format_score(count_up(details.score, progress)))
        self._paint_big_value(painter, QRectF(rect.left(), value_top, rect.width(), BIG_VALUE_HEIGHT), value, PRIMARY_HOVER_COLOR)
        note_rect = QRectF(rect.left(), value_top + BIG_VALUE_HEIGHT, rect.width(), CORPUS_NOTE_HEIGHT)
        if note_rect.bottom() > rect.bottom():
            return
        draw_text(painter, note_rect, CORPUS_NOTE, DISABLED_TEXT_COLOR, text_font(CORPUS_NOTE_SIZE), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, wrap=True)

    def _paint_text_caption(self, painter: QPainter, rect: QRectF, text: str) -> float:
        draw_caption(painter, QRectF(rect.left(), rect.top(), rect.width(), CAPTION_HEIGHT), text)
        return rect.top() + CAPTION_HEIGHT + BAR_INNER_GAP

    def _paint_big_value(self, painter: QPainter, rect: QRectF, text: str, color: str) -> None:
        font = monospace_font(BIG_VALUE_SIZE)
        draw_text(painter, rect, elide(text, font, rect.width()), color, font)
