import math
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QFont, QPainter, QPen

from domain.explanations.metric_walkthrough import MetricWalkthrough
from domain.explanations.timeline import TimelinePosition
from domain.explanations.walkthrough_details import NgramOverlapDetails
from domain.scoring.text_normalization import word_tokens
from presentation.views.branding import (
    BORDER_COLOR,
    DISABLED_TEXT_COLOR,
    LABEL_TEXT_COLOR,
    PRIMARY_COLOR,
    PRIMARY_HOVER_COLOR,
    STRONG_BORDER_COLOR,
    SURFACE_COLOR,
    TEXT_COLOR,
)
from presentation.views.metric_explorer.painting import (
    caption_font,
    clamp_unit,
    draw_card,
    draw_text,
    ease_in_out,
    ease_out_cubic,
    lerp,
    mix_colors,
    segment_progress,
    to_color,
    with_alpha,
)
from presentation.views.metric_explorer.scenes.base_scene import SceneStep, WalkthroughScene
from presentation.views.metric_explorer.scenes.rouge_scene_painting import (
    CAPTION_HEIGHT,
    CARD_HEIGHT,
    RATIO_BLOCK_HEIGHT,
    F_ONE_LINE,
    FINAL_TITLE,
    ChipLook,
    ScoreSelection,
    case_note,
    final_card_detail,
    final_card_label,
    final_step_body,
    final_step_result,
    formula_with_selection,
    score_selection,
    selected_formula_line,
    ScoreCard,
    chip_width,
    draw_empty_box,
    draw_note,
    draw_ratio_bar,
    draw_score_cards,
    draw_section_caption,
    draw_word_chip,
    elide,
    fit_scale,
    flow_layout,
    format_ratio,
    format_score,
    inset_area,
    stagger,
    step_phase,
    value_font,
    word_font,
)

UNIGRAM_ORDER = 1
EXTRACT_STEP = 0
COUNT_STEP = 1
RATIO_STEP = 2
F_MEASURE_STEP = 3
BASE_FORMULA = (
    "overlap = Σ min(c<sub>ans</sub>(g), c<sub>exp</sub>(g))",
    "P = overlap / Σ c<sub>ans</sub>",
    "R = overlap / Σ c<sub>exp</sub>",
)
UNIGRAM_LIMITATION = "Ignores word order: the same words in any order score the same."
HIGHER_ORDER_LIMITATION = "Pairs reward local word order: one wrong word breaks the bigrams around it."
UNIT_NAMES = {1: "words", 2: "bigrams"}
GRAM_NAMES = {1: "unigram", 2: "bigram"}
GENERIC_UNIT_FORMAT = "{order}-grams"
GENERIC_GRAM_FORMAT = "{order}-gram"
WINDOW_TITLE_FORMAT = "Slide a {order}-word window"
WINDOW_BODY = "Each run of {order} neighbouring words is a {gram}: {expected} expected, {answer} in the answer. {case_note}"
SPLIT_TITLE = "Split into words"
SPLIT_BODY = "Split both answers into words: {expected} expected, {answer} in the answer. {case_note}"
CLIP_TITLE = "Clip the counts"
CLIP_BODY = "A word scores at most as often as it appears in both answers, so repeats do not help: {overlap} shared."
MATCH_TITLE = "Match {unit}"
MATCH_BODY = "A {gram} counts at most as often as it appears in both answers: {overlap} shared."
RATIO_TITLE = "Precision and recall"
RATIO_BODY = "Divide the {overlap} shared {unit} by the {answer} answer and the {expected} expected {unit}."
F_MEASURE_BODY = ""
EXTRACT_DURATION = 4.5
COUNT_DURATION = 4.5
RATIO_DURATION = 3.5
F_MEASURE_DURATION = 3.0
EXTRACT_RESULT_FORMAT = "{expected} expected · {answer} answer {unit}"
OVERLAP_RESULT_FORMAT = "overlap = {overlap}"
RATIO_RESULT_FORMAT = "P = {precision_ratio} = {precision}<br>R = {recall_ratio} = {recall}"
PRECISION_LABEL = "Precision"
RECALL_LABEL = "Recall"
LABELLED_RATIO_FORMAT = "{label} · {ratio}"
DETAIL_FORMAT = "= {value}"
PRECISION_REVEAL = (0.0, 0.6)
RECALL_REVEAL = (0.3, 0.9)

