import math
from dataclasses import dataclass

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QFont, QFontMetricsF, QPainter, QPen

from domain.explanations.metric_walkthrough import MetricWalkthrough
from domain.explanations.timeline import TimelinePosition
from domain.explanations.walkthrough_details import ExactMatchDetails
from domain.scoring.text_normalization import DEFAULT_NORMALIZATION
from presentation.views.branding import (
    DISABLED_TEXT_COLOR,
    PRIMARY_COLOR,
    SECONDARY_TEXT_COLOR,
    STRONG_BORDER_COLOR,
    SUCCESS_COLOR,
    SURFACE_COLOR,
    TEXT_COLOR,
    WARNING_COLOR,
)
from presentation.views.metric_explorer.painting import (
    clamp_unit,
    draw_caption,
    draw_card,
    draw_text,
    ease_out_cubic,
    monospace_font,
    segment_progress,
    text_font,
    with_alpha,
)
from presentation.views.metric_explorer.scenes.base_scene import SceneStep, WalkthroughScene
from presentation.views.metric_explorer.scenes.token_scene_painting import (
    CAPTION_HEIGHT,
    DIMMED_OPACITY,
    SUCCESS_TINT_ALPHA,
    VERDICT_SCORE_FORMAT,
    WARNING_TINT_ALPHA,
    LayoutCache,
    VerdictLayout,
    elided,
    normalization_formula,
    normalization_options_text,
    options_from_normalization,
    highlighted_text,
    paint_verdict,
    pulse,
    staggered,
    verdict_layout,
)

NORMALIZE_STEP = 0
COMPARE_STEP = 1
SCORE_STEP = 2
STEPS = (
    SceneStep(
        "Normalize both answers",
        "Apply the active cleaning steps to both answers. {options}",
        4.0,
        (0,),
    ),
    SceneStep(
        "Compare the texts",
        "The two normalized texts are compared character by character: {summary}.",
        3.5,
        (1,),
    ),
    SceneStep(
        "Score 1 or 0",
        "Identical texts score 1. Any difference, even one word, scores 0. This pair scores {score}.",
        3.0,
        (1,),
    ),
)
FORMULA_TAIL = (
    "EM = 1 if n(answer) =<br>&nbsp;&nbsp;n(expected), else 0",
)
LIMITATION = "Very strict: a correct answer phrased differently scores 0."
ORIGINAL_STAGE_NAME = "Original"
STAGE_HEADER = "Stage"
EXPECTED_HEADER = "Expected"
ANSWER_HEADER = "Model answer"
COMPARE_CAPTION = "Character by character"
EMPTY_TEXT = "empty"
SPACE_SYMBOL = "·"
ELLIPSIS = "…"
SAME_SUMMARY = "all {count} characters match"
DIFFERENT_SUMMARY = "they first differ at character {position}"
EMPTY_SUMMARY = "both are empty"
MATCH_MESSAGE = "Both normalized texts are identical, so the answers match."
EMPTY_MATCH_MESSAGE = "Both texts are empty after normalization, so they match."
DIFFERENCE_MESSAGE = "First difference at character {position}, so the texts are not identical."
EQUAL_SIGN = "="
DIFFERENT_SIGN = "≠"
COMPARISON_RESULT = "n(answer) {sign} n(expected)"
SCORE_RESULT = "EM = {score}"
STAGE_COLUMN_WIDTH = 130.0
NARROW_STAGE_COLUMN_WIDTH = 96.0
NARROW_AREA_WIDTH = 440.0
COLUMN_GAP = 8.0
HEADER_GAP = 8.0
ROW_GAP = 6.0
ROW_PADDING_X = 8.0
ROW_PADDING_Y = 6.0
ROW_RADIUS = 6.0
STAGE_NAME_SIZE = 12
STAGE_TEXT_SIZES = (12, 11, 10)
CELL_WIDTH = 18.0
CELL_HEIGHT = 24.0
CELL_GAP = 2.0
CELL_ROW_GAP = 4.0
CELL_RADIUS = 4.0
CELL_TEXT_SIZE = 13
CELL_LOOKAHEAD = 3
CURSOR_HEIGHT = 3.0
CURSOR_GAP = 3.0
COMPARE_GAP = 8.0
COMPARE_SECTION_GAP = 28.0
VERDICT_GAP = 16.0
MINIMUM_FLEX_GAP = 12.0
ROW_APPEAR_SHARE = 0.32
ROW_RISE = 6.0
MORPH_START = 0.25
FINAL_ROW_HIGHLIGHT_END = 0.15
SCAN_END = 0.7
BLINK_CYCLES = 2.0
BLINK_ALPHA_BOOST = 1.6
COMPARED_ALPHA = 1.2
VERDICT_APPEAR_END = 0.5
TEXT_FLAGS = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop) | int(Qt.TextFlag.TextWordWrap)


