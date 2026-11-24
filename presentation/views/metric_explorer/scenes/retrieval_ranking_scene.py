from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter

from domain.explanations.metric_walkthrough import MetricWalkthrough
from domain.explanations.rag_walkthrough_details import RetrievalDetails
from domain.explanations.timeline import TimelinePosition
from domain.scoring.rag.relevance_matching import MATCH_BY_IDS
from presentation.views.branding import PRIMARY_HOVER_COLOR, SUCCESS_COLOR, TEXT_COLOR
from presentation.views.metric_explorer.painting import segment_progress
from presentation.views.metric_explorer.scenes.base_scene import SceneStep, WalkthroughScene
from presentation.views.metric_explorer.scenes.rag_scene_painting import (
    CardContent,
    appear_fraction,
    caption_rect,
    paint_card,
    paint_counters,
    paint_cutoff,
    paint_final_bar,
    paint_hidden_rows,
    paint_section_caption,
    scene_frame,
    section_top,
    short_text,
    stack_rows,
)
from presentation.views.metric_explorer.scenes.token_scene_painting import (
    ChipState,
    blend_styles,
    chip_style,
    format_score,
    highlighted_value,
)

RANK_STEP = 0
MATCH_STEP = 1
SCORE_STEP = 2
TARGET_PREVIEW_LENGTH = 34
TARGETS_SEPARATOR = " · "
CONTEXTS_CAPTION = "Retrieved contexts, best first · k = {k}"
TARGETS_CAPTION_IDS = "Relevant ids: {targets}"
TARGETS_CAPTION_TEXT = "Relevant passages: {targets}"
NO_ID_TEXT = "no id"
SCORE_TITLE = "{identifier} · retrieval score {score}"
UNSCORED_TITLE = "{identifier}"
RELEVANT_MARK = "relevant"
BAR_LABELS = {"hit_rate": "Hit@k", "context_precision": "P@k", "context_recall": "R@k", "mrr": "RR", "ndcg": "nDCG"}
MATCH_BY_TEXT = {
    MATCH_BY_IDS: "by id against relevant_context_ids",
}
MATCH_BY_PASSAGE_TEXT = "by text: a context is relevant when it holds at least {threshold:.0%} of a relevant passage's words"

STEP_RANK = SceneStep(
    "Ranked contexts",
    "The system returned {count} contexts, best first. Only the first k = {k} are judged.",
    3.5,
    (),
)
STEP_MATCH = SceneStep(
    "Find the relevant ones",
    "Each context is compared {match_text}. {relevant} of the first {k} are relevant.",
    4.0,
    (),
)
SCENE_TEXTS = {
    "hit_rate": (
        ("Hit@k = 1 if any relevant context is in the first k, else 0",),
        "Did anything relevant reach the prompt? {verdict}.",
        "It only asks whether something relevant was found, not how much or how high.",
        ("relevant in top k", "hit"),
    ),
    "context_precision": (
        ("P@k = |relevant in the first k| / k",),
        "{relevant} relevant contexts divided by k = {k}.",
        "It always divides by k, so a system that returns fewer contexts is penalized, and duplicates all count.",
        ("relevant in top k", "k"),
    ),
    "context_recall": (
        ("R@k = |relevant items found| / |relevant items|",),
        "{found} of the {targets} labelled items appear in the first k.",
        "Each labelled item counts once; it says nothing about the irrelevant contexts that came along.",
        ("items found", "labelled items"),
    ),
    "mrr": (
        ("RR = 1 / rank of the first relevant context", "MRR = mean RR over the questions"),
        "{rank_text}",
        "Only the first relevant context matters; everything after it is ignored.",
        ("first relevant rank", "reciprocal rank"),
    ),
    "ndcg": (
        ("DCG = Σ gain_i / log2(i + 1)", "nDCG = DCG / ideal DCG"),
        "New relevant items gain {gain_kind}, divided by log2(rank + 1). DCG = {dcg}; putting every relevant item first gives {ideal}.",
        "Labels decide everything: a useful context that nobody labelled counts as irrelevant.",
        ("DCG", "ideal DCG"),
    ),
}


def retrieval_details(walkthrough: MetricWalkthrough) -> RetrievalDetails:
    details = walkthrough.details
    if not isinstance(details, RetrievalDetails):
        raise TypeError(f"Expected retrieval details, got {type(details).__name__}.")
    return details


def match_text(walkthrough: MetricWalkthrough, details: RetrievalDetails) -> str:
    if details.relevance.match_by == MATCH_BY_IDS:
        return MATCH_BY_TEXT[MATCH_BY_IDS]
    return MATCH_BY_PASSAGE_TEXT.format(threshold=float(walkthrough.parameters.get("match_threshold", 0.5)))


