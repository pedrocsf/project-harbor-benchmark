from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter

from domain.explanations.metric_walkthrough import MetricWalkthrough
from domain.explanations.timeline import TimelinePosition
from domain.explanations.walkthrough_details import TokenOverlapDetails
from presentation.views.branding import LABEL_TEXT_COLOR, PRIMARY_COLOR, PRIMARY_HOVER_COLOR, SECONDARY_TEXT_COLOR, TEXT_COLOR
from presentation.views.metric_explorer.painting import draw_caption, draw_link, segment_progress, with_alpha
from presentation.views.metric_explorer.scenes.base_scene import SceneStep, WalkthroughScene
from presentation.views.metric_explorer.scenes.token_scene_painting import (
    CAPTION_HEIGHT,
    COUNTER_HEIGHT,
    EMPTY_TOKENS_TEXT,
    PENDING_VALUE_TEXT,
    BAR_GAP,
    BAR_HEIGHT,
    ChipMetrics,
    ChipState,
    LayoutCache,
    bar_fill,
    bars_height,
    blend_styles,
    chip_style,
    choose_chip_metrics,
    counter_rects,
    empty_slot_width,
    format_score,
    highlighted_value,
    normalization_options_text,
    options_from_parameters,
    layout_tokens,
    offset_rects,
    paint_chip,
    paint_counter,
    paint_empty_slot,
    paint_score_bar,
    pulse,
    staggered,
)

TOKENIZE_STEP = 0
SHARED_STEP = 1
PRECISION_STEP = 2
RECALL_STEP = 3
F1_STEP = 4
STEPS = (
    SceneStep(
        "Normalize and tokenize",
        "Clean the text and split on spaces: {expected} expected and {answer} answer tokens. {options}",
        3.5,
        (),
    ),
    SceneStep(
        "Count shared tokens",
        "{common} tokens are shared. A token counts at most as many times as it appears in both.",
        4.0,
        (),
    ),
    SceneStep(
        "Precision",
        "How much of the answer is in the expected text: {common} of {answer}.",
        3.5,
        (0,),
    ),
    SceneStep(
        "Recall",
        "How much of the expected text the answer covers: {common} of {expected}.",
        3.5,
        (1,),
    ),
    SceneStep(
        "F-score",
        "{combination}",
        3.0,
        (2,),
    ),
)
FORMULA_BASE = (
    "P = |common| / |answer|",
    "R = |common| / |expected|",
)
CLASSIC_FORMULA = "F1 = 2·P·R / (P + R)"
BETA_FORMULA = "Fβ = (1+β²)·P·R / (β²·P + R), with β = {beta}"
CLASSIC_COMBINATION = "Harmonic mean of {precision} and {recall}: high only when both are high."
BETA_COMBINATION = "F-β with β = {beta} combines {precision} and {recall}: recall weighs β times as much as precision, so {leaning}. Change β with “Parameters…”."
RECALL_LEANING = "missing expected tokens hurt more than extra answer tokens"
PRECISION_LEANING = "extra answer tokens hurt more than missing expected tokens"
CLASSIC_BETA = 1.0
BETA_FORMAT = "{:g}"
BAR_LABEL_FORMAT = "F{beta}"
LIMITATION = "Word order is ignored and synonyms count as misses: “planets” and “planetas” never match."
EXPECTED_CAPTION = "Expected answer · {count}"
ANSWER_CAPTION = "Model answer · {count}"
TOKEN_COUNT_FORMATS = ("{count} token", "{count} tokens")
COMMON_LABEL = "common"
ANSWER_LABEL = "answer tokens"
EXPECTED_LABEL = "expected tokens"
BAR_LABELS = ("Precision", "Recall", "F-score")
SECTION_GAP = 10.0
LINK_BAND_HEIGHT = 60.0
MINIMUM_LINK_BAND_HEIGHT = 28.0
MAXIMUM_LINK_BAND_GROWTH = 48.0
LINK_BAND_SPARE_SHARE = 0.5
LINK_INSET = 2.0
BOTTOM_GAP = 16.0
MINIMUM_FLEX_GAP = 16.0
CHIP_APPEAR_SHARE = 0.35
LINKS_END = 0.85
LINK_SHARE = 0.45
CHIP_LIGHT_START = 0.6
DIM_START = 0.8
SETTLED_LINK_ALPHA = 0.5
COUNTER_PULSE_CYCLES = 2.0
COUNTER_COUNT = 3


