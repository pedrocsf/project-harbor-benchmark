from dataclasses import dataclass

from domain.entities.question import Question
from domain.entities.retrieved_context import RetrievedContext


@dataclass(frozen=True)
class QuestionScore:
    question: Question
    given_answer: str
    score: float
    response_seconds: float
    contexts: tuple[RetrievedContext, ...] | None = None
