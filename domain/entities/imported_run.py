from dataclasses import dataclass

from domain.entities.imported_answer import ImportedAnswer


@dataclass(frozen=True)
class ImportedRun:
    source_name: str
    answers: tuple[ImportedAnswer, ...]

    @property
    def has_contexts(self) -> bool:
        return bool(self.answers) and all(answer.contexts is not None for answer in self.answers)
