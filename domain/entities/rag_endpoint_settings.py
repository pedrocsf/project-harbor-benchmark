from dataclasses import dataclass

DEFAULT_ANSWER_FIELD = "answer"
DEFAULT_CONTEXTS_FIELD = "contexts"


@dataclass(frozen=True)
class RagEndpointSettings:
    endpoint_url: str
    api_key: str | None = None
    model_name: str | None = None
    answer_field: str = DEFAULT_ANSWER_FIELD
    contexts_field: str = DEFAULT_CONTEXTS_FIELD
