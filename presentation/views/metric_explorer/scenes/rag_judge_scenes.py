from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter

from domain.explanations.metric_walkthrough import MetricWalkthrough
from domain.explanations.rag_walkthrough_details import (
    AnswerRelevancyDetails,
    ContextRelevanceDetails,
    ContextSupportDetails,
    FaithfulnessDetails,
)
from domain.explanations.timeline import TimelinePosition
from presentation.views.branding import PRIMARY_HOVER_COLOR, SUCCESS_COLOR, WARNING_COLOR
from presentation.views.metric_explorer.scenes.base_scene import SceneStep, WalkthroughScene
from presentation.views.metric_explorer.scenes.rag_scene_painting import (
    CardContent,
    appear_fraction,
    caption_rect,
    paint_card,
    paint_counters,
    paint_final_bar,
    paint_hidden_rows,
    paint_section_caption,
    scene_frame,
    section_top,
    stack_rows,
)
from presentation.views.metric_explorer.scenes.token_scene_painting import (
    EMPTY_TOKENS_TEXT,
    ChipState,
    blend_styles,
    chip_style,
    choose_chip_metrics,
    format_score,
    highlighted_value,
    layout_tokens,
    offset_rects,
    paint_chip,
    paint_empty_slot,
    empty_slot_width,
    paint_note,
)

FIRST_STEP = 0
CHECK_STEP = 1
SCORE_STEP = 2
CONTEXT_SHARE = 0.45
REVEALED = 0.95
CHIP_CAPTION_GAP = 10.0
NO_ID_TEXT = "no id"
NOTHING_TO_CHECK_TEXT = "Nothing to check: the answer is empty, has no statements or there are no contexts."
NO_CONTEXTS_TEXT = "The system returned no contexts, so there is nothing to rate."
NO_QUESTIONS_TEXT = "The answer is empty, so the judge writes no question."
SUPPORTED_TEXT = "supported"
UNSUPPORTED_TEXT = "not supported"


def _details(walkthrough: MetricWalkthrough, expected_type: type):
    details = walkthrough.details
    if not isinstance(details, expected_type):
        raise TypeError(f"Expected {expected_type.__name__}, got {type(details).__name__}.")
    return details


def _context_card(index: int, context) -> CardContent:
    return CardContent(str(index + 1), context.identifier or NO_ID_TEXT, context.text)


def _paint_context_rows(painter: QPainter, contexts, top: float, bottom: float, area: QRectF, appear: float, styles=None, trailing=None) -> float:
    rows, hidden = stack_rows(top, bottom, area.left(), area.width(), len(contexts))
    for index, rect in enumerate(rows):
        content = _context_card(index, contexts[index])
        if trailing is not None:
            text, color = trailing(index)
            content = CardContent(content.badge, content.title, content.body, text, color)
        style = styles(index) if styles is not None else chip_style(ChipState.NEUTRAL)
        paint_card(painter, rect, content, style, appear if not callable(appear) else appear(index, len(rows)))
    if not rows:
        return top
    paint_hidden_rows(painter, rows[-1].bottom() + 4, area.left(), area.width(), hidden)
    return rows[-1].bottom()


