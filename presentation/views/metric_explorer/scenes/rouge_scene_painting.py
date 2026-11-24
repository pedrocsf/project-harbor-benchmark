from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import lru_cache

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QFont, QFontMetricsF, QPainter, QPen

from domain.explanations.metric_walkthrough import MetricWalkthrough
from domain.explanations.timeline import TimelinePosition
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
)
from presentation.views.metric_explorer.painting import (
    caption_font,
    clamp_unit,
    draw_card,
    draw_text,
    ease_out_cubic,
    lerp,
    mix_colors,
    monospace_font,
    segment_progress,
    text_font,
    to_color,
    with_alpha,
)

DEFAULT_STAGGER_SPAN = 0.35
CHIP_HORIZONTAL_PADDING = 10.0
CHIP_CORNER_RADIUS = 7.0
CHIP_BORDER_WIDTH = 1.0
CHIP_MATCH_FILL_ALPHA = 0.18
CHIP_DIMMED_TEXT_WEIGHT = 0.5
CAPTION_HEIGHT = 16.0
CARD_HEIGHT = 80.0
CARD_GAP = 10.0
CARD_PADDING = 12.0
CARD_VERTICAL_PADDING = 9.0
CARD_RADIUS = 10.0
CARD_LABEL_SIZE = 11
CARD_VALUE_SIZE = 18
CARD_DETAIL_SIZE = 11
CARD_LABEL_HEIGHT = 14.0
CARD_VALUE_HEIGHT = 26.0
CARD_DETAIL_HEIGHT = 16.0
CARD_TRACK_HEIGHT = 3.0
CARD_DIM_OPACITY = 0.45
RATIO_LABEL_SIZE = 12
RATIO_VALUE_SIZE = 13
RATIO_LABEL_HEIGHT = 16.0
RATIO_TRACK_HEIGHT = 10.0
RATIO_VALUE_HEIGHT = 18.0
RATIO_INNER_GAP = 4.0
RATIO_BLOCK_HEIGHT = RATIO_LABEL_HEIGHT + RATIO_TRACK_HEIGHT + RATIO_VALUE_HEIGHT + 2 * RATIO_INNER_GAP
PENDING_VALUE = "–"
SCORE_FORMAT = "{:.3f}"
RATIO_FORMAT = "{numerator} / {denominator}"
MINIMUM_FIT_SCALE = 0.35
FIT_ITERATIONS = 4
SCENE_INSET = 1.0
PRECISION_TYPE = "precision"
RECALL_TYPE = "recall"
F_MEASURE_TYPE = "f_measure"
CLASSIC_BETA = 1.0
F_ONE_LINE = "F = 2·P·R / (P + R)"
F_BETA_LINE = "F<sub>β</sub> = (1 + β²)·P·R / (β²·P + R), β = {beta}"
F_ONE_RESULT = "F = {value}"
F_BETA_RESULT = "F<sub>β</sub> (β = {beta}) = {value}"
PRECISION_RESULT = "P = {value}"
RECALL_RESULT = "R = {value}"
CASE_NOTE_ON = "Text is lowercased first."
CASE_NOTE_OFF = "Case is kept, so \u201cWord\u201d and \u201cword\u201d do not match."
FINAL_TITLE = "Final score"
PARAMETERS_HINT = "Change these options with \u201cParameters\u2026\u201d."
FINAL_BODY_PRECISION = "The score type is precision, so the result is P, the share of the answer that matches. Recall is ignored. {hint}"
FINAL_BODY_RECALL = "The score type is recall, so the result is R, the share of the expected answer that is covered. Precision is ignored. {hint}"
FINAL_BODY_F_ONE = "The score type is F-measure with \u03b2 = 1: the harmonic mean of precision and recall, high only when both are high. {hint}"
FINAL_BODY_F_BETA = "The score type is F-measure with \u03b2 = {beta}: recall counts {beta} times as much as precision in the weighting. {hint}"
FINAL_LABEL_PRECISION = "Precision (selected)"
FINAL_LABEL_RECALL = "Recall (selected)"
FINAL_LABEL_F_ONE = "F-measure"
FINAL_LABEL_F_BETA = "F-\u03b2 (\u03b2 = {beta})"
FINAL_DETAIL_F_ONE = "2PR / (P + R)"
FINAL_DETAIL_F_BETA = "(1+\u03b2\u00b2)PR / (\u03b2\u00b2P+R)"
FINAL_DETAIL_SELECTED = "selected score"


