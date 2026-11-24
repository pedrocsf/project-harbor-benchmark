import math
from dataclasses import dataclass
from functools import lru_cache

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter

from domain.explanations.metric_walkthrough import MetricWalkthrough
from domain.explanations.timeline import TimelinePosition
from domain.explanations.walkthrough_details import LcsDetails
from presentation.views.branding import (
    BORDER_COLOR,
    DISABLED_TEXT_COLOR,
    PRIMARY_COLOR,
    PRIMARY_HOVER_COLOR,
    SECONDARY_TEXT_COLOR,
    SURFACE_COLOR,
    TEXT_COLOR,
    TEXT_ON_PRIMARY_COLOR,
)
from presentation.views.metric_explorer.painting import (
    clamp_unit,
    draw_card,
    draw_text,
    ease_out_cubic,
    lerp,
    mix_colors,
    segment_progress,
    with_alpha,
)
from presentation.views.metric_explorer.scenes.base_scene import SceneStep, WalkthroughScene
from presentation.views.metric_explorer.scenes.rouge_scene_painting import (
    CAPTION_HEIGHT,
    CARD_HEIGHT,
    ChipLook,
    F_ONE_LINE,
    FINAL_TITLE,
    ScoreCard,
    ScoreSelection,
    case_note,
    final_card_detail,
    final_card_label,
    final_step_body,
    final_step_result,
    formula_with_selection,
    score_selection,
    selected_formula_line,
    chip_width,
    draw_empty_box,
    draw_note,
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
    text_width,
    value_font,
    word_font,
)

METRIC_NAME = "ROUGE-L"
SPLIT_STEP = 0
FILL_STEP = 1
TRACE_STEP = 2
RATIO_STEP = 3
F_MEASURE_STEP = 4
STEPS = (
    SceneStep(
        "Split into words",
        "Split into words: {expected} expected words become rows, {answer} answer words columns. {case_note}",
        3.0,
        (),
    ),
    SceneStep(
        "Fill the LCS table",
        "A match adds 1 to the diagonal; otherwise take the larger neighbour.",
        5.5,
        (),
    ),
    SceneStep(
        "Trace the path back",
        "Walking back from the last cell recovers the {lcs} shared words, in order.",
        4.5,
        (),
    ),
    SceneStep(
        "Precision and recall",
        "Divide the LCS ({lcs}) by the answer ({answer}) and expected ({expected}) lengths.",
        3.5,
        (0, 1),
    ),
    SceneStep(FINAL_TITLE, "", 3.0, (2,)),
)
BASE_FORMULA = (
    "P = LCS / |answer|",
    "R = LCS / |expected|",
)
LIMITATION = "Order matters, gaps are allowed: a correct answer that reorders the sentence loses points."
SPLIT_RESULT_FORMAT = "{expected} × {answer} table"
FILL_RESULT_FORMAT = "L[{expected}][{answer}] = {lcs}"
TRACE_RESULT_FORMAT = "LCS = {lcs}"
RATIO_RESULT_FORMAT = "P = {precision_ratio} = {precision}<br>R = {recall_ratio} = {recall}"
PRECISION_LABEL = "Precision"
RECALL_LABEL = "Recall"
DETAIL_FORMAT = "= {value}"
LCS_CAPTION = "Longest common subsequence"
LCS_COUNTER_FORMAT = "LCS = {count}"
NO_COMMON_WORDS_TEXT = "No words in common: LCS = 0."
EMPTY_ANSWER_TEXT = "The answer has no words, so every cell would be 0."
TRUNCATED_FORMAT = "Showing the first {rows} × {columns} of {expected} × {answer} words."
PRECISION_REVEAL = (0.0, 0.6)
RECALL_REVEAL = (0.3, 0.9)

