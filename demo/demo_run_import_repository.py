from collections.abc import Mapping, Sequence
from pathlib import Path

from demo.demo_data import DemoEntry
from demo.demo_rag_data import DemoRagEntry
from domain.entities.imported_answer import ImportedAnswer
from domain.repositories.run_import_repository import RunImportRepository


class DemoRunImportRepository(RunImportRepository):
    def __init__(self, entries: Sequence[DemoEntry], rag_entries: Mapping[str, DemoRagEntry]):
        self._entries = entries
        self._rag_entries = rag_entries

    def load(self, source: Path) -> list[ImportedAnswer]:
        return [
            ImportedAnswer(
                entry.identifier,
                entry.given_answer,
                self._rag_entries[entry.identifier].contexts,
                entry.response_seconds,
            )
            for entry in self._entries
        ]
