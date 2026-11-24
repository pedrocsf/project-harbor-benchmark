from dataclasses import dataclass

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QFont, QFontMetricsF, QPainter

from domain.explanations.metric_walkthrough import MetricWalkthrough
from domain.explanations.timeline import TimelinePosition
from domain.explanations.walkthrough_details import ContainsAnswerDetails
from domain.scoring.text_normalization import DEFAULT_NORMALIZATION
from presentation.views.branding import DISABLED_TEXT_COLOR, PRIMARY_COLOR, TEXT_COLOR, SUCCESS_COLOR, SURFACE_COLOR, WARNING_COLOR
from presentation.views.metric_explorer.painting import (
    CHIP_RADIUS,
    clamp_unit,
    draw_caption,
    draw_card,
    draw_text,
    ease_in_out,
    lerp,
    monospace_font,
    segment_progress,
    text_font,
    with_alpha,
)
from presentation.views.metric_explorer.scenes.base_scene import SceneStep, WalkthroughScene
from presentation.views.metric_explorer.scenes.token_scene_painting import (
    CAPTION_HEIGHT,
    VERDICT_SCORE_FORMAT,
    ChipMetrics,
    ChipState,
    ChipStyle,
    LayoutCache,
    VerdictLayout,
    blend_styles,
    chip_font,
    chip_style,
    highlighted_text,
    note_height,
    normalization_formula,
    normalization_options_text,
    options_from_normalization,
    paint_chip,
    paint_empty_slot,
    paint_note,
    paint_verdict,
    pulse,
    staggered,
    place_verdict,
)

