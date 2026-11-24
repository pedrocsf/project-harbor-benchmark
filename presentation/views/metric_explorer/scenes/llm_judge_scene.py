import html
from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QFont, QPainter, QPainterPath, QPen

from domain.explanations.metric_walkthrough import MetricWalkthrough
from domain.explanations.timeline import TimelinePosition
from domain.explanations.walkthrough_details import LlmJudgeDetails
from domain.scoring.llm_judge_scoring_method import find_rating
from presentation.views.branding import (
    BORDER_COLOR,
    DISABLED_TEXT_COLOR,
    ERROR_COLOR,
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
    draw_arrow,
    draw_caption,
    draw_text,
    ease_in_out,
    ease_out_cubic,
    lerp,
    mix_colors,
    monospace_font,
    segment_progress,
    text_font,
    to_color,
    with_alpha,
)
from presentation.views.metric_explorer.scenes.base_scene import SceneStep, WalkthroughScene
from presentation.views.metric_explorer.scenes.semantic_scene_painting import (
    draw_dashed_line,
    draw_dot,
    draw_line,
    draw_outlined_card,
    elide_text,
    faded,
    fitted_area,
    is_active_step,
    largest_fitting_font,
    step_phase,
    text_width,
    wave,
    wrap_text,
)

PROMPT_STEP = 0
ASK_STEP = 1
READ_STEP = 2
DIVIDE_STEP = 3
SHORTCUT_FORMULA_LINE = 2
SHORTCUT_HIGHLIGHTED_STEPS = (ASK_STEP, READ_STEP, DIVIDE_STEP)
SCORE_FORMAT = "{:.1f}"
STEPS = (
    SceneStep(
        "Build the prompt",
        "The expected and the given answers go into a fixed grading prompt, without the question.",
        4.5,
        (),
    ),
    SceneStep(
        "Ask the model",
        "The prompt goes to the same endpoint used for the run. In this demo the reply is a fixed sample.",
        3.5,
        (0,),
    ),
    SceneStep(
        "Read the integer",
        "The first integer from 0 to {maximum} in the reply is the rating: {rating}. A reply without one is an error.",
        3.5,
        (0,),
    ),
    SceneStep(
        "Divide by the scale",
        "{rating} / {maximum} = {score}: the rating becomes a score between 0 and 1.",
        3.0,
        (1,),
    ),
)
SHORTCUT_BODIES = (
    "The given answer is empty, so there is nothing worth grading.",
    "An empty answer is never sent: the model is not called at all.",
    "There is no reply to read, so the rating is 0.",
    "An empty answer scores 0 without calling the model.",
)
FORMULA_FORMAT = (
    "rating = LLM(prompt) ∈ 0…{maximum}",
    "score = rating / {maximum}",
    "empty answer → 0, no model call",
)
SAMPLES_FORMULA_FORMAT = "score = (rating₁ + … + rating{samples}) / ({samples} × {maximum})"
DEFAULT_MAXIMUM = 10
PARAMETERS_HINT = " Change the scale, samples and prompt with “Parameters…”."
SAMPLES_BODY = " The {samples} ratings are averaged."
SAMPLES_RESULT_SUFFIX = " (mean of {samples} samples)"
SAMPLES_ASK_NOTE = " It is asked {samples} times."
LIMITATION = (
    "Judges meaning like a person would, but costs a model call per answer and can vary between runs. "
    "Demo ratings are fixed samples."
)
RATING_RESULT_FORMAT = "rating = {rating}"
SCORE_RESULT_FORMAT = "score = {rating} / {maximum} = {score}"
SHORTCUT_RATING_RESULT = "empty answer → rating 0, no model call"
SHORTCUT_SCORE_RESULT = "empty answer → score = 0"

