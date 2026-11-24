from pathlib import Path

import pytest

from data.scoring.bleu_scoring_method import BleuScoringMethod
from data.scoring.chrf_scoring_method import ChrfScoringMethod
from demo.demo_data import DEMO_ENTRIES
from demo.demo_question_repository import DemoQuestionRepository
from demo.demo_run_evaluation import DemoRunEvaluation
from domain.entities.evaluation_request import EvaluationRequest
from domain.entities.language_model_settings import LanguageModelSettings
from domain.errors import EvaluationCancelledError
from domain.scoring.contains_answer_scoring_method import ContainsAnswerScoringMethod
from domain.scoring.exact_match_scoring_method import ExactMatchScoringMethod
from domain.scoring.rouge_scoring_methods import RougeLScoringMethod, RougeNScoringMethod
from domain.scoring.scoring_method import ScoreKind
from domain.scoring.token_f1_scoring_method import TokenF1ScoringMethod
from domain.scoring.token_recall_scoring_method import TokenRecallScoringMethod
from domain.usecases.build_metric_overview import BuildMetricOverview
from domain.usecases.load_questions import LoadQuestions
from domain.usecases.rescore_result import RescoreResult
from main_demo import build_demo_methods

SETTINGS = LanguageModelSettings(endpoint_url="http://127.0.0.1:1234/v1/chat/completions")
SCORE_TOLERANCE = 1e-3


def build_request(method):
    questions = tuple(LoadQuestions(DemoQuestionRepository(DEMO_ENTRIES)).execute(Path("demo-dataset.json")))
    return EvaluationRequest(SETTINGS, questions, method)


def lexical_methods():
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


FIXED_SCORE_EXCEPTIONS = {"answer_relevancy"}


def test_every_entry_has_fixed_scores_for_the_answer_metrics_and_rag_data():
    from demo.demo_rag_data import DEMO_RAG_ENTRIES
    from main import build_answer_methods, build_language_model_gateway

    methods = build_answer_methods(build_language_model_gateway(), None)
    identifiers = {method.identifier for method in methods} - FIXED_SCORE_EXCEPTIONS

    assert all(set(entry.scores) == identifiers for entry in DEMO_ENTRIES)
    assert set(DEMO_RAG_ENTRIES) == {entry.identifier for entry in DEMO_ENTRIES}


def test_demo_offers_every_metric_of_the_real_app():
    from main import build_language_model_gateway, build_scoring_methods

    real = [method.identifier for method in build_scoring_methods(build_language_model_gateway())]

    assert [method.identifier for method in build_demo_methods()] == real


@pytest.mark.parametrize("method", lexical_methods(), ids=lambda method: method.identifier)
def test_fixed_scores_match_the_real_formulas(method):
    for entry in DEMO_ENTRIES:
        real_score = method.score(entry.expected_answer, entry.given_answer)

        assert entry.scores[method.identifier] == pytest.approx(real_score, abs=SCORE_TOLERANCE), entry.identifier


def test_default_demo_scores_reproduce_the_tables():
    for method in build_demo_methods():
        if method.identifier not in DEMO_ENTRIES[0].scores:
            continue
        for entry in DEMO_ENTRIES:
            score = method.score(entry.expected_answer, entry.given_answer)

            assert score == pytest.approx(entry.scores[method.identifier], abs=0.0005), (method.identifier, entry.identifier)


def test_corpus_bleu_comes_from_the_real_method():
    pairs = [(entry.expected_answer, entry.given_answer) for entry in DEMO_ENTRIES]
    bleu = next(method for method in build_demo_methods() if method.identifier == "bleu")

    assert bleu.corpus_score(pairs) == pytest.approx(0.433, abs=SCORE_TOLERANCE)