def token_count_text(count: int) -> str:
    return TOKEN_COUNT_FORMATS[0 if count == 1 else 1].format(count=count)


@dataclass(frozen=True)
class TokenF1Layout:
    metrics: ChipMetrics
    expected_caption: QRectF
    expected_chips: tuple[QRectF, ...]
    expected_empty: QRectF | None
    answer_chips: tuple[QRectF, ...]
    answer_empty: QRectF | None
    answer_caption: QRectF
    links: tuple[tuple[QPointF, QPointF], ...]
    counters: tuple[QRectF, ...]
    bars: tuple[QRectF, ...]


def _group(tokens: tuple[str, ...]) -> tuple[str, ...]:
    return tokens if tokens else (EMPTY_TOKENS_TEXT,)


def _empty_slot(origin: QPointF, metrics: ChipMetrics, width: float) -> QRectF:
    return QRectF(origin.x(), origin.y(), empty_slot_width(metrics, width), metrics.height)


def build_token_f1_layout(walkthrough: MetricWalkthrough, area: QRectF) -> TokenF1Layout:
    details = token_details(walkthrough)
    bottom_height = COUNTER_HEIGHT + BOTTOM_GAP + bars_height(len(BAR_LABELS))
    fixed_height = 2 * CAPTION_HEIGHT + 2 * SECTION_GAP + LINK_BAND_HEIGHT + bottom_height + MINIMUM_FLEX_GAP
    groups = (_group(details.expected_tokens), _group(details.answer_tokens))
    metrics = choose_chip_metrics(groups, area.width(), area.height() - fixed_height)
    expected_flow = layout_tokens(groups[0], area.width(), metrics)
    answer_flow = layout_tokens(groups[1], area.width(), metrics)
    spare = area.height() - fixed_height - expected_flow.height - answer_flow.height
    link_band = max(MINIMUM_LINK_BAND_HEIGHT, LINK_BAND_HEIGHT + min(spare * LINK_BAND_SPARE_SHARE, MAXIMUM_LINK_BAND_GROWTH))
    top = area.top()
    expected_caption = QRectF(area.left(), top, area.width(), CAPTION_HEIGHT)
    expected_origin = QPointF(area.left(), expected_caption.bottom() + SECTION_GAP)
    answer_origin = QPointF(area.left(), expected_origin.y() + expected_flow.height + link_band)
    answer_caption = QRectF(area.left(), answer_origin.y() + answer_flow.height + SECTION_GAP, area.width(), CAPTION_HEIGHT)
    expected_chips = offset_rects(expected_flow.rects, expected_origin) if details.expected_tokens else ()
    answer_chips = offset_rects(answer_flow.rects, answer_origin) if details.answer_tokens else ()
    bars_top = area.bottom() - bars_height(len(BAR_LABELS))
    bars = tuple(QRectF(area.left(), bars_top + index * (BAR_HEIGHT + BAR_GAP), area.width(), BAR_HEIGHT) for index in range(len(BAR_LABELS)))
    counters = counter_rects(area, bars_top - BOTTOM_GAP - COUNTER_HEIGHT, COUNTER_COUNT)
    links = tuple(
        (
            QPointF(expected_chips[expected_index].center().x(), expected_chips[expected_index].bottom() + LINK_INSET),
            QPointF(answer_chips[answer_index].center().x(), answer_chips[answer_index].top() - LINK_INSET),
        )
        for expected_index, answer_index in details.matches
    )
    return TokenF1Layout(
        metrics=metrics,
        expected_caption=expected_caption,
        expected_chips=expected_chips,
        expected_empty=None if details.expected_tokens else _empty_slot(expected_origin, metrics, area.width()),
        answer_chips=answer_chips,
        answer_empty=None if details.answer_tokens else _empty_slot(answer_origin, metrics, area.width()),
        answer_caption=answer_caption,
        links=links,
        counters=counters,
        bars=bars,
    )


def token_details(walkthrough: MetricWalkthrough) -> TokenOverlapDetails:
    if not isinstance(walkthrough.details, TokenOverlapDetails):
        raise TypeError(f"This scene needs token overlap details, got {type(walkthrough.details).__name__}.")
    return walkthrough.details


def link_progress(position: TimelinePosition, match_order: int, match_count: int) -> float:
    if position.step_index < SHARED_STEP:
        return 0.0
    if position.step_index > SHARED_STEP:
        return 1.0
    return staggered(segment_progress(position.step_progress, 0.0, LINKS_END), match_order, match_count, LINK_SHARE)


