from abc import ABC, abstractmethod
from dataclasses import dataclass

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter

from domain.explanations.metric_walkthrough import MetricWalkthrough
from domain.explanations.timeline import TimelinePosition


@dataclass(frozen=True)
class SceneStep:
    title: str
    body: str
    duration_seconds: float
    formula_lines: tuple[int, ...]


class WalkthroughScene(ABC):
    identifier: str

    @property
    @abstractmethod
    def steps(self) -> tuple[SceneStep, ...]:
        ...

    @property
    @abstractmethod
    def formula(self) -> tuple[str, ...]:
        ...

    @property
    @abstractmethod
    def limitation(self) -> str:
        ...

    @abstractmethod
    def paint(self, painter: QPainter, area: QRectF, walkthrough: MetricWalkthrough, position: TimelinePosition) -> None:
        ...

    @property
    def step_durations(self) -> tuple[float, ...]:
        return tuple(step.duration_seconds for step in self.steps)

    def step_body(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        return self.steps[step_index].body

    def formula_lines_for(self, step_index: int, walkthrough: MetricWalkthrough) -> tuple[int, ...]:
        return self.steps[step_index].formula_lines

    def formula_result(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        return ""

    def formula_for(self, walkthrough: MetricWalkthrough) -> tuple[str, ...]:
        return self.formula

    def limitation_for(self, walkthrough: MetricWalkthrough) -> str:
        return self.limitation