MAXIMUM_MATRIX_TOKENS = 14
MAXIMUM_CELL_SIZE = 44.0
MINIMUM_CELL_SIZE = 16.0
CELL_GAP = 4.0
CELL_RADIUS = 6.0
LABEL_GAP = 8.0
LABEL_PADDING = 8.0
MAXIMUM_LABEL_WIDTH = 110.0
MINIMUM_LABEL_WIDTH = 36.0
LABEL_WIDTH_SHARE = 0.26
LABEL_TEXT_SIZE = 11
COMPACT_LABEL_TEXT_SIZE = 10
COMPACT_COLUMN_WIDTH = 36.0
HEADER_HEIGHT = 22.0
CELL_TEXT_SHARE = 0.34
MINIMUM_CELL_TEXT_SIZE = 10
MAXIMUM_CELL_TEXT_SIZE = 14
NOTE_HEIGHT = 16.0
SECTION_GAP = 14.0
CAPTION_GAP = 6.0
CHIP_HEIGHT = 30.0
CHIP_GAP = 6.0
CHIP_TEXT_SIZE = 13
CHIP_RISE_DISTANCE = 8.0
EMPTY_ANSWER_WIDTH_SHARE = 0.6
LABEL_STAGGER_SPAN = 0.4
PLACEHOLDER_REVEAL = (0.0, 0.6)
PLACEHOLDER_BASE_OPACITY = 0.4
PLACEHOLDER_ALPHA = 0.35
MINIMUM_FILL_SPAN = 0.04
MAXIMUM_FILL_SPAN = 0.3
FILL_SPAN_CELLS = 4.0
POP_START_SCALE = 0.6
MATCH_TINT_ALPHA = 0.14
ACTIVE_BORDER_ALPHA = 0.9
TRACE_PATH_END = 0.75
TRACE_SPAN = 0.25
TRACE_DIM_END = 0.3
DIMMED_CELL_OPACITY = 0.5
PATH_FILL_ALPHA = 0.28
CHIP_RISE_DELAY = 0.3
LATE_CHIP_REVEAL = (0.75, 1.0)
PENDING_CAPTION_OPACITY = 0.45


@dataclass(frozen=True)
class MatrixLayout:
    rows: int
    columns: int
    truncated: bool
    left: float
    label_width: float
    cell: float
    grid_width: float
    matrix_bottom: float
    note: QRectF
    lcs_caption: QRectF
    lcs_chips: tuple[QRectF, ...]
    lcs_body: QRectF
    cards: QRectF
    content_height: float

    def cell_rect(self, row: int, column: int) -> QRectF:
        pitch = self.cell + CELL_GAP
        return QRectF(self.left + self.label_width + LABEL_GAP + column * pitch, HEADER_HEIGHT + row * pitch, self.cell, self.cell)

    def row_label_rect(self, row: int) -> QRectF:
        return QRectF(self.left, HEADER_HEIGHT + row * (self.cell + CELL_GAP), self.label_width, self.cell)

    def column_label_rect(self, column: int) -> QRectF:
        cell = self.cell_rect(0, column)
        return QRectF(cell.left() - CELL_GAP / 2, 0.0, cell.width() + CELL_GAP, HEADER_HEIGHT)

    def empty_answer_rect(self) -> QRectF:
        left = self.left + self.label_width + LABEL_GAP
        return QRectF(left, HEADER_HEIGHT, self.grid_width, self.matrix_bottom - HEADER_HEIGHT)


def _label_font(column_width: float) -> QFont:
    return word_font(LABEL_TEXT_SIZE if column_width >= COMPACT_COLUMN_WIDTH else COMPACT_LABEL_TEXT_SIZE)


def _cell_font(cell: float) -> QFont:
    size = round(cell * CELL_TEXT_SHARE)
    return value_font(max(MINIMUM_CELL_TEXT_SIZE, min(MAXIMUM_CELL_TEXT_SIZE, size)), QFont.Weight.Normal)


def _lcs_tokens(details: LcsDetails) -> tuple[str, ...]:
    return tuple(details.expected_tokens[expected] for expected, _ in details.matched_cells)


def _label_width(details: LcsDetails, rows: int, width: float) -> float:
    font = word_font(LABEL_TEXT_SIZE)
    widest = max((text_width(token, font) for token in details.expected_tokens[:rows]), default=0.0)
    return max(MINIMUM_LABEL_WIDTH, min(widest + LABEL_PADDING, width * LABEL_WIDTH_SHARE, MAXIMUM_LABEL_WIDTH))