@dataclass(frozen=True)
class ChipLook:
    highlight: float = 0.0
    dimmed: float = 0.0
    opacity: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0


@dataclass(frozen=True)
class ScoreCard:
    label: str
    value: str
    detail: str
    fraction: float
    reveal: float
    emphasized: bool = False


@dataclass(frozen=True)
class FlowLayout:
    rects: tuple[QRectF, ...]
    height: float


def inset_area(area: QRectF) -> QRectF:
    return area.adjusted(SCENE_INSET, SCENE_INSET, -SCENE_INSET, -SCENE_INSET)


def step_phase(position: TimelinePosition, step_index: int) -> float:
    if position.step_index > step_index:
        return 1.0
    if position.step_index < step_index:
        return 0.0
    return clamp_unit(position.step_progress)


def stagger(progress: float, index: int, count: int, span: float = DEFAULT_STAGGER_SPAN) -> float:
    if count <= 1:
        return segment_progress(progress, 0.0, span)
    start = (1.0 - span) * index / (count - 1)
    return segment_progress(progress, start, start + span)


def format_score(value: float) -> str:
    return SCORE_FORMAT.format(value)


def format_ratio(numerator: int, denominator: int) -> str:
    return RATIO_FORMAT.format(numerator=numerator, denominator=denominator)


@lru_cache(maxsize=32)
def word_font(pixel_size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    return text_font(pixel_size, weight)


@lru_cache(maxsize=32)
def value_font(pixel_size: int, weight: QFont.Weight = QFont.Weight.DemiBold) -> QFont:
    return monospace_font(pixel_size, weight)


@lru_cache(maxsize=1024)
def text_width(text: str, font: QFont) -> float:
    return QFontMetricsF(font).horizontalAdvance(text)


@lru_cache(maxsize=1024)
def elide(text: str, font: QFont, width: float) -> str:
    return QFontMetricsF(font).elidedText(text, Qt.TextElideMode.ElideRight, max(0.0, width))


def chip_width(text: str, font: QFont) -> float:
    return text_width(text, font) + 2 * CHIP_HORIZONTAL_PADDING


def flow_layout(widths: Sequence[float], available_width: float, item_height: float, gap: float) -> FlowLayout:
    rects: list[QRectF] = []
    left, top = 0.0, 0.0
    for width in widths:
        clipped_width = min(width, available_width)
        if left > 0 and left + clipped_width > available_width:
            left, top = 0.0, top + item_height + gap
        rects.append(QRectF(left, top, clipped_width, item_height))
        left += clipped_width + gap
    height = top + item_height if rects else 0.0
    return FlowLayout(tuple(rects), height)


def fit_scale(content_height: Callable[[float, float], float], width: float, height: float) -> float:
    scale = 1.0
    for _ in range(FIT_ITERATIONS):
        needed = content_height(width / scale, height / scale)
        if needed <= height / scale:
            return scale
        scale = max(MINIMUM_FIT_SCALE, scale * (height / scale) / needed)
    return scale


def draw_word_chip(painter: QPainter, rect: QRectF, label: str, font: QFont, look: ChipLook) -> None:
    if look.opacity <= 0 or rect.width() <= 0:
        return
    highlight, dimmed = clamp_unit(look.highlight), clamp_unit(look.dimmed)
    shape = rect.translated(look.offset_x, look.offset_y).adjusted(CHIP_BORDER_WIDTH / 2, CHIP_BORDER_WIDTH / 2, -CHIP_BORDER_WIDTH / 2, -CHIP_BORDER_WIDTH / 2)
    painter.save()
    painter.setOpacity(painter.opacity() * clamp_unit(look.opacity))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(mix_colors(SURFACE_COLOR, with_alpha(SURFACE_COLOR, CHIP_DIMMED_TEXT_WEIGHT), dimmed)))
    painter.drawRoundedRect(shape, CHIP_CORNER_RADIUS, CHIP_CORNER_RADIUS)
    painter.setBrush(QBrush(with_alpha(PRIMARY_COLOR, CHIP_MATCH_FILL_ALPHA * highlight)))
    painter.setPen(_chip_border_pen(highlight, dimmed))
    painter.drawRoundedRect(shape, CHIP_CORNER_RADIUS, CHIP_CORNER_RADIUS)
    painter.restore()
    text_color = mix_colors(mix_colors(LABEL_TEXT_COLOR, TEXT_COLOR, highlight), DISABLED_TEXT_COLOR, dimmed)
    chip_font = QFont(font)
    if highlight >= 0.5:
        chip_font.setWeight(QFont.Weight.DemiBold)
    text = elide(label, chip_font, shape.width() - CHIP_HORIZONTAL_PADDING)
    painter.save()
    painter.setOpacity(painter.opacity() * clamp_unit(look.opacity))
    draw_text(painter, shape, text, text_color, chip_font, Qt.AlignmentFlag.AlignCenter)
    painter.restore()


