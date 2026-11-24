from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedContext:
    identifier: str | None
    text: str
    retrieval_score: float | None = None
