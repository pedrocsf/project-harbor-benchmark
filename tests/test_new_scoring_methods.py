import pytest

from data.scoring.chrf_scoring_method import ChrfScoringMethod
from domain.entities.evaluation_result import EvaluationResult
from domain.entities.language_model_settings import LanguageModelSettings
from domain.entities.question import Question
from domain.entities.question_score import QuestionScore
from domain.errors import JudgeResponseError, LanguageModelError
from domain.gateways.language_model_gateway import LanguageModelGateway
from domain.scoring.contains_answer_scoring_method import ContainsAnswerScoringMethod
from domain.scoring.exact_match_scoring_method import ExactMatchScoringMethod
from domain.scoring.llm_judge_scoring_method import LlmJudgeScoringMethod
from domain.scoring.scoring_method import ScoreKind
from domain.scoring.token_recall_scoring_method import TokenRecallScoringMethod
from domain.usecases.build_metric_overview import BuildMetricOverview

SETTINGS = LanguageModelSettings(endpoint_url="http://127.0.0.1:1234/v1/chat/completions")


class FakeGateway(LanguageModelGateway):
    def __init__(self, reply):
        self.reply = reply
        self.prompts = []

    def ask(self, settings, question_text):
        self.prompts.append(question_text)
        return self.reply


def test_token_recall_ignores_extra_words_in_a_long_answer():
    score = TokenRecallScoringMethod().score("Paris", "A capital da França é Paris, uma cidade linda.")

    assert score == 1.0


def test_token_recall_is_partial_when_tokens_are_missing():
    assert TokenRecallScoringMethod().score("one two three four", "one two") == pytest.approx(0.5)


def test_token_recall_handles_empty_texts():
    method = TokenRecallScoringMethod()

    assert method.score("", "") == 1.0
    assert method.score("", "something") == 0.0
    assert method.score("something", "") == 0.0


def test_contains_answer_finds_the_expected_text_inside_a_longer_answer():
    method = ContainsAnswerScoringMethod()

    assert method.score_kind is ScoreKind.BINARY
    assert method.score("Paris", "A capital é Paris.") == 1.0
    assert method.score("Paris", "Parisiense") == 0.0
    assert method.score("Paris", "Lyon") == 0.0


def test_chrf_is_one_for_identical_text_and_zero_for_empty_answer():
    method = ChrfScoringMethod()

    assert method.score("O rio Amazonas", "O rio Amazonas") == pytest.approx(1.0)
    assert method.score("O rio Amazonas", "") == 0.0


def test_chrf_rewards_inflected_words_that_share_characters():
    method = ChrfScoringMethod()

    assert method.score("os planetas giram", "o planeta gira") > method.score("os planetas giram", "xyz")


def test_judge_converts_the_rating_to_a_zero_to_one_score():
    gateway = FakeGateway("8")
    method = LlmJudgeScoringMethod(gateway)
    method.configure(SETTINGS)

    assert method.score("Paris", "Paris") == pytest.approx(0.8)
    assert "Paris" in gateway.prompts[0]


def test_judge_reads_the_rating_from_a_wordy_reply():
    method = LlmJudgeScoringMethod(FakeGateway("Rating: 10"))
    method.configure(SETTINGS)

    assert method.score("a", "b") == 1.0


def test_judge_scores_an_empty_answer_without_calling_the_model():
    gateway = FakeGateway("10")
    method = LlmJudgeScoringMethod(gateway)

    assert method.score("Paris", "  ") == 0.0
    assert gateway.prompts == []


def test_judge_fails_without_a_rating():
    method = LlmJudgeScoringMethod(FakeGateway("no idea"))
    method.configure(SETTINGS)

    with pytest.raises(JudgeResponseError):
        method.score("a", "b")


def test_judge_fails_when_it_was_never_configured():
    with pytest.raises(LanguageModelError):
        LlmJudgeScoringMethod(FakeGateway("5")).score("a", "b")


def test_overview_skips_the_judge_unless_it_produced_the_result():
    judge = LlmJudgeScoringMethod(FakeGateway("5"))
    judge.configure(SETTINGS)
    exact_match = ExactMatchScoringMethod()
    question = Question("1", "Q?", "Paris")
    from datetime import datetime

    exact_result = EvaluationResult((QuestionScore(question, "Paris", 1.0, 0.1),), datetime.now(), exact_match)
    judge_result = EvaluationResult((QuestionScore(question, "Paris", 0.5, 0.1),), datetime.now(), judge)

    without_judge = BuildMetricOverview().execute(exact_result, [exact_match, judge])
    with_judge = BuildMetricOverview().execute(judge_result, [exact_match, judge])

    assert [entry.method.identifier for entry in without_judge.entries] == ["exact_match"]
    assert [entry.method.identifier for entry in with_judge.entries] == ["exact_match", "llm_judge"]