def _chip_border_pen(highlight: float, dimmed: float) -> QPen:
    if dimmed > highlight:
        pen = QPen(with_alpha(STRONG_BORDER_COLOR, dimmed), CHIP_BORDER_WIDTH, Qt.PenStyle.DashLine)
        pen.setDashPattern([3.0, 3.0])
        return pen
    return QPen(with_alpha(PRIMARY_COLOR, highlight), CHIP_BORDER_WIDTH)


def draw_section_caption(painter: QPainter, rect: QRectF, text: str, trailing: str = "", opacity: float = 1.0) -> None:
    if opacity <= 0:
        return
    painter.save()
    painter.setOpacity(painter.opacity() * clamp_unit(opacity))
    trailing_width = text_width(trailing.upper(), caption_font()) if trailing else 0.0
    caption = elide(text.upper(), caption_font(), rect.width() - trailing_width - CARD_GAP)
    draw_text(painter, rect, caption, SECONDARY_TEXT_COLOR, caption_font())
    if trailing:
        draw_text(painter, rect, trailing.upper(), PRIMARY_HOVER_COLOR, caption_font(), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    painter.restore()


def draw_note(painter: QPainter, rect: QRectF, text: str, opacity: float = 1.0) -> None:
    if opacity <= 0:
        return
    painter.save()
    painter.setOpacity(painter.opacity() * clamp_unit(opacity))
    font = word_font(12)
    draw_text(painter, rect, elide(text, font, rect.width()), DISABLED_TEXT_COLOR, font)
    painter.restore()


def draw_empty_box(painter: QPainter, rect: QRectF, text: str, opacity: float = 1.0) -> None:
    if opacity <= 0:
        return
    painter.save()
    painter.setOpacity(painter.opacity() * clamp_unit(opacity))
    pen = QPen(to_color(STRONG_BORDER_COLOR), CHIP_BORDER_WIDTH, Qt.PenStyle.DashLine)
    pen.setDashPattern([3.0, 3.0])
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    inner = rect.adjusted(CHIP_BORDER_WIDTH, CHIP_BORDER_WIDTH, -CHIP_BORDER_WIDTH, -CHIP_BORDER_WIDTH)
    painter.drawRoundedRect(inner, CHIP_CORNER_RADIUS, CHIP_CORNER_RADIUS)
    font = word_font(12)
    draw_text(painter, inner.adjusted(CHIP_HORIZONTAL_PADDING, 0, -CHIP_HORIZONTAL_PADDING, 0), text, DISABLED_TEXT_COLOR, font, Qt.AlignmentFlag.AlignCenter, wrap=True)
    painter.restore()


def draw_score_cards(painter: QPainter, rect: QRectF, cards: Sequence[ScoreCard]) -> None:
    if not cards:
        return
    width = (rect.width() - CARD_GAP * (len(cards) - 1)) / len(cards)
    for index, card in enumerate(cards):
        left = rect.left() + index * (width + CARD_GAP)
        _draw_score_card(painter, QRectF(left, rect.top(), width, rect.height()), card)


def _draw_score_card(painter: QPainter, rect: QRectF, card: ScoreCard) -> None:
    reveal = ease_out_cubic(card.reveal)
    border = PRIMARY_COLOR if card.emphasized and reveal > 0 else None
    painter.save()
    painter.setOpacity(painter.opacity() * lerp(CARD_DIM_OPACITY, 1.0, reveal))
    draw_card(painter, rect.adjusted(0.5, 0.5, -0.5, -0.5), SURFACE_COLOR, border, CARD_RADIUS)
    content = rect.adjusted(CARD_PADDING, CARD_VERTICAL_PADDING, -CARD_PADDING, -CARD_VERTICAL_PADDING)
    label_font = word_font(CARD_LABEL_SIZE)
    draw_text(painter, QRectF(content.left(), content.top(), content.width(), CARD_LABEL_HEIGHT), elide(card.label, label_font, content.width()), SECONDARY_TEXT_COLOR, label_font)
    value_rect = QRectF(content.left(), content.top() + CARD_LABEL_HEIGHT, content.width(), CARD_VALUE_HEIGHT)
    revealed = reveal > 0
    value_color = PRIMARY_HOVER_COLOR if card.emphasized and revealed else TEXT_COLOR
    big_font = value_font(CARD_VALUE_SIZE)
    draw_text(painter, value_rect, elide(card.value if revealed else PENDING_VALUE, big_font, content.width()), value_color, big_font)
    detail_rect = QRectF(content.left(), value_rect.bottom(), content.width(), CARD_DETAIL_HEIGHT)
    detail_font = value_font(CARD_DETAIL_SIZE, QFont.Weight.Normal)
    painter.setOpacity(painter.opacity() * reveal)
    draw_text(painter, detail_rect, elide(card.detail, detail_font, content.width()), SECONDARY_TEXT_COLOR, detail_font)
    painter.restore()
    _draw_card_track(painter, QRectF(content.left(), content.bottom() - CARD_TRACK_HEIGHT, content.width(), CARD_TRACK_HEIGHT), card.fraction * reveal, reveal)


def _draw_card_track(painter: QPainter, rect: QRectF, fraction: float, reveal: float) -> None:
    painter.save()
    painter.setOpacity(painter.opacity() * lerp(CARD_DIM_OPACITY, 1.0, reveal))
    draw_card(painter, rect, BORDER_COLOR, None, rect.height() / 2)
    fill_width = rect.width() * clamp_unit(fraction)
    if fill_width > 0:
        draw_card(painter, QRectF(rect.left(), rect.top(), max(fill_width, rect.height()), rect.height()), PRIMARY_COLOR, None, rect.height() / 2)
    painter.restore()


def draw_ratio_bar(painter: QPainter, rect: QRectF, label: str, value_text: str, fraction: float, reveal: float) -> None:
    grow = ease_out_cubic(reveal)
    painter.save()
    painter.setOpacity(painter.opacity() * lerp(CARD_DIM_OPACITY, 1.0, grow))
    label_font = word_font(RATIO_LABEL_SIZE, QFont.Weight.DemiBold)
    draw_text(painter, QRectF(rect.left(), rect.top(), rect.width(), RATIO_LABEL_HEIGHT), elide(label, label_font, rect.width()), TEXT_COLOR, label_font)
    track_top = rect.top() + RATIO_LABEL_HEIGHT + RATIO_INNER_GAP
    track = QRectF(rect.left(), track_top, rect.width(), RATIO_TRACK_HEIGHT)
    draw_card(painter, track, SURFACE_COLOR, None, RATIO_TRACK_HEIGHT / 2)
    fill_width = track.width() * clamp_unit(fraction) * grow
    if fill_width > 0:
        draw_card(painter, QRectF(track.left(), track.top(), max(fill_width, RATIO_TRACK_HEIGHT), RATIO_TRACK_HEIGHT), PRIMARY_COLOR, None, RATIO_TRACK_HEIGHT / 2)
    value_rect = QRectF(rect.left(), track.bottom() + RATIO_INNER_GAP, rect.width(), RATIO_VALUE_HEIGHT)
    shown_value = value_text if grow > 0 else PENDING_VALUE
    draw_text(painter, value_rect, shown_value, TEXT_COLOR, value_font(RATIO_VALUE_SIZE, QFont.Weight.Normal))
    painter.restore()


@dataclass(frozen=True)
class ScoreSelection:
    score_type: str
    beta: float
    lowercase: bool
    score: float

    @property
    def beta_text(self) -> str:
        return f"{self.beta:g}"

    @property
    def is_classic(self) -> bool:
        return self.score_type == F_MEASURE_TYPE and self.beta == CLASSIC_BETA


def score_selection(walkthrough: MetricWalkthrough, details) -> ScoreSelection:
    lowercase = bool(walkthrough.parameters.get("lowercase", True))
    return ScoreSelection(details.score_type, details.beta, lowercase, details.score)


def case_note(selection: ScoreSelection) -> str:
    return CASE_NOTE_ON if selection.lowercase else CASE_NOTE_OFF


def formula_with_selection(base_lines: tuple[str, ...], selection: ScoreSelection) -> tuple[str, ...]:
    if selection.score_type != F_MEASURE_TYPE:
        return base_lines
    if selection.is_classic:
        return base_lines + (F_ONE_LINE,)
    return base_lines + (F_BETA_LINE.format(beta=selection.beta_text),)


def selected_formula_line(base_line_count: int, selection: ScoreSelection) -> int:
    if selection.score_type == PRECISION_TYPE:
        return base_line_count - 2
    if selection.score_type == RECALL_TYPE:
        return base_line_count - 1
    return base_line_count


def final_step_body(selection: ScoreSelection) -> str:
    if selection.score_type == PRECISION_TYPE:
        return FINAL_BODY_PRECISION.format(hint=PARAMETERS_HINT)
    if selection.score_type == RECALL_TYPE:
        return FINAL_BODY_RECALL.format(hint=PARAMETERS_HINT)
    if selection.is_classic:
        return FINAL_BODY_F_ONE.format(hint=PARAMETERS_HINT)
    return FINAL_BODY_F_BETA.format(beta=selection.beta_text, hint=PARAMETERS_HINT)


def final_step_result(selection: ScoreSelection) -> str:
    value = format_score(selection.score)
    if selection.score_type == PRECISION_TYPE:
        return PRECISION_RESULT.format(value=value)
    if selection.score_type == RECALL_TYPE:
        return RECALL_RESULT.format(value=value)
    if selection.is_classic:
        return F_ONE_RESULT.format(value=value)
    return F_BETA_RESULT.format(beta=selection.beta_text, value=value)


def final_card_label(selection: ScoreSelection) -> str:
    if selection.score_type == PRECISION_TYPE:
        return FINAL_LABEL_PRECISION
    if selection.score_type == RECALL_TYPE:
        return FINAL_LABEL_RECALL
    if selection.is_classic:
        return FINAL_LABEL_F_ONE
    return FINAL_LABEL_F_BETA.format(beta=selection.beta_text)


def final_card_detail(selection: ScoreSelection) -> str:
    if selection.score_type != F_MEASURE_TYPE:
        return FINAL_DETAIL_SELECTED
    return FINAL_DETAIL_F_ONE if selection.is_classic else FINAL_DETAIL_F_BETA