TABLE_SIDE_LAYOUT_MINIMUM_WIDTH = 470.0
BAR_COLUMN_WIDTH = 170.0
COLUMN_GAP = 20.0
BAR_GAP = 14.0
TABLE_HEADER_HEIGHT = 22.0
TABLE_SUM_HEIGHT = 34.0
TABLE_SECTION_GAP = 6.0
ROW_GAP = 4.0
MINIMUM_ROW_PITCH = 18.0
MAXIMUM_ROW_PITCH = 34.0
COMPACT_ROW_PITCH = 26.0
COUNT_COLUMN_WIDTH = 70.0
COUNT_COLUMN_SHARE = 0.21
CELL_PADDING = 8.0
CELL_GAP = 6.0
ROW_RADIUS = 6.0
ROW_SLIDE_DISTANCE = 8.0
ROW_PENDING_ALPHA = 0.55
ROW_SLOT_ALPHA = 0.3
ROW_TEXT_SIZE = 13
COMPACT_ROW_TEXT_SIZE = 11
ROW_STAGGER_SPAN = 0.22
CLIP_ROWS_END = 0.72
SUM_START = 0.74
ACTIVE_BORDER_ALPHA = 0.9
PENDING_HEADER_OPACITY = 0.45
SUM_SYMBOL = "Σ"
MORE_ROWS_FORMAT = "+ {count} more {unit}"
TABLE_HEADERS = ("expected", "answer", "min")

TOKEN_ROW_HEIGHT = 30.0
TOKEN_GAP = 4.0
TOKEN_TEXT_SIZE = 12
GRAM_CHIP_HEIGHT = 28.0
GRAM_GAP = 6.0
GRAM_TEXT_SIZE = 12
CAPTION_GAP = 6.0
SECTION_GAP = 14.0
WINDOW_FRAME_MARGIN = 3.0
WINDOW_FRAME_WIDTH = 2.0
WINDOW_FRAME_RADIUS = 8.0
WINDOW_MOVE_SHARE = 0.35
DROP_START = 0.35
DROP_LENGTH = 0.5
DROP_DISTANCE = 10.0
FRAME_FADE_SHARE = 0.04
MATCH_PAIRS_END = 0.8
EXPECTED_SWEEP = (0.0, 0.5)
ANSWER_SWEEP = (0.5, 1.0)
EXPECTED_ROW_CAPTION = "Expected answer"
ANSWER_ROW_CAPTION = "Model answer"
EXPECTED_GRAMS_CAPTION = "{unit} · expected ({count})"
ANSWER_GRAMS_CAPTION = "{unit} · model answer ({count})"
SHARED_COUNTER_FORMAT = "{count} shared"
EMPTY_TOKENS_TEXT = "No words"
TOO_SHORT_FORMAT = "No {unit}: it takes at least {order} words."


@dataclass(frozen=True)
class CountRow:
    gram: str
    expected: int
    answer: int
    shared: int


@dataclass(frozen=True)
class TableLayout:
    table: QRectF
    bars: QRectF
    bar_width: float
    row_pitch: float
    visible_rows: int
    count_width: float


@dataclass(frozen=True)
class GramSection:
    caption: QRectF
    chips: tuple[QRectF, ...]
    body: QRectF


@dataclass(frozen=True)
class WindowLayout:
    expected_caption: QRectF
    expected_tokens: tuple[QRectF, ...]
    answer_caption: QRectF
    answer_tokens: tuple[QRectF, ...]
    expected_grams: GramSection
    answer_grams: GramSection
    content_height: float


@dataclass(frozen=True)
class NgramSceneInput:
    details: NgramOverlapDetails
    expected_tokens: tuple[str, ...]
    answer_tokens: tuple[str, ...]


def _unit_name(order: int) -> str:
    return UNIT_NAMES.get(order, GENERIC_UNIT_FORMAT.format(order=order))


def _gram_name(order: int) -> str:
    return GRAM_NAMES.get(order, GENERIC_GRAM_FORMAT.format(order=order))