DESIGN_MINIMUM_WIDTH = 460.0
DESIGN_MINIMUM_HEIGHT = 380.0
TOP_ROW_GAP = 14.0
PROMPT_WIDTH_RATIO = 0.56
PROMPT_PADDING = 12.0
PROMPT_RADIUS = 10.0
PROMPT_HEADER_HEIGHT = 20.0
PROMPT_TEXT_SIZE = 12
PROMPT_LINE_HEIGHT = 18.0
PROMPT_GAP_HEIGHT = 6.0
PROMPT_LINE_OPTIONS = ((2, 3), (2, 2), (1, 2), (1, 1))
PROMPT_HIGHLIGHT_PADDING = 3.0
PROMPT_HIGHLIGHT_ALPHA = 0.16
PROMPT_HIGHLIGHT_RADIUS = 5.0
PROMPT_TYPING_END = 0.85
PROMPT_TITLE = "Prompt"
CARET_WIDTH = 6.0
CARET_BLINKS = 7.0
EMPTY_CANDIDATE_TEXT = "(empty answer)"
MODEL_WIDTH_RATIO = 0.25
MODEL_MINIMUM_WIDTH = 104.0
MODEL_MAXIMUM_WIDTH = 150.0
MODEL_HEIGHT = 110.0
MODEL_RADIUS = 14.0
MODEL_TITLE = "Your model"
MODEL_SUBTITLE = "same endpoint as the run"
MODEL_SKIPPED_TEXT = "not called"
MODEL_TITLE_SIZE = 13
MODEL_SUBTITLE_SIZE = 10
MODEL_IDLE_TINT = 0.06
MODEL_ACTIVE_TINT = 0.16
MODEL_DOT_RADIUS = 3.5
MODEL_DOT_SPACING = 12.0
MODEL_DOT_COUNT = 3
MODEL_DOT_DELAY = 0.12
MODEL_DOT_CYCLES = 2.5
MODEL_DOT_IDLE_ALPHA = 0.2
MODEL_DOT_DONE_ALPHA = 0.75
LANE_GAP = 8.0
ENVELOPE_WIDTH = 30.0
ENVELOPE_HEIGHT = 22.0
ENVELOPE_RADIUS = 3.0
ENVELOPE_LINE_WIDTH = 1.5
STOP_MARK_SIZE = 7.0
STOP_TEXT = "not sent"
STOP_TEXT_HEIGHT = 14.0
STOP_TEXT_WIDTH = 70.0
SHORTCUT_TRAVEL_FRACTION = 0.45
REPLY_CAPTION_HEIGHT = 16.0
REPLY_BOX_HEIGHT = 44.0
REPLY_ROW_HEIGHT = REPLY_CAPTION_HEIGHT + 4.0 + REPLY_BOX_HEIGHT
REPLY_BOX_MINIMUM_WIDTH = 56.0
REPLY_BOX_WIDTH_RATIO = 0.36
REPLY_BOX_PADDING = 12.0
REPLY_SIZES = (28, 20, 15, 12)
REPLY_HIGHLIGHT_ALPHA = 0.22
REPLY_RADIUS = 10.0
REPLY_CAPTION = "Reply"
RATING_CAPTION = "Rating"
SCORE_CAPTION = "Score"
NO_REPLY_TEXT = "no reply"
SHORTCUT_CAPTION = "Shortcut"
ROW_ARROW_LENGTH = 22.0
ROW_GAP = 10.0
RATING_CHIP_WIDTH = 52.0
RATING_SIZE = 24
DIVISION_SIZES = (20, 17, 14)
DIVISION_FORMAT = "/ {maximum} ="
SAMPLES_CAPTION_FORMAT = "× {samples} samples, averaged"
SAMPLES_CAPTION_SIZE = 10
SAMPLES_NOTE_HEIGHT = 11.0
SHORTCUT_DIVISION_TEXT = "="
SCORE_SIZES = (30, 24, 20, 16)
PENDING_TEXT = "–"
CARDS_HEIGHT = 70.0
CARDS_GAP = 10.0
CARD_PADDING = 10.0
CARD_RADIUS = 10.0
CARD_TITLE_SIZE = 11
CARD_VALUE_SIZE = 17
CARD_NOTE_SIZE = 10
CARD_LINE_HEIGHT = 16.0
CARD_VALUE_HEIGHT = 24.0
CARD_IDLE_OPACITY = 0.7
SEPARATOR_GAP = 12.0
GHOST_OPACITY = 0.3
SKIPPED_OPACITY = 0.45
HIGHLIGHT_TINT = 0.18


class PromptLineKind(Enum):
    INSTRUCTION = "instruction"
    LABEL = "label"
    REFERENCE = "reference"
    CANDIDATE = "candidate"
    GAP = "gap"


@dataclass(frozen=True)
class PromptLine:
    text: str
    kind: PromptLineKind
    is_placeholder: bool = False

    @property
    def is_answer(self) -> bool:
        return self.kind in (PromptLineKind.REFERENCE, PromptLineKind.CANDIDATE)

    @property
    def height(self) -> float:
        return PROMPT_GAP_HEIGHT if self.kind is PromptLineKind.GAP else PROMPT_LINE_HEIGHT


@dataclass(frozen=True)
class EdgeCard:
    title: str
    value: str
    note: str
    value_color: str


EMPTY_EDGE_CARD = EdgeCard("Empty answer", "0", "the model is not called", TEXT_COLOR)
NO_NUMBER_EDGE_CARD = EdgeCard("Reply without a number", "error", "no score is given", ERROR_COLOR)
DEMO_EDGE_CARD = EdgeCard("In this demo", "fixed", "sample ratings, not live", SECONDARY_TEXT_COLOR)


@dataclass(frozen=True)
class JudgeLayout:
    prompt_card: QRectF
    prompt_lines: tuple[PromptLine, ...]
    model_box: QRectF
    lane_start: QPointF
    lane_end: QPointF
    reply_top: float
    separator_y: float
    cards: tuple[QRectF, ...]
    area: QRectF


@dataclass(frozen=True)
class JudgeFrame:
    walkthrough: MetricWalkthrough
    details: LlmJudgeDetails
    position: TimelinePosition
    layout: JudgeLayout

    @property
    def was_called(self) -> bool:
        return self.details.model_was_called

    def phase(self, step_index: int) -> float:
        return step_phase(self.position, step_index)

    def is_active(self, step_index: int) -> bool:
        return is_active_step(self.position, step_index)


def prompt_font() -> QFont:
    return monospace_font(PROMPT_TEXT_SIZE, QFont.Weight.Normal)


