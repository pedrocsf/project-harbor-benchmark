from datetime import datetime

from domain.entities.evaluation_result import EvaluationResult
from domain.entities.question import Question
from domain.entities.question_score import QuestionScore
from domain.entities.retrieved_context import RetrievedContext
from domain.scoring.exact_match_scoring_method import ExactMatchScoringMethod
from domain.scoring.rag.context_overlap_scoring_methods import KPrecisionScoringMethod
from domain.scoring.rag.faithfulness_scoring_method import FaithfulnessScoringMethod
from domain.scoring.rag.retrieval_scoring_methods import HitRateScoringMethod, MrrScoringMethod
from domain.usecases.export_result import ExportResult


class RecordingRepository:
    def save(self, result, destination, companion_scores=None):
        self.companion_scores = companion_scores


def result_with(contexts, labelled=True):
    ids = ("doc-1",) if labelled else ()
    scores = (
        QuestionScore(Question("1", "Capital?", "Paris", ids), "Paris", 1.0, 0.1, contexts),
        QuestionScore(Question("2", "Rio?", "Amazonas", ids), "Nilo", 0.0, 0.1, contexts),
    )
    return EvaluationResult(scores, datetime(2026, 11, 24), HitRateScoringMethod())


COMPANIONS = (
    ExactMatchScoringMethod(),
    HitRateScoringMethod(),
    MrrScoringMethod(),
    KPrecisionScoringMethod(),
    FaithfulnessScoringMethod(None),
)


def test_exports_offline_retrieval_and_grounding_scores_next_to_the_result(tmp_path):
    repository = RecordingRepository()
    contexts = (RetrievedContext("doc-2", "Paris"), RetrievedContext("doc-1", "Paris"))

    ExportResult(repository, COMPANIONS).execute(result_with(contexts), tmp_path / "out.json")

    assert repository.companion_scores == {"mrr": (0.5, 0.5), "k_precision": (1.0, 0.0)}


def test_skips_companions_whose_requirements_are_missing(tmp_path):
    repository = RecordingRepository()

    ExportResult(repository, COMPANIONS).execute(result_with(None), tmp_path / "out.json")
    assert repository.companion_scores == {}

    ExportResult(repository, COMPANIONS).execute(result_with((), labelled=False), tmp_path / "out.json")
    assert set(repository.companion_scores) == {"k_precision"}
