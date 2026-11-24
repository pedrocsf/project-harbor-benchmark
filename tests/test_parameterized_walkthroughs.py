from itertools import product
from pathlib import Path

import pytest

from data.scoring.bleu_scoring_method import BleuScoringMethod
from data.scoring.chrf_scoring_method import ChrfScoringMethod
from data.scoring.sacrebleu_statistics_provider import SacrebleuStatisticsProvider
from demo.demo_data import DEMO_ENTRIES
from demo.demo_text_encoder import DemoTextEncoder, load_demo_vectors
from domain.explanations.walkthrough_details import (
    ContainsAnswerDetails,
    LlmJudgeDetails,
    NormalizationDetails,
    TokenOverlapDetails,
)
from domain.scoring.contains_answer_scoring_method import ContainsAnswerScoringMethod
from domain.scoring.embedding_scoring_method import EmbeddingScoringMethod
from domain.scoring.exact_match_scoring_method import ExactMatchScoringMethod
from domain.scoring.rouge_scoring_methods import RougeLScoringMethod, RougeNScoringMethod
from domain.scoring.token_f1_scoring_method import TokenF1ScoringMethod
from domain.scoring.token_recall_scoring_method import TokenRecallScoringMethod
from domain.usecases.build_metric_walkthrough import BuildMetricWalkthrough, WalkthroughRequest

TOLERANCE = 1e-9
DEMO_VECTORS_PATH = Path("demo/demo_embeddings.json")

NORMALIZATION_GRID = [
    {"lowercase": lowercase, "strip_accents": accents, "remove_punctuation": punctuation, "remove_articles": articles}
    for lowercase, accents, punctuation, articles in product(
        (True, False), (True, False), (True, False), ("english", "portuguese", "english_portuguese", "none")
    )
]
ROUGE_GRID = [
    {"score_type": score_type, "beta": beta, "lowercase": lowercase}
    for score_type, beta, lowercase in product(
        ("f_measure", "precision", "recall"), (0.5, 1.0, 3.0), (True, False)
    )
]
EMBEDDING_GRID = [
    {"similarity_function": function, "negative_handling": handling, "normalize_vectors": normalize}
    for function, handling, normalize in product(
        ("cosine", "dot_product", "angular", "euclidean", "manhattan"), ("clip", "rescale"), (True, False)
    )
]
BLEU_GRID = [
    {"max_ngram_order": order, "smooth_method": smoothing, "tokenize": tokenizer, "lowercase": lowercase, "effective_order": effective}
    for order, smoothing, tokenizer, lowercase, effective in product(
        (1, 2, 4), ("exp", "floor", "add-k", "none"), ("13a", "char"), (True, False), (True, False)
    )
]
CHRF_GRID = [
    {"char_order": 3}, {"char_order": 6, "word_order": 2}, {"beta": 1}, {"beta": 3, "lowercase": True}, {"whitespace": True},
]
SUBSTRING_PAIRS = (("cat", "the category list"), ("cat", "a cat sat"), ("", ""), ("cat", ""))


@pytest.fixture(scope="module")
def use_case():
    encoder = DemoTextEncoder(load_demo_vectors(DEMO_VECTORS_PATH))
    return BuildMetricWalkthrough(SacrebleuStatisticsProvider(), encoder)


def walkthrough_score(use_case, identifier, entry, parameters):
    request = WalkthroughRequest(
        identifier, entry.expected_answer, entry.given_answer, entry.scores[identifier], parameters
    )
    return use_case.execute(request)


def assert_matches_method(use_case, identifier, method, grid):
    for parameters in grid:
        method.update_parameters(parameters)
        for entry in DEMO_ENTRIES:
            walkthrough = walkthrough_score(use_case, identifier, entry, method.parameters)
            expected = method.score(entry.expected_answer, entry.given_answer)
            assert walkthrough.final_score == pytest.approx(expected, abs=TOLERANCE), (parameters, entry.identifier)


def test_exact_match_follows_normalization(use_case):
    assert_matches_method(use_case, "exact_match", ExactMatchScoringMethod(), NORMALIZATION_GRID)


def test_token_f1_follows_normalization_and_beta(use_case):
    grid = [{**options, "beta": beta} for options in NORMALIZATION_GRID[::5] for beta in (0.5, 1.0, 4.0)]
    assert_matches_method(use_case, "token_f1", TokenF1ScoringMethod(), grid)


def test_token_recall_follows_normalization(use_case):
    assert_matches_method(use_case, "token_recall", TokenRecallScoringMethod(), NORMALIZATION_GRID)


