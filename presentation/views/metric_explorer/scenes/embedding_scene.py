import html
import math
import random
import zlib
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QFont, QPainter, QPainterPath, QPen

from domain.explanations.metric_walkthrough import MetricWalkthrough
from domain.explanations.timeline import TimelinePosition
from domain.explanations.walkthrough_details import EmbeddingDetails
from domain.scoring.vector_similarity import ANGULAR, CLIP, COSINE, DOT_PRODUCT, EUCLIDEAN, MANHATTAN
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
    draw_value,
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
    clipped_to,
    draw_dashed_line,
    draw_dot,
    draw_line,
    draw_outlined_card,
    faded,
    fitted_area,
    is_active_step,
    largest_fitting_font,
    step_phase,
    text_width,
    wave,
    wrap_text,
)

ENCODE_STEP = 0
VECTOR_STEP = 1
ANGLE_STEP = 2
CLIP_STEP = 3
SCORE_FORMAT = "{:.3f}"
ANGLE_FORMAT = "{:.1f}°"
EMBEDDING_DIMENSIONS = 384
STEPS = (
    SceneStep(
        "Encode both answers",
        "A multilingual MiniLM model reads each answer and turns it into a vector of 384 numbers.",
        3.5,
        (),
    ),
    SceneStep(
        "Get one vector each",
        "Each answer becomes one direction in a 384-dimensional space. The bars and arrows only illustrate it.",
        3.5,
        (),
    ),
    SceneStep(
        "Compare the vectors",
        "The answers are about {angle} apart, so cos θ = {cosine}. Directions matter, lengths do not.",
        4.5,
        (0,),
    ),
    SceneStep(
        "Turn it into a score",
        "cos θ = {cosine} is not negative, so the score stays {score}.",
        3.0,
        (1,),
    ),
)
EMPTY_BODIES = (
    "The answer is empty, so only the expected answer has something to encode.",
    "An empty answer has no vector, so there is no direction to compare.",
    "Without a second vector there is no angle to measure.",
    "An empty answer scores 0.",
)
DISTANCE_FUNCTIONS = (EUCLIDEAN, MANHATTAN)
NEGATIVE_HANDLING_FUNCTIONS = (COSINE, DOT_PRODUCT)
SYMBOL_BY_FUNCTION = {COSINE: "cos θ", DOT_PRODUCT: "a · b", ANGULAR: "θ", EUCLIDEAN: "d", MANHATTAN: "d"}
UNIT_LENGTH_NOTE = " (both vectors scaled to length 1)"
FORMULA_BY_FUNCTION = {
    COSINE: "cos θ = (a · b) / (‖a‖ ‖b‖)",
    DOT_PRODUCT: "s = a · b{note}",
    ANGULAR: "θ = arccos[(a · b) / (‖a‖ ‖b‖)]",
    EUCLIDEAN: "d = ‖a − b‖₂{note}",
    MANHATTAN: "d = ‖a − b‖₁{note}",
}
SCORE_FORMULA_BY_FUNCTION = {
    ANGULAR: "score = 1 − θ / π",
    EUCLIDEAN: "score = 1 / (1 + d)",
    MANHATTAN: "score = 1 / (1 + d)",
}
CLIP_SCORE_FORMULA = "score = max(0, {symbol})"
RESCALE_SCORE_FORMULA = "score = ({symbol} + 1) / 2"
FORMULA = (
    "cos θ = (a · b) / (‖a‖ ‖b‖)",
    "score = max(0, cos θ)",
)
LIMITATION = "Catches paraphrases that token metrics miss, but can rate a fluent wrong answer highly."
PARAMETERS_HINT = " Change the similarity function, negative handling and vector scaling with “Parameters…”."
COMPARE_BODIES = {
    COSINE: "The answers are about {angle} apart, so cos θ = {cosine}. Directions matter, lengths do not.",
    ANGULAR: "The answers are about {angle} apart (cos θ = {cosine}). The angle itself will be compared with 180°.",
    DOT_PRODUCT: "With both vectors scaled to length 1, a · b = {raw}, the same as cos θ.",
    EUCLIDEAN: "The straight-line distance between the two points is d = {raw}{note}.",
    MANHATTAN: "Adding up the difference in every dimension gives d = {raw}{note}.",
}
UNSCALED_DOT_BODY = "Without scaling, a · b = {raw}: it depends on the angle and on how long the vectors are."
CLIPPED_BELOW_BODY = "{symbol} = {raw} is negative, so the score is clipped to 0."
CLIPPED_ABOVE_BODY = "{symbol} = {raw} is above 1, so the score is limited to 1."
KEPT_BODY = "{symbol} = {raw} is not negative, so the score stays {score}."
RESCALED_BODY = "({symbol} + 1) / 2 moves the range −1…1 onto 0…1, so the score is {score}."
ANGULAR_SCORE_BODY = "1 − {angle} / 180° = {score}: the smaller the angle, the higher the score."
DISTANCE_SCORE_BODY = "1 / (1 + {raw}) = {score}: no distance scores 1, a large distance tends to 0."
SCORE_EXPRESSIONS = {
    "clip": "max(0, {raw})",
    "rescale": "({raw} + 1) / 2",
    ANGULAR: "1 − {angle} / 180°",
    EUCLIDEAN: "1 / (1 + {raw})",
    MANHATTAN: "1 / (1 + {raw})",
}
RESCALE_KEY = "rescale"
LIMITED_SUFFIX = " → limited to 0…1"
ANGLE_RESULT_FORMAT = "cos θ = cos({angle}) = {cosine}"
VALUE_RESULT_FORMAT = "{symbol} = {raw}"
ANGLE_ONLY_RESULT_FORMAT = "θ = {angle}"
CLIP_RESULT_FORMAT = "score = {expression} = {score}"
EMPTY_ANGLE_RESULT = "empty answer → no vector, no angle"
EMPTY_CLIP_RESULT = "empty answer → score = 0"

