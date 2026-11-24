import pytest

from domain.entities.evaluation_sample import EvaluationSample
from domain.entities.question import Question
from domain.entities.retrieved_context import RetrievedContext
from domain.errors import DomainError
from domain.scoring.rag.context_overlap import token_support
from domain.scoring.rag.context_overlap_scoring_methods import (
    ContextCoverageScoringMethod,
    KPrecisionScoringMethod,
)
from domain.scoring.sample_requirements import MetricGroup, SampleRequirement
from domain.scoring.text_normalization import DEFAULT_NORMALIZATION

QUESTION = Question("1", "Quem pintou a Mona Lisa?", "A Mona Lisa foi pintada por Leonardo da Vinci.")
CONTEXTS = (
    RetrievedContext("doc-1", "Leonardo da Vinci pintou a Mona Lisa entre 1503 e 1519."),
    RetrievedContext("doc-2", "A obra foi pintada em Florença."),
)


def sample(answer, contexts=CONTEXTS):
    return EvaluationSample(QUESTION, answer, contexts)


def test_token_support_marks_each_answer_token():
    support = token_support("Mona Lisa por Michelangelo", CONTEXTS, DEFAULT_NORMALIZATION)

    assert support.tokens == ("mona", "lisa", "por", "michelangelo")
    assert support.supported == (True, True, False, False)
    assert support.fraction == pytest.approx(0.5)


def test_k_precision_measures_how_much_of_the_answer_is_in_the_contexts():
    method = KPrecisionScoringMethod()

    assert method.score_sample(sample("Leonardo da Vinci pintou a Mona Lisa.")) == pytest.approx(1.0)
    assert method.score_sample(sample("A Mona Lisa foi pintada por Michelangelo.")) == pytest.approx(4 / 6)
    assert method.score_sample(sample("")) == 0.0


def test_context_coverage_measures_how_much_of_the_expected_answer_is_in_the_contexts():
    method = ContextCoverageScoringMethod()

    assert method.score_sample(sample("anything")) == pytest.approx(7 / 8)
    assert method.score_sample(sample("anything", ())) == 0.0


def test_context_limit_uses_only_the_first_contexts():
    method = KPrecisionScoringMethod()
    answer = "A obra foi pintada em Florença."

    assert method.score_sample(sample(answer)) == pytest.approx(1.0)
    method.update_parameters({"context_limit": 1})
    assert method.score_sample(sample(answer)) == 0.0


def test_normalization_parameters_apply():
    method = KPrecisionScoringMethod()
    contexts = (RetrievedContext(None, "avó"),)

    assert method.score_sample(sample("avo", contexts)) == 0.0
    method.update_parameters({"strip_accents": True})
    assert method.score_sample(sample("avo", contexts)) == 1.0


@pytest.mark.parametrize("method", [KPrecisionScoringMethod(), ContextCoverageScoringMethod()])
def test_context_metrics_need_only_contexts(method):
    assert method.requirements == {SampleRequirement.CONTEXTS}
    assert method.metric_group is MetricGroup.GROUNDING
    with pytest.raises(DomainError, match="contexts retrieved"):
        method.score_sample(sample("a", None))
