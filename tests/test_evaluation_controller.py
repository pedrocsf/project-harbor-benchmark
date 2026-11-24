from datetime import datetime
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QThread

from domain.entities.evaluation_result import EvaluationResult
from domain.entities.question import Question
from domain.entities.question_score import QuestionScore
from domain.errors import QuestionsUnavailableError
from domain.repositories.question_repository import QuestionRepository
from domain.scoring.exact_match_scoring_method import ExactMatchScoringMethod
from domain.scoring.metric_parameters import InvalidParameterError, ParameterKind, ParameterSpec
from domain.scoring.scoring_method import ScoreKind, ScoringMethod
from domain.scoring.token_f1_scoring_method import TokenF1ScoringMethod
from domain.usecases.build_metric_overview import BuildMetricOverview
from domain.usecases.export_result import ExportResult
from domain.usecases.load_questions import LoadQuestions
from domain.usecases.rescore_result import RescoreResult
from domain.usecases.run_evaluation import RunEvaluation
from presentation.controllers.evaluation_controller import (
    MISSING_DATASET_MESSAGE,
    MISSING_ENDPOINT_MESSAGE,
    EvaluationController,
    EvaluationUseCases,
)


class FakeQuestionRepository(QuestionRepository):
    def __init__(self, questions=None, error=None):
        self._questions = questions or []
        self._error = error

    def load(self, source):
        if self._error:
            raise self._error
        return self._questions


def build_controller(repository):
    use_cases = EvaluationUseCases(
        load_questions=LoadQuestions(repository),
        run_evaluation=RunEvaluation(None),
        rescore_result=RescoreResult(),
        build_overview=BuildMetricOverview(),
        export_result=ExportResult(None),
    )
    return EvaluationController(use_cases, [TokenF1ScoringMethod(), ExactMatchScoringMethod()])


def record(signal):
    received = []
    signal.connect(lambda *arguments: received.append(arguments))
    return received


def test_starts_with_the_first_scoring_method_selected():
    controller = build_controller(FakeQuestionRepository())

    assert controller.selected_method.identifier == "token_f1"
    assert [method.identifier for method in controller.scoring_methods] == ["token_f1", "exact_match"]


def test_selecting_a_method_without_results_only_changes_the_selection():
    controller = build_controller(FakeQuestionRepository())
    started = record(controller.started)

    controller.select_method("exact_match")

    assert controller.selected_method.identifier == "exact_match"
    assert started == []


def test_ignores_an_unknown_method():
    controller = build_controller(FakeQuestionRepository())

    controller.select_method("does_not_exist")

    assert controller.selected_method.identifier == "token_f1"


def test_shutdown_without_a_running_task_does_nothing():
    controller = build_controller(FakeQuestionRepository())

    controller.shutdown()


def test_ignores_an_overview_request_without_a_result():
    controller = build_controller(FakeQuestionRepository())
    ready = record(controller.overview_ready)
    failed = record(controller.overview_failed)

    controller.build_overview()

    assert ready == []
    assert failed == []


def test_announces_a_loaded_dataset():
    controller = build_controller(FakeQuestionRepository([Question("1", "a?", "A"), Question("2", "b?", "B")]))
    loaded = record(controller.dataset_loaded)

    controller.load_dataset(Path("/data/questions.json"))

    assert loaded == [("/data/questions.json", 2)]


def test_reports_a_dataset_that_cannot_be_loaded():
    controller = build_controller(FakeQuestionRepository(error=QuestionsUnavailableError("broken file")))
    loaded = record(controller.dataset_loaded)
    failures = record(controller.dataset_failed)

    controller.load_dataset(Path("/data/questions.json"))

    assert loaded == []
    assert failures == [("broken file",)]


def test_refuses_to_run_without_a_dataset():
    controller = build_controller(FakeQuestionRepository())
    failures = record(controller.failed)
    started = record(controller.started)

    controller.start_evaluation("http://127.0.0.1:1234/v1/chat/completions", "", "")

    assert failures == [(MISSING_DATASET_MESSAGE,)]
    assert started == []


def test_refuses_to_run_without_an_endpoint():
    controller = build_controller(FakeQuestionRepository([Question("1", "a?", "A")]))
    controller.load_dataset(Path("/data/questions.json"))
    failures = record(controller.failed)

    controller.start_evaluation("   ", "", "")

    assert failures == [(MISSING_ENDPOINT_MESSAGE,)]

WAIT_ATTEMPTS = 300
WAIT_MILLISECONDS = 10
SETTLE_MILLISECONDS = 100


