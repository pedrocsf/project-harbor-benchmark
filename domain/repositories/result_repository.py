from abc import ABC, abstractmethod
from collections.abc import Mapping
from pathlib import Path

from domain.entities.evaluation_result import EvaluationResult

CompanionScores = Mapping[str, tuple[float, ...]]


class ResultRepository(ABC):
    @abstractmethod
    def save(
        self, result: EvaluationResult, destination: Path, companion_scores: CompanionScores | None = None
    ) -> None:
        ...