@pytest.mark.parametrize("match_mode", ("whole_words", "substring"))
def test_contains_answer_follows_match_mode(use_case, match_mode):
    grid = [{**options, "match_mode": match_mode} for options in NORMALIZATION_GRID[::3]]
    assert_matches_method(use_case, "contains_answer", ContainsAnswerScoringMethod(), grid)


@pytest.mark.parametrize("expected, given", SUBSTRING_PAIRS)
def test_substring_contains_matches_the_method(use_case, expected, given):
    method = ContainsAnswerScoringMethod()
    method.update_parameters({"match_mode": "substring"})
    result = use_case.execute(WalkthroughRequest("contains_answer", expected, given, None, method.parameters))
    assert result.final_score == method.score(expected, given)


def test_substring_details_report_the_character_position(use_case):
    parameters = {"match_mode": "substring"}
    result = use_case.execute(WalkthroughRequest("contains_answer", "cat", "big category list", None, parameters))
    details = result.details
    assert isinstance(details, ContainsAnswerDetails)
    assert details.match_mode == "substring"
    assert details.character_position == 4
    assert details.found_at == 1


def test_normalization_stages_list_only_active_ones(use_case):
    parameters = {"lowercase": False, "strip_accents": False, "remove_punctuation": False, "remove_articles": "none"}
    result = use_case.execute(WalkthroughRequest("exact_match", "A b", "a B", None, parameters))
    normalization = result.details.normalization
    assert isinstance(normalization, NormalizationDetails)
    assert normalization.stage_names == ("Collapse whitespace",)
    assert normalization.lowercase is False
    assert normalization.articles == "none"
    assert len(normalization.expected_stages) == 1


def test_token_overlap_reports_beta_and_f_score(use_case):
    entry = DEMO_ENTRIES[1]
    result = walkthrough_score(use_case, "token_f1", entry, {**TokenF1ScoringMethod().parameters, "beta": 2.0})
    details = result.details
    assert isinstance(details, TokenOverlapDetails)
    assert details.beta == 2.0
    assert details.f_score == details.f1 == result.final_score


@pytest.mark.parametrize("identifier, method_factory", (
    ("rouge_1", lambda: RougeNScoringMethod(1)),
    ("rouge_2", lambda: RougeNScoringMethod(2)),
    ("rouge_l", RougeLScoringMethod),
))
def test_rouge_follows_score_type_beta_and_case(use_case, identifier, method_factory):
    assert_matches_method(use_case, identifier, method_factory(), ROUGE_GRID)


def test_embedding_follows_similarity_parameters(use_case):
    assert_matches_method(use_case, "embedding", EmbeddingScoringMethod(use_case._text_encoder), EMBEDDING_GRID)


def test_embedding_details_expose_the_similarity_outcome(use_case):
    parameters = {"similarity_function": "euclidean", "negative_handling": "clip", "normalize_vectors": True}
    result = walkthrough_score(use_case, "embedding", DEMO_ENTRIES[1], parameters)
    details = result.details
    assert details.function == "euclidean"
    assert details.score == result.final_score
    assert 0.0 < details.score <= 1.0
    assert len(details.expected_vector) == len(details.given_vector) > 0


def test_embedding_without_encoder_uses_the_known_score():
    plain = BuildMetricWalkthrough(SacrebleuStatisticsProvider())
    result = plain.execute(WalkthroughRequest("embedding", "a", "b", 0.8))
    assert result.final_score == 0.8
    assert result.details.function == "cosine"
    assert result.details.score == 0.8


def test_bleu_follows_parameters(use_case):
    assert_matches_method(use_case, "bleu", BleuScoringMethod(), BLEU_GRID)


def test_chrf_follows_parameters(use_case):
    assert_matches_method(use_case, "chrf", ChrfScoringMethod(), CHRF_GRID)


@pytest.mark.parametrize("maximum_rating", (2, 5, 10, 100))
def test_llm_judge_uses_scale_and_template(use_case, maximum_rating):
    template = "Scale {maximum_rating}: {expected_answer} | {given_answer}"
    parameters = {"rating_scale_max": maximum_rating, "prompt_template": template, "samples": 3}
    for entry in DEMO_ENTRIES:
        request = WalkthroughRequest("llm_judge", entry.expected_answer, entry.given_answer, 0.66, parameters)
        result = use_case.execute(request)
        details = result.details
        assert isinstance(details, LlmJudgeDetails)
        assert details.maximum_rating == maximum_rating
        assert details.samples == 3
        assert details.prompt_preview == template.format(
            maximum_rating=maximum_rating, expected_answer=entry.expected_answer, given_answer=entry.given_answer
        )
        if entry.given_answer.strip():
            rating = round(0.66 * maximum_rating)
            assert details.judge_score_out_of_ten == rating
            assert result.final_score == rating / maximum_rating
        else:
            assert result.final_score == 0.0
