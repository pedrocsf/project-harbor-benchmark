from dataclasses import dataclass
from datetime import datetime

from domain.entities.evaluation_result import EvaluationResult
from domain.entities.evaluation_sample import EvaluationSample
from domain.entities.imported_answer import ImportedAnswer
from domain.entities.imported_run import ImportedRun
from domain.entities.question import Question
from domain.entities.question_score import QuestionScore
from domain.errors import EvaluationCancelledError, RunImportError
from domain.scoring.scoring_method import ScoringMethod
from domain.usecases.progress import CancellationCheck, ProgressListener, ignore_progress, never_cancelled

MISSING_ANSWERS_MESSAGE = "The imported run has no answer for question(s): {identifiers}."
LISTED_IDENTIFIER_LIMIT = 5


@dataclass(frozen=True)
class ScoreImportedRunRequest:
    run: ImportedRun
    questions: tuple[Question, ...]
    method: ScoringMethod


class ScoreImportedRun:
    def execute(
        self,
        request: ScoreImportedRunRequest,
        on_progress: ProgressListener | None = None,
        is_cancelled: CancellationCheck | None = None,
    ) -> EvaluationResult:
        notify_progress = on_progress or ignore_progress
        was_cancelled = is_cancelled or never_cancelled
        answers = self._answers_by_question(request)

        scores = []
        for position, question in enumerate(request.questions, start=1):
            if was_cancelled():
                raise EvaluationCancelledError()
            answer = answers[question.identifier]
            sample = EvaluationSample(question, answer.answer, answer.contexts)
            score = request.method.score_sample(sample)
            scores.append(QuestionScore(question, answer.answer, score, answer.response_seconds, answer.contexts))
            notify_progress(position, len(request.questions))

        return EvaluationResult(tuple(scores), datetime.now(), request.method)

    def _answers_by_question(self, request: ScoreImportedRunRequest) -> dict[str, ImportedAnswer]:
        answers = {answer.question_identifier: answer for answer in request.run.answers}
        missing = [question.identifier for question in request.questions if question.identifier not in answers]
        if missing:
            listed = ", ".join(missing[:LISTED_IDENTIFIER_LIMIT])
            if len(missing) > LISTED_IDENTIFIER_LIMIT:
                listed += f" and {len(missing) - LISTED_IDENTIFIER_LIMIT} more"
            raise RunImportError(MISSING_ANSWERS_MESSAGE.format(identifiers=listed))
        return answers
