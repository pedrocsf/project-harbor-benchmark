from dataclasses import dataclass

from domain.entities.retrieved_context import RetrievedContext
from domain.scoring.rag.answer_relevancy_scoring_method import GeneratedQuestions
from domain.scoring.rag.context_overlap import TokenSupport
from domain.scoring.rag.context_relevance_scoring_method import ContextRatings
from domain.scoring.rag.faithfulness_scoring_method import FaithfulnessVerdicts
from domain.scoring.rag.relevance_matching import RankedRelevance
from domain.scoring.rag.retrieval_metrics import DcgBreakdown

ANSWER_TEXT = "answer"
EXPECTED_TEXT = "expected"


@dataclass(frozen=True)
class RetrievalDetails:
    question: str
    relevance: RankedRelevance
    cutoff: int
    relevant_in_cutoff: int
    found_targets: tuple[int, ...]
    first_relevant_rank: int | None
    dcg: DcgBreakdown
    graded: bool
    score: float


@dataclass(frozen=True)
class ContextSupportDetails:
    compared_text: str
    contexts: tuple[RetrievedContext, ...]
    support: TokenSupport
    score: float


@dataclass(frozen=True)
class FaithfulnessDetails:
    contexts: tuple[RetrievedContext, ...]
    verdicts: FaithfulnessVerdicts
    score: float


@dataclass(frozen=True)
class ContextRelevanceDetails:
    question: str
    contexts: tuple[RetrievedContext, ...]
    ratings: ContextRatings
    score: float


@dataclass(frozen=True)
class AnswerRelevancyDetails:
    question: str
    generated: GeneratedQuestions
    score: float