def classify_prompt(prompt: str) -> tuple[PromptLine, ...]:
    answer_kinds = [PromptLineKind.REFERENCE, PromptLineKind.CANDIDATE]
    current: PromptLineKind | None = None
    current_has_text = False
    lines: list[PromptLine] = []
    for raw_line in prompt.split("\n"):
        text = raw_line.strip()
        if not text:
            if current is PromptLineKind.CANDIDATE and not current_has_text:
                lines.append(PromptLine(EMPTY_CANDIDATE_TEXT, current, True))
            current = None
            if lines and lines[-1].kind is not PromptLineKind.GAP:
                lines.append(PromptLine("", PromptLineKind.GAP))
            continue
        if text.endswith(":") and answer_kinds and current is None:
            lines.append(PromptLine(text, PromptLineKind.LABEL))
            current = answer_kinds.pop(0)
            current_has_text = False
            continue
        lines.append(PromptLine(text, current or PromptLineKind.INSTRUCTION))
        current_has_text = current is not None or current_has_text
    return tuple(lines)


_prompt_cache: dict[tuple[str, int, tuple[int, int]], tuple[PromptLine, ...]] = {}
PROMPT_CACHE_LIMIT = 32


def layout_prompt(prompt: str, width: float, line_limits: tuple[int, int]) -> tuple[PromptLine, ...]:
    key = (prompt, round(width), line_limits)
    cached = _prompt_cache.get(key)
    if cached is not None:
        return cached
    instruction_lines, answer_lines = line_limits
    font = prompt_font()
    display: list[PromptLine] = []
    for line in classify_prompt(prompt):
        if line.kind is PromptLineKind.GAP:
            display.append(line)
            continue
        if line.is_answer:
            display.extend(PromptLine(part, line.kind, line.is_placeholder) for part in wrap_text(line.text, font, width, answer_lines))
            continue
        limit = instruction_lines if line.kind is PromptLineKind.INSTRUCTION else 1
        display.extend(PromptLine(part, line.kind) for part in wrap_text(line.text, font, width, limit))
    if len(_prompt_cache) >= PROMPT_CACHE_LIMIT:
        _prompt_cache.clear()
    _prompt_cache[key] = tuple(display)
    return _prompt_cache[key]


def prompt_card_height(lines: tuple[PromptLine, ...]) -> float:
    return PROMPT_PADDING * 2 + PROMPT_HEADER_HEIGHT + sum(line.height for line in lines)


def build_layout(area: QRectF, prompt: str) -> JudgeLayout:
    prompt_width = area.width() * PROMPT_WIDTH_RATIO
    text_width_available = prompt_width - PROMPT_PADDING * 2
    cards_top = area.bottom() - CARDS_HEIGHT
    separator_y = cards_top - SEPARATOR_GAP
    available = separator_y - SEPARATOR_GAP - REPLY_ROW_HEIGHT - TOP_ROW_GAP - area.top()
    lines = layout_prompt(prompt, text_width_available, PROMPT_LINE_OPTIONS[-1])
    for line_limits in PROMPT_LINE_OPTIONS:
        candidate = layout_prompt(prompt, text_width_available, line_limits)
        if prompt_card_height(candidate) <= available:
            lines = candidate
            break
    card_height = min(prompt_card_height(lines), max(0.0, available))
    spare = max(0.0, available - card_height)
    prompt_card = QRectF(area.left(), area.top(), prompt_width, card_height)
    model_width = min(MODEL_MAXIMUM_WIDTH, max(MODEL_MINIMUM_WIDTH, area.width() * MODEL_WIDTH_RATIO))
    model_height = min(MODEL_HEIGHT, card_height)
    model_box = QRectF(area.right() - model_width, prompt_card.center().y() - model_height / 2, model_width, model_height)
    lane_y = model_box.center().y()
    lane_start = QPointF(prompt_card.right() + LANE_GAP, lane_y)
    lane_end = QPointF(model_box.left() - LANE_GAP, lane_y)
    reply_top = prompt_card.bottom() + TOP_ROW_GAP + spare / 2
    card_width = (area.width() - CARDS_GAP * 2) / 3
    cards = tuple(QRectF(area.left() + index * (card_width + CARDS_GAP), cards_top, card_width, CARDS_HEIGHT) for index in range(3))
    return JudgeLayout(prompt_card, lines, model_box, lane_start, lane_end, reply_top, separator_y, cards, area)


def format_score(value: float) -> str:
    return SCORE_FORMAT.format(value)


def rating_span(reply: str, maximum_rating: int) -> tuple[int, int] | None:
    match = find_rating(reply, maximum_rating)
    if match is None:
        return None
    return match.span()


