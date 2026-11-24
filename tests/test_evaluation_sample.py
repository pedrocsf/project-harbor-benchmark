from datetime import datetime

import pytest

from data.scoring.bleu_scoring_method import BleuScoringMethod
from data.scoring.chrf_scoring_method import ChrfScoringMethod
from domain.entities.evaluation_result import EvaluationResult
from domain.entities.evaluation_sample import EvaluationSample
from domain.entities.question import Question
from domain.entities.question_score import QuestionScore
from domain.entities.retrieved_context import RetrievedContext
from domain.scoring.contains_answer_scoring_method import ContainsAnswerScoringMethod
from domain.scoring.exact_match_scoring_method import ExactMatchScoringMethod
from domain.scoring.rouge_scoring_methods import RougeLScoringMethod, RougeNScoringMethod
from domain.scoring.sample_requirements import (
    MetricGroup,
    SampleRequirement,
    available_requirements,
    missing_requirements,
)
from domain.scoring.scoring_method import (
    SampleOnlyMetricError,
    SampleScoringMethod,
    ScoreKind,
)
from domain.scoring.token_f1_scoring_method import TokenF1ScoringMethod
from domain.scoring.token_recall_scoring_method import TokenRecallScoringMethod
from domain.usecases.build_metric_overview import BuildMetricOverview
from domain.usecases.rescore_result import RescoreResult

ANSWER_PAIRS = (
    ("O Sistema Solar tem oito planetas.", "Existem oito planetas no Sistema Solar."),
    ("A capital da França é Paris.", "A capital da França é Paris."),
    ("Um hexágono tem seis lados.", "Seis."),
    ("A raiz quadrada de 144 é 12.", ""),
)
CONTEXTS = (RetrievedContext("doc-1", "Paris é a capital da França.", 0.9),)


class ContextCountMethod(SampleScoringMethod):
    identifier = "context_count"
    display_name = "Context count"
    column_header = "Contexts"
    score_kind = ScoreKind.CONTINUOUS
    requirements = frozenset({SampleRequirement.CONTEXTS})
    metric_group = MetricGroup.GROUNDING

    def score_sample(self, sample):
        return min(1.0, len(sample.contexts) / 2)


def answer_methods():
    return [
        ExactMatchScoringMethod(),
        TokenF1ScoringMethod(),
        TokenRecallScoringMethod(),
        ContainsAnswerScoringMethod(),
        RougeNScoringMethod(1),
        RougeNScoringMethod(2),
        RougeLScoringMethod(),
        BleuScoringMethod(),
        ChrfScoringMethod(),
    ]


@pytest.mark.parametrize("method", answer_methods(), ids=lambda method: method.identifier)
def test_score_sample_matches_score_for_answer_metrics(method):
    for expected, given in ANSWER_PAIRS:
        sample = EvaluationSample(Question("1", "Q?", expected), given, CONTEXTS)

        assert method.score_sample(sample) == method.score(expected, given)


@pytest.mark.parametrize("method", answer_methods(), ids=lambda method: method.identifier)
def test_answer_metrics_need_nothing_new(method):
    assert method.requirements == frozenset()
    assert method.metric_group is MetricGroup.ANSWER


def test_sample_only_metric_rejects_plain_answer_pairs():
    with pytest.raises(SampleOnlyMetricError, match="Context count"):
        ContextCountMethod().score("a", "b")


def test_question_knows_whether_it_has_relevance_labels():
    assert not Question("1", "Q?", "A").has_relevance_labels
    assert Question("1", "Q?", "A", relevant_context_ids=("doc-1",)).has_relevance_labels
    assert Question("1", "Q?", "A", relevant_passages=("trecho",)).has_relevance_labels


def test_available_requirements_need_labels_on_every_question():
    labelled = Question("1", "Q?", "A", relevant_context_ids=("doc-1",))
    unlabelled = Question("2", "Q?", "A")

    assert available_requirements([labelled], has_contexts=True) == {
        SampleRequirement.CONTEXTS,
        SampleRequirement.RELEVANCE_LABELS,
    }
    assert available_requirements([labelled, unlabelled], has_contexts=False) == frozenset()
    assert available_requirements([], has_contexts=False) == frozenset()


def test_missing_requirements_keep_a_stable_order():
    required = {SampleRequirement.RELEVANCE_LABELS, SampleRequirement.CONTEXTS}

    assert missing_requirements(required, frozenset()) == (
        SampleRequirement.CONTEXTS,
        SampleRequirement.RELEVANCE_LABELS,
    )
    assert missing_requirements(required, frozenset({SampleRequirement.CONTEXTS})) == (
        SampleRequirement.RELEVANCE_LABELS,
    )


def build_result(contexts):
    scores = (
        QuestionScore(Question("1", "Capital?", "Paris"), "Paris", 1.0, 0.1, contexts),
        QuestionScore(Question("2", "Autor?", "Machado"), "Assis", 0.0, 0.2, contexts),
    )
    return EvaluationResult(scores, datetime(2026, 11, 24), ExactMatchScoringMethod())


def test_rescoring_passes_the_contexts_to_the_method():
    rescored = RescoreResult().execute(build_result(CONTEXTS * 2), ContextCountMethod())

    assert [score.score for score in rescored.scores] == [1.0, 1.0]
    assert rescored.scores[0].contexts == CONTEXTS * 2


def test_result_has_contexts_only_when_every_score_has_them():
    assert build_result(CONTEXTS).has_contexts
    assert build_result(()).has_contexts
    assert not build_result(None).has_contexts


def test_overview_skips_methods_whose_requirements_are_missing():
    methods = [ExactMatchScoringMethod(), ContextCountMethod()]

    without_contexts = BuildMetricOverview().execute(build_result(None), methods)
    with_contexts = BuildMetricOverview().execute(build_result(CONTEXTS), methods)

    assert [entry.method.identifier for entry in without_contexts.entries] == ["exact_match"]
    assert [entry.method.identifier for entry in with_contexts.entries] == ["exact_match", "context_count"]
    assert with_contexts.entries[1].scores == (0.5, 0.5)
