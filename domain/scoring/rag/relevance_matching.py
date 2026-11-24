from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from domain.entities.question import Question
from domain.entities.retrieved_context import RetrievedContext
from domain.errors import DomainError
from domain.scoring.text_normalization import NormalizationOptions, normalized_tokens

MATCH_AUTO = "auto"
MATCH_BY_IDS = "ids"
MATCH_BY_PASSAGES = "passages"
ID_MATCH_GAIN = 1.0
PASSAGE_NORMALIZATION = NormalizationOptions(articles="english_portuguese")
MISSING_IDS_MESSAGE = "Question {identifier} has no relevant_context_ids to match by ID."
MISSING_PASSAGES_MESSAGE = "Question {identifier} has no relevant_passages to match by text."
MISSING_LABELS_MESSAGE = "Question {identifier} has no relevant_context_ids or relevant_passages."


class MissingRelevanceLabelsError(DomainError):
    pass


@dataclass(frozen=True)
class ContextJudgment:
    rank: int
    context: RetrievedContext
    target_gains: dict[int, float]

    @property
    def is_relevant(self) -> bool:
        return bool(self.target_gains)


@dataclass(frozen=True)
class RankedRelevance:
    match_by: str
    targets: tuple[str, ...]
    judgments: tuple[ContextJudgment, ...]

    def top(self, cutoff: int) -> tuple[ContextJudgment, ...]:
        return self.judgments[:cutoff]


def passage_coverage(passage: str, context_text: str) -> float:
    passage_tokens = Counter(normalized_tokens(passage, PASSAGE_NORMALIZATION))
    if not passage_tokens:
        return 0.0
    context_tokens = Counter(normalized_tokens(context_text, PASSAGE_NORMALIZATION))
    shared = sum((passage_tokens & context_tokens).values())
    return shared / sum(passage_tokens.values())


def resolve_match_mode(question: Question, match_by: str) -> str:
    if match_by == MATCH_BY_IDS:
        if not question.relevant_context_ids:
            raise MissingRelevanceLabelsError(MISSING_IDS_MESSAGE.format(identifier=question.identifier))
        return MATCH_BY_IDS
    if match_by == MATCH_BY_PASSAGES:
        if not question.relevant_passages:
            raise MissingRelevanceLabelsError(MISSING_PASSAGES_MESSAGE.format(identifier=question.identifier))
        return MATCH_BY_PASSAGES
    if question.relevant_context_ids:
        return MATCH_BY_IDS
    if question.relevant_passages:
        return MATCH_BY_PASSAGES
    raise MissingRelevanceLabelsError(MISSING_LABELS_MESSAGE.format(identifier=question.identifier))


def judge_contexts(
    question: Question,
    contexts: Sequence[RetrievedContext],
    match_by: str = MATCH_AUTO,
    match_threshold: float = 0.5,
) -> RankedRelevance:
    mode = resolve_match_mode(question, match_by)
    targets = question.relevant_context_ids if mode == MATCH_BY_IDS else question.relevant_passages
    judgments = tuple(
        ContextJudgment(rank, context, _target_gains(mode, targets, context, match_threshold))
        for rank, context in enumerate(contexts, start=1)
    )
    return RankedRelevance(mode, tuple(targets), judgments)


def _target_gains(
    mode: str, targets: Sequence[str], context: RetrievedContext, match_threshold: float
) -> dict[int, float]:
    if mode == MATCH_BY_IDS:
        return {
            position: ID_MATCH_GAIN
            for position, target in enumerate(targets)
            if context.identifier is not None and context.identifier == target
        }
    gains = {}
    for position, passage in enumerate(targets):
        coverage = passage_coverage(passage, context.text)
        if coverage >= match_threshold and coverage > 0:
            gains[position] = coverage
    return gains
