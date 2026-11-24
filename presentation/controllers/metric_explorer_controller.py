from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal

from domain.explanations.metric_walkthrough import MetricWalkthrough
from domain.explanations.timeline import TimelinePosition, position_at, step_start_seconds, total_cycle_seconds
from domain.scoring.scoring_method import ScoreKind, ScoringMethod
from domain.usecases.build_metric_walkthrough import BuildMetricWalkthrough, WalkthroughRequest

PLAYBACK_SPEEDS = (0.5, 1.0, 2.0)
DEFAULT_SPEED = 1.0
HOLD_SECONDS = 2.0
DEFAULT_EXAMPLE_INDEX = 1
STEP_JUMP_EPSILON = 1e-6
COMPLETE_PROGRESS = 1.0
NO_METHODS_MESSAGE = "The metric explorer needs at least one scoring method."
NO_EXAMPLES_MESSAGE = "The metric explorer needs at least one example."
UNKNOWN_METRIC_MESSAGE = "Unknown metric {identifier!r}."
UNKNOWN_EXAMPLE_MESSAGE = "There is no example at index {index}."
UNSUPPORTED_SPEED_MESSAGE = "Unsupported playback speed {speed!r}; choose one of {speeds}."
NEGATIVE_DELTA_MESSAGE = "Time cannot move backwards: {delta!r}"


@dataclass(frozen=True)
class ExplorerMetric:
    identifier: str
    display_name: str
    score_kind: ScoreKind


@dataclass(frozen=True)
class ExplorerExample:
    identifier: str
    question: str
    expected_answer: str
    given_answer: str
    scores: Mapping[str, float]


class MetricExplorerController(QObject):
    metric_changed = Signal(str)
    example_changed = Signal(int)
    playback_changed = Signal()
    position_changed = Signal()
    parameters_refreshed = Signal()

    def __init__(
        self,
        scoring_methods: Sequence[ScoringMethod],
        examples: Sequence[ExplorerExample],
        build_walkthrough: BuildMetricWalkthrough,
        step_durations: Callable[[str], Sequence[float]],
        motion_enabled: bool = True,
    ):
        super().__init__()
        if not scoring_methods:
            raise ValueError(NO_METHODS_MESSAGE)
        if not examples:
            raise ValueError(NO_EXAMPLES_MESSAGE)
        self._scoring_methods = {method.identifier: method for method in scoring_methods}
        self._metrics = tuple(
            ExplorerMetric(method.identifier, method.display_name, method.score_kind) for method in scoring_methods
        )
        self._examples = tuple(examples)
        self._build_walkthrough = build_walkthrough
        self._step_durations = step_durations
        self._motion_enabled = motion_enabled
        self._metric_index = 0
        self._example_index = min(DEFAULT_EXAMPLE_INDEX, len(self._examples) - 1)
        self._is_playing = motion_enabled
        self._speed = DEFAULT_SPEED
        self._elapsed_seconds = 0.0
        self._manual_step_index = 0
        self._walkthroughs: dict[tuple[str, int], MetricWalkthrough] = {}

    @property
    def metrics(self) -> tuple[ExplorerMetric, ...]:
        return self._metrics

    @property
    def examples(self) -> tuple[ExplorerExample, ...]:
        return self._examples

    @property
    def selected_metric(self) -> ExplorerMetric:
        return self._metrics[self._metric_index]

    @property
    def selected_example_index(self) -> int:
        return self._example_index

    @property
    def selected_example(self) -> ExplorerExample:
        return self._examples[self._example_index]

    @property
    def motion_enabled(self) -> bool:
        return self._motion_enabled

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def elapsed_seconds(self) -> float:
        return self._elapsed_seconds

    @property
    def step_durations(self) -> tuple[float, ...]:
        return tuple(self._step_durations(self.selected_metric.identifier))

    @property
    def step_count(self) -> int:
        return len(self.step_durations)

    @property
    def current_walkthrough(self) -> MetricWalkthrough:
        key = (self.selected_metric.identifier, self._example_index)
        if key not in self._walkthroughs:
            self._walkthroughs[key] = self._build_current_walkthrough()
        return self._walkthroughs[key]

    @property
    def current_position(self) -> TimelinePosition:
        if not self._motion_enabled:
            return TimelinePosition(self._manual_step_index, COMPLETE_PROGRESS, False)
        return position_at(self._elapsed_seconds, self.step_durations, HOLD_SECONDS)

    def select_metric(self, identifier: str) -> None:
        index = next((position for position, metric in enumerate(self._metrics) if metric.identifier == identifier), None)
        if index is None:
            raise ValueError(UNKNOWN_METRIC_MESSAGE.format(identifier=identifier))
        if index == self._metric_index:
            return
        self._metric_index = index
        self._reset_timeline()
        self.metric_changed.emit(identifier)
        self.position_changed.emit()

    def select_example(self, index: int) -> None:
        if not 0 <= index < len(self._examples):
            raise ValueError(UNKNOWN_EXAMPLE_MESSAGE.format(index=index))
        if index == self._example_index:
            return
        self._example_index = index
        self._reset_timeline()
        self.example_changed.emit(index)
        self.position_changed.emit()

    def refresh_parameters(self, identifier: str) -> None:
        if identifier not in self._scoring_methods:
            return
        self._walkthroughs = {key: value for key, value in self._walkthroughs.items() if key[0] != identifier}
        if identifier == self.selected_metric.identifier:
            self.parameters_refreshed.emit()
            self.position_changed.emit()

    def toggle_play(self) -> None:
        if not self._motion_enabled:
            return
        self._is_playing = not self._is_playing
        self.playback_changed.emit()

    def set_speed(self, speed: float) -> None:
        if speed not in PLAYBACK_SPEEDS:
            raise ValueError(UNSUPPORTED_SPEED_MESSAGE.format(speed=speed, speeds=PLAYBACK_SPEEDS))
        if speed == self._speed:
            return
        self._speed = speed
        self.playback_changed.emit()

    def restart(self) -> None:
        self._reset_timeline()
        self.position_changed.emit()

    def tick(self, delta_seconds: float) -> None:
        if delta_seconds < 0:
            raise ValueError(NEGATIVE_DELTA_MESSAGE.format(delta=delta_seconds))
        if not self._motion_enabled or not self._is_playing:
            return
        cycle_seconds = total_cycle_seconds(self.step_durations, HOLD_SECONDS)
        self._elapsed_seconds = (self._elapsed_seconds + delta_seconds * self._speed) % cycle_seconds
        self.position_changed.emit()

    def next_step(self) -> None:
        self._jump_to_step((self.current_position.step_index + 1) % self.step_count)

    def previous_step(self) -> None:
        self._jump_to_step((self.current_position.step_index - 1) % self.step_count)

    def _jump_to_step(self, step_index: int) -> None:
        self._manual_step_index = step_index
        self._elapsed_seconds = step_start_seconds(self.step_durations, step_index) + STEP_JUMP_EPSILON
        self.position_changed.emit()

    def _reset_timeline(self) -> None:
        self._elapsed_seconds = 0.0
        self._manual_step_index = 0

    def _build_current_walkthrough(self) -> MetricWalkthrough:
        example = self.selected_example
        identifier = self.selected_metric.identifier
        method = self._scoring_methods[identifier]
        return self._build_walkthrough.execute(
            WalkthroughRequest(
                identifier,
                example.expected_answer,
                example.given_answer,
                known_score=method.score(example.expected_answer, example.given_answer),
                parameters=method.parameters,
            )
        )
