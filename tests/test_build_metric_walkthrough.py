import pytest

from data.scoring.sacrebleu_statistics_provider import SacrebleuStatisticsProvider
from demo.demo_data import DEMO_ENTRIES
from domain.explanations.walkthrough_details import (
    BleuDetails,
    ChrfDetails,
    ContainsAnswerDetails,
    EmbeddingDetails,
    ExactMatchDetails,
    LcsDetails,
    LlmJudgeDetails,
    NgramOverlapDetails,
    TokenOverlapDetails,
)
from domain.scoring.text_normalization import normalize_answer
from domain.usecases.build_metric_walkthrough import (
    BuildMetricWalkthrough,
    UnknownWalkthroughMetricError,
    WalkthroughRequest,
)

IDENTIFIERS = (
    "embedding",
    "exact_match",
    "token_f1",
    "token_recall",
    "contains_answer",
    "rouge_1",
    "rouge_2",
    "rouge_l",
    "bleu",
    "chrf",
    "llm_judge",
)
PLANETS_ENTRY = DEMO_ENTRIES[1]
SCORE_DECIMALS = 3


@pytest.fixture(scope="module")
def use_case():
    return BuildMetricWalkthrough(SacrebleuStatisticsProvider())


def build(use_case, identifier, entry=PLANETS_ENTRY):
    return use_case.execute(
        WalkthroughRequest(identifier, entry.expected_answer, entry.given_answer, entry.scores[identifier])
    )


def test_supports_every_metric(use_case):
    assert set(use_case.supported_identifiers) == set(IDENTIFIERS)


@pytest.mark.parametrize("identifier", IDENTIFIERS)
def test_final_score_matches_the_demo_table_for_every_entry(use_case, identifier):
    for entry in DEMO_ENTRIES:
        walkthrough = build(use_case, identifier, entry)

        assert round(walkthrough.final_score, SCORE_DECIMALS) == entry.scores[identifier], entry.identifier
        assert walkthrough.identifier == identifier
        assert walkthrough.expected_answer == entry.expected_answer
        assert walkthrough.given_answer == entry.given_answer


def test_unknown_metric_raises_a_clear_error(use_case):
    with pytest.raises(UnknownWalkthroughMetricError, match="meteor"):
        use_case.execute(WalkthroughRequest("meteor", "a", "b"))


@pytest.mark.parametrize("identifier", ["embedding", "llm_judge"])
def test_model_based_metrics_need_the_known_score(use_case, identifier):
    with pytest.raises(ValueError):
        use_case.execute(WalkthroughRequest(identifier, "a", "b"))


def test_token_f1_counts_four_shared_tokens(use_case):
    details = build(use_case, "token_f1").details

    assert isinstance(details, TokenOverlapDetails)
    assert details.common_count == 4
    assert details.precision == pytest.approx(0.667, abs=1e-3)
    assert details.recall == pytest.approx(0.667, abs=1e-3)
    assert details.expected_tokens == ("o", "sistema", "solar", "tem", "oito", "planetas")
    assert all(details.expected_tokens[e] == details.answer_tokens[a] for e, a in details.matches)


def test_token_matches_respect_clipped_counts(use_case):
    walkthrough = use_case.execute(WalkthroughRequest("token_f1", "sim sim nao", "sim sim sim"))

    assert walkthrough.details.common_count == 2
    assert walkthrough.details.matches == ((0, 0), (1, 1))


def test_rouge_l_finds_a_subsequence_of_two(use_case):
    details = build(use_case, "rouge_l").details

    assert isinstance(details, LcsDetails)
    assert details.lcs_length == 2
    assert details.table[-1][-1] == 2
    assert len(details.matched_cells) == 2
    assert details.path[0] == (len(details.expected_tokens), len(details.answer_tokens))
    assert all(details.expected_tokens[e] == details.answer_tokens[a] for e, a in details.matched_cells)


def test_bleu_exposes_smoothed_precisions_and_brevity_penalty(use_case):
    details = build(use_case, "bleu").details

    assert isinstance(details, BleuDetails)
    assert details.precisions == pytest.approx((5 / 7, 2 / 6, 0.1, 0.0625))
    assert details.smoothed_orders == (3, 4)
    assert details.brevity_penalty == 1.0
    assert details.answer_length == details.reference_length == 7
    assert details.brevity_penalty * details.geometric_mean == pytest.approx(details.score)


def test_chrf_uses_six_character_and_two_word_orders(use_case):
    details = build(use_case, "chrf").details

    assert isinstance(details, ChrfDetails)
    assert len(details.character_orders) == 6
    assert len(details.word_orders) == 2
    assert details.beta == 2.0
    beta_squared = details.beta**2
    expected = (1 + beta_squared) * details.average_precision * details.average_recall
    expected /= beta_squared * details.average_precision + details.average_recall
    assert details.f_score == pytest.approx(expected)


def test_rouge_n_lists_ngrams_of_the_requested_order(use_case):
    details = build(use_case, "rouge_2").details

    assert isinstance(details, NgramOverlapDetails)
    assert details.order == 2
    assert all(len(ngram) == 2 for ngram in details.expected_ngrams + details.answer_ngrams)
    assert details.overlap_count == 2


def test_normalization_stages_end_in_the_real_normalized_text(use_case):
    entry = DEMO_ENTRIES[0]
    details = build(use_case, "exact_match", entry).details

    assert isinstance(details, ExactMatchDetails)
    assert details.is_match
    assert len(details.normalization.stage_names) == len(details.normalization.expected_stages)
    assert details.normalization.expected_stages[-1] == normalize_answer(entry.expected_answer)
    assert details.normalization.expected_stages[0] == entry.expected_answer.lower()


def test_contains_answer_reports_where_the_window_matched(use_case):
    walkthrough = use_case.execute(WalkthroughRequest("contains_answer", "Paris", "It is Paris, of course."))

    assert isinstance(walkthrough.details, ContainsAnswerDetails)
    assert walkthrough.details.found_at == 2
    assert walkthrough.details.window_positions == (0, 1, 2)
    assert walkthrough.final_score == 1.0


def test_embedding_angle_comes_from_the_cosine(use_case):
    details = build(use_case, "embedding", DEMO_ENTRIES[0]).details

    assert isinstance(details, EmbeddingDetails)
    assert details.cosine == 1.0
    assert details.angle_degrees == pytest.approx(0.0)
    assert not details.clipped


def test_llm_judge_rebuilds_the_prompt_and_reply(use_case):
    details = build(use_case, "llm_judge", DEMO_ENTRIES[4]).details

    assert isinstance(details, LlmJudgeDetails)
    assert details.judge_score_out_of_ten == 9
    assert details.raw_reply == "9"
    assert DEMO_ENTRIES[4].expected_answer in details.prompt_preview
    assert details.model_was_called


def test_llm_judge_skips_the_model_for_an_empty_answer(use_case):
    details = build(use_case, "llm_judge", DEMO_ENTRIES[10]).details

    assert not details.model_was_called
    assert details.judge_score_out_of_ten == 0
