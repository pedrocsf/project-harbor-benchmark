import math
from dataclasses import dataclass

from domain.scoring.rag.relevance_matching import RankedRelevance


@dataclass(frozen=True)
class RankedGain:
    rank: int
    gain: float
    discount: float
    new_targets: tuple[int, ...]

    @property
    def discounted_gain(self) -> float:
        return self.gain / self.discount


@dataclass(frozen=True)
class DcgBreakdown:
    gains: tuple[RankedGain, ...]
    dcg: float
    ideal_dcg: float

    @property
    def ndcg(self) -> float:
        if self.ideal_dcg == 0:
            return 0.0
        return min(1.0, self.dcg / self.ideal_dcg)


def rank_discount(rank: int) -> float:
    return math.log2(rank + 1)


def hit_rate(relevance: RankedRelevance, cutoff: int) -> float:
    return 1.0 if any(judgment.is_relevant for judgment in relevance.top(cutoff)) else 0.0


def precision_at_k(relevance: RankedRelevance, cutoff: int) -> float:
    relevant_count = sum(1 for judgment in relevance.top(cutoff) if judgment.is_relevant)
    return relevant_count / cutoff


def recall_at_k(relevance: RankedRelevance, cutoff: int) -> float:
    if not relevance.targets:
        return 0.0
    return len(hit_targets(relevance, cutoff)) / len(relevance.targets)


def hit_targets(relevance: RankedRelevance, cutoff: int) -> set[int]:
    found: set[int] = set()
    for judgment in relevance.top(cutoff):
        found.update(judgment.target_gains)
    return found


def first_relevant_rank(relevance: RankedRelevance, cutoff: int) -> int | None:
    return next((judgment.rank for judgment in relevance.top(cutoff) if judgment.is_relevant), None)


def reciprocal_rank(relevance: RankedRelevance, cutoff: int) -> float:
    rank = first_relevant_rank(relevance, cutoff)
    return 0.0 if rank is None else 1.0 / rank


def dcg_breakdown(relevance: RankedRelevance, cutoff: int, graded: bool) -> DcgBreakdown:
    credited: set[int] = set()
    gains = []
    for judgment in relevance.top(cutoff):
        new_targets = tuple(sorted(set(judgment.target_gains) - credited))
        credited.update(new_targets)
        gain = _gain(judgment.target_gains, new_targets, graded)
        gains.append(RankedGain(judgment.rank, gain, rank_discount(judgment.rank), new_targets))
    ideal_count = min(len(relevance.targets), cutoff)
    ideal_dcg = sum(1.0 / rank_discount(rank) for rank in range(1, ideal_count + 1))
    dcg = sum(ranked_gain.discounted_gain for ranked_gain in gains)
    return DcgBreakdown(tuple(gains), dcg, ideal_dcg)


def _gain(target_gains: dict[int, float], new_targets: tuple[int, ...], graded: bool) -> float:
    if not new_targets:
        return 0.0
    if not graded:
        return 1.0
    return max(target_gains[target] for target in new_targets)


def ndcg_at_k(relevance: RankedRelevance, cutoff: int, graded: bool = False) -> float:
    return dcg_breakdown(relevance, cutoff, graded).ndcg
