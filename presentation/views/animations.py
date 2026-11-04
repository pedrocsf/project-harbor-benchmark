import os

from PySide6.QtCore import (
    QEasingCurve,
    QPauseAnimation,
    QPropertyAnimation,
    QSequentialAnimationGroup,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

REDUCE_MOTION_VARIABLE = "HARBOR_REDUCE_MOTION"
DISABLED_VALUES = frozenset({"1", "true", "yes"})
FADE_MILLISECONDS = 240
WINDOW_FADE_MILLISECONDS = 200
PROGRESS_MILLISECONDS = 220
SCORE_REVEAL_MILLISECONDS = 800
MAXIMUM_STAGGERED_ROWS = 14
ROW_STAGGER = 0.025
MAXIMUM_ROW_STAGGER = MAXIMUM_STAGGERED_ROWS * ROW_STAGGER


def motion_enabled() -> bool:
    return os.environ.get(REDUCE_MOTION_VARIABLE, "").strip().lower() not in DISABLED_VALUES


def row_reveal_progress(reveal: float, row: int) -> float:
    delay = min(row, MAXIMUM_STAGGERED_ROWS) * ROW_STAGGER
    return max(0.0, min(1.0, reveal * (1.0 + MAXIMUM_ROW_STAGGER) - delay))


def fade_in(widget: QWidget, delay_milliseconds: int = 0, duration_milliseconds: int = FADE_MILLISECONDS) -> None:
    if not motion_enabled():
        return
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)
    fade = QPropertyAnimation(effect, b"opacity", widget)
    fade.setDuration(duration_milliseconds)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(QEasingCurve.Type.OutCubic)
    sequence = QSequentialAnimationGroup(widget)
    sequence.addAnimation(QPauseAnimation(delay_milliseconds))
    sequence.addAnimation(fade)
    sequence.finished.connect(lambda: widget.setGraphicsEffect(None))
    sequence.start(QSequentialAnimationGroup.DeletionPolicy.DeleteWhenStopped)


def fade_in_window(window: QWidget) -> None:
    if not motion_enabled():
        return
    window.setWindowOpacity(0.0)
    fade = QPropertyAnimation(window, b"windowOpacity", window)
    fade.setDuration(WINDOW_FADE_MILLISECONDS)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(QEasingCurve.Type.OutCubic)
    fade.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


def build_value_animation(target: QWidget, property_name: bytes) -> QPropertyAnimation:
    animation = QPropertyAnimation(target, property_name, target)
    animation.setDuration(PROGRESS_MILLISECONDS if motion_enabled() else 0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    return animation
