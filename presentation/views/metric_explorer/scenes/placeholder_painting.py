from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QFont, QPainter

from domain.explanations.metric_walkthrough import MetricWalkthrough
from domain.explanations.timeline import TimelinePosition
from presentation.views.branding import PRIMARY_COLOR, SECONDARY_TEXT_COLOR, TEXT_COLOR
from presentation.views.metric_explorer.painting import (
    draw_bar,
    draw_caption,
    draw_text,
    draw_value,
    ease_out_cubic,
    text_font,
)
from presentation.views.metric_explorer.scenes.base_scene import WalkthroughScene

TITLE_SIZE = 20
TITLE_HEIGHT = 32.0
BODY_SIZE = 13
BODY_HEIGHT = 40.0
ROW_GAP = 16.0
BAR_HEIGHT = 24.0
SCORE_SIZE = 28
SCORE_HEIGHT = 40.0
SCORE_FORMAT = "{:.3f}"
PROGRESS_FORMAT = "{:.0%}"


def paint_placeholder(
    painter: QPainter,
    area: QRectF,
    metric_name: str,
    scene: WalkthroughScene,
    walkthrough: MetricWalkthrough,
    position: TimelinePosition,
) -> None:
    steps = scene.steps
    step = steps[position.step_index]
    draw_caption(painter, QPointF(area.left(), area.top()), f"{metric_name} · step {position.step_index + 1} of {len(steps)}")
    title_top = area.top() + ROW_GAP + BODY_SIZE
    draw_text(painter, QRectF(area.left(), title_top, area.width(), TITLE_HEIGHT), step.title, TEXT_COLOR, text_font(TITLE_SIZE, QFont.Weight.Bold))
    body_top = title_top + TITLE_HEIGHT
    draw_text(painter, QRectF(area.left(), body_top, area.width(), BODY_HEIGHT), scene.step_body(position.step_index, walkthrough), SECONDARY_TEXT_COLOR, text_font(BODY_SIZE), wrap=True)
    bar_top = body_top + BODY_HEIGHT + ROW_GAP
    progress = ease_out_cubic(position.step_progress)
    draw_bar(painter, QRectF(area.left(), bar_top, area.width(), BAR_HEIGHT), progress, PRIMARY_COLOR, "Step", PROGRESS_FORMAT.format(position.step_progress))
    score_top = area.bottom() - SCORE_HEIGHT
    draw_caption(painter, QPointF(area.left(), score_top - ROW_GAP), "Score")
    draw_value(painter, QRectF(area.left(), score_top, area.width(), SCORE_HEIGHT), SCORE_FORMAT.format(walkthrough.final_score), PRIMARY_COLOR, SCORE_SIZE)
