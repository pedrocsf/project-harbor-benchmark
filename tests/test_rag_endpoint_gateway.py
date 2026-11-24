import json

import httpx
import pytest

from data.gateways.rag_endpoint_gateway import RagEndpointGateway, resolve_field
from domain.entities.rag_endpoint_settings import RagEndpointSettings
from domain.entities.retrieved_context import RetrievedContext
from domain.errors import LanguageModelError

PLAIN_URL = "http://127.0.0.1:8000/rag"
OPENAI_URL = "http://127.0.0.1:8000/v1/chat/completions"
CONTEXTS = [{"id": "doc-12#3", "text": "Paris é a capital da França.", "score": 0.82}]
EXPECTED_CONTEXTS = (RetrievedContext("doc-12#3", "Paris é a capital da França.", 0.82),)


def build_gateway(body, captured=None, status=200):
    def handler(request):
        if captured is not None:
            captured["url"] = str(request.url)
            captured["headers"] = request.headers
            captured["payload"] = json.loads(request.content)
        if isinstance(body, str):
            return httpx.Response(status, text=body)
        return httpx.Response(status, json=body)

    return RagEndpointGateway(httpx.Client(transport=httpx.MockTransport(handler)))


def test_plain_endpoint_receives_the_question_and_returns_answer_and_contexts():
    captured = {}
    gateway = build_gateway({"answer": "Paris", "contexts": CONTEXTS}, captured)

    rag_answer = gateway.ask(RagEndpointSettings(PLAIN_URL, api_key="secret"), "Capital?")

    assert rag_answer.answer == "Paris"
    assert rag_answer.contexts == EXPECTED_CONTEXTS
    assert captured["payload"] == {"question": "Capital?"}
    assert captured["headers"]["authorization"] == "Bearer secret"


def test_field_paths_are_configurable():
    body = {"data": {"output": {"text": "Paris"}, "sources": ["trecho"]}}
    settings = RagEndpointSettings(PLAIN_URL, answer_field="data.output.text", contexts_field="data.sources")

    rag_answer = build_gateway(body).ask(settings, "Capital?")

    assert rag_answer.answer == "Paris"
    assert rag_answer.contexts == (RetrievedContext(None, "trecho"),)


@pytest.mark.parametrize("contexts_root", ["body", "message", "choice"])
def test_openai_compatible_endpoint_with_extra_contexts_field(contexts_root):
    message = {"content": "Paris"}
    choice = {"message": message}
    body = {"choices": [choice]}
    {"body": body, "message": message, "choice": choice}[contexts_root]["contexts"] = CONTEXTS
    captured = {}

    rag_answer = build_gateway(body, captured).ask(RagEndpointSettings(OPENAI_URL, model_name="rag-v2"), "Capital?")

    assert rag_answer == rag_answer.__class__("Paris", EXPECTED_CONTEXTS)
    assert captured["payload"] == {"messages": [{"role": "user", "content": "Capital?"}], "model": "rag-v2"}


def test_url_without_scheme_gets_http():
    captured = {}

    build_gateway({"answer": "a", "contexts": []}, captured).ask(RagEndpointSettings("localhost:8000/rag"), "q")

    assert captured["url"] == "http://localhost:8000/rag"


def test_null_answer_counts_as_empty():
    assert build_gateway({"answer": None, "contexts": []}).ask(RagEndpointSettings(PLAIN_URL), "q").answer == ""


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"contexts": []}, "no field 'answer'"),
        ({"answer": "a"}, "no field 'contexts'"),
        ({"answer": 3, "contexts": []}, "must be text"),
        ({"answer": "a", "contexts": "x"}, "not readable"),
        ("not json", "did not return JSON"),
    ],
)
def test_rejects_unexpected_responses(body, message):
    with pytest.raises(LanguageModelError, match=message):
        build_gateway(body).ask(RagEndpointSettings(PLAIN_URL), "q")


def test_openai_compatible_response_without_contexts_is_rejected():
    body = {"choices": [{"message": {"content": "Paris"}}]}

    with pytest.raises(LanguageModelError, match="no field 'contexts'"):
        build_gateway(body).ask(RagEndpointSettings(OPENAI_URL), "q")


def test_http_errors_become_language_model_errors():
    with pytest.raises(LanguageModelError, match="status 500"):
        build_gateway({"error": "boom"}, status=500).ask(RagEndpointSettings(PLAIN_URL), "q")


def test_resolve_field_walks_dicts_and_lists():
    document = {"a": [{"b": 1}]}

    assert resolve_field(document, "a.0.b") == 1
    assert resolve_field(document, "") is document
    assert resolve_field(document, "a.1.b") is resolve_field(document, "missing")
    assert resolve_field(document, "a.0.b.c") is resolve_field(document, "missing")
