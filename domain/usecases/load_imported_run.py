from pathlib import Path

from domain.entities.imported_run import ImportedRun
from domain.errors import RunImportError
from domain.repositories.run_import_repository import RunImportRepository

EMPTY_RUN_MESSAGE = "No answers found in {name}."
DUPLICATE_IDENTIFIER_MESSAGE = "The run file has more than one answer for question {identifier!r}."


class LoadImportedRun:
    def __init__(self, run_import_repository: RunImportRepository):
        self._run_import_repository = run_import_repository

    def execute(self, source: Path) -> ImportedRun:
        answers = self._run_import_repository.load(source)
        if not answers:
            raise RunImportError(EMPTY_RUN_MESSAGE.format(name=source.name))
        self._reject_duplicates([answer.question_identifier for answer in answers])
        return ImportedRun(source.name, tuple(answers))

    def _reject_duplicates(self, identifiers: list[str]) -> None:
        seen: set[str] = set()
        for identifier in identifiers:
            if identifier in seen:
                raise RunImportError(DUPLICATE_IDENTIFIER_MESSAGE.format(identifier=identifier))
            seen.add(identifier)
