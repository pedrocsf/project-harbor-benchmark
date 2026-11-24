from collections.abc import Mapping, Sequence
from pathlib import Path

from demo.demo_data import DemoEntry
from demo.demo_rag_data import DemoRagEntry
from domain.entities.question import Question
from domain.repositories.question_repository import QuestionRepository


class DemoQuestionRepository(QuestionRepository):
    def __init__(self, entries: Sequence[DemoEntry], rag_entries: Mapping[str, DemoRagEntry] | None = None):
        self._entries = entries
        self._rag_entries = rag_entries or {}

    def load(self, source: Path) -> list[Question]:
        return [self._build_question(entry) for entry in self._entries]

    def _build_question(self, entry: DemoEntry) -> Question:
        rag_entry = self._rag_entries.get(entry.identifier)
        if rag_entry is None:
            return Question(entry.identifier, entry.question, entry.expected_answer)
        return Question(
            entry.identifier,
            entry.question,
            entry.expected_answer,
            rag_entry.relevant_context_ids,
            rag_entry.relevant_passages,
        )