def _cell_size(rows: int, columns: int, matrix_width: float, matrix_height: float) -> float:
    by_height = (matrix_height - HEADER_HEIGHT) / max(1, rows) - CELL_GAP
    by_width = matrix_width / max(1, columns) - CELL_GAP if columns else MAXIMUM_CELL_SIZE
    return max(MINIMUM_CELL_SIZE, min(MAXIMUM_CELL_SIZE, by_height, by_width))


@lru_cache(maxsize=64)
def _matrix_layout(details: LcsDetails, width: float, height: float) -> MatrixLayout:
    rows = min(len(details.expected_tokens), MAXIMUM_MATRIX_TOKENS)
    columns = min(len(details.answer_tokens), MAXIMUM_MATRIX_TOKENS)
    truncated = rows < len(details.expected_tokens) or columns < len(details.answer_tokens)
    chip_font = word_font(CHIP_TEXT_SIZE, QFont.Weight.DemiBold)
    flow = flow_layout([chip_width(token, chip_font) for token in _lcs_tokens(details)], width, CHIP_HEIGHT, CHIP_GAP)
    chips_height = max(flow.height, CHIP_HEIGHT)
    bottom_height = CAPTION_HEIGHT + CAPTION_GAP + chips_height + SECTION_GAP + CARD_HEIGHT
    note_height = NOTE_HEIGHT + CAPTION_GAP if truncated else 0.0
    label_width = _label_width(details, rows, width)
    matrix_height = height - bottom_height - note_height - SECTION_GAP
    cell = _cell_size(rows, columns, width - label_width - LABEL_GAP + CELL_GAP, matrix_height)
    pitch = cell + CELL_GAP
    grid_width = columns * pitch - CELL_GAP if columns else width * EMPTY_ANSWER_WIDTH_SHARE
    matrix_width = label_width + LABEL_GAP + grid_width
    left = max(0.0, (width - matrix_width) / 2)
    matrix_bottom = HEADER_HEIGHT + rows * pitch - CELL_GAP
    note = QRectF(0.0, matrix_bottom + CAPTION_GAP, width, NOTE_HEIGHT)
    caption_top = matrix_bottom + note_height + SECTION_GAP
    lcs_caption = QRectF(0.0, caption_top, width, CAPTION_HEIGHT)
    body_top = lcs_caption.bottom() + CAPTION_GAP
    lcs_chips = tuple(rect.translated(0.0, body_top) for rect in flow.rects)
    lcs_body = QRectF(0.0, body_top, width, chips_height)
    content_height = lcs_body.bottom() + SECTION_GAP + CARD_HEIGHT
    cards = QRectF(0.0, max(content_height, height) - CARD_HEIGHT, width, CARD_HEIGHT)
    return MatrixLayout(rows, columns, truncated, left, label_width, cell, grid_width, matrix_bottom, note, lcs_caption, lcs_chips, lcs_body, cards, content_height)


@lru_cache(maxsize=64)
def _visible_path(details: LcsDetails, rows: int, columns: int) -> tuple[tuple[int, int], ...]:
    return tuple((row - 1, column - 1) for row, column in details.path if 1 <= row <= rows and 1 <= column <= columns)


@dataclass(frozen=True)
class TraceState:
    path_lit: dict[tuple[int, int], float]
    matched: frozenset[tuple[int, int]]
    dim: float