def _build_steps(order: int) -> tuple[SceneStep, ...]:
    if order == UNIGRAM_ORDER:
        extract_step = SceneStep(SPLIT_TITLE, SPLIT_BODY, EXTRACT_DURATION, ())
        count_step = SceneStep(CLIP_TITLE, CLIP_BODY, COUNT_DURATION, (0,))
    else:
        extract_step = SceneStep(WINDOW_TITLE_FORMAT.format(order=order), WINDOW_BODY, EXTRACT_DURATION, ())
        count_step = SceneStep(MATCH_TITLE.format(unit=_unit_name(order)), MATCH_BODY, COUNT_DURATION, (0,))
    return (
        extract_step,
        count_step,
        SceneStep(RATIO_TITLE, RATIO_BODY, RATIO_DURATION, (1, 2)),
        SceneStep(FINAL_TITLE, F_MEASURE_BODY, F_MEASURE_DURATION, (3,)),
    )


@lru_cache(maxsize=64)
def _scene_input(details: NgramOverlapDetails, expected_answer: str, given_answer: str, lowercase: bool) -> NgramSceneInput:
    return NgramSceneInput(details, tuple(word_tokens(expected_answer, lowercase)), tuple(word_tokens(given_answer, lowercase)))


@lru_cache(maxsize=32)
def count_rows(details: NgramOverlapDetails) -> tuple[CountRow, ...]:
    expected_counts = Counter(details.expected_ngrams)
    answer_counts = Counter(details.answer_ngrams)
    grams = dict.fromkeys(details.expected_ngrams + details.answer_ngrams)
    return tuple(
        CountRow(" ".join(gram), expected_counts[gram], answer_counts[gram], min(expected_counts[gram], answer_counts[gram]))
        for gram in grams
    )


def _final_selection(details: NgramOverlapDetails) -> ScoreSelection:
    return ScoreSelection(details.score_type, details.beta, True, details.score)


def _score_values(details: NgramOverlapDetails) -> dict[str, str]:
    return {
        "precision_ratio": format_ratio(details.overlap_count, len(details.answer_ngrams)),
        "recall_ratio": format_ratio(details.overlap_count, len(details.expected_ngrams)),
        "precision": format_score(details.precision),
        "recall": format_score(details.recall),
        "score": format_score(details.score),
    }


