import sys

from PySide6.QtWidgets import QApplication

from data.gateways.anthropic_gateway import AnthropicGateway
from data.gateways.gemini_gateway import GeminiGateway
from data.gateways.openai_compatible_gateway import OpenAiCompatibleGateway
from data.gateways.provider_routing_gateway import ProviderRoutingGateway
from data.gateways.rag_endpoint_gateway import RagEndpointGateway
from data.repositories.file_result_repository import FileResultRepository
from data.repositories.json_question_repository import JsonQuestionRepository
from data.repositories.json_run_import_repository import JsonRunImportRepository
from data.resource_locator import resolve_resource_path
from data.scoring.bleu_scoring_method import BleuScoringMethod
from data.scoring.chrf_scoring_method import ChrfScoringMethod
from data.scoring.fastembed_text_encoder import FastEmbedTextEncoder
from domain.gateways.language_model_gateway import LanguageModelGateway
from domain.gateways.text_encoder import TextEncoder
from domain.scoring.contains_answer_scoring_method import ContainsAnswerScoringMethod
from domain.scoring.embedding_scoring_method import EmbeddingScoringMethod
from domain.scoring.exact_match_scoring_method import ExactMatchScoringMethod
from domain.scoring.llm_judge_scoring_method import LlmJudgeScoringMethod
from domain.scoring.rag.answer_relevancy_scoring_method import AnswerRelevancyScoringMethod
from domain.scoring.rag.context_overlap_scoring_methods import (
    ContextCoverageScoringMethod,
    KPrecisionScoringMethod,
)
from domain.scoring.rag.context_relevance_scoring_method import ContextRelevanceScoringMethod
from domain.scoring.rag.faithfulness_scoring_method import FaithfulnessScoringMethod
from domain.scoring.rag.retrieval_scoring_methods import (
    ContextPrecisionScoringMethod,
    ContextRecallScoringMethod,
    HitRateScoringMethod,
    MrrScoringMethod,
    NdcgScoringMethod,
)
from domain.scoring.rouge_scoring_methods import RougeLScoringMethod, RougeNScoringMethod
from domain.scoring.scoring_method import ScoringMethod
from domain.scoring.token_f1_scoring_method import TokenF1ScoringMethod
from domain.scoring.token_recall_scoring_method import TokenRecallScoringMethod
from domain.usecases.build_metric_overview import BuildMetricOverview
from domain.usecases.export_result import ExportResult
from domain.usecases.load_imported_run import LoadImportedRun
from domain.usecases.load_questions import LoadQuestions
from domain.usecases.prepare_scoring_methods import PrepareScoringMethods
from domain.usecases.rescore_result import RescoreResult
from domain.usecases.run_evaluation import RunEvaluation
from domain.usecases.score_imported_run import ScoreImportedRun
from presentation.controllers.evaluation_controller import EvaluationController, EvaluationUseCases
from presentation.controllers.startup_controller import StartupController
from presentation.views.main_window import MainWindow
from presentation.views.splash_screen import SplashScreen

MODELS_DIRECTORY_NAME = "models"
STARTUP_FAILURE_EXIT_CODE = 1


def build_scoring_methods(
    language_model_gateway: LanguageModelGateway, text_encoder: TextEncoder | None = None
) -> list[ScoringMethod]:
    encoder = text_encoder or FastEmbedTextEncoder(resolve_resource_path(MODELS_DIRECTORY_NAME))
    return [
        *build_answer_methods(language_model_gateway, encoder),
        *build_rag_methods(language_model_gateway),
    ]


def build_answer_methods(language_model_gateway: LanguageModelGateway, text_encoder: TextEncoder) -> list[ScoringMethod]:
    return [
        EmbeddingScoringMethod(text_encoder),
        ExactMatchScoringMethod(),
        TokenF1ScoringMethod(),
        TokenRecallScoringMethod(),
        ContainsAnswerScoringMethod(),
        RougeNScoringMethod(1),
        RougeNScoringMethod(2),
        RougeLScoringMethod(),
        BleuScoringMethod(),
        ChrfScoringMethod(),
        LlmJudgeScoringMethod(language_model_gateway),
        AnswerRelevancyScoringMethod(language_model_gateway, text_encoder),
    ]


def build_rag_methods(language_model_gateway: LanguageModelGateway) -> list[ScoringMethod]:
    return [
        HitRateScoringMethod(),
        ContextPrecisionScoringMethod(),
        ContextRecallScoringMethod(),
        MrrScoringMethod(),
        NdcgScoringMethod(),
        ContextRelevanceScoringMethod(language_model_gateway),
        KPrecisionScoringMethod(),
        ContextCoverageScoringMethod(),
        FaithfulnessScoringMethod(language_model_gateway),
    ]


def build_language_model_gateway() -> ProviderRoutingGateway:
    return ProviderRoutingGateway(OpenAiCompatibleGateway(), AnthropicGateway(), GeminiGateway())


def build_controllers() -> tuple[StartupController, EvaluationController]:
    language_model_gateway = build_language_model_gateway()
    scoring_methods = build_scoring_methods(language_model_gateway)
    startup_controller = StartupController(PrepareScoringMethods(scoring_methods))
    use_cases = EvaluationUseCases(
        load_questions=LoadQuestions(JsonQuestionRepository()),
        run_evaluation=RunEvaluation(language_model_gateway, RagEndpointGateway()),
        rescore_result=RescoreResult(),
        build_overview=BuildMetricOverview(),
        export_result=ExportResult(FileResultRepository(), scoring_methods),
        load_imported_run=LoadImportedRun(JsonRunImportRepository()),
        score_imported_run=ScoreImportedRun(),
    )
    return startup_controller, EvaluationController(use_cases, scoring_methods)


def main() -> int:
    application = QApplication(sys.argv)
    startup_controller, evaluation_controller = build_controllers()
    splash = SplashScreen()
    window = MainWindow(evaluation_controller)

    def open_main_window() -> None:
        window.show()
        splash.close()

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