class LcsMatrixPainter:
    def paint(self, painter: QPainter, width: float, height: float, details: LcsDetails, position: TimelinePosition) -> None:
        scale = fit_scale(lambda virtual_width, virtual_height: _matrix_layout(details, virtual_width, virtual_height).content_height, width, height)
        layout = _matrix_layout(details, width / scale, height / scale)
        painter.save()
        painter.scale(scale, scale)
        split, fill, trace = (step_phase(position, step) for step in (SPLIT_STEP, FILL_STEP, TRACE_STEP))
        state = self._trace_state(details, layout, trace)
        self._paint_labels(painter, details, layout, split, fill, state)
        self._paint_cells(painter, details, layout, split, fill, state)
        self._paint_truncation_note(painter, details, layout)
        self._paint_lcs(painter, details, layout, trace, state)
        draw_score_cards(painter, layout.cards, _lcs_cards(details, position))
        painter.restore()

    def _trace_state(self, details: LcsDetails, layout: MatrixLayout, trace: float) -> TraceState:
        path = _visible_path(details, layout.rows, layout.columns)
        walk = segment_progress(trace, 0.0, TRACE_PATH_END)
        lit = {cell: stagger(walk, rank, len(path), TRACE_SPAN) for rank, cell in enumerate(path)}
        return TraceState(lit, frozenset(details.matched_cells), segment_progress(trace, 0.0, TRACE_DIM_END))

    def _active_cell(self, layout: MatrixLayout, fill: float) -> tuple[int, int] | None:
        total = layout.rows * layout.columns
        if total == 0 or not 0 < fill < 1:
            return None
        index = min(total - 1, math.floor(fill * total))
        return divmod(index, layout.columns)

    def _paint_labels(self, painter: QPainter, details: LcsDetails, layout: MatrixLayout, split: float, fill: float, state: TraceState) -> None:
        active = self._active_cell(layout, fill)
        lit_matches = tuple(cell for cell in state.matched if state.path_lit.get(cell, 0.0) >= 0.5)
        matched_rows = {row for row, _ in lit_matches}
        matched_columns = {column for _, column in lit_matches}
        font = _label_font(layout.cell + CELL_GAP)
        for row in range(layout.rows):
            appear = ease_out_cubic(stagger(split, row, layout.rows, LABEL_STAGGER_SPAN))
            emphasis = row in matched_rows
            color = PRIMARY_HOVER_COLOR if emphasis else (TEXT_COLOR if active and active[0] == row else SECONDARY_TEXT_COLOR)
            rect = layout.row_label_rect(row).adjusted(0.0, 0.0, -LABEL_PADDING / 2, 0.0)
            self._draw_label(painter, rect, details.expected_tokens[row], font, color, appear, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, emphasis)
        for column in range(layout.columns):
            appear = ease_out_cubic(stagger(split, column, layout.columns, LABEL_STAGGER_SPAN))
            emphasis = column in matched_columns
            color = PRIMARY_HOVER_COLOR if emphasis else (TEXT_COLOR if active and active[1] == column else SECONDARY_TEXT_COLOR)
            self._draw_label(painter, layout.column_label_rect(column), details.answer_tokens[column], font, color, appear, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, emphasis)

    def _draw_label(
        self,
        painter: QPainter,
        rect: QRectF,
        text: str,
        font: QFont,
        color: str,
        appear: float,
        alignment: Qt.AlignmentFlag,
        emphasis: bool,
    ) -> None:
        if appear <= 0:
            return
        label_font = QFont(font)
        if emphasis:
            label_font.setWeight(QFont.Weight.Bold)
        painter.save()
        painter.setOpacity(painter.opacity() * appear)
        draw_text(painter, rect, elide(text, label_font, rect.width()), color, label_font, alignment)
        painter.restore()

    def _paint_cells(self, painter: QPainter, details: LcsDetails, layout: MatrixLayout, split: float, fill: float, state: TraceState) -> None:
        if layout.columns == 0:
            draw_empty_box(painter, layout.empty_answer_rect(), EMPTY_ANSWER_TEXT, _placeholder_opacity(split))
            return
        total = layout.rows * layout.columns
        span = max(MINIMUM_FILL_SPAN, min(MAXIMUM_FILL_SPAN, FILL_SPAN_CELLS / total))
        placeholder = _placeholder_opacity(split)
        font = _cell_font(layout.cell)
        for row in range(layout.rows):
            for column in range(layout.columns):
                rect = layout.cell_rect(row, column)
                pop = stagger(fill, row * layout.columns + column, total, span)
                self._paint_cell(painter, rect, details, (row, column), pop, placeholder, state, font)

    def _paint_cell(
        self,
        painter: QPainter,
        rect: QRectF,
        details: LcsDetails,
        cell: tuple[int, int],
        pop: float,
        placeholder: float,
        state: TraceState,
        font: QFont,
    ) -> None:
        if pop <= 0:
            draw_card(painter, rect.adjusted(0.5, 0.5, -0.5, -0.5), with_alpha(SURFACE_COLOR, PLACEHOLDER_ALPHA * placeholder), with_alpha(BORDER_COLOR, placeholder), CELL_RADIUS)
            return
        row, column = cell
        value = details.table[row + 1][column + 1]
        is_match = details.expected_tokens[row] == details.answer_tokens[column]
        lit = state.path_lit.get(cell, 0.0)
        on_path_match = cell in state.matched
        grow = ease_out_cubic(pop)
        scale = lerp(POP_START_SCALE, 1.0, grow)
        shape = QRectF(0.0, 0.0, rect.width() * scale, rect.height() * scale)
        shape.moveCenter(rect.center())
        painter.save()
        painter.setOpacity(painter.opacity() * grow * (1.0 if cell in state.path_lit else lerp(1.0, DIMMED_CELL_OPACITY, state.dim)))
        fill_color, border, text_color = self._cell_colors(value, is_match, lit, on_path_match, pop)
        draw_card(painter, shape.adjusted(0.5, 0.5, -0.5, -0.5), fill_color, border, CELL_RADIUS)
        cell_font = QFont(font)
        if on_path_match and lit >= 0.5:
            cell_font.setWeight(QFont.Weight.Bold)
        draw_text(painter, shape, str(value), text_color, cell_font, Qt.AlignmentFlag.AlignCenter)
        painter.restore()

    def _cell_colors(self, value: int, is_match: bool, lit: float, on_path_match: bool, pop: float) -> tuple[QColor | str, QColor | None, QColor | str]:
        base_fill = mix_colors(SURFACE_COLOR, PRIMARY_COLOR, MATCH_TINT_ALPHA) if is_match else SURFACE_COLOR
        base_text = TEXT_COLOR if value > 0 else DISABLED_TEXT_COLOR
        border = with_alpha(PRIMARY_COLOR, ACTIVE_BORDER_ALPHA * math.sin(math.pi * pop)) if 0 < pop < 1 else None
        if lit <= 0:
            return base_fill, border, base_text
        target_fill = PRIMARY_COLOR if on_path_match else mix_colors(SURFACE_COLOR, PRIMARY_COLOR, PATH_FILL_ALPHA)
        target_text = TEXT_ON_PRIMARY_COLOR if on_path_match else TEXT_COLOR
        return mix_colors(base_fill, target_fill, lit), with_alpha(PRIMARY_COLOR, lit), mix_colors(base_text, target_text, lit)

    def _paint_truncation_note(self, painter: QPainter, details: LcsDetails, layout: MatrixLayout) -> None:
        if not layout.truncated:
            return
        text = TRUNCATED_FORMAT.format(rows=layout.rows, columns=layout.columns, expected=len(details.expected_tokens), answer=len(details.answer_tokens))
        draw_note(painter, layout.note, text)

    def _paint_lcs(self, painter: QPainter, details: LcsDetails, layout: MatrixLayout, trace: float, state: TraceState) -> None:
        reveals = tuple(self._chip_reveal(cell, trace, state) for cell in details.matched_cells)
        shown = sum(1 for reveal in reveals if reveal > 0)
        trailing = LCS_COUNTER_FORMAT.format(count=shown) if trace > 0 else ""
        draw_section_caption(painter, layout.lcs_caption, LCS_CAPTION, trailing, lerp(PENDING_CAPTION_OPACITY, 1.0, trace))
        if not details.matched_cells:
            draw_note(painter, layout.lcs_body, NO_COMMON_WORDS_TEXT, trace)
            return
        font = word_font(CHIP_TEXT_SIZE)
        for rect, token, reveal in zip(layout.lcs_chips, _lcs_tokens(details), reveals):
            eased = ease_out_cubic(reveal)
            look = ChipLook(highlight=1.0, opacity=eased, offset_y=CHIP_RISE_DISTANCE * (1.0 - eased))
            draw_word_chip(painter, rect, token, font, look)

    def _chip_reveal(self, cell: tuple[int, int], trace: float, state: TraceState) -> float:
        lit = state.path_lit.get(cell)
        if lit is None:
            return segment_progress(trace, *LATE_CHIP_REVEAL)
        return clamp_unit((lit - CHIP_RISE_DELAY) / (1.0 - CHIP_RISE_DELAY))


