from abc import ABC, abstractmethod
from pathlib import Path

from domain.entities.imported_answer import ImportedAnswer


class RunImportRepository(ABC):
    @abstractmethod
    def load(self, source: Path) -> list[ImportedAnswer]:
        ...
