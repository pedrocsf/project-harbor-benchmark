from dataclasses import dataclass
from statistics import fmean

from domain.entities.evaluation_sample import EvaluationSample
from domain.errors import JudgeResponseError
from domain.gateways.language_model_gateway import LanguageModelGateway
from domain.gateways.text_encoder import TextEncoder
from domain.scoring.embedding_scoring_method import (
    NEGATIVE_HANDLING_SPEC,
    NORMALIZE_VECTORS_SPEC,
    SIMILARITY_FUNCTION_SPEC,
)
from domain.scoring.llm_judge_scoring_method import SET_TEMPERATURE_SPEC, TEMPERATURE_SPEC
from domain.scoring.metric_parameters import ParameterKind, ParameterSpec
from domain.scoring.rag.language_model_metric import LanguageModelSampleMethod, parse_listed_lines
from domain.scoring.sample_requirements import MetricGroup
from domain.scoring.scoring_method import ScoreKind
from domain.scoring.vector_similarity import measure_similarity

DEFAULT_QUESTION_COUNT = 3
QUESTION_GENERATION_CALLS = 1
NO_QUESTIONS_MESSAGE = "The judge did not write any question for the answer: {reply!r}"
QUESTION_GENERATION_PROMPT_TEMPLATE = """Write {question_count} different questions that the answer below \
would fully answer. Base them only on the answer and write them in the same language as the answer.

Answer:
{answer}

Write one question per line, with no numbering."""


@dataclass(frozen=True)
class GeneratedQuestions:
    questions: tuple[str, ...]
    similarities: tuple[float, ...]

    @property
    def score(self) -> float:
        if not self.similarities:
            return 0.0
        return fmean(self.similarities)


class AnswerRelevancyScoringMethod(LanguageModelSampleMethod):
    identifier = "answer_relevancy"
    display_name = "Answer relevancy"
    column_header = "Relevancy"
    score_kind = ScoreKind.CONTINUOUS
    requirements = frozenset()
    metric_group = MetricGroup.ANSWER
    template_placeholders = {"prompt_template": ("answer", "question_count")}
    parameter_specs = (
        ParameterSpec(
            key="question_count",
            label="Generated questions",
            description="How many questions the judge writes from the answer. The score is their average similarity to the original question.",
            kind=ParameterKind.INTEGER,
            default=DEFAULT_QUESTION_COUNT,
            minimum=1,
            maximum=10,
        ),
        SIMILARITY_FUNCTION_SPEC,
        NEGATIVE_HANDLING_SPEC,
        NORMALIZE_VECTORS_SPEC,
        ParameterSpec(
            key="prompt_template",
            label="Prompt template",
            description="Asks the judge to write questions from the answer. Use {answer} and {question_count}.",
            kind=ParameterKind.TEXT,
            default=QUESTION_GENERATION_PROMPT_TEMPLATE,
        ),
        SET_TEMPERATURE_SPEC,
        TEMPERATURE_SPEC,
    )

    def __init__(self, language_model_gateway: LanguageModelGateway | None, text_encoder: TextEncoder):
        super().__init__(language_model_gateway)
        self._text_encoder = text_encoder

    def prepare(self) -> None:
        self._text_encoder.prepare()

    def judge_calls_per_question(self) -> int | None:
        return QUESTION_GENERATION_CALLS

    def score_sample(self, sample: EvaluationSample) -> float:
        return self.generated_questions(sample).score

    def generated_questions(self, sample: EvaluationSample) -> GeneratedQuestions:
        if not sample.given_answer.strip():
            return GeneratedQuestions((), ())
        question_count = int(self.parameter("question_count"))
        questions = self.generate_questions(sample, question_count)[:question_count]
        vectors = self._text_encoder.encode([sample.question_text, *questions])
        similarities = tuple(
            measure_similarity(vectors[0], vector, self.parameters).score for vector in vectors[1:]
        )
        return GeneratedQuestions(questions, similarities)

    def generate_questions(self, sample: EvaluationSample, question_count: int) -> tuple[str, ...]:
        prompt = str(self.parameter("prompt_template")).format(
            answer=sample.given_answer, question_count=question_count
        )
        reply = self.ask_judge(prompt)
        questions = parse_listed_lines(reply)
        if not questions:
            raise JudgeResponseError(NO_QUESTIONS_MESSAGE.format(reply=reply[:80]))
        return questions