class CountTablePainter:
    def paint(self, painter: QPainter, size: QRectF, scene_input: NgramSceneInput, position: TimelinePosition) -> None:
        details = scene_input.details
        rows = count_rows(details)
        layout = _table_layout(len(rows), size.width(), size.height())
        extract, clip = step_phase(position, EXTRACT_STEP), step_phase(position, COUNT_STEP)
        self._paint_header(painter, layout, details.order, clip)
        row_clip = segment_progress(clip, 0.0, CLIP_ROWS_END)
        for index in range(layout.visible_rows):
            appear = stagger(extract, index, layout.visible_rows, ROW_STAGGER_SPAN)
            clipped = stagger(row_clip, index, layout.visible_rows, ROW_STAGGER_SPAN)
            self._paint_row(painter, layout, index, rows[index], appear, clipped)
        self._paint_more_rows(painter, layout, len(rows), details.order, extract)
        self._paint_sum(painter, layout, details, segment_progress(clip, SUM_START, 1.0))
        self._paint_bars(painter, layout, details, position)

    def _columns(self, layout: TableLayout, top: float, height: float) -> tuple[QRectF, ...]:
        inner_left = layout.table.left() + CELL_PADDING
        inner_right = layout.table.right() - CELL_PADDING
        count_left = inner_right - 3 * layout.count_width - 2 * CELL_GAP
        word_rect = QRectF(inner_left, top, max(0.0, count_left - CELL_GAP - inner_left), height)
        counts = tuple(QRectF(count_left + index * (layout.count_width + CELL_GAP), top, layout.count_width, height) for index in range(3))
        return (word_rect,) + counts

    def _paint_header(self, painter: QPainter, layout: TableLayout, order: int, clip: float) -> None:
        columns = self._columns(layout, layout.table.top(), TABLE_HEADER_HEIGHT)
        font = caption_font()
        draw_text(painter, columns[0], elide(_gram_name(order).upper(), font, columns[0].width()), LABEL_TEXT_COLOR, font)
        for index, header in enumerate(TABLE_HEADERS):
            opacity = 1.0 if index < 2 else lerp(PENDING_HEADER_OPACITY, 1.0, clip)
            painter.save()
            painter.setOpacity(painter.opacity() * opacity)
            draw_text(painter, columns[index + 1], elide(header.upper(), font, columns[index + 1].width()), LABEL_TEXT_COLOR, font, Qt.AlignmentFlag.AlignCenter)
            painter.restore()

    def _row_top(self, layout: TableLayout, index: int) -> float:
        return layout.table.top() + TABLE_HEADER_HEIGHT + index * layout.row_pitch

    def _paint_row(self, painter: QPainter, layout: TableLayout, index: int, row: CountRow, appear: float, clipped: float) -> None:
        eased = ease_out_cubic(appear)
        height = layout.row_pitch - ROW_GAP
        slot = QRectF(layout.table.left(), self._row_top(layout, index), layout.table.width(), height).adjusted(0.5, 0.5, -0.5, -0.5)
        draw_card(painter, slot, with_alpha(SURFACE_COLOR, ROW_SLOT_ALPHA * (1.0 - eased)), None, ROW_RADIUS)
        if appear <= 0:
            return
        shift = -ROW_SLIDE_DISTANCE * (1.0 - eased)
        row_rect = QRectF(layout.table.left(), self._row_top(layout, index), layout.table.width(), height)
        is_shared = row.shared > 0
        painter.save()
        painter.setOpacity(painter.opacity() * eased)
        painter.translate(shift, 0.0)
        background_alpha = lerp(ROW_PENDING_ALPHA, 1.0 if is_shared else 0.0, clipped)
        border = with_alpha(PRIMARY_COLOR, ACTIVE_BORDER_ALPHA * math.sin(math.pi * clipped)) if 0 < clipped < 1 else None
        draw_card(painter, row_rect.adjusted(max(0.0, -shift) + 0.5, 0.5, -0.5, -0.5), with_alpha(SURFACE_COLOR, background_alpha), border, ROW_RADIUS)
        text_color = mix_colors(LABEL_TEXT_COLOR, TEXT_COLOR if is_shared else DISABLED_TEXT_COLOR, clipped)
        font = value_font(ROW_TEXT_SIZE if layout.row_pitch >= COMPACT_ROW_PITCH else COMPACT_ROW_TEXT_SIZE, QFont.Weight.Normal)
        columns = self._columns(layout, row_rect.top(), height)
        draw_text(painter, columns[0], elide(row.gram, font, columns[0].width()), text_color, font)
        for column, count in zip(columns[1:3], (row.expected, row.answer)):
            draw_text(painter, column, str(count), text_color, font, Qt.AlignmentFlag.AlignCenter)
        self._paint_min_cell(painter, columns[3], row, clipped, font)
        painter.restore()

    def _paint_min_cell(self, painter: QPainter, rect: QRectF, row: CountRow, clipped: float, font: QFont) -> None:
        if clipped <= 0:
            return
        bold = QFont(font)
        bold.setWeight(QFont.Weight.Bold)
        color = PRIMARY_HOVER_COLOR if row.shared > 0 else STRONG_BORDER_COLOR
        painter.save()
        painter.setOpacity(painter.opacity() * clipped)
        draw_text(painter, rect.translated(0.0, DROP_DISTANCE / 2 * (1.0 - ease_out_cubic(clipped))), str(row.shared), color, bold, Qt.AlignmentFlag.AlignCenter)
        painter.restore()

    def _paint_more_rows(self, painter: QPainter, layout: TableLayout, row_count: int, order: int, extract: float) -> None:
        hidden = row_count - layout.visible_rows
        if hidden <= 0:
            return
        top = self._row_top(layout, layout.visible_rows)
        rect = QRectF(layout.table.left() + CELL_PADDING, top, layout.table.width() - 2 * CELL_PADDING, layout.row_pitch - ROW_GAP)
        draw_note(painter, rect, MORE_ROWS_FORMAT.format(count=hidden, unit=_unit_name(order)), segment_progress(extract, 1.0 - ROW_STAGGER_SPAN, 1.0))

    def _paint_sum(self, painter: QPainter, layout: TableLayout, details: NgramOverlapDetails, reveal: float) -> None:
        if reveal <= 0:
            return
        rows_shown = layout.visible_rows + (1 if layout.visible_rows < len(count_rows(details)) else 0)
        top = self._row_top(layout, rows_shown) + TABLE_SECTION_GAP
        painter.save()
        painter.setOpacity(painter.opacity() * ease_out_cubic(reveal))
        painter.setPen(QPen(to_color(BORDER_COLOR), 1.0))
        painter.drawLine(QPointF(layout.table.left() + 0.5, top + 0.5), QPointF(layout.table.right() - 0.5, top + 0.5))
        columns = self._columns(layout, top, TABLE_SUM_HEIGHT)
        font = value_font(ROW_TEXT_SIZE)
        draw_text(painter, columns[0], SUM_SYMBOL, TEXT_COLOR, word_font(ROW_TEXT_SIZE, QFont.Weight.DemiBold))
        draw_text(painter, columns[1], str(len(details.expected_ngrams)), TEXT_COLOR, font, Qt.AlignmentFlag.AlignCenter)
        draw_text(painter, columns[2], str(len(details.answer_ngrams)), TEXT_COLOR, font, Qt.AlignmentFlag.AlignCenter)
        draw_text(painter, columns[3], str(details.overlap_count), PRIMARY_HOVER_COLOR, font, Qt.AlignmentFlag.AlignCenter)
        painter.restore()

    def _paint_bars(self, painter: QPainter, layout: TableLayout, details: NgramOverlapDetails, position: TimelinePosition) -> None:
        ratios = step_phase(position, RATIO_STEP)
        values = _score_values(details)
        bars = (
            (LABELLED_RATIO_FORMAT.format(label=PRECISION_LABEL, ratio=values["precision_ratio"]), values["precision"], details.precision, segment_progress(ratios, *PRECISION_REVEAL)),
            (LABELLED_RATIO_FORMAT.format(label=RECALL_LABEL, ratio=values["recall_ratio"]), values["recall"], details.recall, segment_progress(ratios, *RECALL_REVEAL)),
            (final_card_label(_final_selection(details)), values["score"], details.score, step_phase(position, F_MEASURE_STEP)),
        )
        for index, (label, value_text, fraction, reveal) in enumerate(bars):
            top = layout.bars.top() + index * (RATIO_BLOCK_HEIGHT + BAR_GAP)
            draw_ratio_bar(painter, QRectF(layout.bars.left(), top, layout.bar_width, RATIO_BLOCK_HEIGHT), label, value_text, fraction, reveal)


