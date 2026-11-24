import pytest

from domain.scoring.contains_answer_scoring_method import ContainsAnswerScoringMethod
from domain.scoring.exact_match_scoring_method import ExactMatchScoringMethod
from domain.scoring.metric_parameters import InvalidParameterError
from domain.scoring.rouge_scoring_methods import RougeLScoringMethod, RougeNScoringMethod
from domain.scoring.text_normalization import (
    NormalizationOptions,
    normalization_stages,
    normalize_answer,
    strip_accents,
)
from domain.scoring.token_f1_scoring_method import TokenF1ScoringMethod
from domain.scoring.token_recall_scoring_method import TokenRecallScoringMethod


def configured(method, **values):
    method.update_parameters(values)
    return method


def test_default_normalization_matches_previous_behavior():
    assert normalize_answer("The Cat, sat!") == "cat sat"
    assert len(normalization_stages("x")) == 4


def test_strip_accents_function():
    assert strip_accents("avó ação") == "avo acao"


def test_strip_accents_parameter_changes_exact_match():
    assert ExactMatchScoringMethod().score("avó", "avo") == 0.0
    assert configured(ExactMatchScoringMethod(), strip_accents=True).score("avó", "avo") == 1.0


def test_stage_count_grows_with_accent_stripping():
    options = NormalizationOptions(strip_accents=True)
    assert len(normalization_stages("x", options)) == 5


def test_portuguese_articles():
    assert ExactMatchScoringMethod().score("a casa", "casa") == 1.0
    assert ExactMatchScoringMethod().score("os gatos", "gatos") == 0.0
    method = configured(ExactMatchScoringMethod(), remove_articles="portuguese")
    assert method.score("os gatos", "gatos") == 1.0
    assert method.score("the cat", "cat") == 0.0


def test_english_portuguese_articles():
    method = configured(ExactMatchScoringMethod(), remove_articles="english_portuguese")
    assert method.score("the cat", "cat") == 1.0
    assert method.score("o gato", "gato") == 1.0


def test_no_articles_removed():
    method = configured(ExactMatchScoringMethod(), remove_articles="none")
    assert method.score("the cat", "cat") == 0.0


def test_lowercase_off():
    assert ExactMatchScoringMethod().score("Paris", "paris") == 1.0
    assert configured(ExactMatchScoringMethod(), lowercase=False).score("Paris", "paris") == 0.0


def test_articles_removed_case_insensitively_without_lowercase():
    method = configured(ExactMatchScoringMethod(), lowercase=False)
    assert method.score("The Cat", "Cat") == 1.0


def test_remove_punctuation_off():
    assert ExactMatchScoringMethod().score("yes!", "yes") == 1.0
    assert configured(ExactMatchScoringMethod(), remove_punctuation=False).score("yes!", "yes") == 0.0


def test_token_recall_uses_normalization_parameters():
    method = configured(TokenRecallScoringMethod(), strip_accents=True)
    assert TokenRecallScoringMethod().score("avó feliz", "avo feliz") == 0.5
    assert method.score("avó feliz", "avo feliz") == 1.0


def test_contains_substring_vs_whole_words():
    assert ContainsAnswerScoringMethod().score("cat", "category") == 0.0
    method = configured(ContainsAnswerScoringMethod(), match_mode="substring")
    assert method.score("cat", "category") == 1.0
    assert method.score("", "category") == 0.0


def test_token_f1_default_and_beta():
    default_score = TokenF1ScoringMethod().score("red blue green", "red")
    assert default_score == pytest.approx(0.5)
    recall_heavy = configured(TokenF1ScoringMethod(), beta=2.0).score("red blue green", "red")
    precision_heavy = configured(TokenF1ScoringMethod(), beta=0.5).score("red blue green", "red")
    assert recall_heavy == pytest.approx(5 * 1.0 * (1 / 3) / (4 * 1.0 + 1 / 3))
    assert recall_heavy < default_score < precision_heavy


def test_token_f1_empty_rules_kept():
    method = TokenF1ScoringMethod()
    assert method.score("", "") == 1.0
    assert method.score("cat", "") == 0.0


def test_rouge_defaults_equal_f1():
    assert RougeNScoringMethod(1).score("red blue green", "red") == pytest.approx(0.5)
    assert RougeLScoringMethod().score("red blue green", "red") == pytest.approx(0.5)


def test_rouge_precision_and_recall():
    precision = configured(RougeNScoringMethod(1), score_type="precision")
    recall = configured(RougeNScoringMethod(1), score_type="recall")
    assert precision.score("red blue green", "red") == 1.0
    assert recall.score("red blue green", "red") == pytest.approx(1 / 3)
    assert configured(RougeLScoringMethod(), score_type="recall").score("a b c d", "a b") == 0.5


def test_rouge_zero_denominator():
    method = configured(RougeNScoringMethod(2), score_type="precision")
    assert method.score("red blue", "red") == 0.0


def test_rouge_beta_and_lowercase():
    beta = configured(RougeNScoringMethod(1), beta=2.0)
    assert beta.score("red blue green", "red") < 0.5
    assert RougeNScoringMethod(1).score("Red", "red") == 1.0
    assert configured(RougeNScoringMethod(1), lowercase=False).score("Red", "red") == 0.0
    assert configured(RougeLScoringMethod(), lowercase=False).score("Red", "red") == 0.0


@pytest.mark.parametrize(
    "method, values",
    [
        (ExactMatchScoringMethod(), {"remove_articles": "klingon"}),
        (ExactMatchScoringMethod(), {"lowercase": "yes"}),
        (TokenF1ScoringMethod(), {"beta": 0.0}),
        (TokenF1ScoringMethod(), {"beta": 11}),
        (ContainsAnswerScoringMethod(), {"match_mode": "fuzzy"}),
        (RougeNScoringMethod(1), {"score_type": "median"}),
        (RougeLScoringMethod(), {"beta": "high"}),
        (TokenRecallScoringMethod(), {"unknown": 1}),
    ],
)
def test_invalid_values_raise(method, values):
    with pytest.raises(InvalidParameterError):
        method.update_parameters(values)
