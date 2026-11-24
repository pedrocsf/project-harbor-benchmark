from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    identifier: str
    text: str
    expected_answer: str
    relevant_context_ids: tuple[str, ...] = ()
    relevant_passages: tuple[str, ...] = ()

    @property
    def has_relevance_labels(self) -> bool:
        return bool(self.relevant_context_ids or self.relevant_passages)
