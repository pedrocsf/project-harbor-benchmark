import math
from collections.abc import Mapping

from sacrebleu.metrics import BLEU, CHRF

from data.scoring.bleu_scoring_method import (
    SACREBLEU_SCALE,
    build_bleu_metric,
    clamp_score,
    resolve_bleu_parameters,
)
from data.scoring.chrf_scoring_method import build_chrf_metric, resolve_chrf_parameters
from domain.explanations.translation_statistics import TranslationStatisticsProvider
from domain.explanations.walkthrough_details import BleuDetails, ChrfDetails, ChrfOrderStatistics

STATISTICS_PER_ORDER = 3
NO_SCORE = 0.0


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return NO_SCORE
    return numerator / denominator


class SacrebleuStatisticsProvider(TranslationStatisticsProvider):
    def bleu_details(
        self, answer: str, reference: str, parameters: Mapping[str, object] | None = None
    ) -> BleuDetails:
        bleu = build_bleu_metric(resolve_bleu_parameters(parameters))
        result = bleu.sentence_score(answer, [reference])
        precisions = tuple(precision / SACREBLEU_SCALE for precision in result.precisions)
        effective_order = self._effective_order(result.totals)
        return BleuDetails(
            answer_tokens=self._bleu_tokens(bleu, answer),
            reference_tokens=self._bleu_tokens(bleu, reference),
            matches_by_order=tuple(result.counts),
            totals_by_order=tuple(result.totals),
            precisions=precisions,
            smoothed_orders=self._smoothed_orders(result.counts, result.totals),
            effective_order=effective_order,
            answer_length=result.sys_len,
            reference_length=result.ref_len,
            brevity_penalty=result.bp,
            geometric_mean=self._geometric_mean(precisions[:effective_order]),
            score=clamp_score(result.score / SACREBLEU_SCALE),
        )

    def chrf_details(
        self, answer: str, reference: str, parameters: Mapping[str, object] | None = None
    ) -> ChrfDetails:
        chrf = build_chrf_metric(resolve_chrf_parameters(parameters))
        statistics = chrf._extract_corpus_statistics([answer], [[reference]])[0]
        orders = [self._order_statistics(chrf, statistics, position) for position in range(chrf.order)]
        character_orders = tuple(orders[: chrf.char_order])
        word_orders = tuple(orders[chrf.char_order :])
        effective = [order for order in orders if order.answer_count > 0 and order.reference_count > 0]
        average_precision = sum(order.precision for order in effective) / len(effective) if effective else NO_SCORE
        average_recall = sum(order.recall for order in effective) / len(effective) if effective else NO_SCORE
        f_score = NO_SCORE
        if answer.strip():
            f_score = clamp_score(chrf.sentence_score(answer, [reference]).score / SACREBLEU_SCALE)
        return ChrfDetails(
            character_orders=character_orders,
            word_orders=word_orders,
            beta=float(chrf.beta),
            average_precision=average_precision,
            average_recall=average_recall,
            f_score=f_score,
        )

    def _bleu_tokens(self, bleu: BLEU, text: str) -> tuple[str, ...]:
        return tuple(bleu.tokenizer(text.rstrip()).split())

    def _effective_order(self, totals: list[int]) -> int:
        effective_order = 0
        for total in totals:
            if total == 0:
                break
            effective_order += 1
        return effective_order

    def _smoothed_orders(self, counts: list[int], totals: list[int]) -> tuple[int, ...]:
        if not any(counts):
            return ()
        return tuple(
            order
            for order, (count, total) in enumerate(zip(counts, totals), start=1)
            if count == 0 and total > 0
        )

    def _geometric_mean(self, precisions: tuple[float, ...]) -> float:
        if not precisions or min(precisions) <= 0:
            return NO_SCORE
        return math.exp(sum(math.log(precision) for precision in precisions) / len(precisions))

    def _order_statistics(self, chrf: CHRF, statistics: list[int], position: int) -> ChrfOrderStatistics:
        start = STATISTICS_PER_ORDER * position
        answer_count, reference_count, match_count = statistics[start : start + STATISTICS_PER_ORDER]
        order_number = position + 1 if position < chrf.char_order else position - chrf.char_order + 1
        return ChrfOrderStatistics(
            order=order_number,
            answer_count=answer_count,
            reference_count=reference_count,
            match_count=match_count,
            precision=_ratio(match_count, answer_count),
            recall=_ratio(match_count, reference_count),
        )