class ParameterizedMethod(ScoringMethod):
    identifier = "parameterized"
    display_name = "Parameterized"
    column_header = "Parameterized"
    score_kind = ScoreKind.CONTINUOUS
    parameter_specs = (
        ParameterSpec("weight", "Weight", "Weight.", ParameterKind.DECIMAL, 1.0, minimum=0.0, maximum=2.0),
    )

    def __init__(self, fail_scoring=False):
        self.fail_scoring = fail_scoring

    def score(self, expected_answer, given_answer):
        if self.fail_scoring and self.parameters["weight"] != 1.0:
            raise InvalidParameterError("scoring broke")
        return self.parameters["weight"] / 2


def build_parameter_controller(method):
    controller = build_controller(FakeQuestionRepository())
    controller._scoring_methods.append(method)
    return controller


def build_parameter_result(method):
    scores = (QuestionScore(Question("1", "Q", "a"), "a", 0.5, 1.0),)
    return EvaluationResult(scores, datetime(2026, 10, 28), method)


def wait_for_worker(controller):
    for _ in range(WAIT_ATTEMPTS):
        if controller._worker is None:
            QThread.msleep(SETTLE_MILLISECONDS)
            QCoreApplication.processEvents()
            return
        QCoreApplication.processEvents()
        QThread.msleep(WAIT_MILLISECONDS)
    raise AssertionError("worker did not finish")


@pytest.fixture(scope="module")
def core_application():
    return QCoreApplication.instance() or QCoreApplication([])


def test_applies_valid_parameters(core_application):
    method = ParameterizedMethod()
    controller = build_parameter_controller(method)
    changes = record(controller.parameters_changed)

    controller.update_method_parameters("parameterized", {"weight": 1.5})

    assert method.parameters == {"weight": 1.5}
    assert changes == [("parameterized",)]


def test_invalid_parameters_keep_old_values(core_application):
    method = ParameterizedMethod()
    controller = build_parameter_controller(method)
    failures = record(controller.parameters_failed)

    controller.update_method_parameters("parameterized", {"weight": 5.0})

    assert method.parameters == {"weight": 1.0}
    assert len(failures) == 1


def test_reset_restores_defaults(core_application):
    method = ParameterizedMethod()
    controller = build_parameter_controller(method)
    controller.update_method_parameters("parameterized", {"weight": 1.5})

    controller.reset_method_parameters("parameterized")

    assert method.parameters == {"weight": 1.0}


def test_unknown_identifier_is_ignored(core_application):
    controller = build_parameter_controller(ParameterizedMethod())
    changes = record(controller.parameters_changed)
    failures = record(controller.parameters_failed)

    controller.update_method_parameters("missing", {"weight": 1.5})

    assert changes == [] and failures == []


def test_rescores_the_last_result_for_the_selected_method(core_application):
    method = ParameterizedMethod()
    controller = build_parameter_controller(method)
    controller.select_method("parameterized")
    controller._last_result = build_parameter_result(method)
    results = record(controller.completed)

    controller.update_method_parameters("parameterized", {"weight": 1.5})
    wait_for_worker(controller)

    assert results[0][0].scores[0].score == pytest.approx(0.75)


def test_does_not_rescore_when_method_is_not_selected(core_application):
    method = ParameterizedMethod()
    controller = build_parameter_controller(method)
    controller._last_result = build_parameter_result(controller.selected_method)
    results = record(controller.completed)

    controller.update_method_parameters("parameterized", {"weight": 1.5})

    assert controller._worker is None and results == []


def test_rolls_back_when_rescoring_fails(core_application):
    method = ParameterizedMethod(fail_scoring=True)
    controller = build_parameter_controller(method)
    controller.select_method("parameterized")
    previous = build_parameter_result(method)
    controller._last_result = previous
    failures = record(controller.failed)
    changes = record(controller.parameters_changed)

    controller.update_method_parameters("parameterized", {"weight": 1.5})
    wait_for_worker(controller)

    assert method.parameters == {"weight": 1.0}
    assert len(failures) == 1
    assert len(changes) == 2


def test_ignores_parameter_changes_while_running(core_application):
    method = ParameterizedMethod()
    controller = build_parameter_controller(method)
    controller._worker = object()
    changes = record(controller.parameters_changed)

    controller.update_method_parameters("parameterized", {"weight": 1.5})

    assert method.parameters == {"weight": 1.0} and changes == []
    controller._worker = None