def _bars_height() -> float:
    return 3 * RATIO_BLOCK_HEIGHT + 2 * BAR_GAP


@lru_cache(maxsize=64)
def _table_layout(row_count: int, width: float, height: float) -> TableLayout:
    bars_height = _bars_height()
    if width >= TABLE_SIDE_LAYOUT_MINIMUM_WIDTH:
        table = QRectF(0.0, 0.0, width - BAR_COLUMN_WIDTH - COLUMN_GAP, height)
        bars = QRectF(width - BAR_COLUMN_WIDTH, max(0.0, height - bars_height), BAR_COLUMN_WIDTH, bars_height)
    else:
        table = QRectF(0.0, 0.0, width, max(0.0, height - bars_height - COLUMN_GAP))
        bars = QRectF(0.0, max(0.0, height - bars_height), width, bars_height)
    available = table.height() - TABLE_HEADER_HEIGHT - TABLE_SECTION_GAP - TABLE_SUM_HEIGHT
    pitch = min(MAXIMUM_ROW_PITCH, max(MINIMUM_ROW_PITCH, available / max(1, row_count)))
    visible = row_count if row_count * pitch <= available else max(0, math.floor(available / pitch) - 1)
    count_width = min(COUNT_COLUMN_WIDTH, table.width() * COUNT_COLUMN_SHARE)
    return TableLayout(table, bars, bars.width(), pitch, visible, count_width)


