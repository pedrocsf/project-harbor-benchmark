import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from domain.entities.evaluation_request import EvaluationRequest
from domain.entities.evaluation_result import EvaluationResult
from domain.entities.imported_run import ImportedRun
from domain.entities.language_model_settings import LanguageModelSettings
from domain.entities.question import Question
from domain.entities.rag_endpoint_settings import (
    DEFAULT_ANSWER_FIELD,
    DEFAULT_CONTEXTS_FIELD,
    RagEndpointSettings,
)
from domain.errors import DomainError, EvaluationCancelledError
from domain.scoring.metric_parameters import InvalidParameterError, ParameterValues
from domain.scoring.sample_requirements import (
    REQUIREMENT_DESCRIPTIONS,
    SampleRequirement,
    available_requirements,
    missing_requirements,
)
from domain.scoring.scoring_method import ScoringMethod
from domain.usecases.build_metric_overview import BuildMetricOverview
from domain.usecases.export_result import ExportResult
from domain.usecases.load_imported_run import LoadImportedRun
from domain.usecases.load_questions import LoadQuestions
from domain.usecases.progress import CancellationCheck, ProgressListener
from domain.usecases.rescore_result import RescoreResult
from domain.usecases.run_evaluation import RunEvaluation
from domain.usecases.score_imported_run import ScoreImportedRun, ScoreImportedRunRequest
from presentation.controllers.answer_source import AnswerSource, EndpointInput, RagEndpointInput

MISSING_ENDPOINT_MESSAGE = "Enter the LLM URL."
MISSING_RAG_ENDPOINT_MESSAGE = "Enter the RAG endpoint URL."
MISSING_IMPORTED_RUN_MESSAGE = "Load a run file first."
MISSING_DATASET_MESSAGE = "Load a dataset first."
JUDGE_REQUIRED_MESSAGE = "{name} uses a judge model. Fill in the judge model URL."
UNAVAILABLE_METRIC_MESSAGE = "{name} is not available. {reason}"
IMPORT_NOT_SUPPORTED_MESSAGE = "This build cannot import runs."
RUNNING_STATUS = "Running…"
SCORING_STATUS = "Scoring…"
SHUTDOWN_WAIT_MILLISECONDS = 3000

BackgroundTask = Callable[[ProgressListener, CancellationCheck], object]
CompletionHandler = Callable[[object], None]
FailureHandler = Callable[[str], None]


@dataclass(frozen=True)
class EvaluationUseCases:
    load_questions: LoadQuestions
    run_evaluation: RunEvaluation
    rescore_result: RescoreResult
    build_overview: BuildMetricOverview
    export_result: ExportResult
    load_imported_run: LoadImportedRun | None = None
    score_imported_run: ScoreImportedRun | None = None


class BackgroundWorker(QThread):
    progressed = Signal(int, int)
    completed = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, task: BackgroundTask, parent: QObject | None = None):
        super().__init__(parent)
        self._task = task
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def run(self) -> None:
        try:
            outcome = self._task(self.progressed.emit, self._cancel_event.is_set)
        except EvaluationCancelledError:
            self.cancelled.emit()
        except DomainError as error:
            self.failed.emit(str(error))
        except Exception as error:
            self.failed.emit(f"Unexpected error: {error}")
        else:
            self.completed.emit(outcome)


