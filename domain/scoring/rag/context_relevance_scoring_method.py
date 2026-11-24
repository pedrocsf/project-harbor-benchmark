from dataclasses import dataclass

from domain.entities.evaluation_sample import EvaluationSample
from domain.errors import JudgeResponseError
from domain.scoring.llm_judge_scoring_method import SET_TEMPERATURE_SPEC, TEMPERATURE_SPEC, find_rating
from domain.scoring.metric_parameters import ParameterKind, ParameterSpec
from domain.scoring.rag.language_model_metric import LanguageModelSampleMethod, judge_context_limit_spec
from domain.scoring.sample_requirements import MetricGroup, SampleRequirement
from domain.scoring.scoring_method import ScoreKind

DEFAULT_RATING_SCALE = 1
DEFAULT_CONTEXT_LIMIT = 5
UNREADABLE_RATING_MESSAGE = "The judge did not return a rating from 0 to {maximum_rating}: {reply!r}"
CONTEXT_RELEVANCE_PROMPT_TEMPLATE = """Rate how useful the context is for answering the question. \
Use an integer from 0 (unrelated or useless) to {maximum_rating} (contains what is needed to answer).

Question:
{question}

Context:
{context}

Reply with the integer only."""


@dataclass(frozen=True)
class ContextRatings:
    ratings: tuple[int, ...]
    maximum_rating: int

    @property
    def score(self) -> float:
        if not self.ratings:
            return 0.0
        return sum(self.ratings) / len(self.ratings) / self.maximum_rating


class ContextRelevanceScoringMethod(LanguageModelSampleMethod):
    identifier = "context_relevance"
    display_name = "Context relevance"
    column_header = "Ctx relevance"
    score_kind = ScoreKind.CONTINUOUS
    requirements = frozenset({SampleRequirement.CONTEXTS})
    metric_group = MetricGroup.RETRIEVAL
    template_placeholders = {"prompt_template": ("question", "context", "maximum_rating")}
    parameter_specs = (
        ParameterSpec(
            key="rating_scale_max",
            label="Rating scale maximum",
            description="Each context is rated from 0 to this value. 1 makes it a yes/no decision.",
            kind=ParameterKind.INTEGER,
            default=DEFAULT_RATING_SCALE,
            minimum=1,
            maximum=10,
        ),
        judge_context_limit_spec(DEFAULT_CONTEXT_LIMIT),
        ParameterSpec(
            key="prompt_template",
            label="Prompt template",
            description="Sent once per context. Use {question}, {context} and {maximum_rating}.",
            kind=ParameterKind.TEXT,
            default=CONTEXT_RELEVANCE_PROMPT_TEMPLATE,
        ),
        SET_TEMPERATURE_SPEC,
        TEMPERATURE_SPEC,
    )

    def judge_calls_per_question(self) -> int | None:
        limit = int(self.parameter("context_limit"))
        return limit if limit > 0 else None

    def score_sample(self, sample: EvaluationSample) -> float:
        return self.ratings(sample).score

    def ratings(self, sample: EvaluationSample) -> ContextRatings:
        maximum_rating = int(self.parameter("rating_scale_max"))
        contexts = self.judged_contexts(sample)
        ratings = tuple(self.rate_context(sample.question_text, context.text, maximum_rating) for context in contexts)
        return ContextRatings(ratings, maximum_rating)

    def rate_context(self, question: str, context: str, maximum_rating: int) -> int:
        prompt = str(self.parameter("prompt_template")).format(
            question=question, context=context, maximum_rating=maximum_rating
        )
        reply = self.ask_judge(prompt)
        match = find_rating(reply, maximum_rating)
        if match is None:
            raise JudgeResponseError(
                UNREADABLE_RATING_MESSAGE.format(maximum_rating=maximum_rating, reply=reply[:80])
            )
        return int(match.group())
