import re

from domain.entities.language_model_settings import LanguageModelSettings
from domain.errors import JudgeResponseError, LanguageModelError
from domain.gateways.language_model_gateway import LanguageModelGateway
from domain.scoring.scoring_method import ScoreKind, ScoringMethod

MAXIMUM_RATING = 10
RATING_PATTERN = re.compile(r"\b(10|[0-9])\b")
MISSING_SETTINGS_MESSAGE = "The LLM judge needs a model endpoint. Run the benchmark first."
UNREADABLE_RATING_MESSAGE = "The LLM judge did not return a rating from 0 to 10: {reply!r}"
JUDGE_PROMPT = """You are a strict grader. Compare the candidate answer with the reference answer.

Rate how correct the candidate is, considering only whether it conveys the same facts as the reference. \
Ignore style, length and wording. Use an integer from 0 (wrong or unrelated) to 10 (fully correct).

Reference answer:
{expected_answer}

Candidate answer:
{given_answer}

Reply with the integer only."""


class LlmJudgeScoringMethod(ScoringMethod):
    identifier = "llm_judge"
    display_name = "LLM judge"
    column_header = "Judge"
    score_kind = ScoreKind.CONTINUOUS
    uses_language_model = True

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
        prompt = JUDGE_PROMPT.format(expected_answer=expected_answer, given_answer=given_answer)
        reply = self._language_model_gateway.ask(self._settings, prompt)
        return self._parse_rating(reply) / MAXIMUM_RATING

    def _parse_rating(self, reply: str) -> int:
        match = RATING_PATTERN.search(reply)
        if match is None:
            raise JudgeResponseError(UNREADABLE_RATING_MESSAGE.format(reply=reply[:80]))
        return int(match.group(1))
