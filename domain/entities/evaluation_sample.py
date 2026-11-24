from dataclasses import dataclass

from domain.entities.question import Question
from domain.entities.question_score import QuestionScore
from domain.entities.retrieved_context import RetrievedContext


@dataclass(frozen=True)
class EvaluationSample:
    question: Question
    given_answer: str
    contexts: tuple[RetrievedContext, ...] | None = None

    @property
    def question_text(self) -> str:
        return self.question.text

    @property
    def expected_answer(self) -> str:
        return self.question.expected_answer

    @property
    def has_contexts(self) -> bool:
        return self.contexts is not None

    @classmethod
    def from_score(cls, score: QuestionScore) -> "EvaluationSample":
        return cls(score.question, score.given_answer, score.contexts)