DESIGN_MINIMUM_WIDTH = 460.0
DESIGN_MINIMUM_HEIGHT = 360.0
CARD_HEIGHT = 58.0
CARD_GAP = 8.0
CARD_WIDTH_RATIO = 0.36
CARD_RADIUS = 8.0
CARD_PADDING = 10.0
CARD_LABEL_HEIGHT = 14.0
CARD_TEXT_SIZE = 12
CARD_LINE_HEIGHT = 15.0
CARD_MAXIMUM_LINES = 2
CARD_DOT_RADIUS = 3.0
CARD_SLIDE_DISTANCE = 14.0
FLOW_GAP = 6.0
FLOW_ARROW_LENGTH = 24.0
FLOW_DOT_RADIUS = 3.5
ENCODER_WIDTH_RATIO = 0.17
ENCODER_MINIMUM_WIDTH = 76.0
ENCODER_MAXIMUM_WIDTH = 110.0
ENCODER_HEIGHT = 72.0
ENCODER_RADIUS = 10.0
ENCODER_TITLE_SIZE = 12
ENCODER_SUBTITLE_SIZE = 10
ENCODER_IDLE_TINT = 0.06
ENCODER_LIT_TINT = 0.14
ENCODER_GLOW_TINT = 0.16
STRIP_HEIGHT = 30.0
STRIP_LIFT = 4.0
BAR_WIDTH = 6.0
BAR_SPACING = 2.0
BAR_RADIUS = 2.0
BAR_MAXIMUM_COUNT = 20
BAR_MINIMUM_VALUE = 0.15
REAL_BAR_FLOOR = 1e-9
BAR_STAGGER_SPAN = 0.45
BAR_GROW_SPAN = 0.3
BAR_IDLE_SCALE = 0.08
STRIP_CAPTION_SIZE = 10
STRIP_CAPTION_HEIGHT = 12.0
SECTION_GAP = 14.0
PLANE_WIDTH_RATIO = 0.47
COLUMN_GAP = 20.0
ORIGIN_X_RATIO = 0.34
ORIGIN_Y_RATIO = 0.9
PLANE_MARGIN = 12.0
BASE_ANGLE_DEGREES = 12.0
SWEEP_OFFSET_DEGREES = 45.0
MAXIMUM_DRAWN_ANGLE_DEGREES = 168.0
RIGHT_ANGLE_DEGREES = 90.0
STRAIGHT_ANGLE_DEGREES = 180.0
ANSWER_LENGTH_RATIO = 0.9
VECTOR_LINE_WIDTH = 3.0
AXIS_PADDING = 4.0
ARC_RADIUS_RATIO = 0.34
ARC_MINIMUM_RADIUS = 28.0
ARC_LINE_WIDTH = 1.6
ANGLE_LABEL_SIZE = 13
ANGLE_LABEL_GAP = 10.0
INSIDE_LABEL_MINIMUM_DEGREES = 30.0
OUTSIDE_LABEL_OFFSET_DEGREES = 18.0
OUTSIDE_LABEL_RADIUS_RATIO = 0.45
VECTOR_LABEL_SIZE = 11
VECTOR_LABEL_HEIGHT = 14.0
VECTOR_LABEL_WIDTH = 70.0
GHOST_OPACITY = 0.28
DIMMED_OPACITY = 0.5
CLIP_ZONE_ALPHA = 0.14
CLIP_ZONE_TEXT = "{symbol} < 0\n→ score 0"
RESCALE_ZONE_TEXT = "{symbol} < 0\n→ score < 0.5"
CLIP_ZONE_TEXT_HEIGHT = 30.0
CLIP_ZONE_TEXT_HEIGHT_RATIO = 0.55
INTRO_TEXT = "Same meaning points the same way. The smaller the angle, the closer cos θ gets to 1."
DISTANCE_INTRO_TEXT = "Same meaning lands close together. The smaller the distance, the closer the score gets to 1."
INTRO_SIZE = 12
INTRO_LINE_HEIGHT = 17.0
INTRO_MAXIMUM_LINES = 3
ROOMY_COLUMN_HEIGHT = 290.0
VALUE_SIZES = (28, 24, 20, 17)
VALUE_HEIGHT = 38.0
VALUE_TEXT_FORMAT = "{symbol} = {value}"
PENDING_VALUE = "–"
ANGLE_ROW_SIZE = 13
ANGLE_ROW_HEIGHT = 20.0
ANGLE_ROW_FORMAT = "θ ≈ {angle}"
CLIP_CHIPS = ("0° → 1.0", "90° → 0.0", "> 90° → clipped to 0")
RESCALE_CHIPS = ("0° → 1.0", "90° → 0.5", "180° → 0.0")
ANGULAR_CHIPS = ("0° → 1.0", "90° → 0.5", "180° → 0.0")
DISTANCE_CHIPS = ("d = 0 → 1.0", "d = 1 → 0.5", "d → ∞ → 0.0")
HIGH_SCORE_LIMIT = 0.67
MIDDLE_SCORE_LIMIT = 0.25
FAR_ANGLE_LIMIT_DEGREES = 135.0
DISTANCE_ROW_FORMAT = "{norm} distance"
EUCLIDEAN_NORM_NAME = "L2"
MANHATTAN_NORM_NAME = "L1"
PROJECTION_WIDTH = 2.4
POINT_RADIUS = 5.0
STAIRCASE_WIDTH = 2.2
DISTANCE_LABEL_FORMAT = "d = {raw}"
CLOSE_CHIP = 0
RIGHT_ANGLE_CHIP = 1
CLIPPED_CHIP = 2
CLOSE_ANGLE_LIMIT_DEGREES = 45.0
REFERENCE_CHIP_SIZE = 11
REFERENCE_CHIP_HEIGHT = 24.0
REFERENCE_CHIP_PADDING = 8.0
REFERENCE_CHIP_GAP = 6.0
REFERENCE_CHIP_RADIUS = 6.0
HIGHLIGHT_TINT = 0.2
BLOCK_GAP = 10.0
SCORE_CAPTION_HEIGHT = 16.0
SCORE_CARD_HEIGHT = 36.0
SCORE_CARD_PADDING = 10.0
SCORE_SIZES = (18, 15, 13)
SCORE_TEXT_FORMAT = "score = {score}"
EMPTY_SCORE_CAPTION = "empty answer"
NOTE_TEXT = "2D drawing for illustration; the real angle is measured in 384 dimensions."
NOTE_SIZE = 11
NOTE_LINE_HEIGHT = 15.0
NOTE_MAXIMUM_LINES = 2
EMPTY_CARD_TEXT = "(empty answer)"
EMPTY_STRIP_TEXT = "no vector"
EMPTY_VECTOR_TEXT = "no answer vector"
EMPTY_NOTICE_TEXT = "Empty answer → score 0"
EMPTY_NOTICE_HEIGHT = 34.0
STRIP_CAPTION_FORMAT = "{dimensions} numbers each · {count} shown"
EXPECTED_LABEL = "Expected"
ANSWER_LABEL = "Answer"
EXPECTED_VECTOR_LABEL = "expected"
ANSWER_VECTOR_LABEL = "answer"
ENCODER_TITLE = "MiniLM"
ENCODER_SUBTITLE = "encoder"
EXPECTED_COLOR = PRIMARY_COLOR
ANSWER_COLOR = WARNING_COLOR


@dataclass(frozen=True)
class EmbeddingLayout:
    expected_card: QRectF
    answer_card: QRectF
    encoder: QRectF
    first_arrow: tuple[QPointF, QPointF]
    second_arrow: tuple[QPointF, QPointF]
    expected_strip: QRectF
    answer_strip: QRectF
    strip_caption: QRectF
    separator_y: float
    plane: QRectF
    origin: QPointF
    radius: float
    column: QRectF


@dataclass(frozen=True)
class EmbeddingFrame:
    walkthrough: MetricWalkthrough
    details: EmbeddingDetails
    position: TimelinePosition
    layout: EmbeddingLayout

    @property
    def is_empty(self) -> bool:
        return not self.walkthrough.given_answer.strip()

    def phase(self, step_index: int) -> float:
        return step_phase(self.position, step_index)

    def is_active(self, step_index: int) -> bool:
        return is_active_step(self.position, step_index)


_bar_cache: dict[tuple[str, str, int, float], tuple[tuple[float, ...], tuple[float, ...]]] = {}


def _seeded_values(text: str, count: int) -> list[float]:
    generator = random.Random(zlib.crc32(text.encode("utf-8")))
    return [generator.uniform(BAR_MINIMUM_VALUE, 1.0) for _ in range(count)]


