import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from domain.errors import DomainError
from domain.gateways.text_encoder import TextEncoder

UNKNOWN_TEXT_MESSAGE = "No demo embedding is available for the text {text!r}."


class UnknownDemoTextError(DomainError):
    pass


class DemoTextEncoder(TextEncoder):
    def __init__(self, vectors_by_text: Mapping[str, Sequence[float]]):
        self._vectors_by_text = vectors_by_text

    def prepare(self) -> None:
        return None

    def encode(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        return [self._vector_for(text) for text in texts]

    def _vector_for(self, text: str) -> tuple[float, ...]:
        if text not in self._vectors_by_text:
            raise UnknownDemoTextError(UNKNOWN_TEXT_MESSAGE.format(text=text))
        return tuple(self._vectors_by_text[text])


def load_demo_vectors(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
