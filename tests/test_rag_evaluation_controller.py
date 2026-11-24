from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QThread

from domain.entities.imported_answer import ImportedAnswer
from domain.entities.question import Question
from domain.entities.rag_answer import RagAnswer
from domain.entities.retrieved_context import RetrievedContext
from domain.errors import RunImportError
from domain.repositories.question_repository import QuestionRepository
from domain.scoring.exact_match_scoring_method import ExactMatchScoringMethod
from domain.scoring.rag.context_overlap_scoring_methods import KPrecisionScoringMethod
from domain.scoring.rag.faithfulness_scoring_method import FaithfulnessScoringMethod
from domain.scoring.rag.retrieval_scoring_methods import HitRateScoringMethod
from domain.scoring.sample_requirements import SampleRequirement
from domain.usecases.build_metric_overview import BuildMetricOverview
from domain.usecases.export_result import ExportResult
from domain.usecases.load_imported_run import LoadImportedRun
from domain.usecases.load_questions import LoadQuestions
from domain.usecases.rescore_result import RescoreResult
from domain.usecases.run_evaluation import RunEvaluation
from domain.usecases.score_imported_run import ScoreImportedRun
from presentation.controllers.answer_source import AnswerSource, RagEndpointInput
from presentation.controllers.evaluation_controller import (
    MISSING_IMPORTED_RUN_MESSAGE,
    MISSING_RAG_ENDPOINT_MESSAGE,
    EvaluationController,
    EvaluationUseCases,
)

WAIT_ATTEMPTS = 300
WAIT_MILLISECONDS = 10
LABELLED = (
    Question("1", "Capital?", "Paris", relevant_context_ids=("geo-1",)),
    Question("2", "Rio?", "Amazonas", relevant_context_ids=("geo-2",)),
)
CONTEXTS = (RetrievedContext("geo-1", "Paris é a capital."),)


class FixedQuestions(QuestionRepository):
    def __init__(self, questions):
        self._questions = list(questions)

    def load(self, source):
        return list(self._questions)


class FixedRun:
    def __init__(self, answers=None, error=None):
        self._answers = answers or []
        self._error = error

    def load(self, source):
        if self._error:
            raise self._error
        return list(self._answers)


class FakeRagGateway:
    def __init__(self):
        self.settings = []

    def ask(self, settings, question_text):
        self.settings.append(settings)
        return RagAnswer("Paris", CONTEXTS)


def build_controller(questions=LABELLED, run=None, rag_gateway=None, with_import=True):
    use_cases = EvaluationUseCases(
        load_questions=LoadQuestions(FixedQuestions(questions)),
        run_evaluation=RunEvaluation(None, rag_gateway or FakeRagGateway()),
        rescore_result=RescoreResult(),
        build_overview=BuildMetricOverview(),
        export_result=ExportResult(None),
        load_imported_run=LoadImportedRun(run or FixedRun()) if with_import else None,
        score_imported_run=ScoreImportedRun() if with_import else None,
    )
    methods = [ExactMatchScoringMethod(), HitRateScoringMethod(), KPrecisionScoringMethod(), FaithfulnessScoringMethod(None)]
    controller = EvaluationController(use_cases, methods)
    controller.load_dataset(Path("questions.json"))
    return controller


def record(signal):
    received = []
    signal.connect(lambda *arguments: received.append(arguments))
    return received


def wait_for_worker(controller):
    for _ in range(WAIT_ATTEMPTS):
        if controller._worker is None:
            QCoreApplication.processEvents()
            return
        QCoreApplication.processEvents()
        QThread.msleep(WAIT_MILLISECONDS)
    raise AssertionError("worker did not finish")


@pytest.fixture(scope="module")
def core_application():
    return QCoreApplication.instance() or QCoreApplication([])


def missing(controller, identifier):
    return controller.missing_requirements_for(controller.method_by_identifier(identifier))


def test_model_endpoint_source_disables_context_metrics():
    controller = build_controller()

    assert controller.answer_source is AnswerSource.MODEL_ENDPOINT
    assert missing(controller, "exact_match") == ()
    assert missing(controller, "hit_rate") == (SampleRequirement.CONTEXTS,)


def test_rag_source_enables_retrieval_metrics_when_every_question_is_labelled():
    controller = build_controller()
    changes = record(controller.availability_changed)

    controller.set_answer_source(AnswerSource.RAG_ENDPOINT)

    assert changes == [()]
    assert missing(controller, "hit_rate") == ()
    unlabelled = build_controller(questions=(Question("1", "Q?", "A"),))
    unlabelled.set_answer_source(AnswerSource.RAG_ENDPOINT)
    assert missing(unlabelled, "hit_rate") == (SampleRequirement.RELEVANCE_LABELS,)
    assert missing(unlabelled, "k_precision") == ()


