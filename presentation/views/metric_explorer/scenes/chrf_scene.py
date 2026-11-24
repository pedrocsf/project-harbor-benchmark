from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QFont, QPainter, QPen, QPolygonF

from domain.explanations.metric_walkthrough import MetricWalkthrough
from domain.explanations.timeline import TimelinePosition
from domain.explanations.walkthrough_details import ChrfDetails, ChrfOrderStatistics
from presentation.views.branding import (
    BORDER_COLOR,
    LABEL_TEXT_COLOR,
    PRIMARY_COLOR,
    PRIMARY_HOVER_COLOR,
    SECONDARY_TEXT_COLOR,
    STRONG_BORDER_COLOR,
    SURFACE_COLOR,
    TEXT_COLOR,
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
    characters_with_spaces,
    characters_without_spaces,
    chip_widths,
    chrf_words,
    clipped_match_flags,
    count_up,
    draw_character_strip,
    draw_dashed_line,
    draw_divider,
    draw_empty_strip,
    draw_token_strip,
    draw_window,
    elide,
    format_score,
    layout_cells,
    layout_flow,
    parameter_flag,
    space_visible_labels,
    stage_progress,
    sweep_frame,
)

CHARACTER_STEP = 0
WORD_STEP = 1
AVERAGE_STEP = 2
SCORE_STEP = 3

STEPS = (
    SceneStep(
        "Character n-grams",
        "Slide windows of 1 to {character_order} characters over both texts{spacing}{case} and count the shared ones. {characters}",
        6.0,
        (0,),
    ),
    SceneStep(
        "Word n-grams",
        "{words}",
        4.0,
        (0,),
    ),
    SceneStep(
        "Average precision and recall",
        "{average}",
        3.5,
        (0,),
    ),
    SceneStep(
        "F-score weighted by β",
        "{beta_sentence} {name} = {score}.",
        3.5,
        (1, 2),
    ),
)
DEFAULT_CHARACTER_ORDER = 6
DEFAULT_WORD_ORDER = 2
DEFAULT_BETA = 2.0
FORMULA_TEMPLATE = (
    "P, R = mean over {orders}",
    "{name}<sub>β</sub> = (1+β²)·P·R / (β²·P + R)",
    "β = {beta}",
)
PLAIN_NAME = "chrF"
PLUS_NAME = "chrF++"
CHARACTER_ORDERS_FORMAT = "char 1–{count}"
WORD_ORDERS_FORMAT = " + word 1–{count}"
SPACES_REMOVED_TEXT = " with spaces removed"
SPACES_KEPT_TEXT = " with spaces kept (shown as ␣)"
IGNORE_CASE_TEXT = ", ignoring letter case"
WORD_SENTENCE_SINGLE = "Do the same with single words. {words}"
WORD_SENTENCE_MULTIPLE = "Do the same with words, from single words up to {count}-word sequences. {words}"
WORDS_OFF_SENTENCE = "Word n-grams are off (word order 0), so this is plain chrF and this step adds nothing. Change the options with “Parameters…”."
BETA_EQUAL_SENTENCE = "β = 1 weighs precision and recall equally, so the score is their harmonic mean:"
BETA_WEIGHTED_SENTENCE = "β = {beta} makes recall count {beta}× as much as precision, so the score leans toward R:"
EPSILON_SENTENCE = " Epsilon smoothing gives orders with zero statistics a tiny value instead of skipping them."
LIMITATION_WHITESPACE = " Spaces are counted as characters here."
LIMITATION_EPSILON = " Epsilon smoothing keeps orders with no matches from being skipped."
LIMITATION = "Robust to inflections and small typos, but it still only measures surface overlap, not meaning."

CHARACTER_SENTENCE = "Single characters: {matches} shared, out of {answer} in the answer and {reference} in the reference."
WORD_SENTENCE = "Shared: {single} of {single_total} words of the answer."
WORD_PAIRS_SENTENCE = "Shared: {single} of {single_total} words and {pairs} of {pairs_total} word pairs of the answer."
AVERAGE_SENTENCE = "Average precision and recall over the {count} orders that have n-grams on both sides: P = {precision}, R = {recall}."
EMPTY_AVERAGE_SENTENCE = "No order has n-grams on both sides, so P = R = 0."
EMPTY_ANSWER_TEXT = "(empty answer)"
CHARACTER_CAPTION = "Character n-grams · spaces removed"
WORD_CAPTION = "Word n-grams"
AVERAGE_CAPTION = "Average over the orders"
SCORE_CAPTION = "F-score · β = {beta}"
WORDS_OFF_TEXT = "Word n-grams off (word order 0): plain chrF"
BETA_EQUAL_TEXT = "β = 1: precision and recall count equally"
CHARACTER_ROW_LABEL = "chars"
WORD_ROW_LABEL = "words"
PRECISION_HEADER = "Precision"
RECALL_HEADER = "Recall"
AVERAGE_HEADER_FORMAT = "avg {value}"
CHARACTER_ORDER_FORMAT = "char {order}"
WORD_ORDER_FORMAT = "word {order}"
MISSING_VALUE_TEXT = "—"
AVERAGE_PRECISION_FORMAT = "average P = {value}"
AVERAGE_RECALL_FORMAT = "average R = {value}"
BETA_TEXT_FORMAT = "β = {beta}: recall counts {weight}× as much"
SCORE_FORMAT = "{name} = {value}"
PRECISION_PAN_TEXT = "P"
RECALL_PAN_TEXT = "R"
WEIGHTED_RECALL_PAN_TEXT = "R ×{weight}"
NUMBER_FORMAT = "{:g}"

