from datetime import datetime
from time import perf_counter

from domain.entities.evaluation_request import EvaluationRequest
from domain.entities.evaluation_result import EvaluationResult
from domain.entities.evaluation_sample import EvaluationSample
from domain.entities.question_score import QuestionScore
from domain.entities.rag_answer import RagAnswer
from domain.errors import DomainError, EvaluationCancelledError
from domain.gateways.language_model_gateway import LanguageModelGateway
from domain.gateways.rag_gateway import RagGateway
from domain.usecases.progress import CancellationCheck, ProgressListener, ignore_progress, never_cancelled

MISSING_RAG_GATEWAY_MESSAGE = "This build cannot call RAG endpoints."
MISSING_SETTINGS_MESSAGE = "The evaluation needs a model endpoint or a RAG endpoint."


class RunEvaluation:
    def __init__(self, language_model_gateway: LanguageModelGateway, rag_gateway: RagGateway | None = None):
        self._language_model_gateway = language_model_gateway
        self._rag_gateway = rag_gateway

    def execute(
        self,
        request: EvaluationRequest,
        on_progress: ProgressListener | None = None,
        is_cancelled: CancellationCheck | None = None,
    ) -> EvaluationResult:
        notify_progress = on_progress or ignore_progress
        was_cancelled = is_cancelled or never_cancelled
        self._check_request(request)

        scores = []
        for position, question in enumerate(request.questions, start=1):
            if was_cancelled():
                raise EvaluationCancelledError()
            started_at = perf_counter()
            rag_answer = self._ask(request, question.text)
            response_seconds = perf_counter() - started_at
            sample = EvaluationSample(question, rag_answer.answer, rag_answer.contexts)
            score = request.method.score_sample(sample)
            scores.append(QuestionScore(question, rag_answer.answer, score, response_seconds, rag_answer.contexts))
            notify_progress(position, len(request.questions))

        return EvaluationResult(tuple(scores), datetime.now(), request.method)

    def _check_request(self, request: EvaluationRequest) -> None:
        if request.rag_settings is not None and self._rag_gateway is None:
            raise DomainError(MISSING_RAG_GATEWAY_MESSAGE)
        if request.rag_settings is None and request.settings is None:
            raise DomainError(MISSING_SETTINGS_MESSAGE)

    def _ask(self, request: EvaluationRequest, question_text: str) -> RagAnswer:
        if request.rag_settings is not None:
            return self._rag_gateway.ask(request.rag_settings, question_text)
        answer = self._language_model_gateway.ask(request.settings, question_text)
        return RagAnswer(answer, None)