class SlidingWindowPainter:
    def paint(self, painter: QPainter, size: QRectF, scene_input: NgramSceneInput, position: TimelinePosition) -> None:
        width, height = size.width(), size.height()
        scale = fit_scale(lambda virtual_width, _: self._required_height(scene_input, virtual_width), width, height)
        virtual_width, virtual_height = width / scale, height / scale
        layout = _window_layout(scene_input, virtual_width)
        painter.save()
        painter.scale(scale, scale)
        extract = step_phase(position, EXTRACT_STEP)
        matching = step_phase(position, COUNT_STEP)
        order = scene_input.details.order
        self._paint_token_row(painter, layout.expected_caption, EXPECTED_ROW_CAPTION, layout.expected_tokens, scene_input.expected_tokens, order, segment_progress(extract, *EXPECTED_SWEEP))
        self._paint_token_row(painter, layout.answer_caption, ANSWER_ROW_CAPTION, layout.answer_tokens, scene_input.answer_tokens, order, segment_progress(extract, *ANSWER_SWEEP))
        self._paint_gram_sections(painter, layout, scene_input, extract, matching)
        cards_rect = QRectF(0.0, virtual_height - CARD_HEIGHT, virtual_width, CARD_HEIGHT)
        draw_score_cards(painter, cards_rect, _ngram_cards(scene_input.details, position))
        painter.restore()

    def _required_height(self, scene_input: NgramSceneInput, width: float) -> float:
        return _window_layout(scene_input, width).content_height + SECTION_GAP + CARD_HEIGHT

    def _paint_token_row(
        self,
        painter: QPainter,
        caption: QRectF,
        title: str,
        rects: tuple[QRectF, ...],
        tokens: tuple[str, ...],
        order: int,
        sweep: float,
    ) -> None:
        draw_section_caption(painter, caption, title)
        if not tokens:
            draw_empty_box(painter, QRectF(caption.left(), caption.bottom() + CAPTION_GAP, caption.width(), TOKEN_ROW_HEIGHT), EMPTY_TOKENS_TEXT)
            return
        window_count = len(tokens) - order + 1
        window = _window_position(sweep, window_count)
        font = word_font(TOKEN_TEXT_SIZE)
        for index, (rect, token) in enumerate(zip(rects, tokens)):
            highlight = 0.0 if window is None else clamp_unit(1.0 - max(0.0, window - index, index - window - order + 1))
            draw_word_chip(painter, rect, token, font, ChipLook(highlight=highlight))
        if window is None:
            return
        self._paint_window_frame(painter, rects, window, order, _frame_opacity(sweep))

    def _paint_window_frame(self, painter: QPainter, rects: tuple[QRectF, ...], window: float, order: int, opacity: float) -> None:
        first = math.floor(window)
        fraction = window - first
        start = _span_rect(rects, first, order)
        target = _span_rect(rects, min(first + 1, len(rects) - order), order)
        frame = QRectF(
            lerp(start.left(), target.left(), fraction),
            start.top(),
            lerp(start.width(), target.width(), fraction),
            start.height(),
        ).adjusted(-WINDOW_FRAME_MARGIN + 1, -WINDOW_FRAME_MARGIN + 1, WINDOW_FRAME_MARGIN - 1, WINDOW_FRAME_MARGIN - 1)
        painter.save()
        painter.setOpacity(painter.opacity() * opacity)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(to_color(PRIMARY_COLOR), WINDOW_FRAME_WIDTH))
        painter.drawRoundedRect(frame, WINDOW_FRAME_RADIUS, WINDOW_FRAME_RADIUS)
        painter.restore()

    def _paint_gram_sections(self, painter: QPainter, layout: WindowLayout, scene_input: NgramSceneInput, extract: float, matching: float) -> None:
        details = scene_input.details
        unit = _unit_name(details.order)
        pair_progress = segment_progress(matching, 0.0, MATCH_PAIRS_END)
        dim = segment_progress(matching, MATCH_PAIRS_END, 1.0)
        ordered_matches = sorted(details.matches)
        expected_lit = {expected: stagger(pair_progress, rank, len(ordered_matches)) for rank, (expected, _) in enumerate(ordered_matches)}
        answer_lit = {answer: stagger(pair_progress, rank, len(ordered_matches)) for rank, (_, answer) in enumerate(ordered_matches)}
        shared = sum(1 for value in expected_lit.values() if value >= 0.5)
        trailing = SHARED_COUNTER_FORMAT.format(count=shared) if matching > 0 else ""
        self._paint_gram_section(
            painter,
            layout.expected_grams,
            EXPECTED_GRAMS_CAPTION.format(unit=unit, count=len(details.expected_ngrams)),
            trailing,
            details.expected_ngrams,
            expected_lit,
            segment_progress(extract, *EXPECTED_SWEEP),
            dim,
            details.order,
        )
        self._paint_gram_section(
            painter,
            layout.answer_grams,
            ANSWER_GRAMS_CAPTION.format(unit=unit, count=len(details.answer_ngrams)),
            "",
            details.answer_ngrams,
            answer_lit,
            segment_progress(extract, *ANSWER_SWEEP),
            dim,
            details.order,
        )

    def _paint_gram_section(
        self,
        painter: QPainter,
        section: GramSection,
        caption: str,
        trailing: str,
        grams: tuple[tuple[str, ...], ...],
        lit: dict[int, float],
        sweep: float,
        dim: float,
        order: int,
    ) -> None:
        draw_section_caption(painter, section.caption, caption, trailing)
        if not grams:
            draw_note(painter, section.body, TOO_SHORT_FORMAT.format(unit=_unit_name(order), order=order), sweep)
            return
        font = word_font(GRAM_TEXT_SIZE)
        for index, (rect, gram) in enumerate(zip(section.chips, grams)):
            drop = segment_progress(sweep * len(grams), index + DROP_START, index + DROP_START + DROP_LENGTH)
            if drop <= 0:
                continue
            highlight = lit.get(index, 0.0)
            look = ChipLook(
                highlight=highlight,
                dimmed=0.0 if index in lit else dim,
                opacity=ease_out_cubic(drop),
                offset_y=-DROP_DISTANCE * (1.0 - ease_out_cubic(drop)),
            )
            draw_word_chip(painter, rect, " ".join(gram), font, look)


