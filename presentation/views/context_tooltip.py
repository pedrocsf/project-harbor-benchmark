from html import escape

from domain.entities.retrieved_context import RetrievedContext

NO_CONTEXTS_TEXT = "—"
EMPTY_CONTEXTS_TOOLTIP = "The system returned no contexts for this question."
CONTEXT_PREVIEW_LENGTH = 220
MAXIMUM_LISTED_CONTEXTS = 8
ELLIPSIS = "…"
UNKNOWN_IDENTIFIER = "no id"


def context_count_text(contexts: tuple[RetrievedContext, ...] | None) -> str:
    if contexts is None:
        return NO_CONTEXTS_TEXT
    return str(len(contexts))


def contexts_tooltip(contexts: tuple[RetrievedContext, ...] | None) -> str:
    if contexts is None:
        return ""
    if not contexts:
        return EMPTY_CONTEXTS_TOOLTIP
    entries = [_context_entry(position, context) for position, context in enumerate(contexts[:MAXIMUM_LISTED_CONTEXTS], start=1)]
    hidden_count = len(contexts) - MAXIMUM_LISTED_CONTEXTS
    if hidden_count > 0:
        entries.append(f"<i>+{hidden_count} more</i>")
    return "<qt>" + "<br><br>".join(entries) + "</qt>"


def _context_entry(position: int, context: RetrievedContext) -> str:
    details = [escape(context.identifier or UNKNOWN_IDENTIFIER)]
    if context.retrieval_score is not None:
        details.append(f"score {context.retrieval_score:.3f}")
    preview = context.text if len(context.text) <= CONTEXT_PREVIEW_LENGTH else context.text[:CONTEXT_PREVIEW_LENGTH] + ELLIPSIS
    return f"<b>{position}.</b> <i>{' · '.join(details)}</i><br>{escape(preview)}"