def test_unavailable_methods_cannot_be_selected():
    controller = build_controller()

    controller.select_method("hit_rate")

    assert controller.selected_method.identifier == "exact_match"


def test_imported_run_availability_follows_its_contexts():
    run = FixedRun([ImportedAnswer("1", "Paris"), ImportedAnswer("2", "Nilo")])
    controller = build_controller(run=run)
    loaded = record(controller.run_import_loaded)
    controller.set_answer_source(AnswerSource.IMPORTED_RUN)

    controller.load_imported_run(Path("/runs/run.json"))

    assert loaded == [("run.json", 2, False)]
    assert missing(controller, "k_precision") == (SampleRequirement.CONTEXTS,)


def test_reports_an_unreadable_run():
    controller = build_controller(run=FixedRun(error=RunImportError("bad run")))
    failures = record(controller.run_import_failed)

    controller.load_imported_run(Path("run.json"))

    assert failures == [("bad run",)]
    assert controller.imported_run is None


def test_reports_when_imports_are_not_supported():
    controller = build_controller(with_import=False)
    failures = record(controller.run_import_failed)

    controller.load_imported_run(Path("run.json"))

    assert not controller.supports_run_import
    assert len(failures) == 1


@pytest.mark.parametrize(
    ("source", "message"),
    [(AnswerSource.RAG_ENDPOINT, MISSING_RAG_ENDPOINT_MESSAGE), (AnswerSource.IMPORTED_RUN, MISSING_IMPORTED_RUN_MESSAGE)],
)
def test_each_source_needs_its_input(source, message):
    controller = build_controller()
    controller.set_answer_source(source)
    failures = record(controller.failed)

    controller.start_evaluation("", "", "", RagEndpointInput(url="  "))

    assert failures == [(message,)]


def test_judge_metrics_need_a_judge_endpoint_outside_the_model_source():
    controller = build_controller()
    controller.set_answer_source(AnswerSource.RAG_ENDPOINT)
    controller.select_method("faithfulness")
    failures = record(controller.failed)

    controller.start_evaluation("", "", "", RagEndpointInput(url="http://rag"))

    assert len(failures) == 1
    assert "judge model" in failures[0][0]


def test_runs_against_the_rag_endpoint_with_the_given_fields(core_application):
    gateway = FakeRagGateway()
    controller = build_controller(rag_gateway=gateway)
    controller.set_answer_source(AnswerSource.RAG_ENDPOINT)
    controller.select_method("hit_rate")
    completed = record(controller.completed)

    controller.start_evaluation("", "", "", RagEndpointInput(" http://rag ", "key", "data.answer", ""))
    wait_for_worker(controller)

    result = completed[0][0]
    assert [score.score for score in result.scores] == [1.0, 0.0]
    assert gateway.settings[0].endpoint_url == "http://rag"
    assert gateway.settings[0].api_key == "key"
    assert gateway.settings[0].answer_field == "data.answer"
    assert gateway.settings[0].contexts_field == "contexts"


def test_scores_an_imported_run_and_rescores_with_another_context_metric(core_application):
    run = FixedRun([ImportedAnswer("1", "Paris", CONTEXTS), ImportedAnswer("2", "Nilo", ())])
    controller = build_controller(run=run)
    controller.set_answer_source(AnswerSource.IMPORTED_RUN)
    controller.load_imported_run(Path("run.json"))
    controller.select_method("hit_rate")
    completed = record(controller.completed)

    controller.start_evaluation("", "", "")
    wait_for_worker(controller)
    controller.select_method("k_precision")
    wait_for_worker(controller)

    assert [score.score for score in completed[0][0].scores] == [1.0, 0.0]
    assert completed[1][0].method.identifier == "k_precision"
    assert [score.score for score in completed[1][0].scores] == [1.0, 0.0]


def test_changing_the_source_discards_the_last_result(core_application):
    run = FixedRun([ImportedAnswer("1", "Paris", CONTEXTS), ImportedAnswer("2", "Nilo", ())])
    controller = build_controller(run=run)
    controller.set_answer_source(AnswerSource.IMPORTED_RUN)
    controller.load_imported_run(Path("run.json"))
    controller.start_evaluation("", "", "")
    wait_for_worker(controller)

    controller.set_answer_source(AnswerSource.MODEL_ENDPOINT)

    assert controller._last_result is None
    assert missing(controller, "hit_rate") == (SampleRequirement.CONTEXTS,)
