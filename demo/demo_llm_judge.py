from collections.abc import Mapping

from domain.entities.language_model_settings import LanguageModelSettings
from domain.errors import DomainError
from domain.scoring.llm_judge_scoring_method import LlmJudgeScoringMethod

DEMO_JUDGE_ENDPOINT = "http://127.0.0.1:1234/v1/chat/completions"
UNKNOWN_ANSWERS_MESSAGE = "The demo judge has no rating for this pair of answers."


class UnknownDemoAnswersError(DomainError):
    pass


class DemoLlmJudgeScoringMethod(LlmJudgeScoringMethod):
    uses_language_model = False

    def __init__(self, fractions_by_answers: Mapping[tuple[str, str], float]):
        super().__init__(None)
        self._fractions_by_answers = fractions_by_answers
        self.configure(LanguageModelSettings(endpoint_url=DEMO_JUDGE_ENDPOINT))

    def _request_rating(self, prompt: str, expected_answer: str, given_answer: str) -> int:
        key = (expected_answer, given_answer)
        if key not in self._fractions_by_answers:
            raise UnknownDemoAnswersError(UNKNOWN_ANSWERS_MESSAGE)
        return round(self._fractions_by_answers[key] * int(self.parameter("rating_scale_max")))