def illustrative_bars(expected: str, given: str, count: int, similarity: float) -> tuple[tuple[float, ...], tuple[float, ...]]:
    key = (expected, given, count, similarity)
    cached = _bar_cache.get(key)
    if cached is not None:
        return cached
    expected_values = _seeded_values(expected, count)
    noise = _seeded_values(given, count)
    weight = clamp_unit(similarity)
    answer_values = [lerp(random_value, base, weight) for base, random_value in zip(expected_values, noise)]
    bars = (tuple(expected_values), tuple(answer_values))
    _bar_cache[key] = bars
    return bars


def real_bars(expected: tuple[float, ...], given: tuple[float, ...], count: int) -> tuple[tuple[float, ...], tuple[float, ...]]:
    shown_expected = [abs(value) for value in expected[:count]]
    shown_given = [abs(value) for value in given[:count]]
    largest = max(shown_expected + shown_given + [REAL_BAR_FLOOR])
    return (
        tuple(lerp(BAR_MINIMUM_VALUE, 1.0, value / largest) for value in shown_expected),
        tuple(lerp(BAR_MINIMUM_VALUE, 1.0, value / largest) for value in shown_given),
    )


def build_layout(area: QRectF) -> EmbeddingLayout:
    left, top = area.left(), area.top()
    card_width = area.width() * CARD_WIDTH_RATIO
    expected_card = QRectF(left, top, card_width, CARD_HEIGHT)
    answer_card = QRectF(left, top + CARD_HEIGHT + CARD_GAP, card_width, CARD_HEIGHT)
    flow_y = (expected_card.top() + answer_card.bottom()) / 2
    first_start = QPointF(expected_card.right() + FLOW_GAP, flow_y)
    first_end = QPointF(first_start.x() + FLOW_ARROW_LENGTH, flow_y)
    encoder_width = min(ENCODER_MAXIMUM_WIDTH, max(ENCODER_MINIMUM_WIDTH, area.width() * ENCODER_WIDTH_RATIO))
    encoder = QRectF(first_end.x() + FLOW_GAP, flow_y - ENCODER_HEIGHT / 2, encoder_width, ENCODER_HEIGHT)
    second_start = QPointF(encoder.right() + FLOW_GAP, flow_y)
    second_end = QPointF(second_start.x() + FLOW_ARROW_LENGTH, flow_y)
    strips_left = second_end.x() + FLOW_GAP
    strips_width = max(0.0, area.right() - strips_left)
    expected_strip = QRectF(strips_left, expected_card.center().y() - STRIP_HEIGHT / 2 - STRIP_LIFT, strips_width, STRIP_HEIGHT)
    answer_strip = QRectF(strips_left, answer_card.center().y() - STRIP_HEIGHT / 2 - STRIP_LIFT, strips_width, STRIP_HEIGHT)
    strip_caption = QRectF(strips_left, answer_strip.bottom() + 2, strips_width, STRIP_CAPTION_HEIGHT)
    separator_y = answer_card.bottom() + SECTION_GAP
    bottom_top = separator_y + SECTION_GAP
    bottom_height = max(0.0, area.bottom() - bottom_top)
    plane_width = area.width() * PLANE_WIDTH_RATIO
    side = min(plane_width, bottom_height)
    plane = QRectF(left, bottom_top + (bottom_height - side) / 2, plane_width, side)
    origin = QPointF(plane.left() + plane_width * ORIGIN_X_RATIO, plane.top() + side * ORIGIN_Y_RATIO)
    radius = max(0.0, min(plane.right() - origin.x(), origin.y() - plane.top()) - PLANE_MARGIN)
    column_left = left + plane_width + COLUMN_GAP
    column = QRectF(column_left, bottom_top, max(0.0, area.right() - column_left), bottom_height)
    return EmbeddingLayout(
        expected_card,
        answer_card,
        encoder,
        (first_start, first_end),
        (second_start, second_end),
        expected_strip,
        answer_strip,
        strip_caption,
        separator_y,
        plane,
        origin,
        radius,
        column,
    )


def point_at(origin: QPointF, angle_degrees: float, length: float) -> QPointF:
    radians = math.radians(angle_degrees)
    return QPointF(origin.x() + length * math.cos(radians), origin.y() - length * math.sin(radians))


def length_inside(plane: QRectF, origin: QPointF, angle_degrees: float, desired: float) -> float:
    radians = math.radians(angle_degrees)
    horizontal, vertical = math.cos(radians), -math.sin(radians)
    limits = [desired]
    if horizontal > 0:
        limits.append((plane.right() - PLANE_MARGIN - origin.x()) / horizontal)
    if horizontal < 0:
        limits.append((plane.left() + PLANE_MARGIN - origin.x()) / horizontal)
    if vertical < 0:
        limits.append((plane.top() + PLANE_MARGIN - origin.y()) / vertical)
    return max(0.0, min(limits))


def format_score(value: float) -> str:
    return SCORE_FORMAT.format(value)


def format_angle(value: float) -> str:
    return ANGLE_FORMAT.format(value)