NORMALIZE_STEP = 0
SLIDE_STEP = 1
SCORE_STEP = 2
STEPS = (
    SceneStep(
        "Normalize both answers",
        "Clean both answers: {expected} expected and {answer} answer tokens. {options}",
        3.5,
        (0,),
    ),
    SceneStep(
        "Search the answer",
        "{search}",
        4.5,
        (1,),
    ),
    SceneStep(
        "Score 1 or 0",
        "1 if the whole expected text appears in the answer, 0 otherwise. This pair scores {score}.",
        3.0,
        (1,),
    ),
)
WHOLE_WORDS_MODE = "whole_words"
SUBSTRING_MODE = "substring"
WHOLE_WORDS_FORMULA = "score = 1 if n(expected)<br>&nbsp;&nbsp;appears in n(answer),<br>&nbsp;&nbsp;else 0"
SUBSTRING_FORMULA = "score = 1 if n(expected)<br>&nbsp;&nbsp;is a substring of n(answer),<br>&nbsp;&nbsp;else 0"
WHOLE_WORDS_SEARCH = "A window as long as the expected text ({expected} tokens) moves over the answer, one word at a time: {positions}. Switch to substring matching with “Parameters…”."
SUBSTRING_SEARCH = "The expected text ({characters} characters) is searched inside the answer as plain text, even in the middle of a word: {outcome}. Switch to whole words with “Parameters…”."
SUBSTRING_FOUND_OUTCOME = "it starts at character {position}"
SUBSTRING_MISSING_OUTCOME = "no match"
SUBSTRING_FOUND_RESULT = "found at character {position}"
SUBSTRING_FOUND_NOTE = "The {length} expected characters appear in the answer starting at character {position}, even when they sit inside a longer word."
SUBSTRING_MISSING_NOTE = "No stretch of the normalized answer matches the expected text character for character."
SUBSTRING_EMPTY_FOUND_NOTE = "The expected text is empty after normalization, so it is found trivially."
SUBSTRING_EXPECTED_CAPTION = "Normalized expected answer"
SUBSTRING_ANSWER_CAPTION = "Normalized model answer"
EMPTY_TEXT = "empty"
SUBSTRING_TEXT_SIZES = (13, 12, 11, 10)
SUBSTRING_CARD_PADDING = 8.0
SUBSTRING_LINE_SPACING = 6.0
SUBSTRING_CARD_RADIUS = 6.0
SUBSTRING_SECTION_GAP = 8.0
SUBSTRING_BLOCK_GAP = 14.0
SUBSTRING_HIGHLIGHT_ALPHA = 0.28
SUBSTRING_SCAN_ALPHA = 0.14
SCAN_CURSOR_HEIGHT = 3.0
SPACE_REFERENCE = "0"
LIMITATION = "Rewards answers that quote the expected text, even when they add wrong facts around it."
WINDOW_CAPTION = "Search window · normalized expected answer"
ANSWER_CAPTION = "Normalized model answer"
POSITION_FORMATS = ("{count} position", "{count} positions")
NO_POSITIONS_TEXT = "it fits in no position"
POSITIONS_TEXT = "{positions} tried"
FOUND_RESULT = "found at token {position}"
NOT_FOUND_RESULT = "not found"
SCORE_RESULT = "score = {score}"
EMPTY_ANSWER_TEXT = "The answer is empty after normalization, so there is nothing to search."
EMPTY_EXPECTED_TEXT = "The expected text is empty after normalization, so there is no window to slide."
SHORTER_TEXT = "The answer is shorter than the expected text ({answer} vs {expected} tokens), so the window cannot fit anywhere."
FOUND_TEXT = "The window matches at token {position}: all {expected} expected tokens appear in order."
SINGLE_POSITION_SAME_LENGTH_TEXT = "Both texts have {expected} tokens, so the window fits in only one position."
SINGLE_POSITION_TEXT = "The window fits in only one position."
MANY_POSITIONS_TEXT = "The window tried {count} positions and broke at each one."
BREAK_TEXT = " It breaks at token {position}: “{answer}” is not “{expected}”."
LAST_BREAK_TEXT = " At the last one, “{answer}” is not “{expected}”."
FOUND_VERDICT = "The expected text appears inside the answer."
NOT_FOUND_VERDICT = "The expected text does not appear inside the answer."
EQUAL_SIGN = "="
DIFFERENT_SIGN = "≠"
CELL_GAP = 4.0
MAXIMUM_CELL_WIDTH = 72.0
CELL_HEIGHT = 32.0
CELL_PADDING = 3.0
CELL_FONT_SIZES = (12, 11, 10)
SECTION_GAP = 10.0
WINDOW_FRAME_INSET = 4.0
WINDOW_FRAME_RADIUS = CHIP_RADIUS + WINDOW_FRAME_INSET
WINDOW_FRAME_FILL_ALPHA = 0.06
WINDOW_FRAME_BORDER_ALPHA = 0.6
CHECK_ROW_HEIGHT = 20.0
CHECK_SIZE = 14
ANSWER_CAPTION_GAP = 8.0
TRACK_GAP = 14.0
TRACK_HEIGHT = 6.0
TRACK_PILL_HEIGHT = 10.0
NOTE_GAP = 14.0
VERDICT_GAP = 24.0
MINIMUM_FLEX_GAP = 12.0
CHIP_APPEAR_SHARE = 0.35
FIRST_SETTLE_WEIGHT = 0.4
MOVE_WEIGHT = 1.0
CHECK_WEIGHT = 0.55
SLIDE_END = 0.88
NOTE_START = 0.88
OVERHANG_PULSE_CYCLES = 1.5
OVERHANG_BASE_ALPHA = 0.1
OVERHANG_PULSE_ALPHA = 0.15
VERDICT_APPEAR_END = 0.5


@dataclass(frozen=True)
class PositionSlot:
    answer_start: int
    start: float
    move_end: float
    end: float
    check_count: int


@dataclass(frozen=True)
class ContainsAnswerLayout:
    metrics: ChipMetrics
    left: float
    cell_width: float
    window_caption: QRectF
    window_top: float
    checks_top: float
    answer_top: float
    answer_caption: QRectF
    track: QRectF
    note_rect: QRectF
    note: str
    slots: tuple[PositionSlot, ...]
    verdict: VerdictLayout


@dataclass(frozen=True)
class SubstringLayout:
    text_size: int
    advance: float
    line_height: float
    characters_per_line: int
    expected_caption: QRectF
    expected_card: QRectF
    answer_caption: QRectF
    answer_card: QRectF
    note_rect: QRectF
    note: str
    verdict: VerdictLayout


@dataclass(frozen=True)
class WindowState:
    offset: float
    slot: PositionSlot | None
    checks_shown: float


def contains_details(walkthrough: MetricWalkthrough) -> ContainsAnswerDetails:
    if not isinstance(walkthrough.details, ContainsAnswerDetails):
        raise TypeError(f"Contains answer needs contains answer details, got {type(walkthrough.details).__name__}.")
    return walkthrough.details


