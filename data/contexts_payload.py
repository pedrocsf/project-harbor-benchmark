from domain.entities.retrieved_context import RetrievedContext

TEXT_KEYS = ("text", "content", "page_content", "passage")
IDENTIFIER_KEYS = ("id", "identifier", "doc_id", "document_id", "chunk_id")
SCORE_KEYS = ("score", "retrieval_score", "similarity")
NOT_A_LIST_MESSAGE = "contexts must be a list."
UNREADABLE_ITEM_MESSAGE = (
    "context {position} must be a string or an object with a 'text' field."
)


class ContextsFormatError(ValueError):
    pass


def parse_contexts(raw: object) -> tuple[RetrievedContext, ...]:
    if not isinstance(raw, list):
        raise ContextsFormatError(NOT_A_LIST_MESSAGE)
    return tuple(_parse_context(position, item) for position, item in enumerate(raw, start=1))


def _parse_context(position: int, item: object) -> RetrievedContext:
    if isinstance(item, str):
        return RetrievedContext(identifier=None, text=item)
    if not isinstance(item, dict):
        raise ContextsFormatError(UNREADABLE_ITEM_MESSAGE.format(position=position))
    text = _first_value(item, TEXT_KEYS)
    if not isinstance(text, str):
        raise ContextsFormatError(UNREADABLE_ITEM_MESSAGE.format(position=position))
    return RetrievedContext(
        identifier=_read_identifier(item),
        text=text,
        retrieval_score=_read_score(item),
    )


def _first_value(item: dict, keys: tuple[str, ...]) -> object:
    for key in keys:
        if key in item:
            return item[key]
    return None


def _read_identifier(item: dict) -> str | None:
    identifier = _first_value(item, IDENTIFIER_KEYS)
    if identifier is None or isinstance(identifier, bool):
        return None
    return str(identifier)


def _read_score(item: dict) -> float | None:
    score = _first_value(item, SCORE_KEYS)
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        return None
    return float(score)


def contexts_to_payload(contexts: tuple[RetrievedContext, ...] | None) -> list[dict] | None:
    if contexts is None:
        return None
    return [
        {"id": context.identifier, "text": context.text, "score": context.retrieval_score}
        for context in contexts
    ]
