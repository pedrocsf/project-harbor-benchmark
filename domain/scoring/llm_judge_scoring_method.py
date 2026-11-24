import re
from collections.abc import Mapping

from domain.entities.language_model_settings import LanguageModelSettings
from domain.errors import JudgeResponseError, LanguageModelError
from domain.gateways.language_model_gateway import LanguageModelGateway
from domain.scoring.metric_parameters import (
    InvalidParameterError,
    ParameterKind,
    ParameterSpec,
    ParameterValue,
)
from domain.scoring.scoring_method import ScoreKind, ScoringMethod

MAXIMUM_RATING = 10
MINIMUM_RATING_SCALE = 2
MAXIMUM_RATING_SCALE = 100
MINIMUM_SAMPLES = 1
MAXIMUM_SAMPLES = 10
MINIMUM_TEMPERATURE = 0.0
MAXIMUM_TEMPERATURE = 2.0
TEMPERATURE_STEP = 0.1
RATING_PATTERN = re.compile(r"\b(10|[0-9])\b")
MISSING_SETTINGS_MESSAGE = "The LLM judge needs a model endpoint. Run the benchmark first."
UNREADABLE_RATING_MESSAGE = "The LLM judge did not return a rating from 0 to {maximum_rating}: {reply!r}"
REQUIRED_PLACEHOLDERS = ("expected_answer", "given_answer")
MISSING_PLACEHOLDER_MESSAGE = "The prompt template must contain {{{placeholder}}}."
UNFORMATTABLE_TEMPLATE_MESSAGE = "The prompt template cannot be filled in: {reason}."
JUDGE_PROMPT_TEMPLATE = """You are a strict grader. Compare the candidate answer with the reference answer.

Rate how correct the candidate is, considering only whether it conveys the same facts as the reference. \
Ignore style, length and wording. Use an integer from 0 (wrong or unrelated) to {maximum_rating} (fully correct).

Reference answer:
{expected_answer}

Candidate answer:
{given_answer}

Reply with the integer only."""


def build_judge_prompt(
    template: str, expected_answer: str, given_answer: str, maximum_rating: int
) -> str:
    return template.format(
        expected_answer=expected_answer,
        given_answer=given_answer,
        maximum_rating=maximum_rating,
    )


JUDGE_PROMPT = build_judge_prompt(
    JUDGE_PROMPT_TEMPLATE, "{expected_answer}", "{given_answer}", MAXIMUM_RATING
)


def find_rating(reply: str, maximum_rating: int) -> re.Match | None:
    for match in re.finditer(r"\b\d+\b", reply):
        if int(match.group()) <= maximum_rating:
            return match
    return None


class LlmJudgeScoringMethod(ScoringMethod):
    identifier = "llm_judge"
    display_name = "LLM judge"
    column_header = "Judge"
    score_kind = ScoreKind.CONTINUOUS
    uses_language_model = True
    parameter_specs = (
        ParameterSpec(
            key="rating_scale_max",
            label="Rating scale maximum",
            description="The judge rates answers with an integer from 0 to this value; the score is the rating divided by it.",
            kind=ParameterKind.INTEGER,
            default=MAXIMUM_RATING,
            minimum=MINIMUM_RATING_SCALE,
            maximum=MAXIMUM_RATING_SCALE,
        ),
        ParameterSpec(
            key="prompt_template",
            label="Prompt template",
            description="The instruction sent to the judge. Use {expected_answer}, {given_answer} and {maximum_rating} as placeholders.",
            kind=ParameterKind.TEXT,
            default=JUDGE_PROMPT_TEMPLATE,
        ),
        ParameterSpec(
            key="samples",
            label="Samples per answer",
            description="How many times the judge is asked about each answer. The ratings are averaged.",
            kind=ParameterKind.INTEGER,
            default=MINIMUM_SAMPLES,
            minimum=MINIMUM_SAMPLES,
            maximum=MAXIMUM_SAMPLES,
        ),
        ParameterSpec(
            key="set_temperature",
            label="Set temperature",
            description="When off, the provider's default temperature is used. Some models reject custom temperatures.",
            kind=ParameterKind.BOOLEAN,
            default=False,
        ),
        ParameterSpec(
            key="temperature",
            label="Temperature",
            description="Sampling temperature sent to the model; applies only when \"Set temperature\" is on. Higher values make the ratings more varied.",
            kind=ParameterKind.DECIMAL,
            default=MINIMUM_TEMPERATURE,
            minimum=MINIMUM_TEMPERATURE,
            maximum=MAXIMUM_TEMPERATURE,
            step=TEMPERATURE_STEP,
            decimals=1,
        ),
    )

    def __init__(self, language_model_gateway: LanguageModelGateway):
        self._language_model_gateway = language_model_gateway
        self._settings: LanguageModelSettings | None = None

    def configure(self, settings: LanguageModelSettings) -> None:
        self._settings = settings

    def score(self, expected_answer: str, given_answer: str) -> float:
        if not given_answer.strip():
            return 0.0
        if self._settings is None:
            raise LanguageModelError(MISSING_SETTINGS_MESSAGE)
        maximum_rating = int(self.parameter("rating_scale_max"))
        prompt = build_judge_prompt(
            str(self.parameter("prompt_template")), expected_answer, given_answer, maximum_rating
        )
        sample_count = int(self.parameter("samples"))
        ratings = [
            self._request_rating(prompt, expected_answer, given_answer)
            for _ in range(sample_count)
        ]
        return sum(ratings) / sample_count / maximum_rating

    def _request_rating(self, prompt: str, expected_answer: str, given_answer: str) -> int:
        temperature = float(self.parameter("temperature")) if self.parameter("set_temperature") else None
        reply = self._language_model_gateway.ask(self._settings, prompt, temperature)
        return self._parse_rating(reply)

    def _parse_rating(self, reply: str) -> int:
        maximum_rating = int(self.parameter("rating_scale_max"))
        match = find_rating(reply, maximum_rating)
        if match is None:
            raise JudgeResponseError(
                UNREADABLE_RATING_MESSAGE.format(maximum_rating=maximum_rating, reply=reply[:80])
            )
        return int(match.group())

    def _check_parameters(self, values: Mapping[str, ParameterValue]) -> None:
        template = str(values["prompt_template"])
        for placeholder in REQUIRED_PLACEHOLDERS:
            if "{" + placeholder + "}" not in template:
                raise InvalidParameterError(
                    MISSING_PLACEHOLDER_MESSAGE.format(placeholder=placeholder)
                )
        try:
            build_judge_prompt(template, "", "", int(values["rating_scale_max"]))
        except (KeyError, IndexError, ValueError) as error:
            raise InvalidParameterError(
                UNFORMATTABLE_TEMPLATE_MESSAGE.format(reason=repr(error))
            ) from error
