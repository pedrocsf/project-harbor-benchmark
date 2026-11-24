from dataclasses import dataclass
from enum import Enum

from domain.entities.rag_endpoint_settings import DEFAULT_ANSWER_FIELD, DEFAULT_CONTEXTS_FIELD


class AnswerSource(Enum):
    MODEL_ENDPOINT = "model_endpoint"
    RAG_ENDPOINT = "rag_endpoint"
    IMPORTED_RUN = "imported_run"


ANSWER_SOURCE_LABELS = {
    AnswerSource.MODEL_ENDPOINT: "Model endpoint",
    AnswerSource.RAG_ENDPOINT: "RAG endpoint",
    AnswerSource.IMPORTED_RUN: "Imported run",
}


@dataclass(frozen=True)
class EndpointInput:
    url: str = ""
    api_key: str = ""
    model_name: str = ""


@dataclass(frozen=True)
class RagEndpointInput:
    url: str = ""
    api_key: str = ""
    answer_field: str = DEFAULT_ANSWER_FIELD
    contexts_field: str = DEFAULT_CONTEXTS_FIELD