class LlmJudgeScene(WalkthroughScene):
    identifier = "llm_judge"

    @property
    def steps(self) -> tuple[SceneStep, ...]:
        return STEPS

    @property
    def formula(self) -> tuple[str, ...]:
        return tuple(line.format(maximum=DEFAULT_MAXIMUM) for line in FORMULA_FORMAT)

    @property
    def limitation(self) -> str:
        return LIMITATION

    def step_body(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        details = self._details(walkthrough)
        if not details.model_was_called:
            return SHORTCUT_BODIES[step_index]
        body = STEPS[step_index].body.format(
            rating=details.judge_score_out_of_ten,
            maximum=details.maximum_rating,
            score=format_score(walkthrough.final_score),
        )
        if details.samples > 1 and step_index == ASK_STEP:
            body += SAMPLES_ASK_NOTE.format(samples=details.samples)
        if details.samples > 1 and step_index == DIVIDE_STEP:
            body += SAMPLES_BODY.format(samples=details.samples)
        return body

    def formula_for(self, walkthrough: MetricWalkthrough) -> tuple[str, ...]:
        details = self._details(walkthrough)
        lines = tuple(line.format(maximum=details.maximum_rating) for line in FORMULA_FORMAT)
        if details.samples > 1:
            lines = (lines[0], SAMPLES_FORMULA_FORMAT.format(samples=details.samples, maximum=details.maximum_rating), lines[2])
        return lines

    def limitation_for(self, walkthrough: MetricWalkthrough) -> str:
        return LIMITATION + PARAMETERS_HINT

    def formula_lines_for(self, step_index: int, walkthrough: MetricWalkthrough) -> tuple[int, ...]:
        if self._details(walkthrough).model_was_called:
            return STEPS[step_index].formula_lines
        if step_index in SHORTCUT_HIGHLIGHTED_STEPS:
            return (SHORTCUT_FORMULA_LINE,)
        return ()

    def formula_result(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        details = self._details(walkthrough)
        if step_index == READ_STEP:
            text = RATING_RESULT_FORMAT.format(rating=details.judge_score_out_of_ten) if details.model_was_called else SHORTCUT_RATING_RESULT
            return html.escape(text)
        if step_index == DIVIDE_STEP:
            if not details.model_was_called:
                return html.escape(SHORTCUT_SCORE_RESULT)
            return html.escape(
                SCORE_RESULT_FORMAT.format(
                    rating=details.judge_score_out_of_ten,
                    maximum=details.maximum_rating,
                    score=format_score(walkthrough.final_score),
                )
                + (SAMPLES_RESULT_SUFFIX.format(samples=details.samples) if details.samples > 1 else "")
            )
        return ""

    def paint(self, painter: QPainter, area: QRectF, walkthrough: MetricWalkthrough, position: TimelinePosition) -> None:
        if area.width() <= 0 or area.height() <= 0:
            return
        details = self._details(walkthrough)
        with fitted_area(painter, area, DESIGN_MINIMUM_WIDTH, DESIGN_MINIMUM_HEIGHT) as logical_area:
            frame = JudgeFrame(walkthrough, details, position, build_layout(logical_area, details.prompt_preview))
            self._paint_prompt(painter, frame)
            self._paint_request(painter, frame)
            self._paint_model(painter, frame)
            self._paint_reply_row(painter, frame)
            self._paint_edge_cards(painter, frame)

    def _details(self, walkthrough: MetricWalkthrough) -> LlmJudgeDetails:
        if not isinstance(walkthrough.details, LlmJudgeDetails):
            raise TypeError(f"The LLM judge needs judge details, got {type(walkthrough.details).__name__}.")
        return walkthrough.details

    def _paint_prompt(self, painter: QPainter, frame: JudgeFrame) -> None:
        layout = frame.layout
        card = layout.prompt_card
        if card.height() <= 0:
            return
        draw_outlined_card(painter, card, SURFACE_COLOR, BORDER_COLOR, PROMPT_RADIUS)
        inner = card.adjusted(PROMPT_PADDING, PROMPT_PADDING, -PROMPT_PADDING, -PROMPT_PADDING)
        draw_caption(painter, QRectF(inner.left(), inner.top(), inner.width(), PROMPT_HEADER_HEIGHT - 6), PROMPT_TITLE)
        progress = frame.phase(PROMPT_STEP)
        typed = ease_in_out(segment_progress(progress, 0.0, PROMPT_TYPING_END))
        placed = self._placed_prompt_lines(layout.prompt_lines, inner)
        total = sum(len(line.text) for line, _ in placed)
        revealed = round(total * typed)
        visible_texts = []
        for line, _ in placed:
            visible_texts.append(line.text[: max(0, revealed)])
            revealed -= len(line.text)
        self._paint_answer_blocks(painter, placed, visible_texts, inner, progress)
        font = prompt_font()
        caret_drawn = False
        for (line, rect), visible in zip(placed, visible_texts):
            if line.kind is PromptLineKind.GAP:
                continue
            draw_text(painter, rect, visible, self._prompt_line_color(line), font)
            if not caret_drawn and len(visible) < len(line.text) and frame.is_active(PROMPT_STEP):
                self._paint_caret(painter, rect, visible, font, progress)
                caret_drawn = True

    def _placed_prompt_lines(self, lines: tuple[PromptLine, ...], inner: QRectF) -> list[tuple[PromptLine, QRectF]]:
        placed = []
        top = inner.top() + PROMPT_HEADER_HEIGHT
        for line in lines:
            if top + line.height > inner.bottom() + 1:
                break
            placed.append((line, QRectF(inner.left(), top, inner.width(), line.height)))
            top += line.height
        return placed

    def _paint_answer_blocks(
        self,
        painter: QPainter,
        placed: list[tuple[PromptLine, QRectF]],
        visible_texts: list[str],
        inner: QRectF,
        progress: float,
    ) -> None:
        weight = segment_progress(progress, 0.55, 1.0)
        for kind in (PromptLineKind.REFERENCE, PromptLineKind.CANDIDATE):
            rows = [(line, rect) for (line, rect), visible in zip(placed, visible_texts) if line.kind is kind and visible]
            if not rows:
                continue
            accent = WARNING_COLOR if kind is PromptLineKind.CANDIDATE else PRIMARY_COLOR
            block = QRectF(inner.left() - PROMPT_HIGHLIGHT_PADDING * 2, rows[0][1].top(), inner.width() + PROMPT_HIGHLIGHT_PADDING * 4, rows[-1][1].bottom() - rows[0][1].top())
            fill = with_alpha(accent, lerp(PROMPT_HIGHLIGHT_ALPHA * 0.4, PROMPT_HIGHLIGHT_ALPHA, weight))
            draw_outlined_card(painter, block, fill, with_alpha(accent, weight), PROMPT_HIGHLIGHT_RADIUS, rows[0][0].is_placeholder)

    def _prompt_line_color(self, line: PromptLine) -> str:
        if line.is_placeholder:
            return WARNING_COLOR
        if line.is_answer:
            return TEXT_COLOR
        if line.kind is PromptLineKind.LABEL:
            return DISABLED_TEXT_COLOR
        return SECONDARY_TEXT_COLOR

    def _paint_caret(self, painter: QPainter, rect: QRectF, visible: str, font: QFont, progress: float) -> None:
        if wave(progress, CARET_BLINKS) < 0.35:
            return
        left = rect.left() + text_width(visible, font) + 1
        caret = QRectF(left, rect.top() + 3, CARET_WIDTH, rect.height() - 6)
        painter.fillRect(caret, with_alpha(PRIMARY_HOVER_COLOR, 0.85))

    def _paint_request(self, painter: QPainter, frame: JudgeFrame) -> None:
        layout = frame.layout
        if layout.lane_end.x() - layout.lane_start.x() < ENVELOPE_WIDTH:
            return
        draw_dashed_line(painter, layout.lane_start, layout.lane_end, STRONG_BORDER_COLOR)
        progress = frame.phase(ASK_STEP)
        if progress <= 0:
            return
        if frame.was_called:
            self._paint_sent_envelope(painter, layout, progress)
            return
        self._paint_blocked_envelope(painter, layout, progress)

    def _paint_sent_envelope(self, painter: QPainter, layout: JudgeLayout, progress: float) -> None:
        travel = ease_in_out(segment_progress(progress, 0.0, 0.45))
        opacity = segment_progress(progress, 0.0, 0.08) * (1 - segment_progress(progress, 0.4, 0.5))
        if opacity <= 0:
            return
        center_x = lerp(layout.lane_start.x() + ENVELOPE_WIDTH / 2, layout.lane_end.x(), travel)
        with faded(painter, opacity):
            self._paint_envelope(painter, QPointF(center_x, layout.lane_start.y()), PRIMARY_COLOR)

    def _paint_blocked_envelope(self, painter: QPainter, layout: JudgeLayout, progress: float) -> None:
        travel = ease_out_cubic(segment_progress(progress, 0.0, 0.4))
        lane_length = layout.lane_end.x() - layout.lane_start.x()
        start_x = layout.lane_start.x() + ENVELOPE_WIDTH / 2
        center = QPointF(lerp(start_x, layout.lane_start.x() + lane_length * SHORTCUT_TRAVEL_FRACTION, travel), layout.lane_start.y())
        with faded(painter, segment_progress(progress, 0.0, 0.1)):
            self._paint_envelope(painter, center, WARNING_COLOR)
        stop = ease_out_cubic(segment_progress(progress, 0.4, 0.65))
        if stop <= 0:
            return
        mark_center = QPointF(center.x() + ENVELOPE_WIDTH / 2 + STOP_MARK_SIZE + 2, center.y())
        with faded(painter, stop):
            self._paint_stop_mark(painter, mark_center)
            text_rect = QRectF(center.x() - STOP_TEXT_WIDTH / 2, center.y() + ENVELOPE_HEIGHT / 2 + 4, STOP_TEXT_WIDTH, STOP_TEXT_HEIGHT)
            draw_text(painter, text_rect, STOP_TEXT, WARNING_COLOR, text_font(CARD_NOTE_SIZE, QFont.Weight.DemiBold), Qt.AlignmentFlag.AlignCenter)

    def _paint_envelope(self, painter: QPainter, center: QPointF, color: str) -> None:
        body = QRectF(center.x() - ENVELOPE_WIDTH / 2, center.y() - ENVELOPE_HEIGHT / 2, ENVELOPE_WIDTH, ENVELOPE_HEIGHT)
        draw_outlined_card(painter, body, SURFACE_COLOR, color, ENVELOPE_RADIUS)
        flap = QPainterPath(QPointF(body.left() + 2, body.top() + 3))
        flap.lineTo(QPointF(body.center().x(), body.center().y() + 1))
        flap.lineTo(QPointF(body.right() - 2, body.top() + 3))
        painter.save()
        painter.setPen(QPen(to_color(color), ENVELOPE_LINE_WIDTH, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(flap)
        painter.restore()

    def _paint_stop_mark(self, painter: QPainter, center: QPointF) -> None:
        size = STOP_MARK_SIZE / 2
        draw_line(painter, QPointF(center.x() - size, center.y() - size), QPointF(center.x() + size, center.y() + size), WARNING_COLOR, 2.0)
        draw_line(painter, QPointF(center.x() - size, center.y() + size), QPointF(center.x() + size, center.y() - size), WARNING_COLOR, 2.0)

    def _paint_model(self, painter: QPainter, frame: JudgeFrame) -> None:
        box = frame.layout.model_box
        if box.height() <= 0:
            return
        progress = frame.phase(ASK_STEP)
        skipped = not frame.was_called and progress > 0
        opacity = lerp(1.0, SKIPPED_OPACITY, segment_progress(progress, 0.4, 0.7)) if not frame.was_called else 1.0
        arrival = segment_progress(progress, 0.4, 0.55) if frame.was_called else 0.0
        with faded(painter, opacity):
            tint = lerp(MODEL_IDLE_TINT, MODEL_ACTIVE_TINT, arrival)
            border = mix_colors(STRONG_BORDER_COLOR, PRIMARY_COLOR, max(arrival, 0.0 if skipped else GHOST_OPACITY))
            draw_outlined_card(painter, box, with_alpha(PRIMARY_COLOR, tint), border, MODEL_RADIUS)
            title_rect = QRectF(box.left(), box.center().y() - 30, box.width(), 18)
            draw_text(painter, title_rect, MODEL_TITLE, TEXT_COLOR, text_font(MODEL_TITLE_SIZE, QFont.Weight.DemiBold), Qt.AlignmentFlag.AlignCenter)
            subtitle_font = text_font(MODEL_SUBTITLE_SIZE)
            subtitle_rect = QRectF(box.left() + 6, title_rect.bottom() + 2, box.width() - 12, 14)
            draw_text(painter, subtitle_rect, elide_text(MODEL_SUBTITLE, subtitle_font, subtitle_rect.width()), SECONDARY_TEXT_COLOR, subtitle_font, Qt.AlignmentFlag.AlignCenter)
        dots_center = QPointF(box.center().x(), subtitle_rect.bottom() + 16)
        if skipped:
            with faded(painter, segment_progress(progress, 0.5, 0.8)):
                text_rect = QRectF(box.left(), dots_center.y() - 8, box.width(), 16)
                draw_text(painter, text_rect, MODEL_SKIPPED_TEXT, WARNING_COLOR, text_font(MODEL_SUBTITLE_SIZE, QFont.Weight.DemiBold), Qt.AlignmentFlag.AlignCenter)
            return
        self._paint_thinking_dots(painter, frame, dots_center)

    def _paint_thinking_dots(self, painter: QPainter, frame: JudgeFrame, center: QPointF) -> None:
        progress = frame.phase(ASK_STEP)
        thinking = segment_progress(progress, 0.45, 1.0)
        for index in range(MODEL_DOT_COUNT):
            offset = (index - (MODEL_DOT_COUNT - 1) / 2) * MODEL_DOT_SPACING
            alpha = self._dot_alpha(frame, thinking, index)
            draw_dot(painter, QPointF(center.x() + offset, center.y()), MODEL_DOT_RADIUS, with_alpha(PRIMARY_HOVER_COLOR, alpha))

    def _dot_alpha(self, frame: JudgeFrame, thinking: float, index: int) -> float:
        if thinking >= 1 or frame.position.step_index > ASK_STEP:
            return MODEL_DOT_DONE_ALPHA
        if thinking <= 0:
            return MODEL_DOT_IDLE_ALPHA
        local = clamp_unit(thinking - index * MODEL_DOT_DELAY)
        return lerp(MODEL_DOT_IDLE_ALPHA, 1.0, wave(local, MODEL_DOT_CYCLES))

    def _paint_reply_row(self, painter: QPainter, frame: JudgeFrame) -> None:
        layout = frame.layout
        area = layout.area
        caption_top = layout.reply_top
        box_top = caption_top + REPLY_CAPTION_HEIGHT + 4
        read = frame.phase(READ_STEP)
        divide = frame.phase(DIVIDE_STEP)
        reply_text = frame.details.raw_reply if frame.was_called else NO_REPLY_TEXT
        reply_box = self._reply_box(area, box_top, reply_text)
        self._paint_return_link(painter, frame, reply_box, read)
        left_caption = REPLY_CAPTION if frame.was_called else SHORTCUT_CAPTION
        draw_caption(painter, QRectF(reply_box.left(), caption_top, reply_box.width() + RATING_CHIP_WIDTH, REPLY_CAPTION_HEIGHT), left_caption, SECONDARY_TEXT_COLOR if read > 0 else DISABLED_TEXT_COLOR)
        reveal = ease_out_cubic(segment_progress(read, 0.3, 0.55))
        self._paint_reply_box(painter, frame, reply_box, reply_text, reveal, segment_progress(read, 0.55, 0.85))
        arrow_start = QPointF(reply_box.right() + ROW_GAP / 2, reply_box.center().y())
        arrow_end = QPointF(arrow_start.x() + ROW_ARROW_LENGTH, arrow_start.y())
        extracted = ease_out_cubic(segment_progress(read, 0.7, 1.0))
        with faded(painter, lerp(GHOST_OPACITY, 1.0, extracted)):
            draw_arrow(painter, arrow_start, arrow_end, PRIMARY_COLOR if extracted > 0 else BORDER_COLOR)
        chip = QRectF(arrow_end.x() + ROW_GAP / 2, box_top, RATING_CHIP_WIDTH, REPLY_BOX_HEIGHT)
        draw_caption(painter, QRectF(chip.left(), caption_top, chip.width() + ROW_GAP, REPLY_CAPTION_HEIGHT), RATING_CAPTION, SECONDARY_TEXT_COLOR if extracted > 0 else DISABLED_TEXT_COLOR)
        self._paint_rating_chip(painter, frame, chip, extracted)
        self._paint_division(painter, frame, QRectF(chip.right() + ROW_GAP, caption_top, area.right() - chip.right() - ROW_GAP, box_top + REPLY_BOX_HEIGHT - caption_top), divide)

    def _reply_box(self, area: QRectF, top: float, text: str) -> QRectF:
        maximum = area.width() * REPLY_BOX_WIDTH_RATIO
        font = largest_fitting_font(text, REPLY_SIZES, maximum - REPLY_BOX_PADDING * 2, monospace_font)
        width = min(maximum, max(REPLY_BOX_MINIMUM_WIDTH, text_width(text, font) + REPLY_BOX_PADDING * 2))
        return QRectF(area.left(), top, width, REPLY_BOX_HEIGHT)

    def _paint_return_link(self, painter: QPainter, frame: JudgeFrame, reply_box: QRectF, read: float) -> None:
        if not frame.was_called or not frame.is_active(READ_STEP):
            return
        travel = ease_in_out(segment_progress(read, 0.0, 0.4))
        if travel <= 0 or travel >= 1:
            return
        start = QPointF(frame.layout.model_box.center().x(), frame.layout.model_box.bottom())
        end = reply_box.center()
        corner = QPointF(start.x(), end.y())
        route = QPainterPath(start)
        route.cubicTo(corner, corner, end)
        center = route.pointAtPercent(travel)
        with faded(painter, segment_progress(travel, 0.0, 0.15)):
            self._paint_envelope(painter, center, WARNING_COLOR)

    def _paint_reply_box(self, painter: QPainter, frame: JudgeFrame, box: QRectF, text: str, reveal: float, highlight: float) -> None:
        if reveal <= 0:
            with faded(painter, GHOST_OPACITY):
                draw_outlined_card(painter, box, SURFACE_COLOR, BORDER_COLOR, REPLY_RADIUS, True)
            return
        accent = WARNING_COLOR
        inner = box.adjusted(REPLY_BOX_PADDING, 0, -REPLY_BOX_PADDING, 0)
        font = largest_fitting_font(text, REPLY_SIZES, inner.width(), monospace_font)
        shown = elide_text(text, font, inner.width())
        with faded(painter, reveal):
            if not frame.was_called:
                draw_outlined_card(painter, box, SURFACE_COLOR, DISABLED_TEXT_COLOR, REPLY_RADIUS, True)
                draw_text(painter, inner, shown, DISABLED_TEXT_COLOR, text_font(CARD_TITLE_SIZE + 1), Qt.AlignmentFlag.AlignCenter)
                return
            draw_outlined_card(painter, box, SURFACE_COLOR, accent, REPLY_RADIUS)
            span = rating_span(shown, frame.details.maximum_rating)
            if span is not None and highlight > 0:
                self._paint_number_highlight(painter, inner, shown, span, font, highlight)
            draw_text(painter, inner, shown, accent, font, self._reply_alignment(text, font, inner))

    def _reply_alignment(self, text: str, font: QFont, inner: QRectF) -> Qt.AlignmentFlag:
        if text_width(text, font) <= inner.width():
            return Qt.AlignmentFlag.AlignCenter
        return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

    def _paint_number_highlight(self, painter: QPainter, inner: QRectF, shown: str, span: tuple[int, int], font: QFont, weight: float) -> None:
        full_width = text_width(shown, font)
        start_x = inner.left() + max(0.0, (inner.width() - full_width) / 2) if full_width <= inner.width() else inner.left()
        left = start_x + text_width(shown[: span[0]], font)
        width = text_width(shown[span[0] : span[1]], font)
        mark = QRectF(left - 4, inner.top() + 6, width + 8, inner.height() - 12)
        draw_outlined_card(painter, mark, with_alpha(WARNING_COLOR, REPLY_HIGHLIGHT_ALPHA * weight), with_alpha(WARNING_COLOR, weight), 6.0)

    def _paint_rating_chip(self, painter: QPainter, frame: JudgeFrame, chip: QRectF, extracted: float) -> None:
        accent = WARNING_COLOR if not frame.was_called else PRIMARY_COLOR
        fill = mix_colors(SURFACE_COLOR, with_alpha(accent, HIGHLIGHT_TINT), extracted)
        border = mix_colors(BORDER_COLOR, accent, extracted)
        with faded(painter, lerp(GHOST_OPACITY, 1.0, extracted)):
            draw_outlined_card(painter, chip, fill, border, REPLY_RADIUS)
            text = str(frame.details.judge_score_out_of_ten) if extracted > 0 else PENDING_TEXT
            draw_text(painter, chip, text, TEXT_COLOR, monospace_font(RATING_SIZE), Qt.AlignmentFlag.AlignCenter)

    def _paint_division(self, painter: QPainter, frame: JudgeFrame, rect: QRectF, divide: float) -> None:
        if rect.width() <= 0:
            return
        division_text = DIVISION_FORMAT.format(maximum=frame.details.maximum_rating) if frame.was_called else SHORTCUT_DIVISION_TEXT
        score_text = format_score(frame.walkthrough.final_score)
        value_rect = QRectF(rect.left(), rect.bottom() - REPLY_BOX_HEIGHT, rect.width(), REPLY_BOX_HEIGHT)
        division_font = largest_fitting_font(division_text, DIVISION_SIZES, rect.width() * 0.5, monospace_font)
        division_width = text_width(division_text, division_font)
        score_rect = QRectF(value_rect.left() + division_width + ROW_GAP, value_rect.top(), max(0.0, value_rect.width() - division_width - ROW_GAP), REPLY_BOX_HEIGHT)
        draw_caption(painter, QRectF(score_rect.left(), rect.top(), score_rect.width(), REPLY_CAPTION_HEIGHT), SCORE_CAPTION, SECONDARY_TEXT_COLOR if divide > 0 else DISABLED_TEXT_COLOR)
        operator = ease_out_cubic(segment_progress(divide, 0.0, 0.35))
        with faded(painter, lerp(GHOST_OPACITY, 1.0, operator)):
            draw_text(painter, value_rect, division_text, LABEL_TEXT_COLOR, division_font)
        result = ease_out_cubic(segment_progress(divide, 0.3, 0.8))
        score_font = largest_fitting_font(score_text, SCORE_SIZES, score_rect.width(), monospace_font)
        shown = score_text if result > 0 else PENDING_TEXT
        color = mix_colors(DISABLED_TEXT_COLOR, PRIMARY_HOVER_COLOR, result)
        draw_text(painter, score_rect, shown, color, score_font)
        if frame.details.samples > 1 and frame.was_called:
            self._paint_samples_note(painter, frame, QRectF(rect.left(), value_rect.bottom() + 1, rect.width(), SAMPLES_NOTE_HEIGHT), divide)

    def _paint_samples_note(self, painter: QPainter, frame: JudgeFrame, note_rect: QRectF, divide: float) -> None:
        font = text_font(SAMPLES_CAPTION_SIZE)
        text = elide_text(SAMPLES_CAPTION_FORMAT.format(samples=frame.details.samples), font, note_rect.width())
        with faded(painter, lerp(GHOST_OPACITY, 1.0, segment_progress(divide, 0.0, 0.5))):
            draw_text(painter, note_rect, text, SECONDARY_TEXT_COLOR, font)

    def _paint_edge_cards(self, painter: QPainter, frame: JudgeFrame) -> None:
        layout = frame.layout
        area = layout.area
        draw_line(painter, QPointF(area.left(), layout.separator_y), QPointF(area.right(), layout.separator_y), BORDER_COLOR)
        weights = self._edge_weights(frame)
        for rect, card, weight in zip(layout.cards, (EMPTY_EDGE_CARD, NO_NUMBER_EDGE_CARD, DEMO_EDGE_CARD), weights):
            self._paint_edge_card(painter, rect, card, weight)

    def _edge_weights(self, frame: JudgeFrame) -> tuple[float, float, float]:
        if not frame.was_called:
            return ease_out_cubic(segment_progress(frame.phase(ASK_STEP), 0.4, 0.8)), 0.0, 0.0
        return 0.0, ease_out_cubic(segment_progress(frame.phase(READ_STEP), 0.6, 1.0)), 0.0

    def _paint_edge_card(self, painter: QPainter, rect: QRectF, card: EdgeCard, weight: float) -> None:
        with faded(painter, lerp(CARD_IDLE_OPACITY, 1.0, weight)):
            draw_outlined_card(painter, rect, mix_colors(SURFACE_COLOR, with_alpha(PRIMARY_COLOR, HIGHLIGHT_TINT), weight), mix_colors(SURFACE_COLOR, PRIMARY_COLOR, weight), CARD_RADIUS)
            inner = rect.adjusted(CARD_PADDING, CARD_PADDING - 2, -CARD_PADDING, -CARD_PADDING + 2)
            title_font = text_font(CARD_TITLE_SIZE)
            note_font = text_font(CARD_NOTE_SIZE)
            title_rect = QRectF(inner.left(), inner.top(), inner.width(), CARD_LINE_HEIGHT)
            value_rect = QRectF(inner.left(), title_rect.bottom(), inner.width(), CARD_VALUE_HEIGHT)
            note_rect = QRectF(inner.left(), value_rect.bottom(), inner.width(), CARD_LINE_HEIGHT)
            draw_text(painter, title_rect, elide_text(card.title, title_font, inner.width()), SECONDARY_TEXT_COLOR, title_font)
            draw_text(painter, value_rect, card.value, card.value_color, monospace_font(CARD_VALUE_SIZE))
            draw_text(painter, note_rect, elide_text(card.note, note_font, inner.width()), DISABLED_TEXT_COLOR, note_font)
