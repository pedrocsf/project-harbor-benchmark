import itertools

import pytest
from sacrebleu import corpus_bleu, sentence_bleu, sentence_chrf

from data.scoring.bleu_scoring_method import BleuScoringMethod
from data.scoring.chrf_scoring_method import ChrfScoringMethod
from data.scoring.sacrebleu_statistics_provider import SacrebleuStatisticsProvider
from demo.demo_data import DEMO_ENTRIES
from domain.scoring.metric_parameters import InvalidParameterError

REFERENCE = "the quick brown fox jumps over the lazy dog"
ANSWER = "The quick brown fox leaps over a lazy dog"
SHORT_ANSWER = "quick fox"
PAIRS = [(entry.expected_answer, entry.given_answer) for entry in DEMO_ENTRIES]
TOLERANCE = 1e-9

BLEU_GRID = [
    {"max_ngram_order": order, "smooth_method": method, "tokenize": tokenize, "lowercase": lowercase, "effective_order": effective}
    for order, method, tokenize, lowercase, effective in itertools.product(
        (1, 4, 6), ("exp", "floor", "add-k", "none"), ("13a", "char"), (False, True), (False, True)
    )
]
CHRF_GRID = [
    {"char_order": char, "word_order": word, "beta": beta, "lowercase": lowercase, "whitespace": whitespace, "eps_smoothing": eps}
    for char, word, beta, lowercase, whitespace, eps in itertools.product(
        (1, 6), (0, 2, 3), (1, 2, 4), (False, True), (False, True), (False, True)
    )
]


def bleu_with(**values):
    method = BleuScoringMethod()
    method.update_parameters(values)
    return method


def chrf_with(**values):
    method = ChrfScoringMethod()
    method.update_parameters(values)
    return method


@pytest.mark.parametrize("expected,given", PAIRS)
def test_bleu_defaults_match_plain_sacrebleu(expected, given):
    method = BleuScoringMethod()
    assert method.score(expected, given) == pytest.approx(min(1.0, sentence_bleu(given, [expected]).score / 100.0))


def test_bleu_default_corpus_matches_plain_sacrebleu():
    references = [expected for expected, _ in PAIRS]
    hypotheses = [given for _, given in PAIRS]
    assert BleuScoringMethod().corpus_score(PAIRS) == corpus_bleu(hypotheses, [references]).score / 100.0


@pytest.mark.parametrize("expected,given", PAIRS)
def test_chrf_defaults_match_plain_sacrebleu(expected, given):
    expected_score = 0.0 if not given.strip() else sentence_chrf(given, [expected], word_order=2).score / 100.0
    assert ChrfScoringMethod().score(expected, given) == expected_score


def test_lower_max_ngram_order_raises_score():
    assert bleu_with(max_ngram_order=1).score(REFERENCE, ANSWER) > bleu_with(max_ngram_order=4).score(REFERENCE, ANSWER)


def test_no_smoothing_gives_zero_when_an_order_has_no_match():
    answer = "the quick brown cat sat on a mat"
    assert bleu_with(smooth_method="none", effective_order=False).score(REFERENCE, answer) == 0.0
    assert bleu_with(smooth_method="exp", effective_order=False).score(REFERENCE, answer) > 0.0


def test_floor_value_increases_score():
    low = bleu_with(smooth_method="floor", floor_value=0.01, effective_order=False)
    high = bleu_with(smooth_method="floor", floor_value=1.0, effective_order=False)
    assert high.score(REFERENCE, ANSWER) > low.score(REFERENCE, ANSWER)


def test_add_k_value_changes_score_only_with_add_k():
    low = bleu_with(smooth_method="add-k", add_k_value=1, effective_order=False)
    high = bleu_with(smooth_method="add-k", add_k_value=5, effective_order=False)
    assert low.score(REFERENCE, ANSWER) != high.score(REFERENCE, ANSWER)
    other = bleu_with(smooth_method="exp", add_k_value=5)
    assert other.score(REFERENCE, ANSWER) == BleuScoringMethod().score(REFERENCE, ANSWER)


def test_floor_value_ignored_by_other_methods():
    assert bleu_with(floor_value=0.9).score(REFERENCE, ANSWER) == BleuScoringMethod().score(REFERENCE, ANSWER)


def test_lowercase_removes_case_penalty():
    assert bleu_with(lowercase=True).score("Hello World Again Now", "hello world again now") == pytest.approx(1.0)
    assert BleuScoringMethod().score("Hello World Again Now", "hello world again now") < 1.0