def _frame_opacity(sweep: float) -> float:
    return min(segment_progress(sweep, 0.0, FRAME_FADE_SHARE), 1.0 - segment_progress(sweep, 1.0 - FRAME_FADE_SHARE, 1.0))


def _window_position(sweep: float, window_count: int) -> float | None:
    if window_count <= 0 or not 0 < sweep < 1:
        return None
    steps = sweep * window_count
    index = min(math.floor(steps), window_count - 1)
    local = steps - index
    if index == 0:
        return 0.0
    return index - 1 + ease_in_out(clamp_unit(local / WINDOW_MOVE_SHARE))


def _span_rect(rects: tuple[QRectF, ...], first: int, order: int) -> QRectF:
    last = min(len(rects) - 1, first + order - 1)
    return rects[first].united(rects[last])


def _ngram_cards(details: NgramOverlapDetails, position: TimelinePosition) -> tuple[ScoreCard, ...]:
    ratios = step_phase(position, RATIO_STEP)
    values = _score_values(details)
    selection = _final_selection(details)
    return (
        ScoreCard(PRECISION_LABEL, values["precision_ratio"], DETAIL_FORMAT.format(value=values["precision"]), details.precision, segment_progress(ratios, *PRECISION_REVEAL)),
        ScoreCard(RECALL_LABEL, values["recall_ratio"], DETAIL_FORMAT.format(value=values["recall"]), details.recall, segment_progress(ratios, *RECALL_REVEAL)),
        ScoreCard(final_card_label(selection), values["score"], final_card_detail(selection), details.score, step_phase(position, F_MEASURE_STEP), True),
    )


def _token_rects(tokens: tuple[str, ...], top: float, width: float) -> tuple[QRectF, ...]:
    if not tokens:
        return ()
    font = word_font(TOKEN_TEXT_SIZE)
    natural = [chip_width(token, font) for token in tokens]
    gaps = TOKEN_GAP * (len(tokens) - 1)
    factor = min(1.0, max(0.0, width - gaps) / sum(natural))
    rects = []
    left = 0.0
    for natural_width in natural:
        chip = natural_width * factor
        rects.append(QRectF(left, top, chip, TOKEN_ROW_HEIGHT))
        left += chip + TOKEN_GAP
    return tuple(rects)


def _gram_section(grams: tuple[tuple[str, ...], ...], top: float, width: float) -> GramSection:
    caption = QRectF(0.0, top, width, CAPTION_HEIGHT)
    body_top = caption.bottom() + CAPTION_GAP
    font = word_font(GRAM_TEXT_SIZE, QFont.Weight.DemiBold)
    flow = flow_layout([chip_width(" ".join(gram), font) for gram in grams], width, GRAM_CHIP_HEIGHT, GRAM_GAP)
    chips = tuple(rect.translated(0.0, body_top) for rect in flow.rects)
    body = QRectF(0.0, body_top, width, max(flow.height, GRAM_CHIP_HEIGHT))
    return GramSection(caption, chips, body)


