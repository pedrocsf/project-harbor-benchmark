import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from data.resource_locator import resolve_resource_path
from data.repositories.file_result_repository import FileResultRepository
from data.scoring.sacrebleu_statistics_provider import SacrebleuStatisticsProvider
from demo.demo_data import (
    DEMO_BADGE_TEXT,
    DEMO_DATASET_NAME,
    DEMO_ENDPOINT,
    DEMO_ENTRIES,
)
from demo.demo_question_repository import DemoQuestionRepository
from demo.demo_run_evaluation import DemoRunEvaluation
from demo.demo_llm_judge import DemoLlmJudgeScoringMethod
from demo.demo_text_encoder import DemoTextEncoder, load_demo_vectors
from data.scoring.bleu_scoring_method import BleuScoringMethod
from data.scoring.chrf_scoring_method import ChrfScoringMethod
from domain.scoring.contains_answer_scoring_method import ContainsAnswerScoringMethod
from domain.scoring.embedding_scoring_method import EmbeddingScoringMethod
from domain.scoring.exact_match_scoring_method import ExactMatchScoringMethod
from domain.scoring.rouge_scoring_methods import RougeLScoringMethod, RougeNScoringMethod
from domain.scoring.scoring_method import ScoringMethod
from domain.scoring.token_f1_scoring_method import TokenF1ScoringMethod
from domain.scoring.token_recall_scoring_method import TokenRecallScoringMethod
from domain.usecases.build_metric_overview import BuildMetricOverview
from domain.usecases.build_metric_walkthrough import BuildMetricWalkthrough
from domain.usecases.export_result import ExportResult
from domain.usecases.load_questions import LoadQuestions
from domain.usecases.prepare_scoring_methods import PrepareScoringMethods
from domain.usecases.rescore_result import RescoreResult
from presentation.controllers.evaluation_controller import EvaluationController, EvaluationUseCases
from presentation.controllers.metric_explorer_controller import ExplorerExample, MetricExplorerController
from presentation.controllers.startup_controller import StartupController
from presentation.views.animations import motion_enabled
from presentation.views.main_window import MainWindow, MainWindowOptions
from presentation.views.metric_explorer.metric_explorer_window import MetricExplorerWindow
from presentation.views.metric_explorer.scenes.scene_registry import SceneRegistry, build_scene_registry
from presentation.views.splash_screen import SplashScreen

DEMO_DATASET_PATH = Path(DEMO_DATASET_NAME)
SPLASH_STATUS = "Loading demo data…"
DEMO_EMBEDDINGS_PATH = "demo/demo_embeddings.json"
JUDGE_IDENTIFIER = "llm_judge"
STARTUP_FAILURE_EXIT_CODE = 1


def build_demo_text_encoder() -> DemoTextEncoder:
    return DemoTextEncoder(load_demo_vectors(resolve_resource_path(DEMO_EMBEDDINGS_PATH)))


def build_demo_methods(text_encoder: DemoTextEncoder | None = None) -> list[ScoringMethod]:
    judge_fractions = {
        (entry.expected_answer, entry.given_answer): entry.scores[JUDGE_IDENTIFIER] for entry in DEMO_ENTRIES
    }
    return [
        EmbeddingScoringMethod(text_encoder or build_demo_text_encoder()),
        ExactMatchScoringMethod(),
        TokenF1ScoringMethod(),
        TokenRecallScoringMethod(),
        ContainsAnswerScoringMethod(),
        RougeNScoringMethod(1),
        RougeNScoringMethod(2),
        RougeLScoringMethod(),
        BleuScoringMethod(),
        ChrfScoringMethod(),
        DemoLlmJudgeScoringMethod(judge_fractions),
    ]


def build_controllers(
    text_encoder: DemoTextEncoder | None = None,
) -> tuple[StartupController, EvaluationController]:
    demo_methods = build_demo_methods(text_encoder)
    use_cases = EvaluationUseCases(
        load_questions=LoadQuestions(DemoQuestionRepository(DEMO_ENTRIES)),
        run_evaluation=DemoRunEvaluation(DEMO_ENTRIES),
        rescore_result=RescoreResult(),
        build_overview=BuildMetricOverview(),
        export_result=ExportResult(FileResultRepository()),
    )
    startup_controller = StartupController(PrepareScoringMethods(demo_methods))
    return startup_controller, EvaluationController(use_cases, demo_methods)


def build_explorer_examples() -> list[ExplorerExample]:
    return [
        ExplorerExample(entry.identifier, entry.question, entry.expected_answer, entry.given_answer, entry.scores)
        for entry in DEMO_ENTRIES
    ]


def build_metric_explorer_controller(
    scene_registry: SceneRegistry, evaluation_controller: EvaluationController, text_encoder: DemoTextEncoder
) -> MetricExplorerController:
    controller = MetricExplorerController(
        evaluation_controller.scoring_methods,
        build_explorer_examples(),
        BuildMetricWalkthrough(SacrebleuStatisticsProvider(), text_encoder=text_encoder),
        scene_registry.step_durations,
        motion_enabled(),
    )
    evaluation_controller.parameters_changed.connect(controller.refresh_parameters)
    return controller


def build_metric_explorer(
    evaluation_controller: EvaluationController, text_encoder: DemoTextEncoder
) -> MetricExplorerWindow:
    scene_registry = build_scene_registry()
    controller = build_metric_explorer_controller(scene_registry, evaluation_controller, text_encoder)
    window = MetricExplorerWindow(controller, scene_registry, DEMO_BADGE_TEXT)
    controller.setParent(window)
    return window


def main() -> int:
    application = QApplication(sys.argv)
    text_encoder = build_demo_text_encoder()
    startup_controller, evaluation_controller = build_controllers(text_encoder)
    splash = SplashScreen(SPLASH_STATUS)
    options = MainWindowOptions(
        dataset_picker=lambda: DEMO_DATASET_PATH,
        initial_endpoint=DEMO_ENDPOINT,
        badge_text=DEMO_BADGE_TEXT,
        metric_explorer_factory=lambda: build_metric_explorer(evaluation_controller, text_encoder),
    )
    window = MainWindow(evaluation_controller, options)

    def open_main_window() -> None:
        window.show()
        splash.close()
        evaluation_controller.load_dataset(DEMO_DATASET_PATH)
        evaluation_controller.start_evaluation(DEMO_ENDPOINT, "", "")

    def abort_startup(message: str) -> None:
        splash.show_failure(message)
        application.exit(STARTUP_FAILURE_EXIT_CODE)

    startup_controller.ready.connect(open_main_window)
    startup_controller.failed.connect(abort_startup)
    application.aboutToQuit.connect(evaluation_controller.shutdown)
    splash.show()
    startup_controller.start()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
