import re
from dataclasses import dataclass

from domain.entities.evaluation_sample import EvaluationSample
from domain.entities.retrieved_context import RetrievedContext
from domain.errors import JudgeResponseError
from domain.scoring.llm_judge_scoring_method import SET_TEMPERATURE_SPEC, TEMPERATURE_SPEC
from domain.scoring.metric_parameters import ParameterKind, ParameterSpec
from domain.scoring.rag.language_model_metric import (
    LanguageModelSampleMethod,
    format_contexts,
    judge_context_limit_spec,
    parse_listed_lines,
)
from domain.scoring.sample_requirements import MetricGroup, SampleRequirement
from domain.scoring.scoring_method import ScoreKind

DEFAULT_MAXIMUM_STATEMENTS = 20
EXTRACTION_AND_VERIFICATION_CALLS = 2
SUPPORTED_WORDS = frozenset({"yes", "sim", "true", "supported"})
VERDICT_PATTERN = re.compile(
    r"^\s*\[?(\d+)\]?\s*[:.)\-]\s*(yes|no|sim|n[aã]o|true|false|supported|unsupported)\b",
    re.IGNORECASE,
)
UNREADABLE_VERDICTS_MESSAGE = "The judge did not return a yes/no verdict for the statements: {reply!r}"
STATEMENTS_PROMPT_TEMPLATE = """Break the answer below into short, standalone factual statements. \
Each statement must make sense on its own (replace pronouns with what they refer to). \
Do not add facts that are not in the answer.

Question:
{question}

Answer:
{answer}

Write one statement per line, with no numbering. If the answer has no factual statement, reply with NONE."""
VERIFICATION_PROMPT_TEMPLATE = """Decide whether each statement can be directly inferred from the context. \
Use only the context, not your own knowledge.

Context:
{contexts}

Statements:
{statements}

For every statement, reply with one line in the form "<number>: yes" or "<number>: no", and nothing else."""


@dataclass(frozen=True)
class FaithfulnessVerdicts:
    statements: tuple[str, ...]
    supported: tuple[bool, ...]

    @property
    def score(self) -> float:
        if not self.statements:
            return 0.0
        return sum(self.supported) / len(self.statements)


def number_statements(statements: tuple[str, ...]) -> str:
    return "\n".join(f"{position}. {statement}" for position, statement in enumerate(statements, start=1))


def parse_verdicts(reply: str, statement_count: int) -> tuple[bool, ...]:
    verdicts: dict[int, bool] = {}
    for line in reply.splitlines():
        match = VERDICT_PATTERN.match(line)
        if match is None:
            continue
        position = int(match.group(1))
        if 1 <= position <= statement_count and position not in verdicts:
            verdicts[position] = match.group(2).lower() in SUPPORTED_WORDS
    if not verdicts:
        raise JudgeResponseError(UNREADABLE_VERDICTS_MESSAGE.format(reply=reply[:80]))
    return tuple(verdicts.get(position, False) for position in range(1, statement_count + 1))


class FaithfulnessScoringMethod(LanguageModelSampleMethod):
    identifier = "faithfulness"
    display_name = "Faithfulness"
    column_header = "Faithful"
    score_kind = ScoreKind.CONTINUOUS
    requirements = frozenset({SampleRequirement.CONTEXTS})
    metric_group = MetricGroup.GROUNDING
    template_placeholders = {
        "statements_prompt": ("question", "answer"),
        "verification_prompt": ("contexts", "statements"),
    }
    parameter_specs = (
        ParameterSpec(
            key="max_statements",
            label="Maximum statements",
            description="Statements beyond this number are ignored, which caps the size of the verification prompt.",
            kind=ParameterKind.INTEGER,
            default=DEFAULT_MAXIMUM_STATEMENTS,
            minimum=1,
            maximum=100,
        ),
        judge_context_limit_spec(0),
        ParameterSpec(
            key="statements_prompt",
            label="Statement extraction prompt",
            description="Asks the judge to split the answer into statements. Use {question} and {answer}.",
            kind=ParameterKind.TEXT,
            default=STATEMENTS_PROMPT_TEMPLATE,
        ),
        ParameterSpec(
            key="verification_prompt",
            label="Verification prompt",
            description="Asks the judge whether each statement follows from the contexts. Use {contexts} and {statements}.",
            kind=ParameterKind.TEXT,
            default=VERIFICATION_PROMPT_TEMPLATE,
        ),
        SET_TEMPERATURE_SPEC,
        TEMPERATURE_SPEC,
    )

    def judge_calls_per_question(self) -> int | None:
        return EXTRACTION_AND_VERIFICATION_CALLS

    def score_sample(self, sample: EvaluationSample) -> float:
        return self.verdicts(sample).score

    def verdicts(self, sample: EvaluationSample) -> FaithfulnessVerdicts:
        contexts = self.judged_contexts(sample)
        if not sample.given_answer.strip() or not contexts:
            return FaithfulnessVerdicts((), ())
        statements = self.extract_statements(sample)[: int(self.parameter("max_statements"))]
        if not statements:
            return FaithfulnessVerdicts((), ())
        return FaithfulnessVerdicts(statements, self.verify_statements(statements, contexts))

    def extract_statements(self, sample: EvaluationSample) -> tuple[str, ...]:
        prompt = str(self.parameter("statements_prompt")).format(
            question=sample.question_text, answer=sample.given_answer
        )
        return parse_listed_lines(self.ask_judge(prompt))

    def verify_statements(
        self, statements: tuple[str, ...], contexts: tuple[RetrievedContext, ...]
    ) -> tuple[bool, ...]:
        prompt = str(self.parameter("verification_prompt")).format(
            contexts=format_contexts(contexts), statements=number_statements(statements)
        )
        return parse_verdicts(self.ask_judge(prompt), len(statements))
