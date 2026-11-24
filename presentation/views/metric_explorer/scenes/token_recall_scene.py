from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter

from domain.explanations.metric_walkthrough import MetricWalkthrough
from domain.explanations.timeline import TimelinePosition
from domain.explanations.walkthrough_details import TokenOverlapDetails
from presentation.views.branding import LABEL_TEXT_COLOR, PRIMARY_HOVER_COLOR, SECONDARY_TEXT_COLOR, TEXT_COLOR
from presentation.views.metric_explorer.painting import draw_caption, segment_progress
from presentation.views.metric_explorer.scenes.base_scene import SceneStep, WalkthroughScene
from presentation.views.metric_explorer.scenes.token_f1_scene import token_count_text, token_details
from presentation.views.metric_explorer.scenes.token_scene_painting import (
    BAR_HEIGHT,
    CAPTION_HEIGHT,
    COUNTER_HEIGHT,
    EMPTY_TOKENS_TEXT,
    PENDING_VALUE_TEXT,
    normalization_options_text,
    options_from_parameters,
    ChipMetrics,
    ChipState,
    ChipStyle,
    LayoutCache,
    bar_fill,
    blend_styles,
    chip_style,
    choose_chip_metrics,
    counter_rects,
    empty_slot_width,
    highlighted_value,
    layout_tokens,
    note_height,
    offset_rects,
    paint_chip,
    paint_counter,
    paint_empty_slot,
    paint_note,
    paint_score_bar,
    pulse,
    quoted_list,
    staggered,
)

TOKENIZE_STEP = 0
FIND_STEP = 1
RECALL_STEP = 2
STEPS = (
    SceneStep(
        "Normalize and tokenize",
        "Clean the text and split on spaces: {expected} expected and {answer} answer tokens. {options}",
        3.5,
        (),
    ),
    SceneStep(
        "Find the expected tokens",
        "Each expected token lights up when the answer contains it: {common} of {expected} are found. A token counts at most as many times as it appears in both.",
        4.0,
        (),
    ),
    SceneStep(
        "Recall",
        "The share of the expected tokens that the answer covers: {common} of {expected}.",
        3.5,
        (0,),
    ),
)
FORMULA = (
    "R = |common| / |expected|",
)
LIMITATION = "Extra words in the answer are not penalized, so a long answer that lists everything can still score 1."
EXPECTED_CAPTION = "Expected · {count}"
ANSWER_CAPTION = "Model answer · {count}"
FOUND_LABEL = "found"
EXPECTED_LABEL = "expected tokens"
RECALL_LABEL = "Recall"
EXTRA_SINGLE_FORMAT = "{items} is extra and costs nothing."
EXTRA_PLURAL_FORMAT = "{items} are extra and cost nothing."
MISSING_SINGLE_FORMAT = "{items} is missing, so it lowers recall."
MISSING_PLURAL_FORMAT = "{items} are missing, so they lower recall."
ALL_FOUND_TEXT = "Every expected token is in the answer."
EMPTY_ANSWER_TEXT = "The answer is empty, so no expected token can be found."
EMPTY_EXPECTED_TEXT = "The expected answer has no tokens to look for."
SECTION_GAP = 10.0
GROUP_GAP = 18.0
NOTE_GAP = 14.0
BOTTOM_GAP = 12.0
MINIMUM_FLEX_GAP = 12.0
CHIP_APPEAR_SHARE = 0.35
REVEAL_END = 0.82
REVEAL_SHARE = 0.4
LIGHT_START = 0.3
NOTE_START = 0.82
EXTRA_DIM_START = 0.82
COUNTER_PULSE_CYCLES = 2.0
COUNTER_COUNT = 2


@dataclass(frozen=True)
class TokenRecallLayout:
    metrics: ChipMetrics
    expected_caption: QRectF
    expected_chips: tuple[QRectF, ...]
    expected_empty: QRectF | None
    answer_caption: QRectF
    answer_chips: tuple[QRectF, ...]
    answer_empty: QRectF | None
    note_rect: QRectF
    note: str
    counters: tuple[QRectF, ...]
    bar: QRectF


def _plural_sentence(items: list[str], single_format: str, plural_format: str) -> str:
    template = single_format if len(items) == 1 else plural_format
    return template.format(items=quoted_list(items))


def recall_note(details: TokenOverlapDetails) -> str:
    if not details.expected_tokens:
        return EMPTY_EXPECTED_TEXT
    if not details.answer_tokens:
        return EMPTY_ANSWER_TEXT
    matched_answer = set(details.matched_answer_indexes)
    matched_expected = set(details.matched_expected_indexes)
    extras = [token for index, token in enumerate(details.answer_tokens) if index not in matched_answer]
    missing = [token for index, token in enumerate(details.expected_tokens) if index not in matched_expected]
    sentences = []
    if extras:
        sentences.append(_plural_sentence(extras, EXTRA_SINGLE_FORMAT, EXTRA_PLURAL_FORMAT))
    sentences.append(_plural_sentence(missing, MISSING_SINGLE_FORMAT, MISSING_PLURAL_FORMAT) if missing else ALL_FOUND_TEXT)
    return " ".join(sentences)


