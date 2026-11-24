from collections.abc import Sequence
from dataclasses import dataclass

from domain.entities.retrieved_context import RetrievedContext
from domain.scoring.text_normalization import NormalizationOptions, normalized_tokens

ALL_CONTEXTS = 0


@dataclass(frozen=True)
class TokenSupport:
    tokens: tuple[str, ...]
    supported: tuple[bool, ...]

    @property
    def supported_count(self) -> int:
        return sum(self.supported)

    @property
    def fraction(self) -> float:
        if not self.tokens:
            return 0.0
        return self.supported_count / len(self.tokens)


def considered_contexts(contexts: Sequence[RetrievedContext], limit: int) -> tuple[RetrievedContext, ...]:
    if limit == ALL_CONTEXTS:
        return tuple(contexts)
    return tuple(contexts[:limit])


def context_vocabulary(contexts: Sequence[RetrievedContext], options: NormalizationOptions) -> frozenset[str]:
    vocabulary: set[str] = set()
    for context in contexts:
        vocabulary.update(normalized_tokens(context.text, options))
    return frozenset(vocabulary)


def token_support(text: str, contexts: Sequence[RetrievedContext], options: NormalizationOptions) -> TokenSupport:
    tokens = tuple(normalized_tokens(text, options))
    vocabulary = context_vocabulary(contexts, options)
    return TokenSupport(tokens, tuple(token in vocabulary for token in tokens))