def mismatch_index(details: ContainsAnswerDetails, answer_start: int) -> int | None:
    for offset, expected_token in enumerate(details.expected_tokens):
        if details.answer_tokens[answer_start + offset] != expected_token:
            return offset
    return None


def check_count(details: ContainsAnswerDetails, answer_start: int) -> int:
    mismatch = mismatch_index(details, answer_start)
    return len(details.expected_tokens) if mismatch is None else mismatch + 1


def position_slots(details: ContainsAnswerDetails) -> tuple[PositionSlot, ...]:
    weights = []
    for order, answer_start in enumerate(details.window_positions):
        move = FIRST_SETTLE_WEIGHT if order == 0 else MOVE_WEIGHT
        weights.append((answer_start, move, check_count(details, answer_start)))
    total = sum(move + checks * CHECK_WEIGHT for _, move, checks in weights)
    slots = []
    cursor = 0.0
    for answer_start, move, checks in weights:
        move_end = cursor + move / total * SLIDE_END
        end = move_end + checks * CHECK_WEIGHT / total * SLIDE_END
        slots.append(PositionSlot(answer_start, cursor, move_end, end, checks))
        cursor = end
    return tuple(slots)


def _break_sentence(details: ContainsAnswerDetails, answer_start: int, template: str) -> str:
    mismatch = mismatch_index(details, answer_start)
    if mismatch is None:
        return ""
    return template.format(position=mismatch + 1, answer=details.answer_tokens[answer_start + mismatch], expected=details.expected_tokens[mismatch])


def explanation(details: ContainsAnswerDetails) -> str:
    expected_count, answer_count = len(details.expected_tokens), len(details.answer_tokens)
    if not details.expected_tokens:
        return EMPTY_EXPECTED_TEXT
    if not details.answer_tokens:
        return EMPTY_ANSWER_TEXT
    if not details.window_positions:
        return SHORTER_TEXT.format(answer=answer_count, expected=expected_count)
    if details.found_at is not None:
        return FOUND_TEXT.format(position=details.found_at + 1, expected=expected_count)
    last_start = details.window_positions[-1]
    if len(details.window_positions) == 1:
        opening = SINGLE_POSITION_SAME_LENGTH_TEXT.format(expected=expected_count) if answer_count == expected_count else SINGLE_POSITION_TEXT
        return opening + _break_sentence(details, last_start, BREAK_TEXT)
    return MANY_POSITIONS_TEXT.format(count=len(details.window_positions)) + _break_sentence(details, last_start, LAST_BREAK_TEXT)


def _cell_metrics(details: ContainsAnswerDetails, cell_width: float) -> ChipMetrics:
    tokens = details.expected_tokens + details.answer_tokens
    for size in CELL_FONT_SIZES:
        metrics = ChipMetrics(size, CELL_HEIGHT, CELL_PADDING, CELL_GAP, 0.0)
        widest = max((QFontMetricsF(chip_font(metrics, True)).horizontalAdvance(token) for token in tokens), default=0.0)
        if widest + 2 * CELL_PADDING <= cell_width:
            return metrics
    return ChipMetrics(CELL_FONT_SIZES[-1], CELL_HEIGHT, CELL_PADDING, CELL_GAP, 0.0)


def substring_note(details: ContainsAnswerDetails) -> str:
    if details.character_position is None:
        return SUBSTRING_MISSING_NOTE
    if not details.normalization.normalized_expected:
        return SUBSTRING_EMPTY_FOUND_NOTE
    return SUBSTRING_FOUND_NOTE.format(length=len(details.normalization.normalized_expected), position=details.character_position + 1)