StageTexts = tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]


@dataclass(frozen=True)
class StageRow:
    name_rect: QRectF
    expected_rect: QRectF
    answer_rect: QRectF


@dataclass(frozen=True)
class CharacterComparison:
    first_difference: int | None
    last_compared: int
    length: int
    slot_count: int


@dataclass(frozen=True)
class CharacterView:
    indexes: tuple[int, ...]
    leading_ellipsis: bool


@dataclass(frozen=True)
class ExactMatchLayout:
    header_rects: tuple[QRectF, QRectF, QRectF]
    rows: tuple[StageRow, ...]
    text_size: int
    elide_text: bool
    compare_caption: QRectF
    expected_cells_top: float
    answer_cells_top: float
    cells_left: float
    comparison: CharacterComparison
    verdict: VerdictLayout


def exact_details(walkthrough: MetricWalkthrough) -> ExactMatchDetails:
    if not isinstance(walkthrough.details, ExactMatchDetails):
        raise TypeError(f"Exact match needs exact match details, got {type(walkthrough.details).__name__}.")
    return walkthrough.details


def stage_texts(walkthrough: MetricWalkthrough) -> StageTexts:
    normalization = exact_details(walkthrough).normalization
    names = (ORIGINAL_STAGE_NAME, *normalization.stage_names)
    expected = (walkthrough.expected_answer, *normalization.expected_stages)
    answer = (walkthrough.given_answer, *normalization.answer_stages)
    return names, expected, answer


def first_difference(first: str, second: str) -> int | None:
    for index, (left, right) in enumerate(zip(first, second)):
        if left != right:
            return index
    if len(first) != len(second):
        return min(len(first), len(second))
    return None


def _text_height(text: str, width: float, size: int) -> float:
    metrics = QFontMetricsF(monospace_font(size, QFont.Weight.Normal))
    if not text:
        return metrics.height()
    return metrics.boundingRect(QRectF(0, 0, max(1.0, width), 10_000), TEXT_FLAGS, text).height()


def _name_height(name: str, width: float) -> float:
    metrics = QFontMetricsF(text_font(STAGE_NAME_SIZE))
    return metrics.boundingRect(QRectF(0, 0, max(1.0, width), 10_000), TEXT_FLAGS, name).height()


def _row_heights(texts: StageTexts, widths: tuple[float, float], size: int, elide_text: bool) -> list[float]:
    names, expected, answer = texts
    name_width, text_width = widths
    single_line = QFontMetricsF(monospace_font(size, QFont.Weight.Normal)).height()
    heights = []
    for name, expected_text, answer_text in zip(names, expected, answer):
        content = single_line if elide_text else max(_text_height(expected_text, text_width, size), _text_height(answer_text, text_width, size))
        heights.append(math.ceil(max(content + 2 * ROW_PADDING_Y, _name_height(name, name_width))))
    return heights


