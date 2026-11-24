import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from demo.demo_data import DEMO_ENTRIES
from demo.demo_question_repository import DemoQuestionRepository
from demo.demo_rag_data import DEMO_RAG_ENDPOINT, DEMO_RAG_ENTRIES
from demo.demo_run_evaluation import DemoRunEvaluation
from demo.demo_run_import_repository import DemoRunImportRepository
from domain.entities.evaluation_request import EvaluationRequest
from domain.entities.rag_endpoint_settings import RagEndpointSettings
from domain.explanations.timeline import TimelinePosition
from domain.usecases.build_metric_overview import BuildMetricOverview
from domain.usecases.build_rag_walkthrough import BuildRagWalkthrough
from domain.usecases.load_imported_run import LoadImportedRun
from domain.usecases.rescore_result import RescoreResult
from domain.usecases.score_imported_run import ScoreImportedRun, ScoreImportedRunRequest
from main_demo import build_demo_methods
from presentation.controllers.metric_explorer_controller import ExplorerExample
from presentation.views.metric_explorer.scenes.scene_registry import build_scene_registry

PAINT_PROGRESSES = (0.0, 0.5, 1.0)
PAINT_SIZES = ((640, 480), (420, 360))
RAG_IDENTIFIERS = (
    "answer_relevancy",
    "hit_rate",
    "context_precision",
    "context_recall",
    "mrr",
    "ndcg",
    "context_relevance",
    "k_precision",
    "context_coverage",
    "faithfulness",
)


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


def demo_questions():
    return tuple(DemoQuestionRepository(DEMO_ENTRIES, DEMO_RAG_ENTRIES).load(Path("demo.json")))


def methods_by_identifier():
    return {method.identifier: method for method in build_demo_methods()}


def rag_result():
    method = methods_by_identifier()["hit_rate"]
    request = EvaluationRequest(None, demo_questions(), method, RagEndpointSettings(DEMO_RAG_ENDPOINT))
    return DemoRunEvaluation(DEMO_ENTRIES, step_seconds=0, rag_entries=DEMO_RAG_ENTRIES).execute(request)


def scores_of(result):
    return {score.question.identifier: round(score.score, 3) for score in result.scores}


def test_demo_questions_carry_relevance_labels():
    questions = demo_questions()

    assert all(question.has_relevance_labels for question in questions)
    assert questions[2].relevant_passages and not questions[2].relevant_context_ids


def test_demo_rag_run_returns_contexts_and_didactic_retrieval_scores():
    result = rag_result()
    rescore = RescoreResult()
    methods = methods_by_identifier()

    mrr = scores_of(rescore.execute(result, methods["mrr"]))
    precision = scores_of(rescore.execute(result, methods["context_precision"]))

    assert result.has_contexts
    assert scores_of(result)["7"] == 0.0
    assert mrr["4"] == 0.5
    assert mrr["5"] == 0.333
    assert precision["6"] == 0.2
    assert scores_of(rescore.execute(result, methods["ndcg"]))["12"] == 1.0


def test_demo_judges_tell_the_didactic_stories():
    result = rag_result()
    rescore = RescoreResult()
    methods = methods_by_identifier()

    faithfulness = scores_of(rescore.execute(result, methods["faithfulness"]))
    relevancy = scores_of(rescore.execute(result, methods["answer_relevancy"]))
    context_relevance = scores_of(rescore.execute(result, methods["context_relevance"]))

    assert faithfulness["9"] == 0.0
    assert faithfulness["7"] == 0.0
    assert faithfulness["5"] == 1.0
    assert faithfulness["11"] == 0.0
    assert relevancy["9"] > 0.9
    assert relevancy["10"] < relevancy["1"]
    assert relevancy["11"] == 0.0
    assert context_relevance["5"] == 0.333


