import pytest

from domain.entities.evaluation_sample import EvaluationSample
from domain.entities.language_model_settings import LanguageModelSettings
from domain.entities.question import Question
from domain.entities.retrieved_context import RetrievedContext
from domain.errors import DomainError, JudgeResponseError, LanguageModelError
from domain.gateways.language_model_gateway import LanguageModelGateway
from domain.gateways.text_encoder import TextEncoder
from domain.scoring.metric_parameters import InvalidParameterError
from domain.scoring.rag.answer_relevancy_scoring_method import AnswerRelevancyScoringMethod
from domain.scoring.rag.context_relevance_scoring_method import ContextRelevanceScoringMethod
from domain.scoring.rag.faithfulness_scoring_method import (
    FaithfulnessScoringMethod,
    number_statements,
    parse_verdicts,
)
from domain.scoring.rag.language_model_metric import format_contexts, parse_listed_lines
from domain.scoring.sample_requirements import MetricGroup, SampleRequirement

SETTINGS = LanguageModelSettings("http://127.0.0.1:1234/v1/chat/completions")
QUESTION = Question("1", "Quem pintou a Mona Lisa?", "Leonardo da Vinci.")
CONTEXTS = (
    RetrievedContext("doc-1", "Leonardo da Vinci pintou a Mona Lisa."),
    RetrievedContext("doc-2", "O Louvre fica em Paris."),
)


class ScriptedGateway(LanguageModelGateway):
    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []
        self.temperatures = []

    def ask(self, settings, question_text, temperature=None):
        self.prompts.append(question_text)
        self.temperatures.append(temperature)
        return self.replies.pop(0)


class TableEncoder(TextEncoder):
    def __init__(self, vectors):
        self.vectors = vectors
        self.prepared = False

    def prepare(self):
        self.prepared = True

    def encode(self, texts):
        return [self.vectors[text] for text in texts]


def configured(method):
    method.configure(SETTINGS)
    return method


def sample(answer="Foi Leonardo da Vinci, em Florença.", contexts=CONTEXTS):
    return EvaluationSample(QUESTION, answer, contexts)


def test_parse_listed_lines_strips_markers_and_none():
    reply = "1. Leonardo pintou.\n- Foi em Florença.\n\n2) Terceira\n• Quarta\nNONE"

    assert parse_listed_lines(reply) == ("Leonardo pintou.", "Foi em Florença.", "Terceira", "Quarta")
    assert parse_listed_lines("None.") == ()


def test_format_contexts_numbers_each_context():
    assert format_contexts(CONTEXTS) == "[1] Leonardo da Vinci pintou a Mona Lisa.\n\n[2] O Louvre fica em Paris."


def test_parse_verdicts_reads_numbered_answers_and_defaults_missing_to_no():
    assert parse_verdicts("1: yes\n2. No\n[3] - sim", 3) == (True, False, True)
    assert parse_verdicts("Here you go\n2: yes", 3) == (False, True, False)
    with pytest.raises(JudgeResponseError):
        parse_verdicts("I cannot tell", 2)


def test_faithfulness_counts_supported_statements():
    gateway = ScriptedGateway(["Leonardo da Vinci pintou a Mona Lisa.\nA pintura foi feita em Florença.", "1: yes\n2: no"])
    method = configured(FaithfulnessScoringMethod(gateway))

    verdicts = method.verdicts(sample())

    assert verdicts.statements == ("Leonardo da Vinci pintou a Mona Lisa.", "A pintura foi feita em Florença.")
    assert verdicts.supported == (True, False)
    assert verdicts.score == pytest.approx(0.5)
    assert "Foi Leonardo da Vinci, em Florença." in gateway.prompts[0]
    assert QUESTION.text in gateway.prompts[0]
    assert "[2] O Louvre fica em Paris." in gateway.prompts[1]
    assert number_statements(verdicts.statements) in gateway.prompts[1]
    assert gateway.temperatures == [None, None]


def test_faithfulness_skips_calls_when_there_is_nothing_to_check():
    gateway = ScriptedGateway(["NONE", "Uma afirmação."])
    method = configured(FaithfulnessScoringMethod(gateway))

    assert method.score_sample(sample(answer="  ")) == 0.0
    assert method.score_sample(sample()) == 0.0
    assert method.score_sample(sample(contexts=())) == 0.0
    assert len(gateway.prompts) == 1


def test_faithfulness_caps_statements_and_contexts():
    gateway = ScriptedGateway(["a\nb\nc", "1: yes\n2: yes"])
    method = configured(FaithfulnessScoringMethod(gateway))
    method.update_parameters({"max_statements": 2, "context_limit": 1, "set_temperature": True, "temperature": 0.3})

    assert method.score_sample(sample()) == 1.0
    assert "[2]" not in gateway.prompts[1]
    assert gateway.temperatures == [0.3, 0.3]


