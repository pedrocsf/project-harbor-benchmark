from collections.abc import Sequence
from pathlib import Path

from domain.entities.evaluation_result import EvaluationResult
from domain.entities.evaluation_sample import EvaluationSample
from domain.repositories.result_repository import CompanionScores, ResultRepository
from domain.scoring.sample_requirements import MetricGroup, available_requirements
from domain.scoring.scoring_method import ScoringMethod

COMPANION_GROUPS = (MetricGroup.RETRIEVAL, MetricGroup.GROUNDING)


class ExportResult:
    def __init__(self, result_repository: ResultRepository, companion_methods: Sequence[ScoringMethod] = ()):
        self._result_repository = result_repository
        self._companion_methods = tuple(companion_methods)

    def execute(self, result: EvaluationResult, destination: Path) -> None:
        self._result_repository.save(result, destination, self._companion_scores(result))

    def _companion_scores(self, result: EvaluationResult) -> CompanionScores:
        available = available_requirements((score.question for score in result.scores), result.has_contexts)
        return {
            method.identifier: tuple(
                method.score_sample(EvaluationSample.from_score(score)) for score in result.scores
            )
            for method in self._companion_methods
            if self._is_companion(method, result, available)
        }

    def _is_companion(self, method: ScoringMethod, result: EvaluationResult, available) -> bool:
        return (
            method.metric_group in COMPANION_GROUPS
            and not method.uses_language_model
            and method.identifier != result.method.identifier
            and method.requirements <= available
        )
