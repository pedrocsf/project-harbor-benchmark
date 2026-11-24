import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from domain.entities.evaluation_result import EvaluationResult
from domain.entities.question import Question
from domain.entities.question_score import QuestionScore
from domain.entities.retrieved_context import RetrievedContext
from domain.repositories.question_repository import QuestionRepository
from domain.scoring.exact_match_scoring_method import ExactMatchScoringMethod
from domain.scoring.llm_judge_scoring_method import LlmJudgeScoringMethod
from domain.scoring.rag.context_relevance_scoring_method import ContextRelevanceScoringMethod
from domain.scoring.rag.faithfulness_scoring_method import FaithfulnessScoringMethod
from domain.scoring.rag.retrieval_scoring_methods import HitRateScoringMethod
from domain.scoring.sample_requirements import MetricGroup
from domain.usecases.build_metric_overview import BuildMetricOverview
from domain.usecases.export_result import ExportResult
from domain.usecases.load_imported_run import LoadImportedRun
from domain.usecases.load_questions import LoadQuestions
from domain.usecases.rescore_result import RescoreResult
from domain.usecases.run_evaluation import RunEvaluation
from domain.usecases.score_imported_run import ScoreImportedRun
from presentation.controllers.answer_source import AnswerSource
from presentation.controllers.evaluation_controller import EvaluationController, EvaluationUseCases
from presentation.views.context_tooltip import context_count_text, contexts_tooltip
from presentation.views.main_window import CONTEXTS_COLUMN, MainWindow

QUESTIONS = [Question("1", "Capital?", "Paris", ("geo-1",)), Question("2", "Rio?", "Amazonas", ("geo-2",))]


class FixedQuestions(QuestionRepository):
    def load(self, source):
        return list(QUESTIONS)


class EmptyRun:
    def load(self, source):
        return []


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


def build_window():
    use_cases = EvaluationUseCases(
        LoadQuestions(FixedQuestions()),
        RunEvaluation(None),
        RescoreResult(),
        BuildMetricOverview(),
        ExportResult(None),
        LoadImportedRun(EmptyRun()),
        ScoreImportedRun(),
    )
    methods = [
        ExactMatchScoringMethod(),
        LlmJudgeScoringMethod(None),
        HitRateScoringMethod(),
        ContextRelevanceScoringMethod(None),
        FaithfulnessScoringMethod(None),
    ]
    controller = EvaluationController(use_cases, methods)
    window = MainWindow(controller)
    controller.load_dataset(Path("questions.json"))
    return window, controller


def combo_entries(window):
    model = window._method_combo.model()
    return [(model.item(row).text(), model.item(row).isEnabled()) for row in range(model.rowCount())]


def test_metric_combo_is_grouped_and_disables_metrics_without_contexts(application):
    window, _ = build_window()

    assert combo_entries(window) == [
        ("— Answer quality —", False),
        ("Exact match", True),
        ("LLM judge", True),
        ("— Retrieval —", False),
        ("Hit rate@k", False),
        ("Context relevance", False),
        ("— Grounding in contexts —", False),
        ("Faithfulness", False),
    ]
    tooltip = window._method_combo.model().item(4).toolTip()
    assert "RAG endpoint or an imported run" in tooltip


def test_rag_source_shows_its_fields_and_turns_the_model_into_a_judge(application):
    window, controller = build_window()
    window.show()

    window._source_panel.select_source(AnswerSource.RAG_ENDPOINT)

    assert controller.answer_source is AnswerSource.RAG_ENDPOINT
    assert window._source_panel._rag_fields.isVisible()
    assert not window._source_panel._run_fields.isVisible()
    assert window._endpoint_title.text() == "JUDGE MODEL"
    assert not window._judge_hint.isHidden()
    assert all(enabled for text, enabled in combo_entries(window) if not text.startswith("—"))
    window.close()