class ContextSupportScene(WalkthroughScene):
    def __init__(self, identifier: str):
        self.identifier = identifier
        is_answer = identifier == "k_precision"
        self._subject = "answer" if is_answer else "expected answer"
        self._bar_label = "K-Prec" if is_answer else "Coverage"
        self._formula = (
            ("K-Precision = |answer tokens in the contexts| / |answer tokens|",)
            if is_answer
            else ("Coverage = |expected tokens in the contexts| / |expected tokens|",)
        )
        self._limitation = (
            "Word overlap only: paraphrases count as unsupported and a wrong statement built from context words counts as supported."
            if is_answer
            else "It checks the retrieval, not the model: a high coverage does not mean the answer used it."
        )
        self._steps = (
            SceneStep("Pool the context words", "All {contexts} retrieved contexts are tokenized into one vocabulary.", 3.0, ()),
            SceneStep("Look up each token", "Each token of the {subject} lights up when the contexts contain it: {found} of {total}.", 4.0, ()),
            SceneStep("Score", "The share of {subject} tokens found in the contexts: {found} / {total}.", 3.0, (0,)),
        )

    @property
    def steps(self) -> tuple[SceneStep, ...]:
        return self._steps

    @property
    def formula(self) -> tuple[str, ...]:
        return self._formula

    @property
    def limitation(self) -> str:
        return self._limitation

    def step_body(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        details: ContextSupportDetails = _details(walkthrough, ContextSupportDetails)
        return self._steps[step_index].body.format(
            contexts=len(details.contexts),
            subject=self._subject,
            found=details.support.supported_count,
            total=len(details.support.tokens),
        )

    def formula_result(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        if step_index != SCORE_STEP:
            return ""
        details: ContextSupportDetails = _details(walkthrough, ContextSupportDetails)
        return f"{details.support.supported_count} / {len(details.support.tokens)} = {highlighted_value(walkthrough.final_score)}"

    def paint(self, painter: QPainter, area: QRectF, walkthrough: MetricWalkthrough, position: TimelinePosition) -> None:
        details: ContextSupportDetails = _details(walkthrough, ContextSupportDetails)
        frame = scene_frame(area)
        painter.save()
        painter.setClipRect(area)
        contexts_caption = caption_rect(area.left(), frame.content.top(), area.width())
        paint_section_caption(painter, contexts_caption, f"Retrieved contexts · {len(details.contexts)}")
        contexts_bottom = frame.content.top() + frame.content.height() * CONTEXT_SHARE
        last_bottom = _paint_context_rows(
            painter,
            details.contexts,
            section_top(contexts_caption),
            contexts_bottom,
            area,
            lambda index, count: appear_fraction(position, FIRST_STEP, index, count),
        )
        tokens_caption = caption_rect(area.left(), max(last_bottom, contexts_bottom) + 14, area.width())
        paint_section_caption(painter, tokens_caption, f"{self._subject} · {len(details.support.tokens)} tokens")
        self._paint_tokens(painter, details, QRectF(area.left(), section_top(tokens_caption), area.width(), frame.content.bottom() - section_top(tokens_caption)), position)
        values = None if position.step_index < CHECK_STEP else (str(details.support.supported_count), str(len(details.support.tokens)))
        paint_counters(painter, frame, ("found in contexts", f"{self._subject} tokens"), values, position, SCORE_STEP)
        paint_final_bar(painter, frame, self._bar_label, walkthrough.final_score, position, SCORE_STEP)
        painter.restore()

    def _paint_tokens(self, painter: QPainter, details: ContextSupportDetails, area: QRectF, position: TimelinePosition) -> None:
        tokens = details.support.tokens or (EMPTY_TOKENS_TEXT,)
        metrics = choose_chip_metrics((tokens,), area.width(), area.height())
        if not details.support.tokens:
            paint_empty_slot(painter, QRectF(area.left(), area.top(), empty_slot_width(metrics, area.width()), metrics.height), metrics)
            return
        rects = offset_rects(layout_tokens(tokens, area.width(), metrics).rects, QPointF(area.left(), area.top()))
        for index, (rect, token, supported) in enumerate(zip(rects, details.support.tokens, details.support.supported)):
            reveal = appear_fraction(position, CHECK_STEP, index, len(rects))
            target = ChipState.SUCCESS if supported else ChipState.MISSING
            paint_chip(painter, rect, token, blend_styles(ChipState.NEUTRAL, target, reveal), metrics)


class FaithfulnessScene(WalkthroughScene):
    identifier = "faithfulness"

    _steps = (
        SceneStep("Split into statements", "The judge splits the answer into {count} standalone statement(s).", 3.5, ()),
        SceneStep("Check against the contexts", "Each statement is checked against the retrieved contexts only: {supported} of {count} are supported.", 4.5, ()),
        SceneStep("Score", "Supported statements divided by all statements: {supported} / {count}.", 3.0, (0,)),
    )

    @property
    def steps(self) -> tuple[SceneStep, ...]:
        return self._steps

    @property
    def formula(self) -> tuple[str, ...]:
        return ("Faithfulness = |supported statements| / |statements|",)

    @property
    def limitation(self) -> str:
        return "A correct fact that is not in the contexts counts as unsupported, and the verdicts depend on the judge model."

    def step_body(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        details: FaithfulnessDetails = _details(walkthrough, FaithfulnessDetails)
        if not details.verdicts.statements:
            return NOTHING_TO_CHECK_TEXT
        return self._steps[step_index].body.format(
            count=len(details.verdicts.statements), supported=sum(details.verdicts.supported)
        )

    def formula_result(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        if step_index != SCORE_STEP:
            return ""
        details: FaithfulnessDetails = _details(walkthrough, FaithfulnessDetails)
        return f"{sum(details.verdicts.supported)} / {len(details.verdicts.statements)} = {highlighted_value(walkthrough.final_score)}"

    def paint(self, painter: QPainter, area: QRectF, walkthrough: MetricWalkthrough, position: TimelinePosition) -> None:
        details: FaithfulnessDetails = _details(walkthrough, FaithfulnessDetails)
        frame = scene_frame(area)
        painter.save()
        painter.setClipRect(area)
        contexts_caption = caption_rect(area.left(), frame.content.top(), area.width())
        paint_section_caption(painter, contexts_caption, f"Retrieved contexts · {len(details.contexts)}")
        contexts_bottom = frame.content.top() + frame.content.height() * CONTEXT_SHARE
        last_bottom = _paint_context_rows(painter, details.contexts, section_top(contexts_caption), contexts_bottom, area, 1.0)
        statements_caption = caption_rect(area.left(), max(last_bottom, contexts_bottom) + 14, area.width())
        paint_section_caption(painter, statements_caption, f"Statements in the answer · {len(details.verdicts.statements)}")
        statements = details.verdicts.statements
        top = section_top(statements_caption)
        if not statements:
            paint_note(painter, QRectF(area.left(), top, area.width(), 40), NOTHING_TO_CHECK_TEXT)
        rows, hidden = stack_rows(top, frame.content.bottom(), area.left(), area.width(), len(statements))
        for index, rect in enumerate(rows):
            supported = details.verdicts.supported[index]
            reveal = appear_fraction(position, CHECK_STEP, index, len(rows))
            target = ChipState.SUCCESS if supported else ChipState.FAILURE
            label, color = (SUPPORTED_TEXT, SUCCESS_COLOR) if supported else (UNSUPPORTED_TEXT, WARNING_COLOR)
            content = CardContent(str(index + 1), "", statements[index], label if reveal >= REVEALED else "", color)
            paint_card(painter, rect, content, blend_styles(ChipState.NEUTRAL, target, reveal), appear_fraction(position, FIRST_STEP, index, len(rows)))
        if rows:
            paint_hidden_rows(painter, rows[-1].bottom() + 4, area.left(), area.width(), hidden)
        values = None if position.step_index < CHECK_STEP else (str(sum(details.verdicts.supported)), str(len(statements)))
        paint_counters(painter, frame, ("supported", "statements"), values, position, SCORE_STEP)
        paint_final_bar(painter, frame, "Faithful", walkthrough.final_score, position, SCORE_STEP)
        painter.restore()


class ContextRelevanceScene(WalkthroughScene):
    identifier = "context_relevance"

    _steps = (
        SceneStep("One question per context", "The judge sees the question and one context at a time: {count} judge call(s).", 3.0, ()),
        SceneStep("Rate each context", "Each context gets a rating from 0 to {maximum}: {ratings}.", 4.0, ()),
        SceneStep("Average", "The mean rating divided by {maximum}.", 3.0, (0,)),
    )

    @property
    def steps(self) -> tuple[SceneStep, ...]:
        return self._steps

    @property
    def formula(self) -> tuple[str, ...]:
        return ("Context relevance = mean(rating_j) / N",)

    @property
    def limitation(self) -> str:
        return "It needs no labels, but it trusts the judge model, and a useful context may still not hold the answer."

    def step_body(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        details: ContextRelevanceDetails = _details(walkthrough, ContextRelevanceDetails)
        if not details.contexts:
            return NO_CONTEXTS_TEXT
        return self._steps[step_index].body.format(
            count=len(details.contexts),
            maximum=details.ratings.maximum_rating,
            ratings=", ".join(str(rating) for rating in details.ratings.ratings),
        )

    def formula_result(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        if step_index != SCORE_STEP:
            return ""
        return f"score = {highlighted_value(walkthrough.final_score)}"

    def paint(self, painter: QPainter, area: QRectF, walkthrough: MetricWalkthrough, position: TimelinePosition) -> None:
        details: ContextRelevanceDetails = _details(walkthrough, ContextRelevanceDetails)
        frame = scene_frame(area)
        maximum = details.ratings.maximum_rating
        painter.save()
        painter.setClipRect(area)
        question_caption = caption_rect(area.left(), frame.content.top(), area.width())
        paint_section_caption(painter, question_caption, f"Question · {details.question}")
        contexts_caption = caption_rect(area.left(), section_top(question_caption) + 4, area.width())
        paint_section_caption(painter, contexts_caption, f"Retrieved contexts · {len(details.contexts)}")
        if not details.contexts:
            paint_note(painter, QRectF(area.left(), section_top(contexts_caption), area.width(), 40), NO_CONTEXTS_TEXT)

        def style(index: int):
            reveal = appear_fraction(position, CHECK_STEP, index, len(details.contexts))
            rating = details.ratings.ratings[index]
            target = ChipState.SUCCESS if rating * 2 >= maximum and rating > 0 else ChipState.DIMMED
            return blend_styles(ChipState.NEUTRAL, target, reveal)

        def trailing(index: int):
            if appear_fraction(position, CHECK_STEP, index, len(details.contexts)) < REVEALED:
                return "", PRIMARY_HOVER_COLOR
            return f"{details.ratings.ratings[index]} / {maximum}", PRIMARY_HOVER_COLOR

        _paint_context_rows(
            painter,
            details.contexts,
            section_top(contexts_caption),
            frame.content.bottom(),
            area,
            lambda index, count: appear_fraction(position, FIRST_STEP, index, count),
            style,
            trailing,
        )
        values = None if position.step_index < CHECK_STEP else (str(sum(details.ratings.ratings)), str(len(details.contexts) * maximum))
        paint_counters(painter, frame, ("ratings", "maximum possible"), values, position, SCORE_STEP)
        paint_final_bar(painter, frame, "Relevance", walkthrough.final_score, position, SCORE_STEP)
        painter.restore()


class AnswerRelevancyScene(WalkthroughScene):
    identifier = "answer_relevancy"

    _steps = (
        SceneStep("Questions from the answer", "The judge reads only the answer and writes {count} question(s) it would answer.", 3.5, ()),
        SceneStep("Compare with the real question", "Each generated question is embedded and compared with the original one: {similarities}.", 4.0, ()),
        SceneStep("Average", "The mean similarity is the score. Wrong but on-topic answers still score high.", 3.0, (0,)),
    )

    @property
    def steps(self) -> tuple[SceneStep, ...]:
        return self._steps

    @property
    def formula(self) -> tuple[str, ...]:
        return ("Answer relevancy = mean_i sim(E(question), E(q_i))",)

    @property
    def limitation(self) -> str:
        return "It measures focus, not correctness: a confident wrong answer about the right topic scores well."

    def step_body(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        details: AnswerRelevancyDetails = _details(walkthrough, AnswerRelevancyDetails)
        if not details.generated.questions:
            return NO_QUESTIONS_TEXT
        return self._steps[step_index].body.format(
            count=len(details.generated.questions),
            similarities=", ".join(format_score(value) for value in details.generated.similarities),
        )

    def formula_result(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        if step_index != SCORE_STEP:
            return ""
        return f"score = {highlighted_value(walkthrough.final_score)}"

    def paint(self, painter: QPainter, area: QRectF, walkthrough: MetricWalkthrough, position: TimelinePosition) -> None:
        details: AnswerRelevancyDetails = _details(walkthrough, AnswerRelevancyDetails)
        frame = scene_frame(area)
        painter.save()
        painter.setClipRect(area)
        question_caption = caption_rect(area.left(), frame.content.top(), area.width())
        paint_section_caption(painter, question_caption, f"Original question · {details.question}")
        answer_caption = caption_rect(area.left(), section_top(question_caption) + 4, area.width())
        paint_section_caption(painter, answer_caption, f"Answer · {walkthrough.given_answer or '(empty)'}")
        generated_caption = caption_rect(area.left(), section_top(answer_caption) + 10, area.width())
        paint_section_caption(painter, generated_caption, f"Questions written by the judge · {len(details.generated.questions)}")
        questions = details.generated.questions
        top = section_top(generated_caption)
        if not questions:
            paint_note(painter, QRectF(area.left(), top, area.width(), 40), NO_QUESTIONS_TEXT)
        rows, hidden = stack_rows(top, frame.content.bottom(), area.left(), area.width(), len(questions))
        for index, rect in enumerate(rows):
            similarity = details.generated.similarities[index]
            reveal = appear_fraction(position, CHECK_STEP, index, len(rows))
            target = ChipState.SUCCESS if similarity >= 0.5 else ChipState.DIMMED
            content = CardContent(str(index + 1), "", questions[index], f"sim {format_score(similarity)}" if reveal >= REVEALED else "", PRIMARY_HOVER_COLOR)
            paint_card(painter, rect, content, blend_styles(ChipState.NEUTRAL, target, reveal), appear_fraction(position, FIRST_STEP, index, len(rows)))
        if rows:
            paint_hidden_rows(painter, rows[-1].bottom() + 4, area.left(), area.width(), hidden)
        values = None
        if position.step_index >= CHECK_STEP and questions:
            values = (format_score(details.generated.score), str(len(questions)))
        paint_counters(painter, frame, ("mean similarity", "questions"), values, position, SCORE_STEP)
        paint_final_bar(painter, frame, "Relevancy", walkthrough.final_score, position, SCORE_STEP)
        painter.restore()