def _group(tokens: tuple[str, ...]) -> tuple[str, ...]:
    return tokens if tokens else (EMPTY_TOKENS_TEXT,)


def build_token_recall_layout(walkthrough: MetricWalkthrough, area: QRectF) -> TokenRecallLayout:
    details = token_details(walkthrough)
    note = recall_note(details)
    note_space = note_height(note, area.width())
    bottom_height = COUNTER_HEIGHT + BOTTOM_GAP + BAR_HEIGHT
    fixed_height = 2 * CAPTION_HEIGHT + 2 * SECTION_GAP + GROUP_GAP + NOTE_GAP + note_space + MINIMUM_FLEX_GAP + bottom_height
    groups = (_group(details.expected_tokens), _group(details.answer_tokens))
    metrics = choose_chip_metrics(groups, area.width(), area.height() - fixed_height)
    expected_flow = layout_tokens(groups[0], area.width(), metrics)
    answer_flow = layout_tokens(groups[1], area.width(), metrics)
    expected_caption = QRectF(area.left(), area.top(), area.width(), CAPTION_HEIGHT)
    expected_origin = QPointF(area.left(), expected_caption.bottom() + SECTION_GAP)
    answer_caption = QRectF(area.left(), expected_origin.y() + expected_flow.height + GROUP_GAP, area.width(), CAPTION_HEIGHT)
    answer_origin = QPointF(area.left(), answer_caption.bottom() + SECTION_GAP)
    note_rect = QRectF(area.left(), answer_origin.y() + answer_flow.height + NOTE_GAP, area.width(), note_space)
    bar = QRectF(area.left(), area.bottom() - BAR_HEIGHT, area.width(), BAR_HEIGHT)
    counters = counter_rects(area, bar.top() - BOTTOM_GAP - COUNTER_HEIGHT, COUNTER_COUNT)
    return TokenRecallLayout(
        metrics=metrics,
        expected_caption=expected_caption,
        expected_chips=offset_rects(expected_flow.rects, expected_origin) if details.expected_tokens else (),
        expected_empty=None if details.expected_tokens else QRectF(expected_origin.x(), expected_origin.y(), empty_slot_width(metrics, area.width()), metrics.height),
        answer_caption=answer_caption,
        answer_chips=offset_rects(answer_flow.rects, answer_origin) if details.answer_tokens else (),
        answer_empty=None if details.answer_tokens else QRectF(answer_origin.x(), answer_origin.y(), empty_slot_width(metrics, area.width()), metrics.height),
        note_rect=note_rect,
        note=note,
        counters=counters,
        bar=bar,
    )


def reveal_progress(position: TimelinePosition, expected_index: int, expected_count: int) -> float:
    if position.step_index < FIND_STEP:
        return 0.0
    if position.step_index > FIND_STEP:
        return 1.0
    return staggered(segment_progress(position.step_progress, 0.0, REVEAL_END), expected_index, expected_count, REVEAL_SHARE)