@lru_cache(maxsize=64)
def _window_layout(scene_input: NgramSceneInput, width: float) -> WindowLayout:
    expected_caption = QRectF(0.0, 0.0, width, CAPTION_HEIGHT)
    expected_tokens = _token_rects(scene_input.expected_tokens, expected_caption.bottom() + CAPTION_GAP, width)
    answer_caption = QRectF(0.0, expected_caption.bottom() + CAPTION_GAP + TOKEN_ROW_HEIGHT + SECTION_GAP, width, CAPTION_HEIGHT)
    answer_tokens = _token_rects(scene_input.answer_tokens, answer_caption.bottom() + CAPTION_GAP, width)
    expected_grams = _gram_section(scene_input.details.expected_ngrams, answer_caption.bottom() + CAPTION_GAP + TOKEN_ROW_HEIGHT + SECTION_GAP, width)
    answer_grams = _gram_section(scene_input.details.answer_ngrams, expected_grams.body.bottom() + SECTION_GAP, width)
    return WindowLayout(
        expected_caption,
        expected_tokens,
        answer_caption,
        answer_tokens,
        expected_grams,
        answer_grams,
        answer_grams.body.bottom(),
    )


class RougeNScene(WalkthroughScene):
    def __init__(self, order: int):
        self.order = order
        self.identifier = f"rouge_{order}"
        self._metric_name = f"ROUGE-{order}"
        self._steps = _build_steps(order)
        self._layout_painter = CountTablePainter() if order == UNIGRAM_ORDER else SlidingWindowPainter()

    @property
    def steps(self) -> tuple[SceneStep, ...]:
        return self._steps

    @property
    def formula(self) -> tuple[str, ...]:
        return BASE_FORMULA + (F_ONE_LINE,)

    @property
    def limitation(self) -> str:
        return UNIGRAM_LIMITATION if self.order == UNIGRAM_ORDER else HIGHER_ORDER_LIMITATION

    def formula_for(self, walkthrough: MetricWalkthrough) -> tuple[str, ...]:
        return formula_with_selection(BASE_FORMULA, self._selection(walkthrough))

    def formula_lines_for(self, step_index: int, walkthrough: MetricWalkthrough) -> tuple[int, ...]:
        if step_index == F_MEASURE_STEP:
            return (selected_formula_line(len(BASE_FORMULA), self._selection(walkthrough)),)
        return self._steps[step_index].formula_lines

    def step_body(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        scene_input = self._scene_input(walkthrough)
        details = scene_input.details
        selection = self._selection(walkthrough)
        if step_index == F_MEASURE_STEP:
            return final_step_body(selection)
        return self._steps[step_index].body.format(
            order=self.order,
            gram=_gram_name(self.order),
            unit=_unit_name(self.order),
            expected=len(details.expected_ngrams),
            answer=len(details.answer_ngrams),
            overlap=details.overlap_count,
            case_note=case_note(selection),
        )

    def formula_result(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        details = self._details(walkthrough)
        if step_index == EXTRACT_STEP:
            return EXTRACT_RESULT_FORMAT.format(expected=len(details.expected_ngrams), answer=len(details.answer_ngrams), unit=_unit_name(self.order))
        if step_index == COUNT_STEP:
            return OVERLAP_RESULT_FORMAT.format(overlap=details.overlap_count)
        if step_index == RATIO_STEP:
            return RATIO_RESULT_FORMAT.format(**_score_values(details))
        return final_step_result(self._selection(walkthrough))

    def paint(self, painter: QPainter, area: QRectF, walkthrough: MetricWalkthrough, position: TimelinePosition) -> None:
        scene_input = self._scene_input(walkthrough)
        content = inset_area(area)
        painter.save()
        painter.translate(content.topLeft())
        self._layout_painter.paint(painter, QRectF(0.0, 0.0, content.width(), content.height()), scene_input, position)
        painter.restore()

    def _scene_input(self, walkthrough: MetricWalkthrough) -> NgramSceneInput:
        return _scene_input(self._details(walkthrough), walkthrough.expected_answer, walkthrough.given_answer, self._selection(walkthrough).lowercase)

    def _selection(self, walkthrough: MetricWalkthrough) -> ScoreSelection:
        return score_selection(walkthrough, self._details(walkthrough))

    def _details(self, walkthrough: MetricWalkthrough) -> NgramOverlapDetails:
        if not isinstance(walkthrough.details, NgramOverlapDetails):
            raise TypeError(f"{self._metric_name} needs n-gram overlap details, got {type(walkthrough.details).__name__}.")
        return walkthrough.details
