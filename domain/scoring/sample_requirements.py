from collections.abc import Iterable
from enum import Enum

from domain.entities.question import Question


class SampleRequirement(Enum):
    CONTEXTS = "contexts"
    RELEVANCE_LABELS = "relevance_labels"


class MetricGroup(Enum):
    ANSWER = "answer"
    RETRIEVAL = "retrieval"
    GROUNDING = "grounding"


REQUIREMENT_DESCRIPTIONS = {
    SampleRequirement.CONTEXTS: (
        "Needs retrieved contexts: choose a RAG endpoint or an imported run as the answer source."
    ),
    SampleRequirement.RELEVANCE_LABELS: (
        "Needs relevance labels: every question in the dataset must have "
        "relevant_context_ids or relevant_passages."
    ),
}


def available_requirements(
    questions: Iterable[Question], has_contexts: bool
) -> frozenset[SampleRequirement]:
    question_list = list(questions)
    available = set()
    if has_contexts:
        available.add(SampleRequirement.CONTEXTS)
    if question_list and all(question.has_relevance_labels for question in question_list):
        available.add(SampleRequirement.RELEVANCE_LABELS)
    return frozenset(available)


def missing_requirements(
    required: Iterable[SampleRequirement], available: frozenset[SampleRequirement]
) -> tuple[SampleRequirement, ...]:
    return tuple(requirement for requirement in SampleRequirement if requirement in set(required) - available)