class TokenF1Scene(WalkthroughScene):
    identifier = "token_f1"

    def __init__(self):
        self._layouts = LayoutCache(build_token_f1_layout)

    @property
    def steps(self) -> tuple[SceneStep, ...]:
        return STEPS

    @property
    def formula(self) -> tuple[str, ...]:
        return (*FORMULA_BASE, CLASSIC_FORMULA)

    def formula_for(self, walkthrough: MetricWalkthrough) -> tuple[str, ...]:
        beta = token_details(walkthrough).beta
        if beta == CLASSIC_BETA:
            return self.formula
        return (*FORMULA_BASE, BETA_FORMULA.format(beta=BETA_FORMAT.format(beta)))

    @property
    def limitation(self) -> str:
        return LIMITATION

    def step_body(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        details = token_details(walkthrough)
        return STEPS[step_index].body.format(
            options=normalization_options_text(options_from_parameters(walkthrough.parameters)),
            combination=self._combination_text(details),
            common=details.common_count,
            answer=len(details.answer_tokens),
            expected=len(details.expected_tokens),
            precision=format_score(details.precision),
            recall=format_score(details.recall),
        )

    def formula_result(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        details = token_details(walkthrough)
        if step_index == PRECISION_STEP:
            return f"P = {details.common_count} / {len(details.answer_tokens)} = {highlighted_value(details.precision)}"
        if step_index == RECALL_STEP:
            return f"R = {details.common_count} / {len(details.expected_tokens)} = {highlighted_value(details.recall)}"
        if step_index == F1_STEP:
            return self._f1_result(details, walkthrough.final_score)
        return ""

    def paint(self, painter: QPainter, area: QRectF, walkthrough: MetricWalkthrough, position: TimelinePosition) -> None:
        details = token_details(walkthrough)
        layout: TokenF1Layout = self._layouts.get(walkthrough, area)
        painter.save()
        painter.setClipRect(area)
        self._paint_captions(painter, layout, details)
        self._paint_links(painter, layout, position)
        self._paint_tokens(painter, layout, details, position)
        self._paint_counters(painter, layout, details, position)
        self._paint_bars(painter, layout, details, walkthrough.final_score, position)
        painter.restore()

    def _combination_text(self, details: TokenOverlapDetails) -> str:
        precision, recall = format_score(details.precision), format_score(details.recall)
        if details.beta == CLASSIC_BETA:
            return CLASSIC_COMBINATION.format(precision=precision, recall=recall)
        leaning = RECALL_LEANING if details.beta > CLASSIC_BETA else PRECISION_LEANING
        return BETA_COMBINATION.format(beta=BETA_FORMAT.format(details.beta), precision=precision, recall=recall, leaning=leaning)

    def _f1_result(self, details: TokenOverlapDetails, final_score: float) -> str:
        name = BAR_LABEL_FORMAT.format(beta=BETA_FORMAT.format(details.beta))
        precision, recall = format_score(details.precision), format_score(details.recall)
        if details.beta != CLASSIC_BETA:
            return f"{name} = {highlighted_value(final_score)}<br>&nbsp;&nbsp;&nbsp;(P = {precision}, R = {recall})"
        total = details.precision + details.recall
        if total == 0:
            return f"{name} = {highlighted_value(final_score)}"
        return f"{name} = 2·{precision}·{recall} / {format_score(total)}<br>&nbsp;&nbsp;&nbsp;= {highlighted_value(final_score)}"

    def _paint_captions(self, painter: QPainter, layout: TokenF1Layout, details: TokenOverlapDetails) -> None:
        draw_caption(painter, layout.expected_caption, EXPECTED_CAPTION.format(count=token_count_text(len(details.expected_tokens))))
        draw_caption(painter, layout.answer_caption, ANSWER_CAPTION.format(count=token_count_text(len(details.answer_tokens))))

    def _paint_links(self, painter: QPainter, layout: TokenF1Layout, position: TimelinePosition) -> None:
        if position.step_index < SHARED_STEP:
            return
        color = PRIMARY_COLOR if position.step_index == SHARED_STEP else with_alpha(PRIMARY_COLOR, SETTLED_LINK_ALPHA)
        for order, (start, end) in enumerate(layout.links):
            draw_link(painter, start, end, link_progress(position, order, len(layout.links)), color)

    def _paint_tokens(self, painter: QPainter, layout: TokenF1Layout, details: TokenOverlapDetails, position: TimelinePosition) -> None:
        expected_orders = {expected_index: order for order, (expected_index, _) in enumerate(details.matches)}
        answer_orders = {answer_index: order for order, (_, answer_index) in enumerate(details.matches)}
        total = len(layout.expected_chips) + len(layout.answer_chips)
        self._paint_row(painter, layout, layout.expected_chips, details.expected_tokens, expected_orders, 0, total, len(details.matches), position)
        self._paint_row(painter, layout, layout.answer_chips, details.answer_tokens, answer_orders, len(layout.expected_chips), total, len(details.matches), position)
        for empty_slot in (layout.expected_empty, layout.answer_empty):
            if empty_slot is not None:
                paint_empty_slot(painter, empty_slot, layout.metrics)

    def _paint_row(
        self,
        painter: QPainter,
        layout: TokenF1Layout,
        rects: tuple[QRectF, ...],
        tokens: tuple[str, ...],
        match_orders: dict[int, int],
        first_index: int,
        total: int,
        match_count: int,
        position: TimelinePosition,
    ) -> None:
        for index, (rect, token) in enumerate(zip(rects, tokens)):
            appear = staggered(position.step_progress, first_index + index, total, CHIP_APPEAR_SHARE) if position.step_index == TOKENIZE_STEP else 1.0
            style = self._chip_style(match_orders.get(index), match_count, position)
            paint_chip(painter, rect, token, style, layout.metrics, appear)

    def _chip_style(self, match_order: int | None, match_count: int, position: TimelinePosition):
        if position.step_index == TOKENIZE_STEP:
            return chip_style(ChipState.NEUTRAL)
        if match_order is None:
            dim = segment_progress(position.step_progress, DIM_START, 1.0) if position.step_index == SHARED_STEP else 1.0
            return blend_styles(ChipState.NEUTRAL, ChipState.DIMMED, dim)
        light = segment_progress(link_progress(position, match_order, match_count), CHIP_LIGHT_START, 1.0)
        return blend_styles(ChipState.NEUTRAL, ChipState.MATCHED, light)

    def _paint_counters(self, painter: QPainter, layout: TokenF1Layout, details: TokenOverlapDetails, position: TimelinePosition) -> None:
        common_rect, answer_rect, expected_rect = layout.counters
        if position.step_index == TOKENIZE_STEP:
            for rect, label in zip(layout.counters, (COMMON_LABEL, ANSWER_LABEL, EXPECTED_LABEL)):
                paint_counter(painter, rect, label, PENDING_VALUE_TEXT, SECONDARY_TEXT_COLOR)
            return
        paint_counter(painter, common_rect, COMMON_LABEL, str(self._shared_so_far(details, position)), PRIMARY_HOVER_COLOR)
        paint_counter(painter, answer_rect, ANSWER_LABEL, str(len(details.answer_tokens)), self._counter_color(position, PRECISION_STEP), self._glow(position, PRECISION_STEP))
        paint_counter(painter, expected_rect, EXPECTED_LABEL, str(len(details.expected_tokens)), self._counter_color(position, RECALL_STEP), self._glow(position, RECALL_STEP))

    def _shared_so_far(self, details: TokenOverlapDetails, position: TimelinePosition) -> int:
        match_count = len(details.matches)
        return sum(1 for order in range(match_count) if link_progress(position, order, match_count) >= 1.0)

    def _counter_color(self, position: TimelinePosition, emphasis_step: int) -> str:
        if position.step_index in (emphasis_step, F1_STEP):
            return TEXT_COLOR
        return LABEL_TEXT_COLOR

    def _glow(self, position: TimelinePosition, emphasis_step: int) -> float:
        if position.step_index != emphasis_step:
            return 0.0
        return pulse(position.step_progress, COUNTER_PULSE_CYCLES)

    def _paint_bars(self, painter: QPainter, layout: TokenF1Layout, details: TokenOverlapDetails, final_score: float, position: TimelinePosition) -> None:
        values = (details.precision, details.recall, final_score)
        labels = (*BAR_LABELS[:-1], BAR_LABEL_FORMAT.format(beta=BETA_FORMAT.format(details.beta)))
        for bar_step, rect, label, value in zip((PRECISION_STEP, RECALL_STEP, F1_STEP), layout.bars, labels, values):
            fill, reached = bar_fill(position.step_index, bar_step, position.step_progress)
            paint_score_bar(painter, rect, label, value, fill, reached)