SECTION_GAP = 10.0
CAPTION_HEIGHT = 16.0
STRIP_GAP = 8.0
ROW_LABEL_WIDTH = 52.0
ROW_LABEL_SIZE = 11
CHARACTER_ROW_HEIGHT = 28.0
CELL_PREFERRED_WIDTH = 18.0
CELL_MINIMUM_WIDTH = 12.0
WORD_ROW_HEIGHT = 26.0
WORD_GAP = 6.0
GRID_HEADER_HEIGHT = 16.0
GRID_ROW_MINIMUM = 9.0
GRID_TEXT_PADDING = 3.0
GRID_MINIMUM_TEXT_SIZE = 7
GRID_ROW_MAXIMUM = 24.0
GRID_LABEL_WIDTH = 56.0
GRID_VALUE_WIDTH = 44.0
GRID_COLUMN_GAP = 10.0
GRID_LABEL_SIZE = 12
GRID_VALUE_SIZE = 11
TRACK_HEIGHT = 8.0
MINIMUM_TRACK_FILL = 4.0
AVERAGE_LINE_WIDTH = 1.5
BOTTOM_MINIMUM_HEIGHT = 96.0
BOTTOM_MAXIMUM_HEIGHT = 130.0
BALANCE_MAXIMUM_WIDTH = 200.0
BALANCE_WIDTH_FRACTION = 0.42
BALANCE_PIVOT_FRACTION = 0.72
PAN_EDGE_MARGIN = 4.0
BALANCE_ARM_MAXIMUM = 80.0
BALANCE_BEAM_WIDTH = 2.5
BALANCE_NATURAL_HEIGHT = 96.0
BALANCE_MINIMUM_SCALE = 0.3
BALANCE_BOTTOM_MARGIN = 8.0
BALANCE_TILT_CLEARANCE = 12.0
FULCRUM_HALF_WIDTH = 9.0
PAN_WIDTH = 44.0
PAN_HEIGHT = 22.0
WEIGHTED_PAN_WIDTH = 50.0
WEIGHTED_PAN_EXTRA_HEIGHT = 16.0
PAN_RADIUS = 5.0
PAN_TEXT_SIZE = 11
PAN_FILL_ALPHA = 0.25
TILT_DEGREES = 7.0
TEXT_COLUMN_GAP = 20.0
TEXT_LINE_HEIGHT = 19.0
TEXT_SIZE = 13
BIG_VALUE_HEIGHT = 34.0
BIG_VALUE_SIZE = 20
FUTURE_OPACITY = 0.35
SKIPPED_OPACITY = 0.45

CHARACTER_SWEEP_END = 0.92
WORD_SWEEP_END = 0.9
SEGMENT_SWEEP_SHARE = 0.8
AVERAGE_LINE_END = 0.6
AVERAGE_COUNT_END = 0.8
TILT_END = 0.6
SCORE_COUNT_START = 0.25


@dataclass(frozen=True)
class TextOptions:
    lowercase: bool
    whitespace: bool


@dataclass(frozen=True)
class GridRow:
    label_rect: QRectF
    precision_track: QRectF
    precision_value: QRectF
    recall_track: QRectF
    recall_value: QRectF


@dataclass(frozen=True)
class ChrfLayout:
    caption_rect: QRectF
    character_label: QRectF
    character_bounds: QRectF
    character_strip: StripLayout
    word_label: QRectF
    word_bounds: QRectF
    word_strip: StripLayout
    precision_header: QRectF
    recall_header: QRectF
    rows: tuple[GridRow, ...]
    divider_y: float
    balance_rect: QRectF
    text_rect: QRectF


@dataclass(frozen=True)
class BalanceGeometry:
    pivot: QPointF
    scale: float
    arm: float
    bounds: QRectF


@dataclass(frozen=True)
class SweepPlan:
    units: tuple[str, ...]
    reference_units: tuple[str, ...]
    sweep_end: float
    order_count: int


@dataclass(frozen=True)
class RowState:
    precision: float
    recall: float
    revealed: bool


def is_counted(statistics: ChrfOrderStatistics) -> bool:
    return statistics.answer_count > 0 and statistics.reference_count > 0