def test_context_relevance_rates_each_context():
    gateway = ScriptedGateway(["1", "0"])
    method = configured(ContextRelevanceScoringMethod(gateway))

    ratings = method.ratings(sample())

    assert ratings.ratings == (1, 0)
    assert ratings.score == pytest.approx(0.5)
    assert "O Louvre fica em Paris." in gateway.prompts[1]
    assert "0 (unrelated or useless) to 1" in gateway.prompts[0]


def test_context_relevance_with_a_larger_scale_and_limit():
    gateway = ScriptedGateway(["Rating: 4"])
    method = configured(ContextRelevanceScoringMethod(gateway))
    method.update_parameters({"rating_scale_max": 5, "context_limit": 1})

    assert method.score_sample(sample()) == pytest.approx(0.8)
    assert method.score_sample(sample(contexts=())) == 0.0


def test_context_relevance_rejects_replies_without_a_rating():
    method = configured(ContextRelevanceScoringMethod(ScriptedGateway(["useful"])))

    with pytest.raises(JudgeResponseError):
        method.score_sample(sample())


def test_answer_relevancy_averages_the_similarity_of_generated_questions():
    gateway = ScriptedGateway(["1. Quem pintou a Mona Lisa?\n2. Onde fica o Louvre?\n3. Extra?"])
    encoder = TableEncoder(
        {
            QUESTION.text: (1.0, 0.0),
            "Quem pintou a Mona Lisa?": (1.0, 0.0),
            "Onde fica o Louvre?": (0.0, 1.0),
        }
    )
    method = configured(AnswerRelevancyScoringMethod(gateway, encoder))
    method.update_parameters({"question_count": 2})

    generated = method.generated_questions(sample())

    assert generated.questions == ("Quem pintou a Mona Lisa?", "Onde fica o Louvre?")
    assert generated.similarities == pytest.approx((1.0, 0.0))
    assert generated.score == pytest.approx(0.5)
    assert "Write 2 different questions" in gateway.prompts[0]


def test_answer_relevancy_needs_no_contexts_and_prepares_the_encoder():
    encoder = TableEncoder({})
    method = AnswerRelevancyScoringMethod(ScriptedGateway([]), encoder)

    method.prepare()

    assert encoder.prepared
    assert method.requirements == frozenset()
    assert method.metric_group is MetricGroup.ANSWER
    assert method.score_sample(sample(answer="", contexts=None)) == 0.0


def test_answer_relevancy_rejects_an_empty_reply():
    method = configured(AnswerRelevancyScoringMethod(ScriptedGateway(["NONE"]), TableEncoder({})))

    with pytest.raises(JudgeResponseError):
        method.score_sample(sample())


def judge_methods():
    return [
        FaithfulnessScoringMethod(ScriptedGateway([])),
        ContextRelevanceScoringMethod(ScriptedGateway([])),
        AnswerRelevancyScoringMethod(ScriptedGateway([]), TableEncoder({})),
    ]


@pytest.mark.parametrize("method", judge_methods(), ids=lambda method: method.identifier)
def test_judge_methods_need_a_configured_model(method):
    assert method.uses_language_model
    with pytest.raises(LanguageModelError, match="needs a model to act as judge"):
        method.score_sample(sample())


@pytest.mark.parametrize(
    ("method", "key"),
    [
        (FaithfulnessScoringMethod(None), "statements_prompt"),
        (FaithfulnessScoringMethod(None), "verification_prompt"),
        (ContextRelevanceScoringMethod(None), "prompt_template"),
        (AnswerRelevancyScoringMethod(None, TableEncoder({})), "prompt_template"),
    ],
)
def test_prompt_templates_are_validated(method, key):
    with pytest.raises(InvalidParameterError, match="must contain"):
        method.update_parameters({key: "no placeholders"})
    with pytest.raises(InvalidParameterError, match="cannot be filled"):
        method.update_parameters({key: method.parameter(key) + " {unknown}"})


def test_grounding_judges_need_contexts():
    for method in judge_methods()[:2]:
        assert method.requirements == {SampleRequirement.CONTEXTS}
        configured(method)
        with pytest.raises(DomainError, match="contexts retrieved"):
            method.score_sample(sample(contexts=None))


def test_judge_call_estimates():
    from domain.scoring.exact_match_scoring_method import ExactMatchScoringMethod
    from domain.scoring.llm_judge_scoring_method import LlmJudgeScoringMethod

    context_relevance = ContextRelevanceScoringMethod(None)
    judge = LlmJudgeScoringMethod(None)
    judge.update_parameters({"samples": 3})

    assert ExactMatchScoringMethod().judge_calls_per_question() == 0
    assert judge.judge_calls_per_question() == 3
    assert FaithfulnessScoringMethod(None).judge_calls_per_question() == 2
    assert AnswerRelevancyScoringMethod(None, TableEncoder({})).judge_calls_per_question() == 1
    assert context_relevance.judge_calls_per_question() == 5
    context_relevance.update_parameters({"context_limit": 0})
    assert context_relevance.judge_calls_per_question() is None