def _line_count(text: str, characters_per_line: int) -> int:
    return max(1, -(-len(text) // characters_per_line))


def _substring_metrics(text_size: int, card_width: float) -> tuple[float, float, int]:
    metrics = QFontMetricsF(monospace_font(text_size, QFont.Weight.Normal))
    advance = metrics.horizontalAdvance(SPACE_REFERENCE)
    characters_per_line = max(1, int((card_width - 2 * SUBSTRING_CARD_PADDING) // advance))
    return advance, metrics.height() + SUBSTRING_LINE_SPACING, characters_per_line


def _substring_height(details: ContainsAnswerDetails, area: QRectF, text_size: int, note: str, verdict_height: float) -> float:
    _, line_height, per_line = _substring_metrics(text_size, area.width())
    normalization = details.normalization
    card_heights = [_line_count(text, per_line) * line_height + 2 * SUBSTRING_CARD_PADDING for text in (normalization.normalized_expected, normalization.normalized_answer)]
    captions = 2 * (CAPTION_HEIGHT + SUBSTRING_SECTION_GAP)
    return captions + sum(card_heights) + SUBSTRING_BLOCK_GAP + note_height(note, area.width()) + VERDICT_GAP + verdict_height


def build_substring_layout(walkthrough: MetricWalkthrough, area: QRectF) -> SubstringLayout:
    details = contains_details(walkthrough)
    normalization = details.normalization
    note = substring_note(details)
    score_text = VERDICT_SCORE_FORMAT.format(walkthrough.final_score)
    message = verdict_message(details, walkthrough.final_score)
    verdict_height = place_verdict(area, 0.0, score_text, message).score.height()
    text_size = SUBSTRING_TEXT_SIZES[-1]
    for size in SUBSTRING_TEXT_SIZES:
        if _substring_height(details, area, size, note, verdict_height) <= area.height():
            text_size = size
            break
    advance, line_height, per_line = _substring_metrics(text_size, area.width())
    expected_caption = QRectF(area.left(), area.top(), area.width(), CAPTION_HEIGHT)
    expected_height = _line_count(normalization.normalized_expected, per_line) * line_height + 2 * SUBSTRING_CARD_PADDING
    expected_card = QRectF(area.left(), expected_caption.bottom() + SUBSTRING_SECTION_GAP, area.width(), expected_height)
    answer_caption = QRectF(area.left(), expected_card.bottom() + SUBSTRING_BLOCK_GAP, area.width(), CAPTION_HEIGHT)
    answer_height = _line_count(normalization.normalized_answer, per_line) * line_height + 2 * SUBSTRING_CARD_PADDING
    answer_card = QRectF(area.left(), answer_caption.bottom() + SUBSTRING_SECTION_GAP, area.width(), answer_height)
    note_rect = QRectF(area.left(), answer_card.bottom() + SUBSTRING_BLOCK_GAP, area.width(), note_height(note, area.width()))
    verdict = place_verdict(area, note_rect.bottom() + VERDICT_GAP, score_text, message)
    return SubstringLayout(text_size, advance, line_height, per_line, expected_caption, expected_card, answer_caption, answer_card, note_rect, note, verdict)


def build_contains_answer_layout(walkthrough: MetricWalkthrough, area: QRectF) -> ContainsAnswerLayout | SubstringLayout:
    details = contains_details(walkthrough)
    if details.match_mode == SUBSTRING_MODE:
        return build_substring_layout(walkthrough, area)
    columns = max(len(details.answer_tokens), len(details.expected_tokens), 1)
    cells_left = area.left() + WINDOW_FRAME_INSET
    cells_width = area.width() - 2 * WINDOW_FRAME_INSET
    cell_width = min(MAXIMUM_CELL_WIDTH, (cells_width - CELL_GAP * (columns - 1)) / columns)
    note = explanation(details)
    window_caption = QRectF(area.left(), area.top(), area.width(), CAPTION_HEIGHT)
    window_top = window_caption.bottom() + SECTION_GAP + WINDOW_FRAME_INSET
    checks_top = window_top + CELL_HEIGHT + WINDOW_FRAME_INSET
    answer_top = checks_top + CHECK_ROW_HEIGHT
    answer_caption = QRectF(area.left(), answer_top + CELL_HEIGHT + ANSWER_CAPTION_GAP, area.width(), CAPTION_HEIGHT)
    track_width = max(cell_width, max(len(details.answer_tokens), 1) * (cell_width + CELL_GAP) - CELL_GAP)
    track = QRectF(cells_left, answer_caption.bottom() + TRACK_GAP, track_width, TRACK_HEIGHT)
    note_rect = QRectF(area.left(), track.bottom() + NOTE_GAP, area.width(), note_height(note, area.width()))
    score_text = VERDICT_SCORE_FORMAT.format(walkthrough.final_score)
    return ContainsAnswerLayout(
        metrics=_cell_metrics(details, cell_width),
        left=cells_left,
        cell_width=cell_width,
        window_caption=window_caption,
        window_top=window_top,
        checks_top=checks_top,
        answer_top=answer_top,
        answer_caption=answer_caption,
        track=track,
        note_rect=note_rect,
        note=note,
        slots=position_slots(details),
        verdict=place_verdict(area, note_rect.bottom() + VERDICT_GAP, score_text, verdict_message(details, walkthrough.final_score)),
    )


def verdict_message(details: ContainsAnswerDetails, final_score: float) -> str:
    return FOUND_VERDICT if is_found(details, final_score) else NOT_FOUND_VERDICT


def is_found(details: ContainsAnswerDetails, final_score: float) -> bool:
    return details.found_at is not None and final_score > 0


def positions_text(details: ContainsAnswerDetails) -> str:
    count = len(details.window_positions)
    if count == 0:
        return NO_POSITIONS_TEXT
    return POSITIONS_TEXT.format(positions=POSITION_FORMATS[0 if count == 1 else 1].format(count=count))


def score_text(score: float) -> str:
    return f"{score:g}"


class ContainsAnswerScene(WalkthroughScene):
    identifier = "contains_answer"

    def __init__(self):
        self._layouts = LayoutCache(build_contains_answer_layout)

    @property
    def steps(self) -> tuple[SceneStep, ...]:
        return STEPS

    @property
    def formula(self) -> tuple[str, ...]:
        return (normalization_formula(DEFAULT_NORMALIZATION), WHOLE_WORDS_FORMULA)

    def formula_for(self, walkthrough: MetricWalkthrough) -> tuple[str, ...]:
        details = contains_details(walkthrough)
        options = options_from_normalization(details.normalization)
        search_formula = SUBSTRING_FORMULA if details.match_mode == SUBSTRING_MODE else WHOLE_WORDS_FORMULA
        return (normalization_formula(options), search_formula)

    @property
    def limitation(self) -> str:
        return LIMITATION

    def step_body(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        details = contains_details(walkthrough)
        search = self._search_text(details)
        return STEPS[step_index].body.format(
            options=normalization_options_text(options_from_normalization(details.normalization)),
            search=search,
            expected=len(details.expected_tokens),
            answer=len(details.answer_tokens),
            score=score_text(walkthrough.final_score),
        )

    def _search_text(self, details: ContainsAnswerDetails) -> str:
        expected = len(details.expected_tokens)
        if details.match_mode != SUBSTRING_MODE:
            return WHOLE_WORDS_SEARCH.format(expected=expected, positions=positions_text(details))
        if details.character_position is None:
            outcome = SUBSTRING_MISSING_OUTCOME
        else:
            outcome = SUBSTRING_FOUND_OUTCOME.format(position=details.character_position + 1)
        return SUBSTRING_SEARCH.format(characters=len(details.normalization.normalized_expected), outcome=outcome)

    def formula_result(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        details = contains_details(walkthrough)
        if step_index == SLIDE_STEP and details.match_mode == SUBSTRING_MODE:
            if details.character_position is None:
                return highlighted_text(NOT_FOUND_RESULT)
            return highlighted_text(SUBSTRING_FOUND_RESULT.format(position=details.character_position + 1))
        if step_index == SLIDE_STEP:
            if details.found_at is None:
                return highlighted_text(NOT_FOUND_RESULT)
            return highlighted_text(FOUND_RESULT.format(position=details.found_at + 1))
        if step_index == SCORE_STEP:
            return SCORE_RESULT.format(score=highlighted_text(score_text(walkthrough.final_score)))
        return ""

    def paint(self, painter: QPainter, area: QRectF, walkthrough: MetricWalkthrough, position: TimelinePosition) -> None:
        details = contains_details(walkthrough)
        layout = self._layouts.get(walkthrough, area)
        if isinstance(layout, SubstringLayout):
            self._paint_substring(painter, area, layout, walkthrough, details, position)
            return
        state = self._window_state(layout, position)
        painter.save()
        painter.setClipRect(area)
        draw_caption(painter, layout.window_caption, WINDOW_CAPTION)
        draw_caption(painter, layout.answer_caption, ANSWER_CAPTION)
        self._paint_answer_row(painter, layout, details, state, position)
        self._paint_window(painter, layout, details, state, position)
        self._paint_track(painter, layout, details, state)
        paint_note(painter, layout.note_rect, layout.note, self._note_opacity(position))
        self._paint_verdict(painter, layout, walkthrough, position)
        painter.restore()

    def _paint_substring(self, painter: QPainter, area: QRectF, layout: SubstringLayout, walkthrough: MetricWalkthrough, details: ContainsAnswerDetails, position: TimelinePosition) -> None:
        normalization = details.normalization
        appear = 1.0 if position.step_index > NORMALIZE_STEP else position.step_progress
        painter.save()
        painter.setClipRect(area)
        draw_caption(painter, layout.expected_caption, SUBSTRING_EXPECTED_CAPTION)
        draw_caption(painter, layout.answer_caption, SUBSTRING_ANSWER_CAPTION)
        scanned = self._scanned_characters(details, position)
        painter.setOpacity(painter.opacity() * max(appear, 0.0))
        self._paint_text_card(painter, layout, layout.expected_card, normalization.normalized_expected, None, None)
        highlight = self._match_range(details)
        self._paint_text_card(painter, layout, layout.answer_card, normalization.normalized_answer, highlight, scanned)
        painter.setOpacity(1.0)
        paint_note(painter, layout.note_rect, layout.note, self._note_opacity(position))
        self._paint_verdict(painter, layout, walkthrough, position)
        painter.restore()

    def _match_range(self, details: ContainsAnswerDetails) -> tuple[int, int] | None:
        if details.character_position is None:
            return None
        return details.character_position, details.character_position + len(details.normalization.normalized_expected)

    def _scanned_characters(self, details: ContainsAnswerDetails, position: TimelinePosition) -> float | None:
        if position.step_index < SLIDE_STEP:
            return None
        match_range = self._match_range(details)
        target = match_range[1] if match_range else len(details.normalization.normalized_answer)
        if position.step_index > SLIDE_STEP:
            return float(target)
        return segment_progress(position.step_progress, 0.0, SLIDE_END) * target

    def _character_rect(self, layout: SubstringLayout, card: QRectF, index: int) -> QRectF:
        line, column = divmod(index, layout.characters_per_line)
        left = card.left() + SUBSTRING_CARD_PADDING + column * layout.advance
        top = card.top() + SUBSTRING_CARD_PADDING + line * layout.line_height
        return QRectF(left, top, layout.advance, layout.line_height)

    def _paint_text_card(self, painter: QPainter, layout: SubstringLayout, card: QRectF, text: str, highlight: tuple[int, int] | None, scanned: float | None) -> None:
        draw_card(painter, card, SURFACE_COLOR, None, SUBSTRING_CARD_RADIUS)
        if not text:
            draw_text(painter, card.adjusted(SUBSTRING_CARD_PADDING, 0, 0, 0), EMPTY_TEXT, DISABLED_TEXT_COLOR, text_font(layout.text_size), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            return
        font = monospace_font(layout.text_size, QFont.Weight.Normal)
        for index, character in enumerate(text):
            rect = self._character_rect(layout, card, index)
            self._paint_character_background(painter, rect, index, highlight, scanned)
            draw_text(painter, rect, character, TEXT_COLOR, font, Qt.AlignmentFlag.AlignCenter)
        self._paint_scan_cursor(painter, layout, card, text, scanned)

    def _paint_character_background(self, painter: QPainter, rect: QRectF, index: int, highlight: tuple[int, int] | None, scanned: float | None) -> None:
        if scanned is None or index >= scanned:
            return
        is_match = highlight is not None and highlight[0] <= index < highlight[1]
        color, alpha = (SUCCESS_COLOR, SUBSTRING_HIGHLIGHT_ALPHA) if is_match else (PRIMARY_COLOR, SUBSTRING_SCAN_ALPHA)
        draw_card(painter, rect, with_alpha(color, alpha), None, 0.0)

    def _paint_scan_cursor(self, painter: QPainter, layout: SubstringLayout, card: QRectF, text: str, scanned: float | None) -> None:
        if scanned is None or scanned >= len(text) or scanned <= 0:
            return
        rect = self._character_rect(layout, card, int(scanned))
        draw_card(painter, QRectF(rect.left(), rect.bottom() - SCAN_CURSOR_HEIGHT, rect.width(), SCAN_CURSOR_HEIGHT), PRIMARY_COLOR, None, SCAN_CURSOR_HEIGHT / 2)

    def _window_state(self, layout: ContainsAnswerLayout, position: TimelinePosition) -> WindowState:
        if not layout.slots:
            return WindowState(0.0, None, 0.0)
        first = layout.slots[0]
        if position.step_index < SLIDE_STEP:
            return WindowState(float(first.answer_start), None, 0.0)
        progress = 1.0 if position.step_index > SLIDE_STEP else position.step_progress
        for order, slot in enumerate(layout.slots):
            if progress < slot.end or order == len(layout.slots) - 1:
                return self._slot_state(layout, order, progress)
        return WindowState(float(first.answer_start), first, 0.0)

    def _slot_state(self, layout: ContainsAnswerLayout, order: int, progress: float) -> WindowState:
        slot = layout.slots[order]
        previous_start = layout.slots[order - 1].answer_start if order > 0 else slot.answer_start
        move = ease_in_out(segment_progress(progress, slot.start, slot.move_end)) if slot.move_end > slot.start else 1.0
        offset = lerp(previous_start, slot.answer_start, move)
        checks = segment_progress(progress, slot.move_end, slot.end) * slot.check_count if slot.end > slot.move_end else float(slot.check_count)
        return WindowState(offset, slot, checks)

    def _column_left(self, layout: ContainsAnswerLayout, column: float) -> float:
        return layout.left + column * (layout.cell_width + CELL_GAP)

    def _cell(self, layout: ContainsAnswerLayout, column: float, top: float) -> QRectF:
        return QRectF(self._column_left(layout, column), top, layout.cell_width, CELL_HEIGHT)

    def _appear(self, position: TimelinePosition, index: int, total: int) -> float:
        if position.step_index != NORMALIZE_STEP:
            return 1.0
        return staggered(position.step_progress, index, total, CHIP_APPEAR_SHARE)

    def _check_result(self, details: ContainsAnswerDetails, state: WindowState, offset: int) -> tuple[float, bool]:
        if state.slot is None:
            return 0.0, False
        shown = clamp_unit(state.checks_shown - offset)
        answer_index = state.slot.answer_start + offset
        return shown, details.answer_tokens[answer_index] == details.expected_tokens[offset]

    def _checked_style(self, shown: float, is_equal: bool, idle: ChipState) -> ChipStyle:
        return blend_styles(idle, ChipState.SUCCESS if is_equal else ChipState.FAILURE, shown)

    def _paint_window(self, painter: QPainter, layout: ContainsAnswerLayout, details: ContainsAnswerDetails, state: WindowState, position: TimelinePosition) -> None:
        count = len(details.expected_tokens)
        if count == 0:
            return
        total = count + len(details.answer_tokens)
        frame_left = self._column_left(layout, state.offset) - WINDOW_FRAME_INSET
        frame_width = count * (layout.cell_width + CELL_GAP) - CELL_GAP + 2 * WINDOW_FRAME_INSET
        frame = QRectF(frame_left, layout.window_top - WINDOW_FRAME_INSET, frame_width, CELL_HEIGHT + 2 * WINDOW_FRAME_INSET)
        painter.save()
        painter.setOpacity(painter.opacity() * self._appear(position, 0, total))
        draw_card(painter, frame, with_alpha(PRIMARY_COLOR, WINDOW_FRAME_FILL_ALPHA), with_alpha(PRIMARY_COLOR, WINDOW_FRAME_BORDER_ALPHA), WINDOW_FRAME_RADIUS)
        painter.restore()
        for offset, token in enumerate(details.expected_tokens):
            shown, is_equal = self._check_result(details, state, offset)
            style = self._checked_style(shown, is_equal, ChipState.NEUTRAL)
            paint_chip(painter, self._cell(layout, state.offset + offset, layout.window_top), token, style, layout.metrics, self._appear(position, offset, total))
            self._paint_check(painter, layout, state.offset + offset, shown, is_equal)

    def _paint_check(self, painter: QPainter, layout: ContainsAnswerLayout, column: float, shown: float, is_equal: bool) -> None:
        if shown <= 0:
            return
        rect = QRectF(self._column_left(layout, column), layout.checks_top, layout.cell_width, CHECK_ROW_HEIGHT)
        painter.save()
        painter.setOpacity(painter.opacity() * shown)
        draw_text(painter, rect, EQUAL_SIGN if is_equal else DIFFERENT_SIGN, SUCCESS_COLOR if is_equal else WARNING_COLOR, monospace_font(CHECK_SIZE), Qt.AlignmentFlag.AlignCenter)
        painter.restore()

    def _paint_answer_row(self, painter: QPainter, layout: ContainsAnswerLayout, details: ContainsAnswerDetails, state: WindowState, position: TimelinePosition) -> None:
        expected_count = len(details.expected_tokens)
        total = expected_count + len(details.answer_tokens)
        if not details.answer_tokens:
            width = max(1, expected_count) * (layout.cell_width + CELL_GAP) - CELL_GAP
            paint_empty_slot(painter, QRectF(layout.left, layout.answer_top, width, CELL_HEIGHT), layout.metrics)
            return
        for index, token in enumerate(details.answer_tokens):
            style = self._answer_style(details, state, index, position)
            paint_chip(painter, self._cell(layout, index, layout.answer_top), token, style, layout.metrics, self._appear(position, expected_count + index, total))
        self._paint_overhang(painter, layout, details, position)

    def _answer_style(self, details: ContainsAnswerDetails, state: WindowState, index: int, position: TimelinePosition) -> ChipStyle:
        idle = ChipState.NEUTRAL if position.step_index == NORMALIZE_STEP else ChipState.DIMMED
        if state.slot is None:
            return chip_style(idle)
        offset = index - state.slot.answer_start
        if not 0 <= offset < len(details.expected_tokens):
            return chip_style(idle)
        shown, is_equal = self._check_result(details, state, offset)
        return self._checked_style(shown, is_equal, idle)

    def _paint_overhang(self, painter: QPainter, layout: ContainsAnswerLayout, details: ContainsAnswerDetails, position: TimelinePosition) -> None:
        if details.window_positions or position.step_index < SLIDE_STEP:
            return
        emphasis = pulse(position.step_progress, OVERHANG_PULSE_CYCLES) if position.step_index == SLIDE_STEP else 0.0
        for column in range(len(details.answer_tokens), len(details.expected_tokens)):
            rect = self._cell(layout, column, layout.answer_top)
            draw_card(painter, rect, with_alpha(WARNING_COLOR, OVERHANG_BASE_ALPHA + OVERHANG_PULSE_ALPHA * emphasis), None, CHIP_RADIUS)
            paint_empty_slot(painter, rect, layout.metrics, "", WARNING_COLOR)

    def _paint_track(self, painter: QPainter, layout: ContainsAnswerLayout, details: ContainsAnswerDetails, state: WindowState) -> None:
        track = layout.track
        draw_card(painter, track, SURFACE_COLOR, None, TRACK_HEIGHT / 2)
        count = len(details.expected_tokens)
        if count == 0 or not details.answer_tokens:
            return
        pill_left = self._column_left(layout, state.offset)
        pill_right = min(track.right(), pill_left + count * (layout.cell_width + CELL_GAP) - CELL_GAP)
        pill = QRectF(pill_left, track.center().y() - TRACK_PILL_HEIGHT / 2, max(TRACK_PILL_HEIGHT, pill_right - pill_left), TRACK_PILL_HEIGHT)
        color = WARNING_COLOR if not details.window_positions else PRIMARY_COLOR
        draw_card(painter, pill, color, None, TRACK_PILL_HEIGHT / 2)

    def _note_opacity(self, position: TimelinePosition) -> float:
        if position.step_index < SLIDE_STEP:
            return 0.0
        if position.step_index > SLIDE_STEP:
            return 1.0
        return segment_progress(position.step_progress, NOTE_START, 1.0)

    def _paint_verdict(self, painter: QPainter, layout: ContainsAnswerLayout | SubstringLayout, walkthrough: MetricWalkthrough, position: TimelinePosition) -> None:
        if position.step_index < SCORE_STEP:
            return
        details = contains_details(walkthrough)
        appear = segment_progress(position.step_progress, 0.0, VERDICT_APPEAR_END)
        message = verdict_message(details, walkthrough.final_score)
        paint_verdict(painter, layout.verdict, is_found(details, walkthrough.final_score), message, VERDICT_SCORE_FORMAT.format(walkthrough.final_score), appear)