def _choose_text_size(names: tuple[str, ...], expected: tuple[str, ...], answer: tuple[str, ...], widths: tuple[float, float], budget: float) -> tuple[int, bool, list[float]]:
    texts = (names, expected, answer)
    for size in STAGE_TEXT_SIZES:
        heights = _row_heights(texts, widths, size, False)
        if sum(heights) + ROW_GAP * (len(heights) - 1) <= budget:
            return size, False, heights
    smallest = STAGE_TEXT_SIZES[-1]
    return smallest, True, _row_heights(texts, widths, smallest, True)


def character_comparison(expected: str, answer: str, slot_count: int) -> CharacterComparison:
    difference = first_difference(expected, answer)
    length = max(len(expected), len(answer))
    target = difference if difference is not None else max(0, length - 1)
    return CharacterComparison(difference, target, max(length, target + 1), slot_count)


def character_view(comparison: CharacterComparison, cursor: float) -> CharacterView:
    visible_slots = comparison.slot_count - 2
    latest_start = max(0, comparison.length - visible_slots)
    start = min(latest_start, max(0, int(cursor) - (visible_slots - CELL_LOOKAHEAD)))
    end = min(comparison.length, start + visible_slots)
    return CharacterView(tuple(range(start, end)), start > 0)


def build_exact_match_layout(walkthrough: MetricWalkthrough, area: QRectF) -> ExactMatchLayout:
    details = exact_details(walkthrough)
    names, expected, answer = stage_texts(walkthrough)
    stage_width = NARROW_STAGE_COLUMN_WIDTH if area.width() < NARROW_AREA_WIDTH else STAGE_COLUMN_WIDTH
    column_width = (area.width() - stage_width - 2 * COLUMN_GAP) / 2
    score_text = VERDICT_SCORE_FORMAT.format(walkthrough.final_score)
    message = verdict_message(walkthrough)
    verdict_height = verdict_layout(area, 0.0, score_text, message).score.height()
    bottom_height = CAPTION_HEIGHT + COMPARE_GAP + 2 * CELL_HEIGHT + CELL_ROW_GAP + CURSOR_GAP + CURSOR_HEIGHT + VERDICT_GAP + verdict_height
    budget = area.height() - CAPTION_HEIGHT - HEADER_GAP - bottom_height - MINIMUM_FLEX_GAP
    text_size, elide_text, heights = _choose_text_size(names, expected, answer, (stage_width, column_width - 2 * ROW_PADDING_X), budget)
    expected_left = area.left() + stage_width + COLUMN_GAP
    answer_left = expected_left + column_width + COLUMN_GAP
    headers = tuple(QRectF(left, area.top(), width, CAPTION_HEIGHT) for left, width in ((area.left(), stage_width), (expected_left, column_width), (answer_left, column_width)))
    rows = []
    top = area.top() + CAPTION_HEIGHT + HEADER_GAP
    for height in heights:
        rows.append(StageRow(QRectF(area.left(), top, stage_width, height), QRectF(expected_left, top, column_width, height), QRectF(answer_left, top, column_width, height)))
        top += height + ROW_GAP
    compare_top = min(top - ROW_GAP + COMPARE_SECTION_GAP, area.bottom() - bottom_height)
    compare_caption = QRectF(area.left(), compare_top, area.width(), CAPTION_HEIGHT)
    expected_cells_top = compare_caption.bottom() + COMPARE_GAP
    answer_cells_top = expected_cells_top + CELL_HEIGHT + CELL_ROW_GAP
    verdict_top = answer_cells_top + CELL_HEIGHT + CURSOR_GAP + CURSOR_HEIGHT + VERDICT_GAP
    slot_count = max(3, int((area.width() + CELL_GAP) // (CELL_WIDTH + CELL_GAP)))
    return ExactMatchLayout(
        header_rects=headers,
        rows=tuple(rows),
        text_size=text_size,
        elide_text=elide_text,
        compare_caption=compare_caption,
        expected_cells_top=expected_cells_top,
        answer_cells_top=answer_cells_top,
        cells_left=area.left(),
        comparison=character_comparison(details.normalization.normalized_expected, details.normalization.normalized_answer, slot_count),
        verdict=verdict_layout(area, verdict_top, score_text, message),
    )


def comparison_summary(walkthrough: MetricWalkthrough) -> str:
    normalization = exact_details(walkthrough).normalization
    difference = first_difference(normalization.normalized_expected, normalization.normalized_answer)
    if difference is not None:
        return DIFFERENT_SUMMARY.format(position=difference + 1)
    if not normalization.normalized_expected:
        return EMPTY_SUMMARY
    return SAME_SUMMARY.format(count=len(normalization.normalized_expected))


def verdict_message(walkthrough: MetricWalkthrough) -> str:
    details = exact_details(walkthrough)
    difference = first_difference(details.normalization.normalized_expected, details.normalization.normalized_answer)
    if difference is not None:
        return DIFFERENCE_MESSAGE.format(position=difference + 1)
    if not details.normalization.normalized_expected:
        return EMPTY_MATCH_MESSAGE
    return MATCH_MESSAGE


def score_text(score: float) -> str:
    return f"{score:g}"


class ExactMatchScene(WalkthroughScene):
    identifier = "exact_match"

    def __init__(self):
        self._layouts = LayoutCache(build_exact_match_layout)

    @property
    def steps(self) -> tuple[SceneStep, ...]:
        return STEPS

    @property
    def formula(self) -> tuple[str, ...]:
        return (normalization_formula(DEFAULT_NORMALIZATION), *FORMULA_TAIL)

    def formula_for(self, walkthrough: MetricWalkthrough) -> tuple[str, ...]:
        options = options_from_normalization(exact_details(walkthrough).normalization)
        return (normalization_formula(options), *FORMULA_TAIL)

    @property
    def limitation(self) -> str:
        return LIMITATION

    def step_body(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        return STEPS[step_index].body.format(options=normalization_options_text(options_from_normalization(exact_details(walkthrough).normalization)), summary=comparison_summary(walkthrough), score=score_text(walkthrough.final_score))

    def formula_result(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        if step_index == COMPARE_STEP:
            sign = EQUAL_SIGN if exact_details(walkthrough).is_match else DIFFERENT_SIGN
            return COMPARISON_RESULT.format(sign=highlighted_text(sign))
        if step_index == SCORE_STEP:
            return SCORE_RESULT.format(score=highlighted_text(score_text(walkthrough.final_score)))
        return ""

    def paint(self, painter: QPainter, area: QRectF, walkthrough: MetricWalkthrough, position: TimelinePosition) -> None:
        details = exact_details(walkthrough)
        layout: ExactMatchLayout = self._layouts.get(walkthrough, area)
        painter.save()
        painter.setClipRect(area)
        for rect, header in zip(layout.header_rects, (STAGE_HEADER, EXPECTED_HEADER, ANSWER_HEADER)):
            draw_caption(painter, rect, header)
        self._paint_stage_rows(painter, layout, walkthrough, position)
        self._paint_comparison(painter, layout, details, position)
        self._paint_verdict(painter, layout, walkthrough, details, position)
        painter.restore()

    def _paint_stage_rows(self, painter: QPainter, layout: ExactMatchLayout, walkthrough: MetricWalkthrough, position: TimelinePosition) -> None:
        names, expected, answer = stage_texts(walkthrough)
        last_row = len(layout.rows) - 1
        for index, row in enumerate(layout.rows):
            appear = self._row_appear(position, index, len(layout.rows))
            if appear <= 0:
                continue
            painter.save()
            painter.setOpacity(painter.opacity() * appear)
            painter.translate(0, (1.0 - ease_out_cubic(appear)) * ROW_RISE)
            morph = segment_progress(appear, MORPH_START, 1.0) if index > 0 else 1.0
            highlight = self._final_row_highlight(position) if index == last_row else 0.0
            draw_text(painter, row.name_rect, names[index], SECONDARY_TEXT_COLOR, text_font(STAGE_NAME_SIZE), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, wrap=True)
            previous_expected = expected[index - 1] if index > 0 else expected[index]
            previous_answer = answer[index - 1] if index > 0 else answer[index]
            self._paint_stage_box(painter, layout, row.expected_rect, previous_expected, expected[index], morph, highlight)
            self._paint_stage_box(painter, layout, row.answer_rect, previous_answer, answer[index], morph, highlight)
            painter.restore()

    def _row_appear(self, position: TimelinePosition, index: int, count: int) -> float:
        if position.step_index > NORMALIZE_STEP:
            return 1.0
        return staggered(position.step_progress, index, count, ROW_APPEAR_SHARE)

    def _final_row_highlight(self, position: TimelinePosition) -> float:
        if position.step_index == NORMALIZE_STEP:
            return 0.0
        if position.step_index > COMPARE_STEP:
            return 1.0
        return segment_progress(position.step_progress, 0.0, FINAL_ROW_HIGHLIGHT_END)

    def _paint_stage_box(self, painter: QPainter, layout: ExactMatchLayout, rect: QRectF, previous: str, current: str, morph: float, highlight: float) -> None:
        border = with_alpha(PRIMARY_COLOR, highlight) if highlight > 0 else None
        draw_card(painter, rect, SURFACE_COLOR, border, ROW_RADIUS)
        text_rect = rect.adjusted(ROW_PADDING_X, ROW_PADDING_Y, -ROW_PADDING_X, -ROW_PADDING_Y)
        if morph < 1.0 and previous != current:
            self._paint_stage_text(painter, layout, text_rect, previous, 1.0 - morph)
            self._paint_stage_text(painter, layout, text_rect, current, morph)
            return
        self._paint_stage_text(painter, layout, text_rect, current, 1.0)

    def _paint_stage_text(self, painter: QPainter, layout: ExactMatchLayout, rect: QRectF, text: str, opacity: float) -> None:
        if opacity <= 0:
            return
        font = monospace_font(layout.text_size, QFont.Weight.Normal)
        painter.save()
        painter.setOpacity(painter.opacity() * opacity)
        if not text:
            draw_text(painter, rect, EMPTY_TEXT, DISABLED_TEXT_COLOR, text_font(layout.text_size), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        elif layout.elide_text:
            draw_text(painter, rect, elided(text, font, rect.width()), TEXT_COLOR, font, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        else:
            draw_text(painter, rect, text, TEXT_COLOR, font, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, wrap=True)
        painter.restore()

    def _paint_comparison(self, painter: QPainter, layout: ExactMatchLayout, details: ExactMatchDetails, position: TimelinePosition) -> None:
        if position.step_index < COMPARE_STEP:
            painter.save()
            painter.setOpacity(painter.opacity() * DIMMED_OPACITY)
            draw_caption(painter, layout.compare_caption, COMPARE_CAPTION)
            painter.restore()
            return
        draw_caption(painter, layout.compare_caption, COMPARE_CAPTION)
        cursor = self._scan_cursor(layout.comparison, position)
        view = character_view(layout.comparison, cursor)
        blink = self._blink(position)
        normalization = details.normalization
        self._paint_cell_row(painter, layout, view, layout.expected_cells_top, normalization.normalized_expected, cursor, blink)
        self._paint_cell_row(painter, layout, view, layout.answer_cells_top, normalization.normalized_answer, cursor, blink)
        self._paint_cursor(painter, layout, view, cursor, position)

    def _scan_cursor(self, comparison: CharacterComparison, position: TimelinePosition) -> float:
        total = comparison.last_compared + 1
        if position.step_index > COMPARE_STEP:
            return float(total)
        return segment_progress(position.step_progress, 0.0, SCAN_END) * total

    def _blink(self, position: TimelinePosition) -> float:
        if position.step_index != COMPARE_STEP:
            return 0.0
        return pulse(segment_progress(position.step_progress, SCAN_END, 1.0), BLINK_CYCLES)

    def _slot_rect(self, layout: ExactMatchLayout, top: float, slot: int) -> QRectF:
        return QRectF(layout.cells_left + slot * (CELL_WIDTH + CELL_GAP), top, CELL_WIDTH, CELL_HEIGHT)

    def _paint_cell_row(self, painter: QPainter, layout: ExactMatchLayout, view: CharacterView, top: float, text: str, cursor: float, blink: float) -> None:
        if view.leading_ellipsis and text:
            self._paint_ellipsis(painter, self._slot_rect(layout, top, 0))
        first_slot = int(view.leading_ellipsis)
        difference = layout.comparison.first_difference
        for slot, index in enumerate(view.indexes, start=first_slot):
            self._paint_cell(painter, self._slot_rect(layout, top, slot), text, index, clamp_unit(cursor - index), index == difference, blink)
        if view.indexes and len(text) > view.indexes[-1] + 1:
            self._paint_ellipsis(painter, self._slot_rect(layout, top, first_slot + len(view.indexes)))

    def _paint_ellipsis(self, painter: QPainter, rect: QRectF) -> None:
        draw_text(painter, rect, ELLIPSIS, DISABLED_TEXT_COLOR, monospace_font(CELL_TEXT_SIZE), Qt.AlignmentFlag.AlignCenter)

    def _paint_cell(self, painter: QPainter, rect: QRectF, text: str, index: int, compared: float, is_difference: bool, blink: float) -> None:
        if index >= len(text):
            if is_difference and compared > 0:
                self._paint_missing_cell(painter, rect, compared)
            return
        draw_card(painter, rect, SURFACE_COLOR, None, CELL_RADIUS)
        if compared > 0:
            color, alpha = (WARNING_COLOR, WARNING_TINT_ALPHA * (1 + BLINK_ALPHA_BOOST * blink)) if is_difference else (SUCCESS_COLOR, SUCCESS_TINT_ALPHA * COMPARED_ALPHA)
            border = with_alpha(WARNING_COLOR, compared) if is_difference else None
            draw_card(painter, rect, with_alpha(color, alpha * compared), border, CELL_RADIUS)
        character = text[index]
        is_space = character == " "
        color = STRONG_BORDER_COLOR if is_space else TEXT_COLOR
        draw_text(painter, rect, SPACE_SYMBOL if is_space else character, color, monospace_font(CELL_TEXT_SIZE), Qt.AlignmentFlag.AlignCenter)

    def _paint_missing_cell(self, painter: QPainter, rect: QRectF, compared: float) -> None:
        pen = QPen(with_alpha(WARNING_COLOR, compared), 1.0)
        pen.setDashPattern([3.0, 2.0])
        painter.save()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(pen)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), CELL_RADIUS, CELL_RADIUS)
        painter.restore()

    def _paint_cursor(self, painter: QPainter, layout: ExactMatchLayout, view: CharacterView, cursor: float, position: TimelinePosition) -> None:
        if position.step_index != COMPARE_STEP:
            return
        current = min(layout.comparison.last_compared, int(cursor))
        if current not in view.indexes:
            return
        slot = view.indexes.index(current) + int(view.leading_ellipsis)
        cell = self._slot_rect(layout, layout.answer_cells_top, slot)
        draw_card(painter, QRectF(cell.left(), cell.bottom() + CURSOR_GAP, cell.width(), CURSOR_HEIGHT), PRIMARY_COLOR, None, CURSOR_HEIGHT / 2)

    def _paint_verdict(self, painter: QPainter, layout: ExactMatchLayout, walkthrough: MetricWalkthrough, details: ExactMatchDetails, position: TimelinePosition) -> None:
        if position.step_index < SCORE_STEP:
            return
        appear = segment_progress(position.step_progress, 0.0, VERDICT_APPEAR_END)
        score = VERDICT_SCORE_FORMAT.format(walkthrough.final_score)
        paint_verdict(painter, layout.verdict, details.is_match, verdict_message(walkthrough), score, appear)