class EvaluationController(QObject):
    dataset_loaded = Signal(str, int)
    dataset_failed = Signal(str)
    started = Signal(str, bool)
    progressed = Signal(int, int)
    completed = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    exported = Signal(str)
    export_failed = Signal(str)
    overview_ready = Signal(object)
    overview_failed = Signal(str)
    parameters_changed = Signal(str)
    parameters_failed = Signal(str)
    run_import_loaded = Signal(str, int, bool)
    run_import_failed = Signal(str)
    availability_changed = Signal()

    def __init__(self, use_cases: EvaluationUseCases, scoring_methods: Sequence[ScoringMethod]):
        super().__init__()
        self._use_cases = use_cases
        self._scoring_methods = list(scoring_methods)
        self._selected_method = self._scoring_methods[0]
        self._questions: list[Question] = []
        self._worker: BackgroundWorker | None = None
        self._last_result: EvaluationResult | None = None
        self._is_rescoring = False
        self._parameter_snapshot: tuple[ScoringMethod, dict] | None = None
        self._answer_source = AnswerSource.MODEL_ENDPOINT
        self._imported_run: ImportedRun | None = None

    @property
    def scoring_methods(self) -> list[ScoringMethod]:
        return list(self._scoring_methods)

    @property
    def selected_method(self) -> ScoringMethod:
        return self._selected_method

    @property
    def questions(self) -> list[Question]:
        return list(self._questions)

    @property
    def answer_source(self) -> AnswerSource:
        return self._answer_source

    @property
    def imported_run(self) -> ImportedRun | None:
        return self._imported_run

    @property
    def supports_run_import(self) -> bool:
        return self._use_cases.load_imported_run is not None and self._use_cases.score_imported_run is not None

    @property
    def available_requirements(self) -> frozenset[SampleRequirement]:
        if self._last_result is not None:
            return available_requirements(self._questions, self._last_result.has_contexts)
        return self._planned_requirements()

    def missing_requirements_for(self, method: ScoringMethod) -> tuple[SampleRequirement, ...]:
        return missing_requirements(method.requirements, self.available_requirements)

    def load_dataset(self, source: Path) -> None:
        try:
            questions = self._use_cases.load_questions.execute(source)
        except DomainError as error:
            self.dataset_failed.emit(str(error))
            return
        self._questions = questions
        self._last_result = None
        self.dataset_loaded.emit(str(source), len(questions))
        self.availability_changed.emit()

    def set_answer_source(self, source: AnswerSource) -> None:
        if source is self._answer_source or self._worker is not None:
            return
        self._answer_source = source
        self._last_result = None
        self.availability_changed.emit()

    def load_imported_run(self, source: Path) -> None:
        if not self.supports_run_import:
            self.run_import_failed.emit(IMPORT_NOT_SUPPORTED_MESSAGE)
            return
        try:
            imported_run = self._use_cases.load_imported_run.execute(source)
        except DomainError as error:
            self.run_import_failed.emit(str(error))
            return
        self._imported_run = imported_run
        if self._answer_source is AnswerSource.IMPORTED_RUN:
            self._last_result = None
        self.run_import_loaded.emit(imported_run.source_name, len(imported_run.answers), imported_run.has_contexts)
        self.availability_changed.emit()

    def method_by_identifier(self, identifier: str) -> ScoringMethod | None:
        return next((candidate for candidate in self._scoring_methods if candidate.identifier == identifier), None)

    def update_method_parameters(self, identifier: str, values: ParameterValues) -> None:
        self._change_parameters(identifier, lambda method: method.update_parameters(values))

    def reset_method_parameters(self, identifier: str) -> None:
        self._change_parameters(identifier, lambda method: method.reset_parameters())

    def select_method(self, identifier: str) -> None:
        method = self.method_by_identifier(identifier)
        if method is None or method is self._selected_method or self._worker is not None:
            return
        if self.missing_requirements_for(method):
            return
        self._selected_method = method
        if self._last_result is not None:
            self._launch_rescoring(self._last_result, method)

    def start_evaluation(
        self,
        endpoint_url: str,
        api_key: str,
        model_name: str,
        rag_input: RagEndpointInput | None = None,
    ) -> None:
        if self._worker is not None:
            return
        problem = self._find_start_problem(EndpointInput(endpoint_url, api_key, model_name), rag_input)
        if problem is not None:
            self.failed.emit(problem)
            return
        settings = self._model_settings(EndpointInput(endpoint_url, api_key, model_name))
        for scoring_method in self._scoring_methods:
            scoring_method.configure(settings)
        task, status_text = self._build_run_task(settings, rag_input)
        self._last_result = None
        self._is_rescoring = False
        self._launch_worker(
            task,
            self._handle_completed,
            self._handle_failed,
            status_text=status_text,
            is_cancellable=True,
        )

    def _find_start_problem(self, model_input: EndpointInput, rag_input: RagEndpointInput | None) -> str | None:
        if not self._questions:
            return MISSING_DATASET_MESSAGE
        source_problem = self._find_source_problem(model_input, rag_input)
        if source_problem is not None:
            return source_problem
        method = self._selected_method
        missing = missing_requirements(method.requirements, self._planned_requirements())
        if missing:
            return UNAVAILABLE_METRIC_MESSAGE.format(
                name=method.display_name, reason=REQUIREMENT_DESCRIPTIONS[missing[0]]
            )
        if method.uses_language_model and not model_input.url.strip():
            return JUDGE_REQUIRED_MESSAGE.format(name=method.display_name)
        return None

    def _find_source_problem(self, model_input: EndpointInput, rag_input: RagEndpointInput | None) -> str | None:
        if self._answer_source is AnswerSource.MODEL_ENDPOINT and not model_input.url.strip():
            return MISSING_ENDPOINT_MESSAGE
        if self._answer_source is AnswerSource.RAG_ENDPOINT and (rag_input is None or not rag_input.url.strip()):
            return MISSING_RAG_ENDPOINT_MESSAGE
        if self._answer_source is AnswerSource.IMPORTED_RUN and self._imported_run is None:
            return MISSING_IMPORTED_RUN_MESSAGE
        return None

    def _model_settings(self, model_input: EndpointInput) -> LanguageModelSettings | None:
        if not model_input.url.strip():
            return None
        return LanguageModelSettings(
            endpoint_url=model_input.url.strip(),
            api_key=model_input.api_key.strip() or None,
            model_name=model_input.model_name.strip() or None,
        )

    def _build_run_task(
        self, settings: LanguageModelSettings | None, rag_input: RagEndpointInput | None
    ) -> tuple[BackgroundTask, str]:
        questions = tuple(self._questions)
        method = self._selected_method
        if self._answer_source is AnswerSource.IMPORTED_RUN:
            request = ScoreImportedRunRequest(self._imported_run, questions, method)
            score_imported_run = self._use_cases.score_imported_run
            return (
                lambda on_progress, is_cancelled: score_imported_run.execute(request, on_progress, is_cancelled),
                SCORING_STATUS,
            )
        rag_settings = self._rag_settings(rag_input) if self._answer_source is AnswerSource.RAG_ENDPOINT else None
        request = EvaluationRequest(settings, questions, method, rag_settings)
        run_evaluation = self._use_cases.run_evaluation
        return (
            lambda on_progress, is_cancelled: run_evaluation.execute(request, on_progress, is_cancelled),
            RUNNING_STATUS,
        )

    def _rag_settings(self, rag_input: RagEndpointInput) -> RagEndpointSettings:
        return RagEndpointSettings(
            endpoint_url=rag_input.url.strip(),
            api_key=rag_input.api_key.strip() or None,
            answer_field=rag_input.answer_field.strip() or DEFAULT_ANSWER_FIELD,
            contexts_field=rag_input.contexts_field.strip() or DEFAULT_CONTEXTS_FIELD,
        )

    def _planned_requirements(self) -> frozenset[SampleRequirement]:
        return available_requirements(self._questions, self._planned_contexts())

    def _planned_contexts(self) -> bool:
        if self._answer_source is AnswerSource.RAG_ENDPOINT:
            return True
        if self._answer_source is AnswerSource.IMPORTED_RUN:
            return self._imported_run is not None and self._imported_run.has_contexts
        return False

    def cancel_evaluation(self) -> None:
        if self._worker is not None:
            self._worker.cancel()

    def shutdown(self) -> None:
        worker = self._worker
        if worker is None:
            return
        worker.cancel()
        if not worker.wait(SHUTDOWN_WAIT_MILLISECONDS):
            worker.terminate()
            worker.wait()

    def build_overview(self) -> None:
        if self._worker is not None or self._last_result is None:
            return
        result = self._last_result
        self._launch_worker(
            lambda on_progress, is_cancelled: self._use_cases.build_overview.execute(result, self._scoring_methods),
            self._handle_overview_ready,
            self._handle_overview_failed,
        )

    def export_last_result(self, destination: Path) -> None:
        if self._last_result is None:
            return
        try:
            self._use_cases.export_result.execute(self._last_result, destination)
        except DomainError as error:
            self.export_failed.emit(str(error))
            return
        self.exported.emit(str(destination))

    def _change_parameters(self, identifier: str, apply_change: Callable[[ScoringMethod], None]) -> None:
        method = self.method_by_identifier(identifier)
        if method is None or self._worker is not None:
            return
        snapshot = method.parameters
        try:
            apply_change(method)
        except InvalidParameterError as error:
            self.parameters_failed.emit(str(error))
            return
        self.parameters_changed.emit(identifier)
        if self._last_result is not None and method is self._selected_method:
            self._parameter_snapshot = (method, snapshot)
            self._launch_rescoring(self._last_result, method)

    def _restore_parameter_snapshot(self) -> None:
        if self._parameter_snapshot is None:
            return
        method, snapshot = self._parameter_snapshot
        self._parameter_snapshot = None
        method.update_parameters(snapshot)
        self.parameters_changed.emit(method.identifier)

    def _launch_rescoring(self, result: EvaluationResult, method: ScoringMethod) -> None:
        self._is_rescoring = True
        self._launch_worker(
            lambda on_progress, is_cancelled: self._use_cases.rescore_result.execute(result, method, on_progress),
            self._handle_completed,
            self._handle_failed,
            status_text=SCORING_STATUS,
        )

    def _launch_worker(
        self,
        task: BackgroundTask,
        on_completed: CompletionHandler,
        on_failed: FailureHandler,
        status_text: str | None = None,
        is_cancellable: bool = False,
    ) -> None:
        worker = BackgroundWorker(task, parent=self)
        worker.progressed.connect(self.progressed)
        worker.completed.connect(on_completed)
        worker.failed.connect(on_failed)
        worker.cancelled.connect(self.cancelled)
        worker.finished.connect(self._release_worker)
        self._worker = worker
        if status_text is not None:
            self.started.emit(status_text, is_cancellable)
        worker.start()

    def _handle_completed(self, result: EvaluationResult) -> None:
        self._last_result = result
        self._is_rescoring = False
        self._parameter_snapshot = None
        self.completed.emit(result)

    def _handle_failed(self, message: str) -> None:
        self._restore_parameter_snapshot()
        self.failed.emit(message)
        if self._is_rescoring and self._last_result is not None:
            self._is_rescoring = False
            self._selected_method = self._last_result.method
            self.completed.emit(self._last_result)

    def _handle_overview_ready(self, overview: object) -> None:
        self.overview_ready.emit(overview)

    def _handle_overview_failed(self, message: str) -> None:
        self.overview_failed.emit(message)

    def _release_worker(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
        self._worker = None