def test_returning_to_the_model_source_falls_back_to_an_available_metric(application):
    window, controller = build_window()
    window._source_panel.select_source(AnswerSource.IMPORTED_RUN)
    window._source_panel.select_source(AnswerSource.RAG_ENDPOINT)
    window._method_combo.setCurrentIndex(window._method_combo.findData("faithfulness"))
    assert controller.selected_method.identifier == "faithfulness"

    window._source_panel.select_source(AnswerSource.MODEL_ENDPOINT)

    assert controller.selected_method.identifier == "exact_match"
    assert window._endpoint_title.text() == "MODEL ENDPOINT"


def test_judge_metrics_show_a_call_estimate(application):
    window, _ = build_window()
    window._source_panel.select_source(AnswerSource.RAG_ENDPOINT)

    window._method_combo.setCurrentIndex(window._method_combo.findData("faithfulness"))
    assert window._judge_calls_hint.text() == "Calls the judge model about 2 times per question (4 for this dataset)."

    window._method_combo.setCurrentIndex(window._method_combo.findData("exact_match"))
    assert window._judge_calls_hint.isHidden()


def test_contexts_column_appears_only_for_results_with_contexts(application):
    window, _ = build_window()
    contexts = (RetrievedContext("geo-1", "Paris é a capital.", 0.82),)
    with_contexts = EvaluationResult(
        (QuestionScore(QUESTIONS[0], "Paris", 1.0, 0.1, contexts), QuestionScore(QUESTIONS[1], "Nilo", 0.0, 0.1, ())),
        datetime(2026, 11, 24),
        ExactMatchScoringMethod(),
    )
    without_contexts = EvaluationResult(
        (QuestionScore(QUESTIONS[0], "Paris", 1.0, 0.1),), datetime(2026, 11, 24), ExactMatchScoringMethod()
    )

    window._fill_table(with_contexts)
    assert not window._table.isColumnHidden(CONTEXTS_COLUMN)
    assert window._table.item(0, CONTEXTS_COLUMN).text() == "1"
    assert "geo-1" in window._table.item(0, CONTEXTS_COLUMN).toolTip()
    assert window._table.item(1, CONTEXTS_COLUMN).text() == "0"

    window._fill_table(without_contexts)
    assert window._table.isColumnHidden(CONTEXTS_COLUMN)


def test_context_tooltip_escapes_and_truncates():
    many = tuple(RetrievedContext(None, "<b>" + "x" * 300) for _ in range(10))

    tooltip = contexts_tooltip(many)

    assert "&lt;b&gt;" in tooltip
    assert "…" in tooltip
    assert "+2 more" in tooltip
    assert context_count_text(None) == "—"
    assert contexts_tooltip(None) == ""
    assert "no contexts" in contexts_tooltip(())


def test_dataset_card_mentions_relevance_labels(application):
    window, _ = build_window()

    assert window._dataset_count_label.text() == "2 questions · 2 with relevance labels"


def build_result_with_contexts():
    contexts = (RetrievedContext("geo-1", "Paris é a capital.", 0.82),)
    return EvaluationResult(
        (QuestionScore(QUESTIONS[0], "Paris", 1.0, 0.1, contexts), QuestionScore(QUESTIONS[1], "Nilo", 0.0, 0.1, ())),
        datetime(2026, 11, 24),
        ExactMatchScoringMethod(),
    )


def test_chart_export_skips_the_dialog_when_there_is_a_single_category(application):
    window, controller = build_window()
    controller._last_result = EvaluationResult(
        (QuestionScore(QUESTIONS[0], "Paris", 1.0, 0.1),), datetime(2026, 11, 24), ExactMatchScoringMethod()
    )

    assert window._choose_chart_group() is MetricGroup.ANSWER


def test_chart_export_asks_for_the_category_when_there_are_several(application, monkeypatch):
    window, controller = build_window()
    controller._last_result = build_result_with_contexts()
    offered = []

    class FakeDialog:
        def __init__(self, available_groups, unavailable_reason):
            offered.append(tuple(available_groups))

        def exec(self):
            return QDialog.DialogCode.Accepted

        def selected_group(self):
            return MetricGroup.GROUNDING

    monkeypatch.setattr("presentation.views.main_window.ChartCategoryDialog", FakeDialog)

    assert window._choose_chart_group() is MetricGroup.GROUNDING
    assert offered == [(MetricGroup.ANSWER, MetricGroup.RETRIEVAL)]
