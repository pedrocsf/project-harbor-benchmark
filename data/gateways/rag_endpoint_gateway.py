from urllib.parse import urlsplit

import httpx

from data.contexts_payload import ContextsFormatError, parse_contexts
from data.gateways.gateway_http import normalize_url, post_json
from domain.entities.rag_answer import RagAnswer
from domain.entities.rag_endpoint_settings import RagEndpointSettings
from domain.errors import LanguageModelError
from domain.gateways.rag_gateway import RagGateway

REQUEST_TIMEOUT_SECONDS = 300.0
OPENAI_COMPATIBLE_PATH_MARKER = "/chat/completions"
FIELD_PATH_SEPARATOR = "."
QUESTION_KEY = "question"
OPENAI_ANSWER_PATH = "choices.0.message.content"
OPENAI_CONTEXT_ROOTS = ("", "choices.0.message", "choices.0")
MISSING_FIELD_MESSAGE = "The RAG response has no field '{path}'."
ANSWER_NOT_TEXT_MESSAGE = "The field '{path}' of the RAG response must be text."
INVALID_JSON_MESSAGE = "The RAG endpoint did not return JSON."
UNREADABLE_CONTEXTS_MESSAGE = "The field '{path}' of the RAG response is not readable: {reason}"

_MISSING = object()


def resolve_field(document: object, path: str) -> object:
    current = document
    for segment in path.split(FIELD_PATH_SEPARATOR) if path else ():
        current = _step_into(current, segment)
        if current is _MISSING:
            return _MISSING
    return current


def _step_into(current: object, segment: str) -> object:
    if isinstance(current, dict):
        return current.get(segment, _MISSING)
    if isinstance(current, list) and segment.isdigit() and int(segment) < len(current):
        return current[int(segment)]
    return _MISSING


def _join_path(root: str, path: str) -> str:
    return f"{root}{FIELD_PATH_SEPARATOR}{path}" if root else path


def _build_headers(settings: RagEndpointSettings) -> dict:
    if not settings.api_key:
        return {}
    return {"Authorization": f"Bearer {settings.api_key}"}


class RagEndpointGateway(RagGateway):
    def __init__(self, client: httpx.Client | None = None):
        self._client = client or httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS)

    def ask(self, settings: RagEndpointSettings, question_text: str) -> RagAnswer:
        url = normalize_url(settings.endpoint_url)
        is_openai_compatible = OPENAI_COMPATIBLE_PATH_MARKER in urlsplit(url).path
        payload = self._build_payload(settings, question_text, is_openai_compatible)
        document = self._read_json(post_json(self._client, url, payload, _build_headers(settings)))
        if is_openai_compatible:
            return self._read_openai_answer(document, settings.contexts_field)
        return RagAnswer(
            self._read_answer(document, settings.answer_field),
            self._read_contexts(document, settings.contexts_field),
        )

    def _build_payload(self, settings: RagEndpointSettings, question_text: str, is_openai_compatible: bool) -> dict:
        if not is_openai_compatible:
            return {QUESTION_KEY: question_text}
        payload = {"messages": [{"role": "user", "content": question_text}]}
        if settings.model_name:
            payload["model"] = settings.model_name
        return payload

    def _read_json(self, response: httpx.Response) -> object:
        try:
            return response.json()
        except ValueError as error:
            raise LanguageModelError(INVALID_JSON_MESSAGE) from error

    def _read_openai_answer(self, document: object, contexts_field: str) -> RagAnswer:
        answer = self._read_answer(document, OPENAI_ANSWER_PATH)
        for root in OPENAI_CONTEXT_ROOTS:
            path = _join_path(root, contexts_field)
            if resolve_field(document, path) is not _MISSING:
                return RagAnswer(answer, self._read_contexts(document, path))
        raise LanguageModelError(MISSING_FIELD_MESSAGE.format(path=contexts_field))

    def _read_answer(self, document: object, path: str) -> str:
        answer = resolve_field(document, path)
        if answer is _MISSING:
            raise LanguageModelError(MISSING_FIELD_MESSAGE.format(path=path))
        if answer is None:
            return ""
        if not isinstance(answer, str):
            raise LanguageModelError(ANSWER_NOT_TEXT_MESSAGE.format(path=path))
        return answer

    def _read_contexts(self, document: object, path: str):
        raw_contexts = resolve_field(document, path)
        if raw_contexts is _MISSING:
            raise LanguageModelError(MISSING_FIELD_MESSAGE.format(path=path))
        try:
            return parse_contexts(raw_contexts)
        except ContextsFormatError as error:
            raise LanguageModelError(UNREADABLE_CONTEXTS_MESSAGE.format(path=path, reason=error)) from error
