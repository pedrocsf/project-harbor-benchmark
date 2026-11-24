import re
from collections.abc import Mapping, Sequence

from domain.entities.evaluation_sample import EvaluationSample
from domain.entities.language_model_settings import LanguageModelSettings
from domain.entities.retrieved_context import RetrievedContext
from domain.errors import DomainError, LanguageModelError
from domain.gateways.language_model_gateway import LanguageModelGateway
from domain.scoring.llm_judge_scoring_method import chosen_temperature
from domain.scoring.metric_parameters import InvalidParameterError, ParameterKind, ParameterSpec
from domain.scoring.rag.context_overlap import ALL_CONTEXTS, considered_contexts
from domain.scoring.scoring_method import SampleScoringMethod

MISSING_SETTINGS_MESSAGE = (
    "{name} needs a model to act as judge. Fill in the model endpoint and run the benchmark again."
)
MISSING_CONTEXTS_MESSAGE = "{name} needs the contexts retrieved for question {identifier}."
MISSING_PLACEHOLDER_MESSAGE = "The prompt template must contain {{{placeholder}}}."
UNFORMATTABLE_TEMPLATE_MESSAGE = "The prompt template cannot be filled in: {reason}."
LIST_MARKER_PATTERN = re.compile(r"^\s*(?:[-*•]+|\(?\d+[.):]|\d+\s*-)\s*")
EMPTY_LIST_REPLIES = frozenset({"none", "nenhuma", "nenhum", "n/a"})
CONTEXT_SEPARATOR = "\n\n"
MAXIMUM_CONTEXT_LIMIT = 100


def judge_context_limit_spec(default: int) -> ParameterSpec:
    return ParameterSpec(
        key="context_limit",
        label="Contexts considered",
        description="Send only the first N retrieved contexts to the judge. 0 sends all of them.",
        kind=ParameterKind.INTEGER,
        default=default,
        minimum=ALL_CONTEXTS,
        maximum=MAXIMUM_CONTEXT_LIMIT,
    )


def parse_listed_lines(reply: str) -> tuple[str, ...]:
    lines = []
    for raw_line in reply.splitlines():
        line = LIST_MARKER_PATTERN.sub("", raw_line).strip()
        if line and line.lower().strip(".") not in EMPTY_LIST_REPLIES:
            lines.append(line)
    return tuple(lines)


def format_contexts(contexts: Sequence[RetrievedContext]) -> str:
    return CONTEXT_SEPARATOR.join(f"[{position}] {context.text}" for position, context in enumerate(contexts, start=1))


def check_template(template: str, placeholders: Sequence[str]) -> None:
    for placeholder in placeholders:
        if "{" + placeholder + "}" not in template:
            raise InvalidParameterError(MISSING_PLACEHOLDER_MESSAGE.format(placeholder=placeholder))
    try:
        template.format(**{placeholder: "" for placeholder in placeholders})
    except (KeyError, IndexError, ValueError) as error:
        raise InvalidParameterError(UNFORMATTABLE_TEMPLATE_MESSAGE.format(reason=repr(error))) from error


class LanguageModelSampleMethod(SampleScoringMethod):
    uses_language_model = True
    template_placeholders: Mapping[str, tuple[str, ...]] = {}

    def __init__(self, language_model_gateway: LanguageModelGateway | None):
        self._language_model_gateway = language_model_gateway
        self._settings: LanguageModelSettings | None = None

    def configure(self, settings: LanguageModelSettings | None) -> None:
        self._settings = settings

    def ask_judge(self, prompt: str) -> str:
        if self._settings is None or self._language_model_gateway is None:
            raise LanguageModelError(MISSING_SETTINGS_MESSAGE.format(name=self.display_name))
        return self._language_model_gateway.ask(self._settings, prompt, chosen_temperature(self.parameters))

    def judged_contexts(self, sample: EvaluationSample) -> tuple[RetrievedContext, ...]:
        if sample.contexts is None:
            raise DomainError(
                MISSING_CONTEXTS_MESSAGE.format(name=self.display_name, identifier=sample.question.identifier)
            )
        return considered_contexts(sample.contexts, int(self.parameter("context_limit")))

    def _check_parameters(self, values) -> None:
        for key, placeholders in self.template_placeholders.items():
            check_template(str(values[key]), placeholders)