def _placeholder_opacity(split: float) -> float:
    return lerp(PLACEHOLDER_BASE_OPACITY, 1.0, segment_progress(split, *PLACEHOLDER_REVEAL))


def _score_values(details: LcsDetails) -> dict[str, str]:
    return {
        "precision_ratio": format_ratio(details.lcs_length, len(details.answer_tokens)),
        "recall_ratio": format_ratio(details.lcs_length, len(details.expected_tokens)),
        "precision": format_score(details.precision),
        "recall": format_score(details.recall),
        "score": format_score(details.score),
    }


def _lcs_cards(details: LcsDetails, position: TimelinePosition) -> tuple[ScoreCard, ...]:
    ratios = step_phase(position, RATIO_STEP)
    values = _score_values(details)
    selection = ScoreSelection(details.score_type, details.beta, True, details.score)
    return (
        ScoreCard(PRECISION_LABEL, values["precision_ratio"], DETAIL_FORMAT.format(value=values["precision"]), details.precision, segment_progress(ratios, *PRECISION_REVEAL)),
        ScoreCard(RECALL_LABEL, values["recall_ratio"], DETAIL_FORMAT.format(value=values["recall"]), details.recall, segment_progress(ratios, *RECALL_REVEAL)),
        ScoreCard(final_card_label(selection), values["score"], final_card_detail(selection), details.score, step_phase(position, F_MEASURE_STEP), True),
    )


