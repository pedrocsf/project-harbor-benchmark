from dataclasses import dataclass

from domain.entities.retrieved_context import RetrievedContext


@dataclass(frozen=True)
class ImportedAnswer:
    question_identifier: str
    answer: str
    contexts: tuple[RetrievedContext, ...] | None = None
    response_seconds: float = 0.0