def test_changing_a_parameter_changes_the_demo_scores():
    rouge = next(method for method in build_demo_methods() if method.identifier == "rouge_1")
    entry = DEMO_ENTRIES[1]
    before = rouge.score(entry.expected_answer, entry.given_answer)

    rouge.update_parameters({"score_type": "precision"})

    exact = next(method for method in build_demo_methods() if method.identifier == "exact_match")
    assert exact.score("Paris", "paris") == 1.0
    exact.update_parameters({"lowercase": False})
    assert exact.score("Paris", "paris") == 0.0


def test_the_demo_judge_requantizes_to_the_rating_scale():
    judge = next(method for method in build_demo_methods() if method.identifier == "llm_judge")
    entry = next(entry for entry in DEMO_ENTRIES if 0.0 < entry.scores["llm_judge"] < 1.0)
    expected_fraction = entry.scores["llm_judge"]

    judge.update_parameters({"rating_scale_max": 4})

    assert judge.score(entry.expected_answer, entry.given_answer) == round(expected_fraction * 4) / 4
    assert judge.uses_language_model is False


def test_every_fixed_score_is_between_zero_and_one():
    assert all(0.0 <= value <= 1.0 for entry in DEMO_ENTRIES for value in entry.scores.values())


def test_demo_methods_mirror_the_real_ones():
    from main import build_language_model_gateway, build_scoring_methods

    real = [(m.identifier, m.display_name, m.column_header, m.score_kind) for m in build_scoring_methods(build_language_model_gateway())]
    demo = [(m.identifier, m.display_name, m.column_header, m.score_kind) for m in build_demo_methods()]

    assert demo == real


def test_demo_methods_keep_their_score_kind():
    exact_match = next(method for method in build_demo_methods() if method.identifier == "exact_match")
    entry = DEMO_ENTRIES[0]

    assert exact_match.score(entry.expected_answer, entry.given_answer) == 1.0
    assert exact_match.score_kind is ScoreKind.BINARY


def test_the_demo_dataset_has_twelve_questions():
    questions = DemoQuestionRepository(DEMO_ENTRIES).load(Path("anything.json"))

    assert len(questions) == 12
    assert questions[0].text == DEMO_ENTRIES[0].question


def test_the_simulated_run_uses_the_fixed_answers_and_times():
    method = build_demo_methods()[0]

    result = DemoRunEvaluation(DEMO_ENTRIES, step_seconds=0).execute(build_request(method))

    assert [score.given_answer for score in result.scores] == [entry.given_answer for entry in DEMO_ENTRIES]
    assert [score.response_seconds for score in result.scores] == [entry.response_seconds for entry in DEMO_ENTRIES]
    assert [score.score for score in result.scores] == pytest.approx(
        [entry.scores["embedding"] for entry in DEMO_ENTRIES], abs=0.0005
    )


def test_the_simulated_run_reports_progress():
    progress = []

    DemoRunEvaluation(DEMO_ENTRIES, step_seconds=0).execute(
        build_request(build_demo_methods()[0]), on_progress=lambda completed, total: progress.append((completed, total))
    )

    assert progress[0] == (1, 12)
    assert progress[-1] == (12, 12)


def test_the_simulated_run_can_be_cancelled():
    with pytest.raises(EvaluationCancelledError):
        DemoRunEvaluation(DEMO_ENTRIES, step_seconds=0).execute(
            build_request(build_demo_methods()[0]), is_cancelled=lambda: True
        )


def test_switching_metrics_and_building_the_overview_work_with_the_demo_methods():
    methods = build_demo_methods()
    result = DemoRunEvaluation(DEMO_ENTRIES, step_seconds=0).execute(build_request(methods[0]))

    rescored = RescoreResult().execute(result, methods[1])
    overview = BuildMetricOverview().execute(result, methods)

    assert [score.score for score in rescored.scores] == [entry.scores["exact_match"] for entry in DEMO_ENTRIES]
    answer_methods = [method.identifier for method in methods if not method.requirements]
    assert [entry.method.identifier for entry in overview.entries] == answer_methods
    assert rescored.metrics.correct_count == 3