def test_demo_model_run_has_no_contexts():
    method = methods_by_identifier()["exact_match"]
    result = DemoRunEvaluation(DEMO_ENTRIES, step_seconds=0, rag_entries=DEMO_RAG_ENTRIES).execute(
        EvaluationRequest(None, demo_questions(), method)
    )

    assert not result.has_contexts


def test_demo_imported_run_scores_like_the_rag_run():
    run = LoadImportedRun(DemoRunImportRepository(DEMO_ENTRIES, DEMO_RAG_ENTRIES)).execute(Path("demo-run.jsonl"))
    method = methods_by_identifier()["k_precision"]

    imported = ScoreImportedRun().execute(ScoreImportedRunRequest(run, demo_questions(), method))

    assert run.has_contexts
    assert scores_of(imported) == scores_of(RescoreResult().execute(rag_result(), method))


def test_demo_overview_includes_every_metric_after_a_rag_run():
    methods = build_demo_methods()

    overview = BuildMetricOverview().execute(rag_result(), methods)

    assert [entry.method.identifier for entry in overview.entries] == [method.identifier for method in methods]


def explorer_examples():
    return [
        ExplorerExample(
            entry.identifier,
            entry.question,
            entry.expected_answer,
            entry.given_answer,
            entry.scores,
            DEMO_RAG_ENTRIES[entry.identifier].contexts,
            DEMO_RAG_ENTRIES[entry.identifier].relevant_context_ids,
            DEMO_RAG_ENTRIES[entry.identifier].relevant_passages,
        )
        for entry in DEMO_ENTRIES
    ]


@pytest.mark.parametrize("identifier", RAG_IDENTIFIERS)
def test_rag_walkthroughs_match_the_scores(identifier):
    method = methods_by_identifier()[identifier]
    use_case = BuildRagWalkthrough()

    assert use_case.supports(method)
    for example in explorer_examples():
        sample = example.to_sample()
        walkthrough = use_case.execute(method, sample)

        assert walkthrough.final_score == pytest.approx(method.score_sample(sample)), example.identifier
        assert walkthrough.parameters == method.parameters


@pytest.mark.parametrize("identifier", RAG_IDENTIFIERS)
def test_rag_scenes_paint_every_step_for_every_example(application, identifier):
    scene = build_scene_registry().scene_for(identifier)
    method = methods_by_identifier()[identifier]
    for step in scene.steps:
        assert all(0 <= line < len(scene.formula) for line in step.formula_lines)
    for example in explorer_examples():
        walkthrough = BuildRagWalkthrough().execute(method, example.to_sample())
        for step_index in range(len(scene.steps)):
            assert isinstance(scene.step_body(step_index, walkthrough), str)
            assert isinstance(scene.formula_result(step_index, walkthrough), str)
            for width, height in PAINT_SIZES:
                for progress in PAINT_PROGRESSES:
                    image = QImage(width, height, QImage.Format.Format_ARGB32)
                    painter = QPainter(image)
                    scene.paint(painter, QRectF(0, 0, width, height), walkthrough, TimelinePosition(step_index, progress, False))
                    painter.end()


def test_retrieval_parameters_change_the_walkthrough():
    method = methods_by_identifier()["context_precision"]
    example = explorer_examples()[5]

    method.update_parameters({"k": 1})
    walkthrough = BuildRagWalkthrough().execute(method, example.to_sample())

    assert walkthrough.final_score == 1.0
    assert walkthrough.details.cutoff == 1


def test_explorer_controller_routes_rag_metrics_to_the_rag_walkthrough(application):
    from main_demo import build_controllers, build_demo_text_encoder, build_metric_explorer_controller

    encoder = build_demo_text_encoder()
    _, evaluation_controller = build_controllers(encoder)
    controller = build_metric_explorer_controller(build_scene_registry(), evaluation_controller, encoder)

    controller.select_metric("mrr")
    controller.select_example(4)

    assert controller.current_walkthrough.final_score == pytest.approx(1 / 3)