class EmbeddingScene(WalkthroughScene):
    identifier = "embedding"

    @property
    def steps(self) -> tuple[SceneStep, ...]:
        return STEPS

    @property
    def formula(self) -> tuple[str, ...]:
        return FORMULA

    @property
    def limitation(self) -> str:
        return LIMITATION

    def formula_for(self, walkthrough: MetricWalkthrough) -> tuple[str, ...]:
        details = self._details(walkthrough)
        note = UNIT_LENGTH_NOTE if details.normalize_vectors and details.function in (DOT_PRODUCT, EUCLIDEAN, MANHATTAN) else ""
        return (FORMULA_BY_FUNCTION[details.function].format(note=note), self._score_formula(details))

    def limitation_for(self, walkthrough: MetricWalkthrough) -> str:
        return LIMITATION + PARAMETERS_HINT

    def _score_formula(self, details: EmbeddingDetails) -> str:
        if details.function in SCORE_FORMULA_BY_FUNCTION:
            return SCORE_FORMULA_BY_FUNCTION[details.function]
        template = RESCALE_SCORE_FORMULA if details.negative_handling == RESCALE_KEY else CLIP_SCORE_FORMULA
        return template.format(symbol=SYMBOL_BY_FUNCTION[details.function])

    def step_body(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        details = self._details(walkthrough)
        if not walkthrough.given_answer.strip():
            return EMPTY_BODIES[step_index]
        if step_index == ANGLE_STEP:
            return self._compare_body(details)
        if step_index == CLIP_STEP:
            return self._score_body(details, walkthrough.final_score)
        return STEPS[step_index].body

    def _compare_body(self, details: EmbeddingDetails) -> str:
        template = COMPARE_BODIES[details.function]
        if details.function == DOT_PRODUCT and not details.normalize_vectors:
            template = UNSCALED_DOT_BODY
        note = UNIT_LENGTH_NOTE if details.normalize_vectors else ""
        return template.format(
            angle=format_angle(details.angle_degrees),
            cosine=format_score(details.cosine),
            raw=format_score(details.raw_value),
            note=note,
        )

    def _score_body(self, details: EmbeddingDetails, score: float) -> str:
        angle = format_angle(details.angle_degrees)
        raw = format_score(details.raw_value)
        if details.function == ANGULAR:
            return ANGULAR_SCORE_BODY.format(angle=angle, score=format_score(score))
        if details.function in DISTANCE_FUNCTIONS:
            return DISTANCE_SCORE_BODY.format(raw=raw, score=format_score(score))
        symbol = SYMBOL_BY_FUNCTION[details.function]
        if details.negative_handling == RESCALE_KEY:
            return RESCALED_BODY.format(symbol=symbol, score=format_score(score))
        if details.raw_value < 0:
            return CLIPPED_BELOW_BODY.format(symbol=symbol, raw=raw)
        if details.clipped:
            return CLIPPED_ABOVE_BODY.format(symbol=symbol, raw=raw)
        return KEPT_BODY.format(symbol=symbol, raw=raw, score=format_score(score))

    def formula_result(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        details = self._details(walkthrough)
        is_empty = not walkthrough.given_answer.strip()
        if step_index == ANGLE_STEP:
            if is_empty:
                return html.escape(EMPTY_ANGLE_RESULT)
            return html.escape(self._compare_result(details))
        if step_index == CLIP_STEP:
            if is_empty:
                return html.escape(EMPTY_CLIP_RESULT)
            return html.escape(self._score_result(details, walkthrough.final_score))
        return ""

    def _compare_result(self, details: EmbeddingDetails) -> str:
        angle = format_angle(details.angle_degrees)
        if details.function == COSINE:
            return ANGLE_RESULT_FORMAT.format(angle=angle, cosine=format_score(details.cosine))
        if details.function == ANGULAR:
            return ANGLE_ONLY_RESULT_FORMAT.format(angle=angle)
        return VALUE_RESULT_FORMAT.format(symbol=SYMBOL_BY_FUNCTION[details.function], raw=format_score(details.raw_value))

    def _score_result(self, details: EmbeddingDetails, score: float) -> str:
        key = details.function if details.function in SCORE_EXPRESSIONS else details.negative_handling
        text = CLIP_RESULT_FORMAT.format(expression=self._score_expression(details), score=format_score(score))
        if details.clipped and not (key == "clip" and details.raw_value < 0):
            return text + LIMITED_SUFFIX
        return text

    def paint(self, painter: QPainter, area: QRectF, walkthrough: MetricWalkthrough, position: TimelinePosition) -> None:
        if area.width() <= 0 or area.height() <= 0:
            return
        details = self._details(walkthrough)
        with fitted_area(painter, area, DESIGN_MINIMUM_WIDTH, DESIGN_MINIMUM_HEIGHT) as logical_area:
            frame = EmbeddingFrame(walkthrough, details, position, build_layout(logical_area))
            self._paint_encoding(painter, frame)
            self._paint_vectors(painter, frame)
            self._paint_separator(painter, frame, logical_area)
            self._paint_plane(painter, frame)
            self._paint_column(painter, frame)

    def _details(self, walkthrough: MetricWalkthrough) -> EmbeddingDetails:
        if not isinstance(walkthrough.details, EmbeddingDetails):
            raise TypeError(f"Embedding similarity needs embedding details, got {type(walkthrough.details).__name__}.")
        return walkthrough.details

    def _paint_encoding(self, painter: QPainter, frame: EmbeddingFrame) -> None:
        layout = frame.layout
        progress = frame.phase(ENCODE_STEP)
        expected_entry = ease_out_cubic(segment_progress(progress, 0.0, 0.25))
        answer_entry = ease_out_cubic(segment_progress(progress, 0.12, 0.37))
        self._paint_sentence_card(painter, layout.expected_card, EXPECTED_LABEL, frame.walkthrough.expected_answer, EXPECTED_COLOR, expected_entry, False)
        answer_text = EMPTY_CARD_TEXT if frame.is_empty else frame.walkthrough.given_answer
        self._paint_sentence_card(painter, layout.answer_card, ANSWER_LABEL, answer_text, ANSWER_COLOR, answer_entry, frame.is_empty)
        travel = segment_progress(progress, 0.35, 0.7)
        self._paint_flow_arrow(painter, layout.first_arrow, progress > 0.3, travel if frame.is_active(ENCODE_STEP) else None)
        glow = segment_progress(progress, 0.5, 0.85)
        self._paint_encoder(painter, layout.encoder, glow, frame.is_active(ENCODE_STEP))

    def _paint_sentence_card(self, painter: QPainter, rect: QRectF, label: str, text: str, color: str, entry: float, is_empty: bool) -> None:
        if entry <= 0:
            with faded(painter, GHOST_OPACITY):
                draw_outlined_card(painter, rect, SURFACE_COLOR, BORDER_COLOR, CARD_RADIUS)
            return
        shifted = rect.translated(-CARD_SLIDE_DISTANCE * (1 - entry), 0)
        with faded(painter, entry):
            border = WARNING_COLOR if is_empty else (STRONG_BORDER_COLOR if color == ANSWER_COLOR else BORDER_COLOR)
            draw_outlined_card(painter, shifted, SURFACE_COLOR, border, CARD_RADIUS, is_empty)
            inner = shifted.adjusted(CARD_PADDING, CARD_PADDING - 2, -CARD_PADDING, -CARD_PADDING)
            draw_dot(painter, QPointF(inner.left() + CARD_DOT_RADIUS, inner.top() + CARD_LABEL_HEIGHT / 2), CARD_DOT_RADIUS, color)
            label_rect = QRectF(inner.left() + CARD_DOT_RADIUS * 2 + 6, inner.top(), inner.width(), CARD_LABEL_HEIGHT)
            draw_caption(painter, label_rect, label)
            font = text_font(CARD_TEXT_SIZE)
            if is_empty:
                font.setItalic(True)
            text_color = WARNING_COLOR if is_empty else TEXT_COLOR
            lines = wrap_text(text, font, inner.width(), CARD_MAXIMUM_LINES)
            for index, line in enumerate(lines):
                line_rect = QRectF(inner.left(), inner.top() + CARD_LABEL_HEIGHT + index * CARD_LINE_HEIGHT, inner.width(), CARD_LINE_HEIGHT)
                draw_text(painter, line_rect, line, text_color, font)

    def _paint_flow_arrow(self, painter: QPainter, arrow: tuple[QPointF, QPointF], is_lit: bool, travel: float | None) -> None:
        start, end = arrow
        color = PRIMARY_COLOR if is_lit else BORDER_COLOR
        with faded(painter, 1.0 if is_lit else GHOST_OPACITY * 2):
            draw_arrow(painter, start, end, color)
        if travel is None or travel <= 0 or travel >= 1:
            return
        center = QPointF(lerp(start.x(), end.x(), travel), start.y())
        draw_dot(painter, center, FLOW_DOT_RADIUS, PRIMARY_HOVER_COLOR)

    def _paint_encoder(self, painter: QPainter, rect: QRectF, glow: float, is_active: bool) -> None:
        tint = lerp(ENCODER_IDLE_TINT, ENCODER_LIT_TINT, glow)
        if is_active and 0 < glow < 1:
            tint += ENCODER_GLOW_TINT * wave(glow, 1.0)
        border = mix_colors(STRONG_BORDER_COLOR, PRIMARY_COLOR, glow)
        draw_outlined_card(painter, rect, with_alpha(PRIMARY_COLOR, tint), border, ENCODER_RADIUS)
        title_rect = QRectF(rect.left(), rect.center().y() - 17, rect.width(), 18)
        subtitle_rect = QRectF(rect.left(), rect.center().y() + 1, rect.width(), 16)
        draw_text(painter, title_rect, ENCODER_TITLE, TEXT_COLOR, text_font(ENCODER_TITLE_SIZE, QFont.Weight.DemiBold), Qt.AlignmentFlag.AlignCenter)
        draw_text(painter, subtitle_rect, ENCODER_SUBTITLE, SECONDARY_TEXT_COLOR, text_font(ENCODER_SUBTITLE_SIZE), Qt.AlignmentFlag.AlignCenter)

    def _paint_vectors(self, painter: QPainter, frame: EmbeddingFrame) -> None:
        layout = frame.layout
        progress = frame.phase(VECTOR_STEP)
        travel = segment_progress(progress, 0.0, 0.3)
        self._paint_flow_arrow(painter, layout.second_arrow, progress > 0, travel if frame.is_active(VECTOR_STEP) else None)
        count = self._bar_count(layout.expected_strip.width())
        if count <= 0:
            return
        expected_values, answer_values = self._bar_values(frame, count)
        growth = segment_progress(progress, 0.1, 0.7)
        self._paint_strip(painter, layout.expected_strip, expected_values, EXPECTED_COLOR, growth)
        if frame.is_empty:
            self._paint_empty_strip(painter, layout.answer_strip, growth)
        else:
            self._paint_strip(painter, layout.answer_strip, answer_values, ANSWER_COLOR, segment_progress(growth, 0.15, 1.0))
        caption = STRIP_CAPTION_FORMAT.format(dimensions=EMBEDDING_DIMENSIONS, count=count)
        with faded(painter, segment_progress(progress, 0.4, 0.7)):
            draw_text(painter, layout.strip_caption, caption, DISABLED_TEXT_COLOR, text_font(STRIP_CAPTION_SIZE))

    def _bar_values(self, frame: EmbeddingFrame, count: int) -> tuple[tuple[float, ...], tuple[float, ...]]:
        details = frame.details
        if len(details.expected_vector) >= count and (frame.is_empty or len(details.given_vector) >= count):
            return real_bars(details.expected_vector, details.given_vector, count)
        return illustrative_bars(frame.walkthrough.expected_answer, frame.walkthrough.given_answer, count, max(0.0, details.cosine))

    def _bar_count(self, width: float) -> int:
        return min(BAR_MAXIMUM_COUNT, int((width + BAR_SPACING) // (BAR_WIDTH + BAR_SPACING)))

    def _paint_strip(self, painter: QPainter, strip: QRectF, values: tuple[float, ...], color: str, growth: float) -> None:
        stagger = BAR_STAGGER_SPAN / max(1, len(values))
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        for index, value in enumerate(values):
            start = index * stagger
            grown = ease_out_cubic(segment_progress(growth, start, min(1.0, start + BAR_GROW_SPAN)))
            scale = lerp(BAR_IDLE_SCALE, value, grown)
            height = max(BAR_RADIUS, STRIP_HEIGHT * scale)
            left = strip.left() + index * (BAR_WIDTH + BAR_SPACING)
            bar = QRectF(left, strip.bottom() - height, BAR_WIDTH, height)
            fill = color if grown > 0 else BORDER_COLOR
            painter.setBrush(QBrush(with_alpha(fill, lerp(DIMMED_OPACITY, 1.0, grown))))
            painter.drawRoundedRect(bar, BAR_RADIUS, BAR_RADIUS)
        painter.restore()

    def _paint_empty_strip(self, painter: QPainter, strip: QRectF, growth: float) -> None:
        width = min(strip.width(), BAR_MAXIMUM_COUNT * (BAR_WIDTH + BAR_SPACING))
        line_y = strip.bottom() - BAR_RADIUS
        draw_dashed_line(painter, QPointF(strip.left(), line_y), QPointF(strip.left() + width, line_y), with_alpha(WARNING_COLOR, lerp(GHOST_OPACITY, 1.0, growth)))
        with faded(painter, growth):
            label_rect = QRectF(strip.left(), strip.top(), width, strip.height() - BAR_RADIUS * 3)
            draw_text(painter, label_rect, EMPTY_STRIP_TEXT, WARNING_COLOR, text_font(STRIP_CAPTION_SIZE), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)

    def _paint_separator(self, painter: QPainter, frame: EmbeddingFrame, area: QRectF) -> None:
        y = frame.layout.separator_y
        draw_line(painter, QPointF(area.left(), y), QPointF(area.right(), y), BORDER_COLOR)

    def _paint_plane(self, painter: QPainter, frame: EmbeddingFrame) -> None:
        layout = frame.layout
        if layout.radius <= 0:
            return
        vector_phase = frame.phase(VECTOR_STEP)
        axes_opacity = lerp(GHOST_OPACITY, 1.0, segment_progress(vector_phase, 0.35, 0.6))
        with clipped_to(painter, layout.plane):
            with faded(painter, axes_opacity):
                self._paint_axes(painter, layout)
            self._paint_clip_zone(painter, frame)
            growth = ease_out_cubic(segment_progress(vector_phase, 0.5, 1.0))
            if growth <= 0:
                return
            self._paint_expected_vector(painter, layout, growth)
            if frame.is_empty:
                self._paint_missing_vector(painter, layout, growth)
                return
            angle = self._drawn_angle(frame)
            if frame.details.function in DISTANCE_FUNCTIONS:
                self._paint_distance(painter, frame, angle, growth)
                return
            self._paint_arc(painter, frame, angle)
            self._paint_answer_vector(painter, frame, angle, growth)
            if frame.details.function == DOT_PRODUCT and not frame.details.normalize_vectors:
                self._paint_projection(painter, frame, angle, growth)

    def _paint_axes(self, painter: QPainter, layout: EmbeddingLayout) -> None:
        plane, origin = layout.plane, layout.origin
        draw_line(painter, QPointF(plane.left() + AXIS_PADDING, origin.y()), QPointF(plane.right() - AXIS_PADDING, origin.y()), STRONG_BORDER_COLOR)
        draw_line(painter, origin, QPointF(origin.x(), plane.top() + AXIS_PADDING), STRONG_BORDER_COLOR)
        ring = QRectF(origin.x() - layout.radius, origin.y() - layout.radius, layout.radius * 2, layout.radius * 2)
        pen = QPen(with_alpha(BORDER_COLOR, 0.9), 1.0)
        pen.setDashPattern([3.0, 4.0])
        painter.save()
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(ring, 0, int(STRAIGHT_ANGLE_DEGREES * 16))
        painter.restore()

    def _paint_clip_zone(self, painter: QPainter, frame: EmbeddingFrame) -> None:
        progress = frame.phase(CLIP_STEP)
        if progress <= 0 or frame.is_empty or frame.details.function not in NEGATIVE_HANDLING_FUNCTIONS:
            return
        layout = frame.layout
        reveal = ease_out_cubic(segment_progress(progress, 0.0, 0.4))
        boundary = BASE_ANGLE_DEGREES + RIGHT_ANGLE_DEGREES
        reach = layout.radius * 3
        ring = QRectF(layout.origin.x() - reach, layout.origin.y() - reach, reach * 2, reach * 2)
        zone = QPainterPath(layout.origin)
        zone.arcTo(ring, boundary, (STRAIGHT_ANGLE_DEGREES - boundary) * reveal)
        zone.closeSubpath()
        is_clip_rule = frame.details.negative_handling == CLIP
        color = ERROR_COLOR if frame.details.clipped and is_clip_rule else DISABLED_TEXT_COLOR
        zone_text = (CLIP_ZONE_TEXT if is_clip_rule else RESCALE_ZONE_TEXT).format(symbol=SYMBOL_BY_FUNCTION[frame.details.function])
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(with_alpha(color, CLIP_ZONE_ALPHA)))
        painter.drawPath(zone)
        painter.restore()
        with faded(painter, reveal):
            draw_dashed_line(painter, layout.origin, point_at(layout.origin, boundary, length_inside(layout.plane, layout.origin, boundary, reach)), color)
            text_width_available = layout.origin.x() - layout.plane.left() - AXIS_PADDING * 3
            text_top = layout.origin.y() - layout.radius * CLIP_ZONE_TEXT_HEIGHT_RATIO
            text_rect = QRectF(layout.plane.left() + AXIS_PADDING, text_top, text_width_available, CLIP_ZONE_TEXT_HEIGHT)
            draw_text(painter, text_rect, zone_text, color, text_font(VECTOR_LABEL_SIZE, QFont.Weight.DemiBold), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, wrap=True)

    def _paint_expected_vector(self, painter: QPainter, layout: EmbeddingLayout, growth: float) -> None:
        length = length_inside(layout.plane, layout.origin, BASE_ANGLE_DEGREES, layout.radius) * growth
        tip = point_at(layout.origin, BASE_ANGLE_DEGREES, length)
        draw_arrow(painter, layout.origin, tip, EXPECTED_COLOR, VECTOR_LINE_WIDTH)
        with faded(painter, segment_progress(growth, 0.7, 1.0)):
            label_rect = QRectF(tip.x() - VECTOR_LABEL_WIDTH, tip.y() + 6, VECTOR_LABEL_WIDTH, VECTOR_LABEL_HEIGHT)
            draw_text(painter, label_rect, EXPECTED_VECTOR_LABEL, PRIMARY_HOVER_COLOR, text_font(VECTOR_LABEL_SIZE), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def _paint_missing_vector(self, painter: QPainter, layout: EmbeddingLayout, growth: float) -> None:
        with faded(painter, growth):
            label_rect = QRectF(layout.origin.x() + ANGLE_LABEL_GAP, layout.origin.y() - layout.radius * 0.7, layout.radius, VECTOR_LABEL_HEIGHT * 2)
            draw_text(painter, label_rect, EMPTY_VECTOR_TEXT, WARNING_COLOR, text_font(VECTOR_LABEL_SIZE, QFont.Weight.DemiBold), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            draw_dot(painter, layout.origin, FLOW_DOT_RADIUS, WARNING_COLOR)

    def _drawn_angle(self, frame: EmbeddingFrame) -> float:
        real = min(frame.details.angle_degrees, MAXIMUM_DRAWN_ANGLE_DEGREES - BASE_ANGLE_DEGREES)
        start = min(real + SWEEP_OFFSET_DEGREES, MAXIMUM_DRAWN_ANGLE_DEGREES - BASE_ANGLE_DEGREES)
        sweep = ease_in_out(segment_progress(frame.phase(ANGLE_STEP), 0.0, 0.55))
        return lerp(start, real, sweep)

    def _paint_answer_vector(self, painter: QPainter, frame: EmbeddingFrame, angle: float, growth: float) -> None:
        layout = frame.layout
        direction = BASE_ANGLE_DEGREES + angle
        length = length_inside(layout.plane, layout.origin, direction, layout.radius * ANSWER_LENGTH_RATIO) * growth
        tip = point_at(layout.origin, direction, length)
        is_cut = frame.details.clipped and frame.details.negative_handling == CLIP and frame.details.function in NEGATIVE_HANDLING_FUNCTIONS
        color = ERROR_COLOR if is_cut and frame.phase(CLIP_STEP) > 0 else ANSWER_COLOR
        draw_arrow(painter, layout.origin, tip, color, VECTOR_LINE_WIDTH)
        with faded(painter, segment_progress(growth, 0.7, 1.0)):
            label_rect = QRectF(tip.x() - VECTOR_LABEL_WIDTH / 2, tip.y() - VECTOR_LABEL_HEIGHT - 6, VECTOR_LABEL_WIDTH, VECTOR_LABEL_HEIGHT)
            label_rect.moveLeft(max(layout.plane.left(), min(label_rect.left(), layout.plane.right() - VECTOR_LABEL_WIDTH)))
            label_rect.moveTop(max(layout.plane.top(), label_rect.top()))
            draw_text(painter, label_rect, ANSWER_VECTOR_LABEL, color, text_font(VECTOR_LABEL_SIZE), Qt.AlignmentFlag.AlignCenter)

    def _answer_tip(self, frame: EmbeddingFrame, angle: float, growth: float) -> QPointF:
        layout = frame.layout
        direction = BASE_ANGLE_DEGREES + angle
        length = length_inside(layout.plane, layout.origin, direction, layout.radius * ANSWER_LENGTH_RATIO) * growth
        return point_at(layout.origin, direction, length)

    def _paint_projection(self, painter: QPainter, frame: EmbeddingFrame, angle: float, growth: float) -> None:
        reveal = ease_out_cubic(segment_progress(frame.phase(ANGLE_STEP), 0.5, 0.9))
        if reveal <= 0:
            return
        layout = frame.layout
        tip = self._answer_tip(frame, angle, growth)
        along = math.hypot(tip.x() - layout.origin.x(), tip.y() - layout.origin.y()) * math.cos(math.radians(angle))
        foot = point_at(layout.origin, BASE_ANGLE_DEGREES, along)
        with faded(painter, reveal):
            draw_dashed_line(painter, tip, foot, SECONDARY_TEXT_COLOR)
            draw_line(painter, layout.origin, foot, PRIMARY_HOVER_COLOR, PROJECTION_WIDTH)
            draw_dot(painter, foot, FLOW_DOT_RADIUS, PRIMARY_HOVER_COLOR)

    def _paint_distance(self, painter: QPainter, frame: EmbeddingFrame, angle: float, growth: float) -> None:
        layout = frame.layout
        expected_length = length_inside(layout.plane, layout.origin, BASE_ANGLE_DEGREES, layout.radius) * growth
        expected_tip = point_at(layout.origin, BASE_ANGLE_DEGREES, expected_length)
        answer_tip = self._answer_tip(frame, angle, growth)
        with faded(painter, GHOST_OPACITY):
            draw_line(painter, layout.origin, answer_tip, ANSWER_COLOR, VECTOR_LINE_WIDTH)
        draw_dot(painter, expected_tip, POINT_RADIUS, EXPECTED_COLOR)
        draw_dot(painter, answer_tip, POINT_RADIUS, ANSWER_COLOR)
        reveal = ease_out_cubic(segment_progress(frame.phase(ANGLE_STEP), 0.0, 0.5))
        if reveal <= 0:
            return
        corner = QPointF(answer_tip.x(), expected_tip.y())
        with faded(painter, reveal):
            if frame.details.function == MANHATTAN:
                draw_line(painter, expected_tip, corner, PRIMARY_HOVER_COLOR, STAIRCASE_WIDTH)
                draw_line(painter, corner, answer_tip, PRIMARY_HOVER_COLOR, STAIRCASE_WIDTH)
                anchor = corner
            else:
                draw_line(painter, expected_tip, answer_tip, PRIMARY_HOVER_COLOR, STAIRCASE_WIDTH)
                anchor = QPointF((expected_tip.x() + answer_tip.x()) / 2, (expected_tip.y() + answer_tip.y()) / 2)
            text = DISTANCE_LABEL_FORMAT.format(raw=format_score(frame.details.raw_value))
            label = QRectF(anchor.x() + ANGLE_LABEL_GAP / 2, anchor.y() - ANGLE_ROW_HEIGHT / 2, text_width(text, monospace_font(ANGLE_LABEL_SIZE)) + 4, ANGLE_ROW_HEIGHT)
            label.moveLeft(max(layout.plane.left(), min(label.left(), layout.plane.right() - label.width())))
            label.moveTop(max(layout.plane.top(), min(label.top(), layout.origin.y() - label.height())))
            draw_value(painter, label, text, TEXT_COLOR, ANGLE_LABEL_SIZE, Qt.AlignmentFlag.AlignCenter)

    def _paint_arc(self, painter: QPainter, frame: EmbeddingFrame, angle: float) -> None:
        progress = frame.phase(ANGLE_STEP)
        if progress <= 0:
            return
        layout = frame.layout
        reveal = segment_progress(progress, 0.0, 0.15)
        arc_radius = max(ARC_MINIMUM_RADIUS, layout.radius * ARC_RADIUS_RATIO)
        ring = QRectF(layout.origin.x() - arc_radius, layout.origin.y() - arc_radius, arc_radius * 2, arc_radius * 2)
        with faded(painter, reveal):
            wedge = QPainterPath(layout.origin)
            wedge.arcTo(ring, BASE_ANGLE_DEGREES, angle)
            wedge.closeSubpath()
            painter.save()
            painter.setBrush(QBrush(with_alpha(PRIMARY_HOVER_COLOR, HIGHLIGHT_TINT * 0.6)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(wedge)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(to_color(TEXT_COLOR), ARC_LINE_WIDTH))
            painter.drawArc(ring, int(BASE_ANGLE_DEGREES * 16), int(angle * 16))
            painter.restore()
            self._paint_angle_label(painter, layout, angle, arc_radius)

    def _paint_angle_label(self, painter: QPainter, layout: EmbeddingLayout, angle: float, arc_radius: float) -> None:
        text = ANGLE_ROW_FORMAT.format(angle=format_angle(angle))
        font = monospace_font(ANGLE_LABEL_SIZE)
        width = text_width(text, font) + 4
        height = ANGLE_ROW_HEIGHT
        if angle >= INSIDE_LABEL_MINIMUM_DEGREES:
            anchor = point_at(layout.origin, BASE_ANGLE_DEGREES + angle / 2, arc_radius + ANGLE_LABEL_GAP + width / 2)
        else:
            anchor = point_at(layout.origin, BASE_ANGLE_DEGREES + angle + OUTSIDE_LABEL_OFFSET_DEGREES, layout.radius * OUTSIDE_LABEL_RADIUS_RATIO)
        label = QRectF(anchor.x() - width / 2, anchor.y() - height / 2, width, height)
        label.moveLeft(max(layout.plane.left(), min(label.left(), layout.plane.right() - width)))
        label.moveTop(max(layout.plane.top(), min(label.top(), layout.origin.y() - height)))
        draw_value(painter, label, text, TEXT_COLOR, ANGLE_LABEL_SIZE, Qt.AlignmentFlag.AlignCenter)

    def _paint_column(self, painter: QPainter, frame: EmbeddingFrame) -> None:
        column = frame.layout.column
        if column.width() <= 0 or column.height() <= 0:
            return
        top = column.top()
        if column.height() >= ROOMY_COLUMN_HEIGHT:
            top = self._paint_intro(painter, column, top, frame)
        top = self._paint_cosine_value(painter, column, top, frame)
        top = self._paint_reference_chips(painter, column, top, frame)
        self._paint_score(painter, column, top + BLOCK_GAP, frame)
        self._paint_note(painter, column)

    def _paint_intro(self, painter: QPainter, column: QRectF, top: float, frame: EmbeddingFrame) -> float:
        font = text_font(INTRO_SIZE)
        intro = DISTANCE_INTRO_TEXT if frame.details.function in DISTANCE_FUNCTIONS else INTRO_TEXT
        lines = wrap_text(intro, font, column.width(), INTRO_MAXIMUM_LINES)
        opacity = lerp(DIMMED_OPACITY, 1.0, segment_progress(frame.phase(VECTOR_STEP), 0.5, 1.0))
        with faded(painter, opacity):
            for index, line in enumerate(lines):
                draw_text(painter, QRectF(column.left(), top + index * INTRO_LINE_HEIGHT, column.width(), INTRO_LINE_HEIGHT), line, SECONDARY_TEXT_COLOR, font)
        return top + len(lines) * INTRO_LINE_HEIGHT + BLOCK_GAP

    def _value_texts(self, frame: EmbeddingFrame, progress: float) -> tuple[str, str]:
        details = frame.details
        if progress <= 0 or frame.is_empty:
            return PENDING_VALUE, PENDING_VALUE
        angle = self._drawn_angle(frame)
        is_settled = progress >= 1 or angle == details.angle_degrees
        if details.function == COSINE:
            cosine = details.cosine if is_settled else math.cos(math.radians(angle))
            return format_score(cosine), format_angle(angle)
        if details.function == ANGULAR:
            return format_angle(angle), format_score(details.cosine if is_settled else math.cos(math.radians(angle)))
        return format_score(details.raw_value), format_angle(details.angle_degrees)

    def _row_format(self, details: EmbeddingDetails) -> str:
        if details.function == ANGULAR:
            return VALUE_TEXT_FORMAT.format(symbol=SYMBOL_BY_FUNCTION[COSINE], value="{angle}")
        if details.function in DISTANCE_FUNCTIONS:
            return DISTANCE_ROW_FORMAT.format(norm=EUCLIDEAN_NORM_NAME if details.function == EUCLIDEAN else MANHATTAN_NORM_NAME)
        return ANGLE_ROW_FORMAT

    def _paint_cosine_value(self, painter: QPainter, column: QRectF, top: float, frame: EmbeddingFrame) -> float:
        progress = frame.phase(ANGLE_STEP)
        details = frame.details
        value_text, row_value = self._value_texts(frame, progress)
        symbol = SYMBOL_BY_FUNCTION[details.function]
        text = VALUE_TEXT_FORMAT.format(symbol=symbol, value=value_text)
        widest = VALUE_TEXT_FORMAT.format(symbol=symbol, value=format_score(-10.0))
        font = largest_fitting_font(widest, VALUE_SIZES, column.width(), monospace_font)
        color = PRIMARY_HOVER_COLOR if progress > 0 and not frame.is_empty else DISABLED_TEXT_COLOR
        draw_text(painter, QRectF(column.left(), top, column.width(), VALUE_HEIGHT), text, color, font)
        top += VALUE_HEIGHT
        if frame.is_empty and progress > 0:
            return self._paint_empty_notice(painter, column, top, progress)
        angle_row = QRectF(column.left(), top, column.width(), ANGLE_ROW_HEIGHT)
        row_format = self._row_format(details)
        row_text = row_format if details.function in DISTANCE_FUNCTIONS else row_format.format(angle=row_value)
        draw_value(painter, angle_row, row_text, SECONDARY_TEXT_COLOR if progress > 0 else DISABLED_TEXT_COLOR, ANGLE_ROW_SIZE)
        return top + ANGLE_ROW_HEIGHT + BLOCK_GAP

    def _paint_empty_notice(self, painter: QPainter, column: QRectF, top: float, progress: float) -> float:
        notice = QRectF(column.left(), top, column.width(), EMPTY_NOTICE_HEIGHT)
        with faded(painter, ease_out_cubic(segment_progress(progress, 0.0, 0.4))):
            draw_outlined_card(painter, notice, with_alpha(WARNING_COLOR, HIGHLIGHT_TINT * 0.6), WARNING_COLOR, REFERENCE_CHIP_RADIUS, True)
            draw_text(painter, notice.adjusted(SCORE_CARD_PADDING, 0, -SCORE_CARD_PADDING, 0), EMPTY_NOTICE_TEXT, TEXT_COLOR, text_font(INTRO_SIZE, QFont.Weight.DemiBold))
        return notice.bottom() + BLOCK_GAP

    def _chip_texts(self, details: EmbeddingDetails) -> tuple[str, ...]:
        if details.function in DISTANCE_FUNCTIONS:
            return DISTANCE_CHIPS
        if details.function == ANGULAR:
            return ANGULAR_CHIPS
        return CLIP_CHIPS if details.negative_handling == CLIP else RESCALE_CHIPS

    def _is_clip_rule_chip(self, details: EmbeddingDetails, index: int) -> bool:
        return index == CLIPPED_CHIP and details.function in NEGATIVE_HANDLING_FUNCTIONS and details.negative_handling == CLIP

    def _highlighted_chip(self, frame: EmbeddingFrame) -> int | None:
        details = frame.details
        if frame.is_empty:
            return None
        if details.function in DISTANCE_FUNCTIONS:
            if details.score >= HIGH_SCORE_LIMIT:
                return CLOSE_CHIP
            return RIGHT_ANGLE_CHIP if details.score >= MIDDLE_SCORE_LIMIT else CLIPPED_CHIP
        if self._is_clip_rule_chip(details, CLIPPED_CHIP):
            if details.raw_value < 0:
                return CLIPPED_CHIP
            return CLOSE_CHIP if details.angle_degrees < CLOSE_ANGLE_LIMIT_DEGREES else RIGHT_ANGLE_CHIP
        if details.angle_degrees < CLOSE_ANGLE_LIMIT_DEGREES:
            return CLOSE_CHIP
        return RIGHT_ANGLE_CHIP if details.angle_degrees <= FAR_ANGLE_LIMIT_DEGREES else CLIPPED_CHIP

    def _paint_reference_chips(self, painter: QPainter, column: QRectF, top: float, frame: EmbeddingFrame) -> float:
        font = text_font(REFERENCE_CHIP_SIZE)
        highlighted = self._highlighted_chip(frame)
        highlight = ease_out_cubic(segment_progress(frame.phase(CLIP_STEP), 0.25, 0.6))
        opacity = lerp(DIMMED_OPACITY, 1.0, segment_progress(frame.phase(ANGLE_STEP), 0.5, 1.0))
        left, row_top = column.left(), top
        with faded(painter, opacity):
            for index, text in enumerate(self._chip_texts(frame.details)):
                width = min(column.width(), text_width(text, font) + REFERENCE_CHIP_PADDING * 2)
                if left > column.left() and left + width > column.right():
                    left = column.left()
                    row_top += REFERENCE_CHIP_HEIGHT + REFERENCE_CHIP_GAP
                chip = QRectF(left, row_top, width, REFERENCE_CHIP_HEIGHT)
                weight = highlight if index == highlighted else 0.0
                self._paint_reference_chip(painter, chip, text, font, weight, self._is_clip_rule_chip(frame.details, index))
                left += width + REFERENCE_CHIP_GAP
        return row_top + REFERENCE_CHIP_HEIGHT

    def _paint_reference_chip(self, painter: QPainter, chip: QRectF, text: str, font: QFont, weight: float, is_clip_rule: bool) -> None:
        accent = ERROR_COLOR if is_clip_rule else PRIMARY_COLOR
        fill = mix_colors(SURFACE_COLOR, with_alpha(accent, HIGHLIGHT_TINT), weight)
        border = mix_colors(SURFACE_COLOR, accent, weight)
        base_text = DISABLED_TEXT_COLOR if is_clip_rule else LABEL_TEXT_COLOR
        draw_outlined_card(painter, chip, fill, border, REFERENCE_CHIP_RADIUS)
        draw_text(painter, chip, text, mix_colors(base_text, TEXT_COLOR, weight), font, Qt.AlignmentFlag.AlignCenter)

    def _paint_score(self, painter: QPainter, column: QRectF, top: float, frame: EmbeddingFrame) -> None:
        progress = frame.phase(CLIP_STEP)
        reveal = ease_out_cubic(segment_progress(progress, 0.45, 0.9))
        score = 0.0 if frame.is_empty else frame.walkthrough.final_score
        caption = EMPTY_SCORE_CAPTION if frame.is_empty else self._score_expression(frame.details)
        caption_rect = QRectF(column.left(), top, column.width(), SCORE_CAPTION_HEIGHT)
        card = QRectF(column.left(), caption_rect.bottom() + 4, column.width(), SCORE_CARD_HEIGHT)
        if card.bottom() > self._note_top(column):
            return
        with faded(painter, lerp(GHOST_OPACITY, 1.0, reveal)):
            if reveal > 0:
                draw_value(painter, caption_rect, caption, SECONDARY_TEXT_COLOR, ANGLE_ROW_SIZE - 1)
            accent = WARNING_COLOR if score <= 0 else PRIMARY_COLOR
            draw_outlined_card(painter, card, mix_colors(SURFACE_COLOR, with_alpha(accent, HIGHLIGHT_TINT), reveal), mix_colors(BORDER_COLOR, accent, reveal), REFERENCE_CHIP_RADIUS)
            text = SCORE_TEXT_FORMAT.format(score=format_score(score) if reveal > 0 else PENDING_VALUE)
            inner = card.adjusted(SCORE_CARD_PADDING, 0, -SCORE_CARD_PADDING, 0)
            font = largest_fitting_font(SCORE_TEXT_FORMAT.format(score=format_score(0.0)), SCORE_SIZES, inner.width(), monospace_font)
            draw_text(painter, inner, text, TEXT_COLOR, font)

    def _score_expression(self, details: EmbeddingDetails) -> str:
        key = details.function if details.function in SCORE_EXPRESSIONS else details.negative_handling
        return SCORE_EXPRESSIONS[key].format(raw=format_score(details.raw_value), angle=format_angle(details.angle_degrees))

    def _note_top(self, column: QRectF) -> float:
        return column.bottom() - NOTE_LINE_HEIGHT * NOTE_MAXIMUM_LINES

    def _paint_note(self, painter: QPainter, column: QRectF) -> None:
        font = text_font(NOTE_SIZE)
        lines = wrap_text(NOTE_TEXT, font, column.width(), NOTE_MAXIMUM_LINES)
        top = column.bottom() - len(lines) * NOTE_LINE_HEIGHT
        for index, line in enumerate(lines):
            draw_text(painter, QRectF(column.left(), top + index * NOTE_LINE_HEIGHT, column.width(), NOTE_LINE_HEIGHT), line, DISABLED_TEXT_COLOR, font)
