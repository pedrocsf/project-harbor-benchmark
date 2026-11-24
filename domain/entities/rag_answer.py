from dataclasses import dataclass

from domain.entities.retrieved_context import RetrievedContext


@dataclass(frozen=True)
class RagAnswer:
    answer: str
    contexts: tuple[RetrievedContext, ...] | None
