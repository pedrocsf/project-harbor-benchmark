from collections.abc import Mapping, Sequence
from datetime import datetime
from time import sleep

from demo.demo_data import DemoEntry
from demo.demo_rag_data import DemoRagEntry
from domain.entities.evaluation_request import EvaluationRequest
from domain.entities.evaluation_result import EvaluationResult
from domain.entities.evaluation_sample import EvaluationSample
from domain.entities.question_score import QuestionScore
from domain.errors import EvaluationCancelledError
from domain.usecases.progress import CancellationCheck, ProgressListener, ignore_progress, never_cancelled

DEFAULT_STEP_SECONDS = 0.3


class DemoRunEvaluation:
    def __init__(
        self,
        entries: Sequence[DemoEntry],
        step_seconds: float = DEFAULT_STEP_SECONDS,
        rag_entries: Mapping[str, DemoRagEntry] | None = None,
    ):
        self._entries_by_identifier = {entry.identifier: entry for entry in entries}
        self._step_seconds = step_seconds
        self._rag_entries = rag_entries or {}

    def execute(
        self,
        request: EvaluationRequest,
        on_progress: ProgressListener | None = None,
        is_cancelled: CancellationCheck | None = None,
    ) -> EvaluationResult:
        notify_progress = on_progress or ignore_progress
        was_cancelled = is_cancelled or never_cancelled

        scores = []
        for position, question in enumerate(request.questions, start=1):
            if was_cancelled():
                raise EvaluationCancelledError()
            sleep(self._step_seconds)
            entry = self._entries_by_identifier[question.identifier]
            contexts = self._contexts_for(request, question.identifier)
            score = request.method.score_sample(EvaluationSample(question, entry.given_answer, contexts))
            scores.append(QuestionScore(question, entry.given_answer, score, entry.response_seconds, contexts))
            notify_progress(position, len(request.questions))

        return EvaluationResult(tuple(scores), datetime.now(), request.method)

    def _contexts_for(self, request: EvaluationRequest, identifier: str):
        if request.rag_settings is None:
            return None
        rag_entry = self._rag_entries.get(identifier)
        return rag_entry.contexts if rag_entry is not None else ()
