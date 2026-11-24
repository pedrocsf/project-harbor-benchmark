from abc import abstractmethod

from domain.entities.evaluation_sample import EvaluationSample
from domain.errors import DomainError
from domain.scoring.metric_parameters import ParameterChoice, ParameterKind, ParameterSpec
from domain.scoring.rag.relevance_matching import (
    MATCH_AUTO,
    MATCH_BY_IDS,
    MATCH_BY_PASSAGES,
    RankedRelevance,
    judge_contexts,
)
from domain.scoring.rag.retrieval_metrics import (
    hit_rate,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from domain.scoring.sample_requirements import MetricGroup, SampleRequirement
from domain.scoring.scoring_method import SampleScoringMethod, ScoreKind

DEFAULT_CUTOFF = 5
DEFAULT_MRR_CUTOFF = 10
MINIMUM_CUTOFF = 1
MAXIMUM_CUTOFF = 100
DEFAULT_MATCH_THRESHOLD = 0.5
GAIN_BINARY = "binary"
GAIN_GRADED = "graded"
MISSING_CONTEXTS_MESSAGE = "{name} needs the contexts retrieved for question {identifier}."


def cutoff_spec(default: int) -> ParameterSpec:
    return ParameterSpec(
        key="k",
        label="Cutoff k",
        description="Only the first k retrieved contexts are considered, in the order the system returned them.",
        kind=ParameterKind.INTEGER,
        default=default,
        minimum=MINIMUM_CUTOFF,
        maximum=MAXIMUM_CUTOFF,
    )


MATCH_BY_SPEC = ParameterSpec(
    key="match_by",
    label="Match relevant contexts by",
    description=(
        "IDs compare each context id with relevant_context_ids. Text compares each context with "
        "relevant_passages, which keeps working when chunk IDs differ between systems. Automatic "
        "uses IDs when the question has them and text otherwise."
    ),
    kind=ParameterKind.CHOICE,
    default=MATCH_AUTO,
    choices=(
        ParameterChoice(MATCH_AUTO, "Automatic (IDs, then text)"),
        ParameterChoice(MATCH_BY_IDS, "IDs only"),
        ParameterChoice(MATCH_BY_PASSAGES, "Text only"),
    ),
)

MATCH_THRESHOLD_SPEC = ParameterSpec(
    key="match_threshold",
    label="Text match threshold",
    description=(
        "When matching by text, a context counts as relevant if it contains at least this "
        "fraction of the words of a relevant passage."
    ),
    kind=ParameterKind.DECIMAL,
    default=DEFAULT_MATCH_THRESHOLD,
    minimum=0.05,
    maximum=1.0,
    step=0.05,
)

GAIN_SPEC = ParameterSpec(
    key="gain",
    label="Gain",
    description=(
        "Binary gives every newly found relevant item a gain of 1. Graded uses how much of the "
        "relevant passage the context covers (ID matches always gain 1)."
    ),
    kind=ParameterKind.CHOICE,
    default=GAIN_BINARY,
    choices=(
        ParameterChoice(GAIN_BINARY, "Binary (0 or 1)"),
        ParameterChoice(GAIN_GRADED, "Graded (text coverage)"),
    ),
)


class RetrievalScoringMethod(SampleScoringMethod):
    score_kind = ScoreKind.CONTINUOUS
    requirements = frozenset({SampleRequirement.CONTEXTS, SampleRequirement.RELEVANCE_LABELS})
    metric_group = MetricGroup.RETRIEVAL
    parameter_specs = (cutoff_spec(DEFAULT_CUTOFF), MATCH_BY_SPEC, MATCH_THRESHOLD_SPEC)

    def relevance(self, sample: EvaluationSample) -> RankedRelevance:
        if sample.contexts is None:
            raise DomainError(
                MISSING_CONTEXTS_MESSAGE.format(name=self.display_name, identifier=sample.question.identifier)
            )
        return judge_contexts(
            sample.question,
            sample.contexts,
            str(self.parameter("match_by")),
            float(self.parameter("match_threshold")),
        )

    @property
    def cutoff(self) -> int:
        return int(self.parameter("k"))

    def score_sample(self, sample: EvaluationSample) -> float:
        return self.score_relevance(self.relevance(sample))

    @abstractmethod
    def score_relevance(self, relevance: RankedRelevance) -> float:
        ...


class HitRateScoringMethod(RetrievalScoringMethod):
    identifier = "hit_rate"
    display_name = "Hit rate@k"
    column_header = "Hit@k"
    score_kind = ScoreKind.BINARY

    def score_relevance(self, relevance: RankedRelevance) -> float:
        return hit_rate(relevance, self.cutoff)


class ContextPrecisionScoringMethod(RetrievalScoringMethod):
    identifier = "context_precision"
    display_name = "Context precision@k"
    column_header = "P@k"

    def score_relevance(self, relevance: RankedRelevance) -> float:
        return precision_at_k(relevance, self.cutoff)


class ContextRecallScoringMethod(RetrievalScoringMethod):
    identifier = "context_recall"
    display_name = "Context recall@k"
    column_header = "R@k"

    def score_relevance(self, relevance: RankedRelevance) -> float:
        return recall_at_k(relevance, self.cutoff)


class MrrScoringMethod(RetrievalScoringMethod):
    identifier = "mrr"
    display_name = "MRR"
    column_header = "RR"
    parameter_specs = (cutoff_spec(DEFAULT_MRR_CUTOFF), MATCH_BY_SPEC, MATCH_THRESHOLD_SPEC)

    def score_relevance(self, relevance: RankedRelevance) -> float:
        return reciprocal_rank(relevance, self.cutoff)


class NdcgScoringMethod(RetrievalScoringMethod):
    identifier = "ndcg"
    display_name = "nDCG@k"
    column_header = "nDCG"
    parameter_specs = (cutoff_spec(DEFAULT_CUTOFF), MATCH_BY_SPEC, MATCH_THRESHOLD_SPEC, GAIN_SPEC)

    def score_relevance(self, relevance: RankedRelevance) -> float:
        return ndcg_at_k(relevance, self.cutoff, self.parameter("gain") == GAIN_GRADED)
