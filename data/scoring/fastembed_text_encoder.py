from collections.abc import Sequence
from pathlib import Path

from fastembed import TextEmbedding

from domain.errors import ModelUnavailableError
from domain.gateways.text_encoder import TextEncoder

EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
WARM_UP_TEXT = "warm-up"


class FastEmbedTextEncoder(TextEncoder):
    def __init__(self, models_directory: Path):
        self._models_directory = models_directory
        self._model: TextEmbedding | None = None

    def prepare(self) -> None:
        self.encode([WARM_UP_TEXT])

    def encode(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        model = self._load_model()
        return [tuple(float(value) for value in vector) for vector in model.embed(list(texts))]

    def _load_model(self) -> TextEmbedding:
        if self._model is not None:
            return self._model
        try:
            self._model = TextEmbedding(
                model_name=EMBEDDING_MODEL_NAME,
                cache_dir=str(self._models_directory),
            )
        except Exception as error:
            raise ModelUnavailableError(f"Could not load the embedding model: {error}") from error
        return self._model
