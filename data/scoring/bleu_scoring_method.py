from collections.abc import Mapping, Sequence

from sacrebleu.metrics import BLEU

from domain.scoring.metric_parameters import (
    ParameterChoice,
    ParameterKind,
    ParameterSpec,
    ParameterValue,
    validate_parameters,
)
from domain.scoring.scoring_method import ScoreKind, ScoringMethod

SACREBLEU_SCALE = 100.0
MINIMUM_SCORE = 0.0
MAXIMUM_SCORE = 1.0
SMOOTH_EXP = "exp"
SMOOTH_FLOOR = "floor"
SMOOTH_ADD_K = "add-k"
SMOOTH_NONE = "none"

BLEU_PARAMETER_SPECS = (
    ParameterSpec(
        key="max_ngram_order",
        label="Maximum n-gram order",
        description="Longest word sequence compared between answer and reference. Lower values are more forgiving; higher values reward longer exact phrases.",
        kind=ParameterKind.INTEGER,
        default=4,
        minimum=1,
        maximum=6,
        step=1,
    ),
    ParameterSpec(
        key="smooth_method",
        label="Smoothing method",
        description="How n-gram orders with zero matches are handled so the score does not collapse to zero. 'none' disables smoothing.",
        kind=ParameterKind.CHOICE,
        default=SMOOTH_EXP,
        choices=(
            ParameterChoice(SMOOTH_EXP, "Exponential decay"),
            ParameterChoice(SMOOTH_FLOOR, "Floor"),
            ParameterChoice(SMOOTH_ADD_K, "Add-k"),
            ParameterChoice(SMOOTH_NONE, "None"),
        ),
    ),
    ParameterSpec(
        key="floor_value",
        label="Floor value",
        description="Match count substituted for orders with zero matches. Only applies with the Floor smoothing method.",
        kind=ParameterKind.DECIMAL,
        default=0.1,
        minimum=0.01,
        maximum=1.0,
        step=0.01,
    ),
    ParameterSpec(
        key="add_k_value",
        label="Add-k value",
        description="Constant added to match and total counts of every order above unigrams. Only applies with the Add-k smoothing method.",
        kind=ParameterKind.INTEGER,
        default=1,
        minimum=1,
        maximum=10,
        step=1,
    ),
    ParameterSpec(
        key="tokenize",
        label="Tokenizer",
        description="How text is split into tokens before counting n-grams. 'char' compares single characters; 'none' splits only on spaces.",
        kind=ParameterKind.CHOICE,
        default="13a",
        choices=(
            ParameterChoice("13a", "13a (WMT standard)"),
            ParameterChoice("intl", "International"),
            ParameterChoice("char", "Characters"),
            ParameterChoice("none", "None"),
        ),
    ),
    ParameterSpec(
        key="lowercase",
        label="Ignore letter case",
        description="Lowercase both texts before comparing, so capitalization differences are not penalized.",
        kind=ParameterKind.BOOLEAN,
        default=False,
    ),
    ParameterSpec(
        key="effective_order",
        label="Effective order",
        description="At sentence level, only use n-gram orders that exist in the answer, which avoids zero scores for short sentences. Corpus scoring always ignores this option.",
        kind=ParameterKind.BOOLEAN,
        default=True,
    ),
)


def clamp_score(score: float) -> float:
    return min(max(score, MINIMUM_SCORE), MAXIMUM_SCORE)


def resolve_bleu_parameters(parameters: Mapping[str, object] | None) -> dict[str, ParameterValue]:
    return validate_parameters(BLEU_PARAMETER_SPECS, parameters or {})


def _smooth_value(values: Mapping[str, ParameterValue]) -> float | None:
    smooth_method = values["smooth_method"]
    if smooth_method == SMOOTH_FLOOR:
        return values["floor_value"]
    if smooth_method == SMOOTH_ADD_K:
        return values["add_k_value"]
    return None


def build_bleu_metric(values: Mapping[str, ParameterValue], sentence_level: bool = True) -> BLEU:
    return BLEU(
        lowercase=values["lowercase"],
        tokenize=values["tokenize"],
        smooth_method=values["smooth_method"],
        smooth_value=_smooth_value(values),
        max_ngram_order=values["max_ngram_order"],
        effective_order=bool(values["effective_order"]) and sentence_level,
    )


class BleuScoringMethod(ScoringMethod):
    identifier = "bleu"
    display_name = "BLEU"
    column_header = "BLEU"
    score_kind = ScoreKind.CONTINUOUS
    parameter_specs = BLEU_PARAMETER_SPECS

    def score(self, expected_answer: str, given_answer: str) -> float:
        metric = build_bleu_metric(self.parameters)
        return clamp_score(metric.sentence_score(given_answer, [expected_answer]).score / SACREBLEU_SCALE)

    def corpus_score(self, answer_pairs: Sequence[tuple[str, str]]) -> float | None:
        if not answer_pairs:
            return None
        references = [expected_answer for expected_answer, _ in answer_pairs]
        hypotheses = [given_answer for _, given_answer in answer_pairs]
        metric = build_bleu_metric(self.parameters, sentence_level=False)
        return metric.corpus_score(hypotheses, [references]).score / SACREBLEU_SCALE
