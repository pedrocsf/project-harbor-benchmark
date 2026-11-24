import math

import pytest

from domain.entities.evaluation_sample import EvaluationSample
from domain.entities.question import Question
from domain.entities.retrieved_context import RetrievedContext
from domain.scoring.rag.relevance_matching import (
    MATCH_BY_IDS,
    MATCH_BY_PASSAGES,
    MissingRelevanceLabelsError,
    judge_contexts,
    passage_coverage,
)
from domain.scoring.rag.retrieval_metrics import (
    dcg_breakdown,
    hit_rate,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from domain.scoring.rag.retrieval_scoring_methods import (
    ContextPrecisionScoringMethod,
    ContextRecallScoringMethod,
    HitRateScoringMethod,
    MrrScoringMethod,
    NdcgScoringMethod,
)
from domain.scoring.sample_requirements import MetricGroup, SampleRequirement
from domain.scoring.scoring_method import SampleOnlyMetricError, ScoreKind

ID_QUESTION = Question("1", "Q?", "A", relevant_context_ids=("A", "B", "C"))
RANKED_IDS = tuple(RetrievedContext(identifier, f"text {identifier}") for identifier in ("X", "A", "Y", "B", "A"))
PASSAGE = "Paris é a capital da França."
PASSAGE_QUESTION = Question("2", "Capital?", "Paris", relevant_passages=(PASSAGE,))
PASSAGE_CONTEXTS = (
    RetrievedContext(None, "Paris"),
    RetrievedContext(None, "A capital da França é Paris, a cidade luz."),
)


def id_relevance():
    return judge_contexts(ID_QUESTION, RANKED_IDS)


def test_hit_rate_looks_only_at_the_first_k():
    assert hit_rate(id_relevance(), 1) == 0.0
    assert hit_rate(id_relevance(), 2) == 1.0


def test_precision_divides_by_k_and_counts_repeated_relevant_contexts():
    assert precision_at_k(id_relevance(), 5) == pytest.approx(3 / 5)
    assert precision_at_k(id_relevance(), 2) == pytest.approx(1 / 2)
    assert precision_at_k(id_relevance(), 10) == pytest.approx(3 / 10)


def test_recall_counts_each_relevant_item_once():
    assert recall_at_k(id_relevance(), 5) == pytest.approx(2 / 3)
    assert recall_at_k(id_relevance(), 3) == pytest.approx(1 / 3)


def test_reciprocal_rank_uses_the_first_relevant_position_within_the_cutoff():
    assert reciprocal_rank(id_relevance(), 10) == pytest.approx(1 / 2)
    assert reciprocal_rank(id_relevance(), 1) == 0.0


def test_ndcg_rewards_only_new_relevant_items():
    breakdown = dcg_breakdown(id_relevance(), 5, graded=False)
    expected_dcg = 1 / math.log2(3) + 1 / math.log2(5)
    ideal_dcg = 1 + 1 / math.log2(3) + 1 / math.log2(4)

    assert [gain.gain for gain in breakdown.gains] == [0.0, 1.0, 0.0, 1.0, 0.0]
    assert breakdown.dcg == pytest.approx(expected_dcg)
    assert breakdown.ideal_dcg == pytest.approx(ideal_dcg)
    assert ndcg_at_k(id_relevance(), 5) == pytest.approx(expected_dcg / ideal_dcg)


def test_perfect_ranking_scores_one_everywhere():
    contexts = tuple(RetrievedContext(identifier, "t") for identifier in ("A", "B", "C"))
    relevance = judge_contexts(ID_QUESTION, contexts)

    assert precision_at_k(relevance, 3) == 1.0
    assert recall_at_k(relevance, 3) == 1.0
    assert reciprocal_rank(relevance, 3) == 1.0
    assert ndcg_at_k(relevance, 3) == pytest.approx(1.0)


def test_no_contexts_scores_zero():
    relevance = judge_contexts(ID_QUESTION, ())

    assert (hit_rate(relevance, 5), precision_at_k(relevance, 5), recall_at_k(relevance, 5)) == (0.0, 0.0, 0.0)
    assert (reciprocal_rank(relevance, 5), ndcg_at_k(relevance, 5)) == (0.0, 0.0)


def test_passage_coverage_counts_passage_words_found_in_the_context():
    assert passage_coverage(PASSAGE, "A capital da França é Paris, a cidade luz.") == pytest.approx(1.0)
    assert passage_coverage(PASSAGE, "Paris") == pytest.approx(1 / 5)
    assert passage_coverage("", "anything") == 0.0


def test_text_matching_uses_the_threshold():
    relevance = judge_contexts(PASSAGE_QUESTION, PASSAGE_CONTEXTS, match_threshold=0.5)
    permissive = judge_contexts(PASSAGE_QUESTION, PASSAGE_CONTEXTS, match_threshold=0.2)

    assert relevance.match_by == MATCH_BY_PASSAGES
    assert [judgment.is_relevant for judgment in relevance.judgments] == [False, True]
    assert [judgment.is_relevant for judgment in permissive.judgments] == [True, True]


def test_graded_gain_uses_the_coverage():
    relevance = judge_contexts(PASSAGE_QUESTION, PASSAGE_CONTEXTS, match_threshold=0.2)

    graded = dcg_breakdown(relevance, 2, graded=True)

    assert [gain.gain for gain in graded.gains] == [pytest.approx(0.2), 0.0]
    assert graded.ndcg == pytest.approx(0.2)


def test_automatic_matching_prefers_ids_and_forced_modes_need_their_labels():
    both = Question("3", "Q?", "A", relevant_context_ids=("A",), relevant_passages=(PASSAGE,))

    assert judge_contexts(both, RANKED_IDS).match_by == MATCH_BY_IDS
    assert judge_contexts(both, RANKED_IDS, MATCH_BY_PASSAGES).match_by == MATCH_BY_PASSAGES
    with pytest.raises(MissingRelevanceLabelsError, match="relevant_context_ids"):
        judge_contexts(PASSAGE_QUESTION, PASSAGE_CONTEXTS, MATCH_BY_IDS)
    with pytest.raises(MissingRelevanceLabelsError, match="relevant_passages"):
        judge_contexts(ID_QUESTION, RANKED_IDS, MATCH_BY_PASSAGES)
    with pytest.raises(MissingRelevanceLabelsError):
        judge_contexts(Question("4", "Q?", "A"), RANKED_IDS)


def test_contexts_without_id_never_match_by_id():
    relevance = judge_contexts(ID_QUESTION, (RetrievedContext(None, "A"),))

    assert not relevance.judgments[0].is_relevant


def retrieval_methods():
    return [
        HitRateScoringMethod(),
        ContextPrecisionScoringMethod(),
        ContextRecallScoringMethod(),
        MrrScoringMethod(),
        NdcgScoringMethod(),
    ]


def test_scoring_methods_use_their_parameters():
    sample = EvaluationSample(ID_QUESTION, "A", RANKED_IDS)
    methods = {method.identifier: method for method in retrieval_methods()}

    assert {key: method.score_sample(sample) for key, method in methods.items()} == pytest.approx(
        {
            "hit_rate": 1.0,
            "context_precision": 0.6,
            "context_recall": 2 / 3,
            "mrr": 0.5,
            "ndcg": ndcg_at_k(id_relevance(), 5),
        }
    )
    methods["context_precision"].update_parameters({"k": 2})
    methods["mrr"].update_parameters({"k": 1})

    assert methods["context_precision"].score_sample(sample) == pytest.approx(0.5)
    assert methods["mrr"].score_sample(sample) == 0.0


@pytest.mark.parametrize("method", retrieval_methods(), ids=lambda method: method.identifier)
def test_retrieval_methods_declare_their_needs(method):
    assert method.requirements == {SampleRequirement.CONTEXTS, SampleRequirement.RELEVANCE_LABELS}
    assert method.metric_group is MetricGroup.RETRIEVAL
    assert not method.uses_language_model
    with pytest.raises(SampleOnlyMetricError):
        method.score("a", "b")


def test_hit_rate_is_binary_and_mrr_defaults_to_ten():
    assert HitRateScoringMethod().score_kind is ScoreKind.BINARY
    assert MrrScoringMethod().parameter("k") == 10
    assert NdcgScoringMethod().parameter("gain") == "binary"


def test_missing_contexts_raise_a_domain_error():
    from domain.errors import DomainError

    with pytest.raises(DomainError, match="contexts retrieved"):
        HitRateScoringMethod().score_sample(EvaluationSample(ID_QUESTION, "A", None))
