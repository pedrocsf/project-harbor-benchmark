import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel

from domain.entities.question import Question
from domain.repositories.question_repository import QuestionRepository
from domain.scoring.metric_parameters import ParameterKind, ParameterSpec
from domain.scoring.scoring_method import ScoreKind, ScoringMethod
from domain.usecases.build_metric_overview import BuildMetricOverview
from domain.usecases.export_result import ExportResult
from domain.usecases.load_questions import LoadQuestions
from domain.usecases.rescore_result import RescoreResult
from domain.usecases.run_evaluation import RunEvaluation
from presentation.controllers.evaluation_controller import EvaluationController, EvaluationUseCases
from presentation.views.main_window import MainWindow


class PlainMethod(ScoringMethod):
    identifier = "plain"
    display_name = "Plain"
    column_header = "Plain"
    score_kind = ScoreKind.CONTINUOUS

    def score(self, expected_answer, given_answer):
        return 1.0


class TunableMethod(PlainMethod):
    identifier = "tunable"
    display_name = "Tunable"
    parameter_specs = (
        ParameterSpec("weight", "Weight", "Weight.", ParameterKind.DECIMAL, 1.0, minimum=0.0, maximum=2.0),
        ParameterSpec("flag", "Flag", "Flag.", ParameterKind.BOOLEAN, False),
    )


class EmptyRepository(QuestionRepository):
    def load(self, source):
        return []


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


def build_window(methods):
    use_cases = EvaluationUseCases(
        LoadQuestions(EmptyRepository()), RunEvaluation(None), RescoreResult(), BuildMetricOverview(), ExportResult(None)
    )
    controller = EvaluationController(use_cases, methods)
    return MainWindow(controller), controller


def hint_text(window):
    return window._parameters_hint.text()


def test_hides_parameter_controls_without_specs(application):
    window, _ = build_window([PlainMethod()])
    assert window._parameters_controls.isHidden()


def test_shows_default_hint_for_a_method_with_specs(application):
    window, _ = build_window([TunableMethod()])
    assert not window._parameters_controls.isHidden()
    assert hint_text(window) == "Default parameters"


def test_hint_counts_custom_parameters_after_a_change(application):
    window, controller = build_window([TunableMethod()])
    controller.update_method_parameters("tunable", {"weight": 1.5, "flag": True})
    assert hint_text(window) == "2 custom parameters"
    controller.reset_method_parameters("tunable")
    assert hint_text(window) == "Default parameters"


def test_hint_uses_singular_for_one_custom_parameter(application):
    window, controller = build_window([TunableMethod()])
    controller.update_method_parameters("tunable", {"weight": 1.5})
    assert hint_text(window) == "1 custom parameter"


def test_hint_follows_the_selected_metric(application):
    window, _ = build_window([PlainMethod(), TunableMethod()])
    assert window._parameters_controls.isHidden()
    window._method_combo.setCurrentIndex(1)
    assert not window._parameters_controls.isHidden()


def test_button_follows_the_configuration_enabled_state(application):
    window, _ = build_window([TunableMethod()])
    window._set_configuration_enabled(False)
    assert not window._parameters_button.isEnabled()
    window._set_configuration_enabled(True)
    assert window._parameters_button.isEnabled()


def test_extra_windows_are_parentless_and_close_with_the_main_window(application):
    window, _ = build_window([TunableMethod()])
    window.show()
    window._on_info_clicked()
    window._on_parameters_clicked()
    dialog = window._parameters_dialog
    assert window._info_dialog.parentWidget() is None
    assert dialog.parentWidget() is None
    assert dialog.windowModality() == Qt.WindowModality.ApplicationModal
    window.close()
    assert not window._info_dialog.isVisible()
    assert not dialog.isVisible()
