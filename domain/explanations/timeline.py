from collections.abc import Sequence
from dataclasses import dataclass

COMPLETE_PROGRESS = 1.0
EMPTY_DURATIONS_MESSAGE = "A timeline needs at least one step."
NON_POSITIVE_DURATION_MESSAGE = "Every step must last longer than zero seconds: {duration!r}"
NEGATIVE_HOLD_MESSAGE = "The final hold cannot be negative: {hold!r}"
NEGATIVE_ELAPSED_MESSAGE = "Elapsed time cannot be negative: {elapsed!r}"
STEP_OUT_OF_RANGE_MESSAGE = "Step {step_index} does not exist in a timeline of {step_count} steps."


@dataclass(frozen=True)
class TimelinePosition:
    step_index: int
    step_progress: float
    is_holding: bool


def _validate(step_durations: Sequence[float], hold_seconds: float) -> None:
    if not step_durations:
        raise ValueError(EMPTY_DURATIONS_MESSAGE)
    for duration in step_durations:
        if duration <= 0:
            raise ValueError(NON_POSITIVE_DURATION_MESSAGE.format(duration=duration))
    if hold_seconds < 0:
        raise ValueError(NEGATIVE_HOLD_MESSAGE.format(hold=hold_seconds))


def total_cycle_seconds(step_durations: Sequence[float], hold_seconds: float) -> float:
    _validate(step_durations, hold_seconds)
    return sum(step_durations) + hold_seconds


def step_start_seconds(step_durations: Sequence[float], step_index: int) -> float:
    if not 0 <= step_index < len(step_durations):
        raise ValueError(STEP_OUT_OF_RANGE_MESSAGE.format(step_index=step_index, step_count=len(step_durations)))
    return sum(step_durations[:step_index])


def position_at(elapsed_seconds: float, step_durations: Sequence[float], hold_seconds: float) -> TimelinePosition:
    if elapsed_seconds < 0:
        raise ValueError(NEGATIVE_ELAPSED_MESSAGE.format(elapsed=elapsed_seconds))
    moment = elapsed_seconds % total_cycle_seconds(step_durations, hold_seconds)
    for step_index, duration in enumerate(step_durations):
        if moment < duration:
            return TimelinePosition(step_index, moment / duration, False)
        moment -= duration
    return TimelinePosition(len(step_durations) - 1, COMPLETE_PROGRESS, True)