def balance_geometry(rect: QRectF) -> BalanceGeometry:
    usable_height = max(0.0, rect.height() - BALANCE_BOTTOM_MARGIN)
    scale = max(BALANCE_MINIMUM_SCALE, min(1.0, usable_height / BALANCE_NATURAL_HEIGHT))
    pivot = QPointF(rect.center().x(), rect.top() + usable_height * BALANCE_PIVOT_FRACTION)
    arm = max(0.0, min(BALANCE_ARM_MAXIMUM, (rect.width() / 2 - PAN_EDGE_MARGIN) / scale - WEIGHTED_PAN_WIDTH / 2))
    half_width = (arm + WEIGHTED_PAN_WIDTH / 2) * scale
    top = pivot.y() - (PAN_HEIGHT + WEIGHTED_PAN_EXTRA_HEIGHT + BALANCE_TILT_CLEARANCE) * scale
    bounds = QRectF(pivot.x() - half_width, top, 2 * half_width, rect.top() + usable_height - top)
    return BalanceGeometry(pivot, scale, arm, bounds)


def format_number(value: float) -> str:
    return NUMBER_FORMAT.format(value)


class ChrfScene(WalkthroughScene):
    identifier = "chrf"

    def __init__(self):
        self._layout_key: tuple | None = None
        self._layout: ChrfLayout | None = None

    @property
    def steps(self) -> tuple[SceneStep, ...]:
        return STEPS

    @property
    def formula(self) -> tuple[str, ...]:
        return self._formula_lines(DEFAULT_CHARACTER_ORDER, DEFAULT_WORD_ORDER, DEFAULT_BETA)

    @property
    def limitation(self) -> str:
        return LIMITATION

    def formula_for(self, walkthrough: MetricWalkthrough) -> tuple[str, ...]:
        details = self._details(walkthrough)
        return self._formula_lines(len(details.character_orders), len(details.word_orders), details.beta)

    def limitation_for(self, walkthrough: MetricWalkthrough) -> str:
        text = LIMITATION
        if parameter_flag(walkthrough.parameters, "whitespace"):
            text += LIMITATION_WHITESPACE
        if parameter_flag(walkthrough.parameters, "eps_smoothing"):
            text += LIMITATION_EPSILON
        return text

    def _formula_lines(self, character_order: int, word_order: int, beta: float) -> tuple[str, ...]:
        orders = CHARACTER_ORDERS_FORMAT.format(count=character_order)
        if word_order > 0:
            orders += WORD_ORDERS_FORMAT.format(count=word_order)
        return tuple(line.format(orders=orders, name=self._name(word_order), beta=format_number(beta)) for line in FORMULA_TEMPLATE)

    def _name(self, word_order: int) -> str:
        return PLUS_NAME if word_order > 0 else PLAIN_NAME

    def _options(self, walkthrough: MetricWalkthrough) -> TextOptions:
        return TextOptions(parameter_flag(walkthrough.parameters, "lowercase"), parameter_flag(walkthrough.parameters, "whitespace"))

    def step_body(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        details = self._details(walkthrough)
        body = STEPS[step_index].body
        if step_index == CHARACTER_STEP:
            return self._character_body(body, details, walkthrough)
        if step_index == WORD_STEP:
            return body.format(words=self._word_sentence(details))
        if step_index == AVERAGE_STEP:
            return body.format(average=self._average_sentence(details, walkthrough))
        return body.format(beta_sentence=self._beta_sentence(details), name=self._name(len(details.word_orders)), score=format_score(details.f_score))

    def _character_body(self, body: str, details: ChrfDetails, walkthrough: MetricWalkthrough) -> str:
        options = self._options(walkthrough)
        return body.format(
            character_order=len(details.character_orders),
            spacing=SPACES_KEPT_TEXT if options.whitespace else SPACES_REMOVED_TEXT,
            case=IGNORE_CASE_TEXT if options.lowercase else "",
            characters=self._character_sentence(details),
        )

    def _beta_sentence(self, details: ChrfDetails) -> str:
        if details.beta == 1:
            return BETA_EQUAL_SENTENCE
        return BETA_WEIGHTED_SENTENCE.format(beta=format_number(details.beta))

    def formula_result(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        details = self._details(walkthrough)
        if step_index == CHARACTER_STEP:
            return self._order_result(CHARACTER_ORDER_FORMAT, details.character_orders[0])
        if step_index == WORD_STEP:
            if not details.word_orders:
                return PLAIN_NAME + ": no word n-grams"
            return self._order_result(WORD_ORDER_FORMAT, details.word_orders[0])
        if step_index == AVERAGE_STEP:
            return f"P = {format_score(details.average_precision)} · R = {format_score(details.average_recall)}"
        return self._score_result(details)

    def paint(self, painter: QPainter, area: QRectF, walkthrough: MetricWalkthrough, position: TimelinePosition) -> None:
        details = self._details(walkthrough)
        layout = self._layout_for(walkthrough, details, area)
        painter.save()
        painter.setClipRect(area, Qt.ClipOperation.IntersectClip)
        draw_caption(painter, layout.caption_rect, self._caption(position, details))
        self._paint_character_row(painter, layout, walkthrough, position)
        self._paint_word_row(painter, layout, walkthrough, position)
        self._paint_grid(painter, layout, walkthrough, details, position)
        draw_divider(painter, area.left(), area.right(), layout.divider_y)
        self._paint_balance(painter, layout, details, position)
        self._paint_text_column(painter, layout, details, position)
        painter.restore()

    def _details(self, walkthrough: MetricWalkthrough) -> ChrfDetails:
        if not isinstance(walkthrough.details, ChrfDetails):
            raise TypeError(f"chrF++ needs chrF details, got {type(walkthrough.details).__name__}.")
        return walkthrough.details

    def _character_sentence(self, details: ChrfDetails) -> str:
        single = details.character_orders[0]
        return CHARACTER_SENTENCE.format(matches=single.match_count, answer=single.answer_count, reference=single.reference_count)

    def _word_sentence(self, details: ChrfDetails) -> str:
        if not details.word_orders:
            return WORDS_OFF_SENTENCE
        single = details.word_orders[0]
        shared = WORD_SENTENCE.format(single=single.match_count, single_total=single.answer_count)
        if len(details.word_orders) == 1:
            return WORD_SENTENCE_SINGLE.format(words=shared)
        return WORD_SENTENCE_MULTIPLE.format(count=len(details.word_orders), words=self._multiple_word_sentence(details))

    def _multiple_word_sentence(self, details: ChrfDetails) -> str:
        single, pairs = details.word_orders[:2]
        return WORD_PAIRS_SENTENCE.format(
            single=single.match_count,
            single_total=single.answer_count,
            pairs=pairs.match_count,
            pairs_total=pairs.answer_count,
        )

    def _average_sentence(self, details: ChrfDetails, walkthrough: MetricWalkthrough) -> str:
        count = sum(1 for order in self._all_orders(details) if is_counted(order))
        if count == 0:
            return EMPTY_AVERAGE_SENTENCE
        sentence = AVERAGE_SENTENCE.format(count=count, precision=format_score(details.average_precision), recall=format_score(details.average_recall))
        return sentence + (EPSILON_SENTENCE if parameter_flag(walkthrough.parameters, "eps_smoothing") else "")

    def _order_result(self, label_format: str, statistics: ChrfOrderStatistics) -> str:
        label = label_format.format(order=statistics.order)
        return f"{label}: P = {format_score(statistics.precision)} · R = {format_score(statistics.recall)}"

    def _score_result(self, details: ChrfDetails) -> str:
        precision, recall = details.average_precision, details.average_recall
        beta_squared = details.beta**2
        if precision == 0 and recall == 0:
            return f"= <b>{format_score(details.f_score)}</b>"
        numerator = (1 + beta_squared) * precision * recall
        denominator = beta_squared * precision + recall
        return f"= {format_score(numerator)} / {format_score(denominator)} = <b>{format_score(details.f_score)}</b>"

    def _all_orders(self, details: ChrfDetails) -> tuple[ChrfOrderStatistics, ...]:
        return details.character_orders + details.word_orders

    def _caption(self, position: TimelinePosition, details: ChrfDetails) -> str:
        captions = (CHARACTER_CAPTION, WORD_CAPTION, AVERAGE_CAPTION, SCORE_CAPTION.format(beta=format_number(details.beta)))
        return captions[position.step_index]

    def _character_units(self, text: str, options: TextOptions) -> tuple[str, ...]:
        if options.whitespace:
            return characters_with_spaces(text, options.lowercase)
        return characters_without_spaces(text, options.lowercase)

    def _character_plan(self, walkthrough: MetricWalkthrough, details: ChrfDetails) -> SweepPlan:
        options = self._options(walkthrough)
        units = self._character_units(walkthrough.given_answer, options)
        reference = self._character_units(walkthrough.expected_answer, options)
        return SweepPlan(units, reference, CHARACTER_SWEEP_END, min(len(details.character_orders), len(units)))

    def _word_plan(self, walkthrough: MetricWalkthrough, details: ChrfDetails) -> SweepPlan:
        lowercase = self._options(walkthrough).lowercase
        units = chrf_words(walkthrough.given_answer, lowercase)
        reference = chrf_words(walkthrough.expected_answer, lowercase)
        return SweepPlan(units, reference, WORD_SWEEP_END, min(len(details.word_orders), len(units)))

    def _layout_for(self, walkthrough: MetricWalkthrough, details: ChrfDetails, area: QRectF) -> ChrfLayout:
        key = (walkthrough.given_answer, self._options(walkthrough), len(details.character_orders), len(details.word_orders), area.left(), area.top(), area.width(), area.height())
        if key != self._layout_key or self._layout is None:
            self._layout = self._build_layout(walkthrough, details, area)
            self._layout_key = key
        return self._layout

    def _build_layout(self, walkthrough: MetricWalkthrough, details: ChrfDetails, area: QRectF) -> ChrfLayout:
        left, width = area.left(), area.width()
        caption_rect = QRectF(left, area.top(), width, CAPTION_HEIGHT)
        strip_left = left + ROW_LABEL_WIDTH
        strip_width = max(0.0, width - ROW_LABEL_WIDTH)
        character_top = caption_rect.bottom() + STRIP_GAP
        character_bounds = QRectF(strip_left, character_top, strip_width, CHARACTER_ROW_HEIGHT)
        characters = self._character_units(walkthrough.given_answer, self._options(walkthrough))
        character_strip = layout_cells(len(characters), character_bounds, CELL_PREFERRED_WIDTH, CELL_MINIMUM_WIDTH)
        word_top = character_bounds.bottom() + STRIP_GAP
        word_bounds = QRectF(strip_left, word_top, strip_width, WORD_ROW_HEIGHT)
        words = chrf_words(walkthrough.given_answer, self._options(walkthrough).lowercase)
        word_strip = layout_flow(chip_widths(words, strip_width), word_bounds, WORD_ROW_HEIGHT, WORD_GAP, 1)
        header_top = word_bounds.bottom() + SECTION_GAP
        rows_top = header_top + GRID_HEADER_HEIGHT
        character_count = len(details.character_orders)
        row_count = character_count + len(details.word_orders)
        available = area.bottom() - rows_top - 2 * SECTION_GAP - BOTTOM_MINIMUM_HEIGHT
        row_height = max(GRID_ROW_MINIMUM, min(GRID_ROW_MAXIMUM, available / row_count))
        rows = tuple(self._build_row(left, width, rows_top + index * row_height, row_height) for index in range(row_count))
        divider_y = rows_top + row_count * row_height + SECTION_GAP
        bottom_top = divider_y + SECTION_GAP
        bottom_height = max(0.0, min(BOTTOM_MAXIMUM_HEIGHT, area.bottom() - bottom_top))
        balance_rect = QRectF(left, bottom_top, min(BALANCE_MAXIMUM_WIDTH, width * BALANCE_WIDTH_FRACTION), bottom_height)
        text_left = balance_rect.right() + TEXT_COLUMN_GAP
        text_rect = QRectF(text_left, bottom_top, max(0.0, area.right() - text_left), bottom_height)
        first_row = rows[0]
        precision_header = QRectF(first_row.precision_track.left(), header_top, first_row.precision_value.right() - first_row.precision_track.left(), GRID_HEADER_HEIGHT)
        recall_header = QRectF(first_row.recall_track.left(), header_top, first_row.recall_value.right() - first_row.recall_track.left(), GRID_HEADER_HEIGHT)
        return ChrfLayout(
            caption_rect,
            QRectF(left, character_top, ROW_LABEL_WIDTH, CHARACTER_ROW_HEIGHT),
            character_bounds,
            character_strip,
            QRectF(left, word_top, ROW_LABEL_WIDTH, WORD_ROW_HEIGHT),
            word_bounds,
            word_strip,
            precision_header,
            recall_header,
            rows,
            divider_y,
            balance_rect,
            text_rect,
        )

    def _build_row(self, left: float, width: float, top: float, height: float) -> GridRow:
        track_width = max(0.0, (width - GRID_LABEL_WIDTH - 2 * GRID_VALUE_WIDTH - 3 * GRID_COLUMN_GAP) / 2)
        track_top = top + (height - TRACK_HEIGHT) / 2
        precision_left = left + GRID_LABEL_WIDTH + GRID_COLUMN_GAP
        precision_track = QRectF(precision_left, track_top, track_width, TRACK_HEIGHT)
        precision_value = QRectF(precision_track.right(), top, GRID_VALUE_WIDTH, height)
        recall_left = precision_value.right() + GRID_COLUMN_GAP
        recall_track = QRectF(recall_left, track_top, track_width, TRACK_HEIGHT)
        recall_value = QRectF(recall_track.right(), top, GRID_VALUE_WIDTH, height)
        return GridRow(QRectF(left, top, GRID_LABEL_WIDTH, height), precision_track, precision_value, recall_track, recall_value)

    def _segment_bounds(self, plan: SweepPlan, order: int) -> tuple[float, float] | None:
        if order > plan.order_count:
            return None
        length = plan.sweep_end / plan.order_count
        return (order - 1) * length, order * length

    def _active_order(self, plan: SweepPlan, progress: float) -> int | None:
        if plan.order_count == 0 or progress <= 0 or progress >= plan.sweep_end:
            return None
        return min(plan.order_count, int(progress / plan.sweep_end * plan.order_count) + 1)

    def _flags(self, plan: SweepPlan, order: int) -> tuple[bool, ...]:
        return clipped_match_flags(plan.units, plan.reference_units, order)

    def _sweep(self, plan: SweepPlan, strip: StripLayout, order: int, progress: float):
        start, end = self._segment_bounds(plan, order)
        local = segment_progress(progress, start, end)
        visible = max(0, len(strip.unit_rects) - order + 1)
        return sweep_frame(self._flags(plan, order), order, local / SEGMENT_SWEEP_SHARE, visible)

    def _coverage(self, plan: SweepPlan, order: int) -> list[float]:
        flags = self._flags(plan, order)
        covered = {unit for start, flag in enumerate(flags) if flag for unit in range(start, start + order)}
        return [1.0 if unit in covered else 0.0 for unit in range(len(plan.units))]

    def _settled_highlights(self, plan: SweepPlan, progress: float) -> list[float]:
        if plan.order_count == 0:
            return []
        if progress < plan.sweep_end:
            return [0.0] * len(plan.units)
        single = self._coverage(plan, 1)
        if plan.order_count == 1:
            return single
        last = self._coverage(plan, plan.order_count)
        blend = ease_in_out(segment_progress(progress, plan.sweep_end, 1.0))
        return [lerp(previous, final, blend) for previous, final in zip(last, single)]

    def _strip_highlights(self, plan: SweepPlan, strip: StripLayout, progress: float, active_order: int | None) -> tuple[list[float], int]:
        if active_order is None:
            return self._settled_highlights(plan, progress), NO_WINDOW
        sweep = self._sweep(plan, strip, active_order, progress)
        highlights = [1.0 if unit in sweep.covered_units else 0.0 for unit in range(len(plan.units))]
        return highlights, sweep.window_index

    def _paint_row_label(self, painter: QPainter, rect: QRectF, text: str, is_active: bool) -> None:
        color = TEXT_COLOR if is_active else SECONDARY_TEXT_COLOR
        draw_text(painter, rect, text, color, text_font(ROW_LABEL_SIZE, QFont.Weight.DemiBold))

    def _paint_character_row(self, painter: QPainter, layout: ChrfLayout, walkthrough: MetricWalkthrough, position: TimelinePosition) -> None:
        plan = self._character_plan(walkthrough, self._details(walkthrough))
        progress = stage_progress(position, CHARACTER_STEP)
        self._paint_row_label(painter, layout.character_label, CHARACTER_ROW_LABEL, position.step_index == CHARACTER_STEP)
        if not plan.units:
            draw_empty_strip(painter, layout.character_bounds, EMPTY_ANSWER_TEXT)
            return
        active_order = self._active_order(plan, progress)
        highlights, window_index = self._strip_highlights(plan, layout.character_strip, progress, active_order)
        draw_character_strip(painter, layout.character_strip, space_visible_labels(plan.units), highlights)
        if window_index != NO_WINDOW:
            draw_window(painter, layout.character_strip, window_index, active_order)

    def _paint_word_row(self, painter: QPainter, layout: ChrfLayout, walkthrough: MetricWalkthrough, position: TimelinePosition) -> None:
        details = self._details(walkthrough)
        plan = self._word_plan(walkthrough, details)
        progress = stage_progress(position, WORD_STEP)
        self._paint_row_label(painter, layout.word_label, WORD_ROW_LABEL, position.step_index == WORD_STEP)
        if not details.word_orders:
            draw_empty_strip(painter, layout.word_bounds, WORDS_OFF_TEXT)
            return
        if not plan.units:
            draw_empty_strip(painter, layout.word_bounds, EMPTY_ANSWER_TEXT)
            return
        active_order = self._active_order(plan, progress)
        highlights, window_index = self._strip_highlights(plan, layout.word_strip, progress, active_order)
        painter.save()
        painter.setOpacity(1.0 if position.step_index >= WORD_STEP else FUTURE_OPACITY)
        draw_token_strip(painter, layout.word_strip, plan.units, highlights)
        if window_index != NO_WINDOW:
            draw_window(painter, layout.word_strip, window_index, active_order)
        painter.restore()

    def _row_state(self, plan: SweepPlan, strip: StripLayout, statistics: ChrfOrderStatistics, progress: float) -> RowState:
        bounds = self._segment_bounds(plan, statistics.order)
        if bounds is None or not is_counted(statistics):
            return RowState(0.0, 0.0, False)
        local = segment_progress(progress, *bounds)
        if local <= 0:
            return RowState(0.0, 0.0, False)
        matched = self._sweep(plan, strip, statistics.order, progress).matched_count
        settle = ease_in_out(segment_progress(local, SEGMENT_SWEEP_SHARE, 1.0))
        precision = lerp(matched / statistics.answer_count, statistics.precision, settle)
        recall = lerp(matched / statistics.reference_count, statistics.recall, settle)
        return RowState(precision, recall, True)

    def _paint_grid(self, painter: QPainter, layout: ChrfLayout, walkthrough: MetricWalkthrough, details: ChrfDetails, position: TimelinePosition) -> None:
        average_progress = stage_progress(position, AVERAGE_STEP)
        self._paint_grid_headers(painter, layout, details, average_progress)
        character_plan = self._character_plan(walkthrough, details)
        word_plan = self._word_plan(walkthrough, details)
        character_progress = stage_progress(position, CHARACTER_STEP)
        word_progress = stage_progress(position, WORD_STEP)
        for index, statistics in enumerate(details.character_orders):
            state = self._row_state(character_plan, layout.character_strip, statistics, character_progress)
            is_active = self._active_order(character_plan, character_progress) == statistics.order
            self._paint_grid_row(painter, layout.rows[index], CHARACTER_ORDER_FORMAT.format(order=statistics.order), statistics, state, is_active)
        for index, statistics in enumerate(details.word_orders):
            state = self._row_state(word_plan, layout.word_strip, statistics, word_progress)
            is_active = self._active_order(word_plan, word_progress) == statistics.order
            row = layout.rows[len(details.character_orders) + index]
            self._paint_grid_row(painter, row, WORD_ORDER_FORMAT.format(order=statistics.order), statistics, state, is_active)
        self._paint_average_lines(painter, layout, details, average_progress)

    def _paint_grid_headers(self, painter: QPainter, layout: ChrfLayout, details: ChrfDetails, progress: float) -> None:
        draw_caption(painter, layout.precision_header, PRECISION_HEADER)
        draw_caption(painter, layout.recall_header, RECALL_HEADER)
        if progress <= 0:
            return
        painter.save()
        painter.setOpacity(ease_out_cubic(segment_progress(progress, 0.0, AVERAGE_LINE_END)))
        align_right = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        precision_text = AVERAGE_HEADER_FORMAT.format(value=format_score(details.average_precision))
        recall_text = AVERAGE_HEADER_FORMAT.format(value=format_score(details.average_recall))
        draw_value(painter, layout.precision_header, precision_text, PRIMARY_HOVER_COLOR, GRID_VALUE_SIZE, align_right)
        draw_value(painter, layout.recall_header, recall_text, PRIMARY_HOVER_COLOR, GRID_VALUE_SIZE, align_right)
        painter.restore()

    def _paint_grid_row(self, painter: QPainter, row: GridRow, label: str, statistics: ChrfOrderStatistics, state: RowState, is_active: bool) -> None:
        counted = is_counted(statistics)
        painter.save()
        painter.setOpacity(1.0 if counted else SKIPPED_OPACITY)
        label_color = TEXT_COLOR if is_active else LABEL_TEXT_COLOR
        label_size = self._grid_text_size(GRID_LABEL_SIZE, row.label_rect.height())
        value_size = self._grid_text_size(GRID_VALUE_SIZE, row.label_rect.height())
        draw_text(painter, row.label_rect, label, label_color, text_font(label_size, QFont.Weight.DemiBold if is_active else QFont.Weight.Normal))
        self._paint_track(painter, row.precision_track, state.precision, STRONG_BORDER_COLOR, is_active)
        self._paint_track(painter, row.recall_track, state.recall, PRIMARY_COLOR, is_active)
        precision_text, recall_text = self._row_values(counted, state)
        align_right = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        draw_value(painter, row.precision_value, precision_text, LABEL_TEXT_COLOR, value_size, align_right)
        draw_value(painter, row.recall_value, recall_text, LABEL_TEXT_COLOR, value_size, align_right)
        painter.restore()

    def _grid_text_size(self, preferred: int, row_height: float) -> int:
        return max(GRID_MINIMUM_TEXT_SIZE, min(preferred, int(row_height - GRID_TEXT_PADDING)))

    def _row_values(self, counted: bool, state: RowState) -> tuple[str, str]:
        if not counted:
            return MISSING_VALUE_TEXT, MISSING_VALUE_TEXT
        if not state.revealed:
            return "", ""
        return format_score(state.precision), format_score(state.recall)

    def _paint_track(self, painter: QPainter, track: QRectF, fraction: float, color: str, is_active: bool) -> None:
        radius = TRACK_HEIGHT / 2
        draw_card(painter, track, SURFACE_COLOR, BORDER_COLOR if is_active else None, radius)
        if fraction <= 0 or track.width() <= 0:
            return
        width = max(MINIMUM_TRACK_FILL, track.width() * clamp_unit(fraction))
        draw_card(painter, QRectF(track.left(), track.top(), width, track.height()), color, None, radius)

    def _paint_average_lines(self, painter: QPainter, layout: ChrfLayout, details: ChrfDetails, progress: float) -> None:
        reveal = ease_out_cubic(segment_progress(progress, 0.0, AVERAGE_LINE_END))
        if reveal <= 0:
            return
        first, last = layout.rows[0], layout.rows[-1]
        top = first.label_rect.top()
        bottom = lerp(top, last.label_rect.bottom(), reveal)
        for track, value in ((first.precision_track, details.average_precision), (first.recall_track, details.average_recall)):
            x = track.left() + track.width() * clamp_unit(value)
            draw_dashed_line(painter, QPointF(x, top), QPointF(x, bottom), PRIMARY_HOVER_COLOR, AVERAGE_LINE_WIDTH)

    def _paint_balance(self, painter: QPainter, layout: ChrfLayout, details: ChrfDetails, position: TimelinePosition) -> None:
        rect = layout.balance_rect
        if rect.height() < PAN_HEIGHT + WEIGHTED_PAN_EXTRA_HEIGHT or rect.width() <= 0:
            return
        score_progress = stage_progress(position, SCORE_STEP)
        weight = ease_in_out(segment_progress(score_progress, 0.0, TILT_END)) * clamp_unit(details.beta - 1)
        geometry = balance_geometry(rect)
        pivot = geometry.pivot
        painter.save()
        painter.setOpacity(1.0 if position.step_index >= AVERAGE_STEP else FUTURE_OPACITY)
        self._paint_fulcrum(painter, pivot, geometry.bounds.bottom(), geometry.scale)
        painter.translate(pivot)
        painter.scale(geometry.scale, geometry.scale)
        painter.rotate(TILT_DEGREES * weight)
        self._paint_beam(painter, geometry.arm, details, weight)
        painter.restore()

    def _paint_fulcrum(self, painter: QPainter, pivot: QPointF, bottom: float, scale: float) -> None:
        triangle = QPolygonF([pivot, QPointF(pivot.x() - FULCRUM_HALF_WIDTH * scale, bottom), QPointF(pivot.x() + FULCRUM_HALF_WIDTH * scale, bottom)])
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(to_color(BORDER_COLOR)))
        painter.drawPolygon(triangle)
        painter.restore()

    def _paint_beam(self, painter: QPainter, arm: float, details: ChrfDetails, weight: float) -> None:
        painter.save()
        painter.setPen(QPen(to_color(LABEL_TEXT_COLOR), BALANCE_BEAM_WIDTH, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(-arm, 0), QPointF(arm, 0))
        painter.restore()
        precision_pan = QRectF(-arm - PAN_WIDTH / 2, -PAN_HEIGHT, PAN_WIDTH, PAN_HEIGHT)
        draw_card(painter, precision_pan, SURFACE_COLOR, STRONG_BORDER_COLOR, PAN_RADIUS)
        draw_value(painter, precision_pan, PRECISION_PAN_TEXT, LABEL_TEXT_COLOR, PAN_TEXT_SIZE, Qt.AlignmentFlag.AlignCenter)
        recall_width = lerp(PAN_WIDTH, WEIGHTED_PAN_WIDTH, weight)
        recall_height = PAN_HEIGHT + WEIGHTED_PAN_EXTRA_HEIGHT * weight
        recall_pan = QRectF(arm - recall_width / 2, -recall_height, recall_width, recall_height)
        fill = with_alpha(PRIMARY_COLOR, PAN_FILL_ALPHA * weight)
        draw_card(painter, recall_pan, SURFACE_COLOR, None, PAN_RADIUS)
        draw_card(painter, recall_pan, fill, PRIMARY_COLOR if weight > 0 else STRONG_BORDER_COLOR, PAN_RADIUS)
        recall_text = WEIGHTED_RECALL_PAN_TEXT.format(weight=format_number(details.beta)) if weight >= 0.5 else RECALL_PAN_TEXT
        draw_value(painter, recall_pan, recall_text, TEXT_COLOR, PAN_TEXT_SIZE, Qt.AlignmentFlag.AlignCenter)

    def _paint_text_column(self, painter: QPainter, layout: ChrfLayout, details: ChrfDetails, position: TimelinePosition) -> None:
        rect = layout.text_rect
        if rect.width() <= 0 or rect.height() <= 0:
            return
        average_progress = stage_progress(position, AVERAGE_STEP)
        score_progress = stage_progress(position, SCORE_STEP)
        painter.save()
        painter.setOpacity(1.0 if position.step_index >= AVERAGE_STEP else FUTURE_OPACITY)
        counted = segment_progress(average_progress, 0.0, AVERAGE_COUNT_END)
        self._paint_average_line(painter, rect, 0, AVERAGE_PRECISION_FORMAT, details.average_precision, counted, average_progress)
        self._paint_average_line(painter, rect, 1, AVERAGE_RECALL_FORMAT, details.average_recall, counted, average_progress)
        self._paint_beta_line(painter, rect, details, score_progress)
        self._paint_score(painter, rect, details, score_progress)
        painter.restore()

    def _paint_average_line(self, painter: QPainter, rect: QRectF, index: int, template: str, value: float, counted: float, progress: float) -> None:
        font = text_font(TEXT_SIZE)
        shown = format_score(count_up(value, counted)) if progress > 0 else MISSING_VALUE_TEXT
        line_rect = QRectF(rect.left(), rect.top() + index * TEXT_LINE_HEIGHT, rect.width(), TEXT_LINE_HEIGHT)
        draw_text(painter, line_rect, elide(template.format(value=shown), font, rect.width()), LABEL_TEXT_COLOR, font)

    def _paint_beta_line(self, painter: QPainter, rect: QRectF, details: ChrfDetails, progress: float) -> None:
        reveal = ease_out_cubic(segment_progress(progress, 0.0, TILT_END)) if progress > 0 else 0.0
        if reveal <= 0:
            return
        font = text_font(TEXT_SIZE)
        text = BETA_EQUAL_TEXT if details.beta == 1 else BETA_TEXT_FORMAT.format(beta=format_number(details.beta), weight=format_number(details.beta))
        line_rect = QRectF(rect.left(), rect.top() + 2 * TEXT_LINE_HEIGHT, rect.width(), TEXT_LINE_HEIGHT)
        painter.save()
        painter.setOpacity(painter.opacity() * reveal)
        draw_text(painter, line_rect, elide(text, font, rect.width()), SECONDARY_TEXT_COLOR, font)
        painter.restore()

    def _paint_score(self, painter: QPainter, rect: QRectF, details: ChrfDetails, progress: float) -> None:
        font = monospace_font(BIG_VALUE_SIZE)
        counted = segment_progress(progress, SCORE_COUNT_START, 1.0)
        shown = format_score(count_up(details.f_score, counted)) if progress > 0 else MISSING_VALUE_TEXT
        value_rect = QRectF(rect.left(), rect.top() + 3 * TEXT_LINE_HEIGHT, rect.width(), BIG_VALUE_HEIGHT)
        draw_text(painter, value_rect, elide(SCORE_FORMAT.format(name=self._name(len(details.word_orders)), value=shown), font, rect.width()), PRIMARY_HOVER_COLOR, font)
