from collections.abc import Mapping

from sacrebleu.metrics import CHRF

from domain.scoring.metric_parameters import (
    ParameterKind,
    ParameterSpec,
    ParameterValue,
    validate_parameters,
)
from data.scoring.bleu_scoring_method import clamp_score
from domain.scoring.scoring_method import ScoreKind, ScoringMethod

SACREBLEU_SCALE = 100.0
WORD_ORDER = 2

CHRF_PARAMETER_SPECS = (
    ParameterSpec(
        key="char_order",
        label="Character n-gram order",
        description="Longest character sequence compared between answer and reference. Higher values reward longer exact character runs.",
        kind=ParameterKind.INTEGER,
        default=6,
        minimum=1,
        maximum=10,
        step=1,
    ),
    ParameterSpec(
        key="word_order",
        label="Word n-gram order",
        description="Longest word sequence also compared. Use 0 for plain chrF without word n-grams; 2 gives chrF++.",
        kind=ParameterKind.INTEGER,
        default=WORD_ORDER,
        minimum=0,
        maximum=3,
        step=1,
    ),
    ParameterSpec(
        key="beta",
        label="Recall weight (beta)",
        description="How much more recall counts than precision in the F-score. 1 weighs them equally; higher values favor covering the reference.",
        kind=ParameterKind.INTEGER,
        default=2,
        minimum=1,
        maximum=6,
        step=1,
    ),
    ParameterSpec(
        key="lowercase",
        label="Ignore letter case",
        description="Lowercase both texts before comparing, so capitalization differences are not penalized.",
        kind=ParameterKind.BOOLEAN,
        default=False,
    ),
    ParameterSpec(
        key="whitespace",
        label="Include whitespace",
        description="Keep spaces when extracting character n-grams instead of discarding them.",
        kind=ParameterKind.BOOLEAN,
        default=False,
    ),
    ParameterSpec(
        key="eps_smoothing",
        label="Epsilon smoothing",
        description="Use epsilon smoothing for orders with zero statistics instead of excluding them from the average.",
        kind=ParameterKind.BOOLEAN,
        default=False,
    ),
)


def resolve_chrf_parameters(parameters: Mapping[str, object] | None) -> dict[str, ParameterValue]:
    return validate_parameters(CHRF_PARAMETER_SPECS, parameters or {})


def build_chrf_metric(values: Mapping[str, ParameterValue]) -> CHRF:
    return CHRF(
        char_order=values["char_order"],
        word_order=values["word_order"],
        beta=values["beta"],
        lowercase=values["lowercase"],
        whitespace=values["whitespace"],
        eps_smoothing=values["eps_smoothing"],
    )


class ChrfScoringMethod(ScoringMethod):
    identifier = "chrf"
    display_name = "chrF++"
    column_header = "chrF++"
    score_kind = ScoreKind.CONTINUOUS
    parameter_specs = CHRF_PARAMETER_SPECS

    def score(self, expected_answer: str, given_answer: str) -> float:
        if not given_answer.strip():
            return 0.0
        metric = build_chrf_metric(self.parameters)
        return clamp_score(metric.sentence_score(given_answer, [expected_answer]).score / SACREBLEU_SCALE)
