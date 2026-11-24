from abc import abstractmethod

from domain.entities.evaluation_sample import EvaluationSample
from domain.errors import DomainError
from domain.scoring.metric_parameters import ParameterKind, ParameterSpec
from domain.scoring.rag.context_overlap import (
    ALL_CONTEXTS,
    TokenSupport,
    considered_contexts,
    token_support,
)
from domain.scoring.sample_requirements import MetricGroup, SampleRequirement
from domain.scoring.scoring_method import SampleScoringMethod, ScoreKind
from domain.scoring.text_normalization import NORMALIZATION_PARAMETER_SPECS, normalization_options_from

MAXIMUM_CONTEXT_LIMIT = 100
MISSING_CONTEXTS_MESSAGE = "{name} needs the contexts retrieved for question {identifier}."

CONTEXT_LIMIT_SPEC = ParameterSpec(
    key="context_limit",
    label="Contexts considered",
    description="Use only the first N retrieved contexts. 0 uses all of them.",
    kind=ParameterKind.INTEGER,
    default=ALL_CONTEXTS,
    minimum=ALL_CONTEXTS,
    maximum=MAXIMUM_CONTEXT_LIMIT,
)


class ContextOverlapScoringMethod(SampleScoringMethod):
    score_kind = ScoreKind.CONTINUOUS
    requirements = frozenset({SampleRequirement.CONTEXTS})
    metric_group = MetricGroup.GROUNDING
    parameter_specs = NORMALIZATION_PARAMETER_SPECS + (CONTEXT_LIMIT_SPEC,)

    def score_sample(self, sample: EvaluationSample) -> float:
        return self.support(sample).fraction

    def support(self, sample: EvaluationSample) -> TokenSupport:
        if sample.contexts is None:
            raise DomainError(
                MISSING_CONTEXTS_MESSAGE.format(name=self.display_name, identifier=sample.question.identifier)
            )
        contexts = considered_contexts(sample.contexts, int(self.parameter("context_limit")))
        return token_support(self.compared_text(sample), contexts, normalization_options_from(self.parameters))

    @abstractmethod
    def compared_text(self, sample: EvaluationSample) -> str:
        ...


class KPrecisionScoringMethod(ContextOverlapScoringMethod):
    identifier = "k_precision"
    display_name = "K-Precision"
    column_header = "K-Prec"

    def compared_text(self, sample: EvaluationSample) -> str:
        return sample.given_answer


class ContextCoverageScoringMethod(ContextOverlapScoringMethod):
    identifier = "context_coverage"
    display_name = "Context coverage"
    column_header = "Coverage"

    def compared_text(self, sample: EvaluationSample) -> str:
        return sample.expected_answer
