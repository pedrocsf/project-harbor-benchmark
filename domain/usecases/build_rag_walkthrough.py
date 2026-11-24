from domain.entities.evaluation_sample import EvaluationSample
from domain.errors import DomainError
from domain.explanations.metric_walkthrough import MetricWalkthrough
from domain.explanations.rag_walkthrough_details import (
    ANSWER_TEXT,
    EXPECTED_TEXT,
    AnswerRelevancyDetails,
    ContextRelevanceDetails,
    ContextSupportDetails,
    FaithfulnessDetails,
    RetrievalDetails,
)
from domain.scoring.rag.answer_relevancy_scoring_method import AnswerRelevancyScoringMethod
from domain.scoring.rag.context_overlap import considered_contexts
from domain.scoring.rag.context_overlap_scoring_methods import (
    ContextOverlapScoringMethod,
    KPrecisionScoringMethod,
)
from domain.scoring.rag.context_relevance_scoring_method import ContextRelevanceScoringMethod
from domain.scoring.rag.faithfulness_scoring_method import FaithfulnessScoringMethod
from domain.scoring.rag.retrieval_metrics import dcg_breakdown, first_relevant_rank, hit_targets
from domain.scoring.rag.retrieval_scoring_methods import GAIN_GRADED, RetrievalScoringMethod
from domain.scoring.scoring_method import ScoringMethod

UNSUPPORTED_METHOD_MESSAGE = "There is no RAG walkthrough for the metric {identifier!r}."


class UnsupportedRagWalkthroughError(DomainError):
    pass


class BuildRagWalkthrough:
    def supports(self, method: ScoringMethod) -> bool:
        return isinstance(
            method,
            (
                RetrievalScoringMethod,
                ContextOverlapScoringMethod,
                FaithfulnessScoringMethod,
                ContextRelevanceScoringMethod,
                AnswerRelevancyScoringMethod,
            ),
        )

    def execute(self, method: ScoringMethod, sample: EvaluationSample) -> MetricWalkthrough:
        details = self._details(method, sample)
        return MetricWalkthrough(
            method.identifier,
            sample.expected_answer,
            sample.given_answer,
            details.score,
            details,
            dict(method.parameters),
        )

    def _details(self, method: ScoringMethod, sample: EvaluationSample):
        if isinstance(method, RetrievalScoringMethod):
            return self._retrieval(method, sample)
        if isinstance(method, ContextOverlapScoringMethod):
            return self._context_support(method, sample)
        if isinstance(method, FaithfulnessScoringMethod):
            verdicts = method.verdicts(sample)
            return FaithfulnessDetails(method.judged_contexts(sample), verdicts, verdicts.score)
        if isinstance(method, ContextRelevanceScoringMethod):
            ratings = method.ratings(sample)
            return ContextRelevanceDetails(sample.question_text, method.judged_contexts(sample), ratings, ratings.score)
        if isinstance(method, AnswerRelevancyScoringMethod):
            generated = method.generated_questions(sample)
            return AnswerRelevancyDetails(sample.question_text, generated, generated.score)
        raise UnsupportedRagWalkthroughError(UNSUPPORTED_METHOD_MESSAGE.format(identifier=method.identifier))

    def _retrieval(self, method: RetrievalScoringMethod, sample: EvaluationSample) -> RetrievalDetails:
        relevance = method.relevance(sample)
        cutoff = method.cutoff
        graded = method.parameters.get("gain") == GAIN_GRADED
        return RetrievalDetails(
            question=sample.question_text,
            relevance=relevance,
            cutoff=cutoff,
            relevant_in_cutoff=sum(1 for judgment in relevance.top(cutoff) if judgment.is_relevant),
            found_targets=tuple(sorted(hit_targets(relevance, cutoff))),
            first_relevant_rank=first_relevant_rank(relevance, cutoff),
            dcg=dcg_breakdown(relevance, cutoff, graded),
            graded=graded,
            score=method.score_relevance(relevance),
        )

    def _context_support(self, method: ContextOverlapScoringMethod, sample: EvaluationSample) -> ContextSupportDetails:
        support = method.support(sample)
        contexts = considered_contexts(sample.contexts or (), int(method.parameter("context_limit")))
        compared = ANSWER_TEXT if isinstance(method, KPrecisionScoringMethod) else EXPECTED_TEXT
        return ContextSupportDetails(compared, contexts, support, support.fraction)
