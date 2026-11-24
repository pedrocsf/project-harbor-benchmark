from dataclasses import replace

from domain.entities.evaluation_result import EvaluationResult
from domain.entities.evaluation_sample import EvaluationSample
from domain.scoring.scoring_method import ScoringMethod
from domain.usecases.progress import ProgressListener, ignore_progress


class RescoreResult:
    def execute(
        self,
        result: EvaluationResult,
        method: ScoringMethod,
        on_progress: ProgressListener | None = None,
    ) -> EvaluationResult:
        notify_progress = on_progress or ignore_progress
        rescored = []
        for position, score in enumerate(result.scores, start=1):
            new_value = method.score_sample(EvaluationSample.from_score(score))
            rescored.append(replace(score, score=new_value))
            notify_progress(position, len(result.scores))
        return EvaluationResult(tuple(rescored), result.evaluated_at, method)