class TokenRecallScene(WalkthroughScene):
    identifier = "token_recall"

    def __init__(self):
        self._layouts = LayoutCache(build_token_recall_layout)

    @property
    def steps(self) -> tuple[SceneStep, ...]:
        return STEPS

    @property
    def formula(self) -> tuple[str, ...]:
        return FORMULA

    @property
    def limitation(self) -> str:
        return LIMITATION

    def step_body(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        details = token_details(walkthrough)
        return STEPS[step_index].body.format(
            options=normalization_options_text(options_from_parameters(walkthrough.parameters)),
            common=details.common_count,
            answer=len(details.answer_tokens),
            expected=len(details.expected_tokens),
        )

    def formula_result(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        if step_index != RECALL_STEP:
            return ""
        details = token_details(walkthrough)
        return f"R = {details.common_count} / {len(details.expected_tokens)} = {highlighted_value(walkthrough.final_score)}"

    def paint(self, painter: QPainter, area: QRectF, walkthrough: MetricWalkthrough, position: TimelinePosition) -> None:
        details = token_details(walkthrough)
        layout: TokenRecallLayout = self._layouts.get(walkthrough, area)
        painter.save()
        painter.setClipRect(area)
        draw_caption(painter, layout.expected_caption, EXPECTED_CAPTION.format(count=token_count_text(len(details.expected_tokens))))
        draw_caption(painter, layout.answer_caption, ANSWER_CAPTION.format(count=token_count_text(len(details.answer_tokens))))
        self._paint_expected(painter, layout, details, position)
        self._paint_answer(painter, layout, details, position)
        self._paint_empty_slots(painter, layout)
        paint_note(painter, layout.note_rect, layout.note, self._note_opacity(position))
        self._paint_counters(painter, layout, details, position)
        fill, reached = bar_fill(position.step_index, RECALL_STEP, position.step_progress)
        paint_score_bar(painter, layout.bar, RECALL_LABEL, walkthrough.final_score, fill, reached)
        painter.restore()

    def _appear(self, position: TimelinePosition, index: int, total: int) -> float:
        if position.step_index != TOKENIZE_STEP:
            return 1.0
        return staggered(position.step_progress, index, total, CHIP_APPEAR_SHARE)

    def _paint_expected(self, painter: QPainter, layout: TokenRecallLayout, details: TokenOverlapDetails, position: TimelinePosition) -> None:
        matched = set(details.matched_expected_indexes)
        total = len(layout.expected_chips) + len(layout.answer_chips)
        for index, (rect, token) in enumerate(zip(layout.expected_chips, details.expected_tokens)):
            reveal = segment_progress(reveal_progress(position, index, len(layout.expected_chips)), LIGHT_START, 1.0)
            target = ChipState.MATCHED if index in matched else ChipState.MISSING
            paint_chip(painter, rect, token, blend_styles(ChipState.NEUTRAL, target, reveal), layout.metrics, self._appear(position, index, total))

    def _paint_answer(self, painter: QPainter, layout: TokenRecallLayout, details: TokenOverlapDetails, position: TimelinePosition) -> None:
        expected_by_answer = {answer_index: expected_index for expected_index, answer_index in details.matches}
        offset = len(layout.expected_chips)
        total = offset + len(layout.answer_chips)
        for index, (rect, token) in enumerate(zip(layout.answer_chips, details.answer_tokens)):
            style = self._answer_style(expected_by_answer.get(index), len(layout.expected_chips), position)
            paint_chip(painter, rect, token, style, layout.metrics, self._appear(position, offset + index, total))

    def _answer_style(self, expected_index: int | None, expected_count: int, position: TimelinePosition) -> ChipStyle:
        if position.step_index == TOKENIZE_STEP:
            return chip_style(ChipState.NEUTRAL)
        if expected_index is None:
            dim = segment_progress(position.step_progress, EXTRA_DIM_START, 1.0) if position.step_index == FIND_STEP else 1.0
            return blend_styles(ChipState.NEUTRAL, ChipState.DIMMED, dim)
        light = segment_progress(reveal_progress(position, expected_index, expected_count), LIGHT_START, 1.0)
        return blend_styles(ChipState.NEUTRAL, ChipState.MATCHED, light)

    def _paint_empty_slots(self, painter: QPainter, layout: TokenRecallLayout) -> None:
        for empty_slot in (layout.expected_empty, layout.answer_empty):
            if empty_slot is not None:
                paint_empty_slot(painter, empty_slot, layout.metrics)

    def _note_opacity(self, position: TimelinePosition) -> float:
        if position.step_index < FIND_STEP:
            return 0.0
        if position.step_index > FIND_STEP:
            return 1.0
        return segment_progress(position.step_progress, NOTE_START, 1.0)

    def _paint_counters(self, painter: QPainter, layout: TokenRecallLayout, details: TokenOverlapDetails, position: TimelinePosition) -> None:
        found_rect, expected_rect = layout.counters
        if position.step_index == TOKENIZE_STEP:
            paint_counter(painter, found_rect, FOUND_LABEL, PENDING_VALUE_TEXT, SECONDARY_TEXT_COLOR)
            paint_counter(painter, expected_rect, EXPECTED_LABEL, PENDING_VALUE_TEXT, SECONDARY_TEXT_COLOR)
            return
        glow = pulse(position.step_progress, COUNTER_PULSE_CYCLES) if position.step_index == RECALL_STEP else 0.0
        found = self._found_so_far(details, position)
        paint_counter(painter, found_rect, FOUND_LABEL, str(found), PRIMARY_HOVER_COLOR, glow)
        expected_color = TEXT_COLOR if position.step_index == RECALL_STEP else LABEL_TEXT_COLOR
        paint_counter(painter, expected_rect, EXPECTED_LABEL, str(len(details.expected_tokens)), expected_color, glow)

    def _found_so_far(self, details: TokenOverlapDetails, position: TimelinePosition) -> int:
        expected_count = len(details.expected_tokens)
        return sum(1 for index in details.matched_expected_indexes if reveal_progress(position, index, expected_count) >= 1.0)