class RetrievalRankingScene(WalkthroughScene):
    def __init__(self, identifier: str):
        self.identifier = identifier
        formula, score_body, limitation, counter_labels = SCENE_TEXTS[identifier]
        self._formula = formula
        self._limitation = limitation
        self._counter_labels = counter_labels
        self._steps = (
            STEP_RANK,
            STEP_MATCH,
            SceneStep("Score", score_body, 3.5, tuple(range(len(formula)))),
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
        details = retrieval_details(walkthrough)
        rank = details.first_relevant_rank
        return self._steps[step_index].body.format(
            count=len(details.relevance.judgments),
            k=details.cutoff,
            match_text=match_text(walkthrough, details),
            relevant=details.relevant_in_cutoff,
            verdict="Yes" if details.score > 0 else "No",
            found=len(details.found_targets),
            targets=len(details.relevance.targets),
            rank_text=f"The first relevant context is at rank {rank}, so RR = 1/{rank}." if rank else "No relevant context in the first k, so RR = 0.",
            gain_kind="their text coverage" if details.graded else "1",
            dcg=format_score(details.dcg.dcg),
            ideal=format_score(details.dcg.ideal_dcg),
        )

    def formula_result(self, step_index: int, walkthrough: MetricWalkthrough) -> str:
        if step_index != SCORE_STEP:
            return ""
        return f"score = {highlighted_value(walkthrough.final_score)}"

    def paint(self, painter: QPainter, area: QRectF, walkthrough: MetricWalkthrough, position: TimelinePosition) -> None:
        details = retrieval_details(walkthrough)
        frame = scene_frame(area)
        painter.save()
        painter.setClipRect(area)
        targets_rect = caption_rect(area.left(), frame.content.top(), area.width())
        paint_section_caption(painter, targets_rect, self._targets_caption(details))
        contexts_caption = caption_rect(area.left(), section_top(targets_rect), area.width())
        paint_section_caption(painter, contexts_caption, CONTEXTS_CAPTION.format(k=details.cutoff))
        rows, hidden = stack_rows(section_top(contexts_caption), frame.content.bottom() - 18, area.left(), area.width(), len(details.relevance.judgments))
        for index, rect in enumerate(rows):
            appear = appear_fraction(position, RANK_STEP, index, len(rows))
            paint_card(painter, rect, self._card(details, index, position), self._style(details, index, position), appear)
        cutoff_opacity = 1.0 if position.step_index > RANK_STEP else segment_progress(position.step_progress, 0.6, 1.0)
        paint_cutoff(painter, rows, details.cutoff, cutoff_opacity)
        if rows:
            paint_hidden_rows(painter, rows[-1].bottom() + 4, area.left(), area.width(), hidden)
        paint_counters(painter, frame, self._counter_labels, self._counter_values(details, position), position, SCORE_STEP)
        paint_final_bar(painter, frame, BAR_LABELS[self.identifier], walkthrough.final_score, position, SCORE_STEP)
        painter.restore()

    def _targets_caption(self, details: RetrievalDetails) -> str:
        previews = [short_text(target, TARGET_PREVIEW_LENGTH) for target in details.relevance.targets]
        template = TARGETS_CAPTION_IDS if details.relevance.match_by == MATCH_BY_IDS else TARGETS_CAPTION_TEXT
        return template.format(targets=TARGETS_SEPARATOR.join(previews))

    def _card(self, details: RetrievalDetails, index: int, position: TimelinePosition) -> CardContent:
        judgment = details.relevance.judgments[index]
        context = judgment.context
        identifier = context.identifier or NO_ID_TEXT
        title = (
            SCORE_TITLE.format(identifier=identifier, score=format_score(context.retrieval_score))
            if context.retrieval_score is not None
            else UNSCORED_TITLE.format(identifier=identifier)
        )
        trailing, trailing_color = self._trailing(details, index, position)
        return CardContent(str(judgment.rank), title, context.text, trailing, trailing_color)

    def _trailing(self, details: RetrievalDetails, index: int, position: TimelinePosition) -> tuple[str, str]:
        judgment = details.relevance.judgments[index]
        if position.step_index < MATCH_STEP or judgment.rank > details.cutoff:
            return "", TEXT_COLOR
        if position.step_index == SCORE_STEP and self.identifier == "ndcg":
            gain = details.dcg.gains[index]
            return f"{format_score(gain.gain)}/{gain.discount:.2f}", PRIMARY_HOVER_COLOR
        if position.step_index == SCORE_STEP and self.identifier == "mrr" and judgment.rank == details.first_relevant_rank:
            return f"1/{judgment.rank}", PRIMARY_HOVER_COLOR
        return (RELEVANT_MARK, SUCCESS_COLOR) if judgment.is_relevant else ("", TEXT_COLOR)

    def _style(self, details: RetrievalDetails, index: int, position: TimelinePosition):
        judgment = details.relevance.judgments[index]
        if judgment.rank > details.cutoff:
            fade = 1.0 if position.step_index > RANK_STEP else segment_progress(position.step_progress, 0.6, 1.0)
            return blend_styles(ChipState.NEUTRAL, ChipState.DIMMED, fade)
        if position.step_index == RANK_STEP:
            return chip_style(ChipState.NEUTRAL)
        reveal = appear_fraction(position, MATCH_STEP, index, min(details.cutoff, len(details.relevance.judgments)))
        target = ChipState.SUCCESS if judgment.is_relevant else ChipState.DIMMED
        if self.identifier == "mrr" and position.step_index == SCORE_STEP and judgment.rank == details.first_relevant_rank:
            target = ChipState.MATCHED
        return blend_styles(ChipState.NEUTRAL, target, reveal)

    def _counter_values(self, details: RetrievalDetails, position: TimelinePosition) -> tuple[str, str] | None:
        if position.step_index < MATCH_STEP:
            return None
        rank = details.first_relevant_rank
        values = {
            "hit_rate": (str(details.relevant_in_cutoff), "1" if details.score > 0 else "0"),
            "context_precision": (str(details.relevant_in_cutoff), str(details.cutoff)),
            "context_recall": (str(len(details.found_targets)), str(len(details.relevance.targets))),
            "mrr": (str(rank) if rank else "none", f"1/{rank}" if rank else "0"),
            "ndcg": (format_score(details.dcg.dcg), format_score(details.dcg.ideal_dcg)),
        }
        return values[self.identifier]
