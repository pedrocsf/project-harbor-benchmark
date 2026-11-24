from collections.abc import Sequence

from domain.entities.evaluation_result import EvaluationResult
from domain.entities.evaluation_sample import EvaluationSample
from domain.entities.metric_overview import MetricOverview, MetricOverviewEntry
from domain.scoring.sample_requirements import MetricGroup, available_requirements
from domain.scoring.scoring_method import ScoringMethod


class BuildMetricOverview:
    def available_groups(self, result: EvaluationResult, methods: Sequence[ScoringMethod]) -> tuple[MetricGroup, ...]:
        return tuple(
            group
            for group in MetricGroup
            if any(method.metric_group is group and self._is_included(result, method) for method in methods)
        )

    def execute(
        self, result: EvaluationResult, methods: Sequence[ScoringMethod], group: MetricGroup | None = None
    ) -> MetricOverview:
        included_methods = [
            method
            for method in methods
            if (group is None or method.metric_group is group) and self._is_included(result, method)
        ]
        entries = tuple(MetricOverviewEntry(method, self._scores_for(result, method)) for method in included_methods)
        questions = tuple(score.question for score in result.scores)
        return MetricOverview(questions, entries, result.evaluated_at, group)

    def _is_included(self, result: EvaluationResult, method: ScoringMethod) -> bool:
        if method.identifier == result.method.identifier:
            return True
        if method.uses_language_model:
            return False
        return method.requirements <= available_requirements(
            (score.question for score in result.scores), result.has_contexts
        )

    def _scores_for(self, result: EvaluationResult, method: ScoringMethod) -> tuple[float, ...]:
        if method.identifier == result.method.identifier:
            return tuple(score.score for score in result.scores)
        return tuple(method.score_sample(EvaluationSample.from_score(score)) for score in result.scores)
