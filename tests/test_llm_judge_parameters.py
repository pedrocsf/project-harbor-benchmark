import json

import httpx
import pytest

from data.gateways.anthropic_gateway import AnthropicGateway
from data.gateways.gemini_gateway import GeminiGateway
from data.gateways.openai_compatible_gateway import OpenAiCompatibleGateway
from domain.entities.language_model_settings import LanguageModelSettings
from domain.gateways.language_model_gateway import LanguageModelGateway
from domain.scoring.llm_judge_scoring_method import (
    JUDGE_PROMPT,
    LlmJudgeScoringMethod,
    build_judge_prompt,
    find_rating,
)
from domain.scoring.metric_parameters import InvalidParameterError

SETTINGS = LanguageModelSettings(
    endpoint_url="https://api.anthropic.com/v1/messages", api_key="k", model_name="m"
)


class ScriptedGateway(LanguageModelGateway):
    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []
        self.temperatures = []

    def ask(self, settings, question_text, temperature=None):
        self.prompts.append(question_text)
        self.temperatures.append(temperature)
        return self.replies.pop(0)


def build_method(replies):
    gateway = ScriptedGateway(replies)
    method = LlmJudgeScoringMethod(gateway)
    method.configure(SETTINGS)
    return method, gateway


def capture_body(gateway_class, url, reply_body, temperature):
    captured = {}

    def handler(request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=reply_body)

    gateway = gateway_class(httpx.Client(transport=httpx.MockTransport(handler)))
    gateway.ask(LanguageModelSettings(url, "k", "m"), "Q", temperature)
    return captured["body"]


GATEWAY_CASES = [
    (OpenAiCompatibleGateway, "http://x/v1/chat/completions", {"choices": [{"message": {"content": "a"}}]}),
    (AnthropicGateway, "https://api.anthropic.com/v1/messages", {"content": [{"type": "text", "text": "a"}]}),
    (GeminiGateway, "https://generativelanguage.googleapis.com", {"candidates": [{"content": {"parts": [{"text": "a"}]}}]}),
]


def test_default_prompt_matches_the_ten_point_rendering():
    default = build_judge_prompt(str(LlmJudgeScoringMethod(ScriptedGateway([])).parameter("prompt_template")), "E", "G", 10)

    assert default == JUDGE_PROMPT.format(expected_answer="E", given_answer="G")
    assert "to 10 (fully correct)" in default


def test_scale_changes_prompt_and_score():
    method, gateway = build_method(["40"])
    method.update_parameters({"rating_scale_max": 100})

    assert method.score("a", "b") == pytest.approx(0.4)
    assert "to 100 (fully correct)" in gateway.prompts[0]


def test_find_rating_respects_the_maximum():
    assert find_rating("score 50", 100).group() == "50"
    assert find_rating("score 50", 10) is None
    assert find_rating("15 then 7", 10).group() == "7"


@pytest.mark.parametrize("template", ["no placeholders", "{expected_answer} only", "{given_answer} only"])
def test_template_missing_placeholders_is_rejected(template):
    with pytest.raises(InvalidParameterError):
        LlmJudgeScoringMethod(ScriptedGateway([])).update_parameters({"prompt_template": template})


@pytest.mark.parametrize("suffix", [" {unknown}", " {", " }"])
def test_unformattable_template_is_rejected(suffix):
    template = "{expected_answer} {given_answer}" + suffix
    with pytest.raises(InvalidParameterError):
        LlmJudgeScoringMethod(ScriptedGateway([])).update_parameters({"prompt_template": template})


def test_samples_are_averaged():
    method, gateway = build_method(["10", "5", "0"])
    method.update_parameters({"samples": 3})

    assert method.score("a", "b") == pytest.approx(0.5)
    assert len(gateway.prompts) == 3


def test_temperature_is_passed_to_the_gateway():
    method, gateway = build_method(["5"])
    method.update_parameters({"set_temperature": True, "temperature": 0.7})
    method.score("a", "b")

    assert gateway.temperatures == [0.7]


def test_temperature_is_not_sent_by_default():
    method, gateway = build_method(["5"])
    method.update_parameters({"temperature": 0.7})
    method.score("a", "b")

    assert gateway.temperatures == [None]


@pytest.mark.parametrize(("gateway_class", "url", "reply_body"), GATEWAY_CASES)
def test_gateway_without_temperature_keeps_body_unchanged(gateway_class, url, reply_body):
    body = capture_body(gateway_class, url, reply_body, None)

    assert "temperature" not in json.dumps(body)


def test_openai_body_has_temperature():
    body = capture_body(*GATEWAY_CASES[0], 0.4)

    assert body["temperature"] == 0.4


def test_anthropic_temperature_is_clamped():
    assert capture_body(*GATEWAY_CASES[1], 1.5)["temperature"] == 1.0
    assert capture_body(*GATEWAY_CASES[1], 0.3)["temperature"] == 0.3


def test_gemini_temperature_goes_in_generation_config():
    body = capture_body(*GATEWAY_CASES[2], 0.9)

    assert body["generationConfig"] == {"temperature": 0.9}
