from abc import ABC, abstractmethod
from collections.abc import Sequence


class TextEncoder(ABC):
    @abstractmethod
    def prepare(self) -> None:
        ...

    @abstractmethod
    def encode(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        ...