class RougeLScene(WalkthroughScene):
    identifier = "rouge_l"

    def __init__(self):
        self._matrix_painter = LcsMatrixPainter()

    @property
    def steps(self) -> tuple[SceneStep, ...]:
        return STEPS

    @property
    def formula(self) -> tuple[str, ...]:
        return BASE_FORMULA + (F_ONE_LINE,)

    @property
    def limitation(self) -> str:
        return LIMITATION

    def formula_for(self, walkthrough: MetricWalkthrough) -> tuple[str, ...]:
        return formula_with_selection(BASE_FORMULA, self._selection(walkthrough))

    def formula_lines_for(self, step_index: int, walkthrough: MetricWalkthrough) -> tuple[int, ...]:
        if step_index == F_MEASURE_STEP:
            return (selected_formula_line(len(BASE_FORMULA), self._selection(walkthrough)),)
        return STEPS[step_index].formula_lines

    def step_body(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        details = self._details(walkthrough)
        selection = self._selection(walkthrough)
        if step_index == F_MEASURE_STEP:
            return final_step_body(selection)
        return STEPS[step_index].body.format(
            case_note=case_note(selection),
            expected=len(details.expected_tokens),
            answer=len(details.answer_tokens),
            lcs=details.lcs_length,
        )

    def formula_result(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        details = self._details(walkthrough)
        sizes = {"expected": len(details.expected_tokens), "answer": len(details.answer_tokens), "lcs": details.lcs_length}
        if step_index == SPLIT_STEP:
            return SPLIT_RESULT_FORMAT.format(**sizes)
        if step_index == FILL_STEP:
            return FILL_RESULT_FORMAT.format(**sizes)
        if step_index == TRACE_STEP:
            return TRACE_RESULT_FORMAT.format(**sizes)
        if step_index == RATIO_STEP:
            return RATIO_RESULT_FORMAT.format(**_score_values(details))
        return final_step_result(self._selection(walkthrough))

    def paint(self, painter: QPainter, area: QRectF, walkthrough: MetricWalkthrough, position: TimelinePosition) -> None:
        details = self._details(walkthrough)
        content = inset_area(area)
        painter.save()
        painter.translate(content.topLeft())
        self._matrix_painter.paint(painter, content.width(), content.height(), details, position)
        painter.restore()

    def _selection(self, walkthrough: MetricWalkthrough) -> ScoreSelection:
        return score_selection(walkthrough, self._details(walkthrough))

    def _details(self, walkthrough: MetricWalkthrough) -> LcsDetails:
        if not isinstance(walkthrough.details, LcsDetails):
            raise TypeError(f"{METRIC_NAME} needs LCS details, got {type(walkthrough.details).__name__}.")
        return walkthrough.details