def test_tokenizer_changes_score():
    assert bleu_with(tokenize="char").score(REFERENCE, ANSWER) != BleuScoringMethod().score(REFERENCE, ANSWER)


def test_effective_order_raises_short_sentence_score():
    assert bleu_with(effective_order=True).score(REFERENCE, SHORT_ANSWER) > bleu_with(effective_order=False).score(REFERENCE, SHORT_ANSWER)


def test_corpus_ignores_effective_order():
    assert bleu_with(effective_order=True).corpus_score(PAIRS) == bleu_with(effective_order=False).corpus_score(PAIRS)


def test_chrf_beta_changes_score():
    assert chrf_with(beta=1).score(REFERENCE, SHORT_ANSWER) != chrf_with(beta=6).score(REFERENCE, SHORT_ANSWER)


def test_chrf_word_order_zero_is_plain_chrf():
    plain = sentence_chrf(ANSWER, [REFERENCE], word_order=0).score / 100.0
    assert chrf_with(word_order=0).score(REFERENCE, ANSWER) == plain


def test_chrf_char_order_changes_score():
    assert chrf_with(char_order=2).score(REFERENCE, ANSWER) > chrf_with(char_order=10).score(REFERENCE, ANSWER)


def test_chrf_lowercase_removes_case_penalty():
    assert chrf_with(lowercase=True).score("Hello World", "hello world") > ChrfScoringMethod().score("Hello World", "hello world")


def test_chrf_whitespace_changes_score():
    assert chrf_with(whitespace=True).score(REFERENCE, ANSWER) != ChrfScoringMethod().score(REFERENCE, ANSWER)


def test_chrf_empty_answer_stays_zero():
    assert chrf_with(eps_smoothing=True).score(REFERENCE, "  ") == 0.0


@pytest.mark.parametrize("values", BLEU_GRID)
def test_bleu_details_match_method_score(values):
    method = bleu_with(**values)
    provider = SacrebleuStatisticsProvider()
    for expected, given in PAIRS:
        details = provider.bleu_details(given, expected, values)
        assert abs(details.score - method.score(expected, given)) < TOLERANCE
        assert len(details.matches_by_order) == values["max_ngram_order"]


@pytest.mark.parametrize("values", CHRF_GRID)
def test_chrf_details_match_method_score(values):
    method = chrf_with(**values)
    provider = SacrebleuStatisticsProvider()
    for expected, given in PAIRS:
        details = provider.chrf_details(given, expected, values)
        assert abs(details.f_score - method.score(expected, given)) < TOLERANCE
        assert len(details.character_orders) == values["char_order"]
        assert len(details.word_orders) == values["word_order"]


def test_details_without_parameters_use_defaults():
    provider = SacrebleuStatisticsProvider()
    assert provider.bleu_details(ANSWER, REFERENCE).score == BleuScoringMethod().score(REFERENCE, ANSWER)
    assert provider.chrf_details(ANSWER, REFERENCE).f_score == ChrfScoringMethod().score(REFERENCE, ANSWER)


@pytest.mark.parametrize(
    "values",
    [
        {"max_ngram_order": 0},
        {"max_ngram_order": 7},
        {"max_ngram_order": 2.5},
        {"smooth_method": "bogus"},
        {"floor_value": 0.0},
        {"floor_value": 2.0},
        {"add_k_value": 11},
        {"tokenize": "zh"},
        {"lowercase": "yes"},
        {"effective_order": 1},
        {"unknown": 1},
    ],
)
def test_bleu_rejects_invalid_values(values):
    with pytest.raises(InvalidParameterError):
        BleuScoringMethod().update_parameters(values)


@pytest.mark.parametrize(
    "values",
    [
        {"char_order": 0},
        {"char_order": 11},
        {"word_order": -1},
        {"word_order": 4},
        {"beta": 0},
        {"beta": 7},
        {"whitespace": "no"},
        {"eps_smoothing": 0},
        {"unknown": 1},
    ],
)
def test_chrf_rejects_invalid_values(values):
    with pytest.raises(InvalidParameterError):
        ChrfScoringMethod().update_parameters(values)


def test_provider_rejects_invalid_values():
    provider = SacrebleuStatisticsProvider()
    with pytest.raises(InvalidParameterError):
        provider.bleu_details(ANSWER, REFERENCE, {"max_ngram_order": 99})
    with pytest.raises(InvalidParameterError):
        provider.chrf_details(ANSWER, REFERENCE, {"beta": 99})
