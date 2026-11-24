from collections import Counter

from domain.scoring.metric_parameters import ParameterKind, ParameterSpec
from domain.scoring.scoring_method import ScoreKind, ScoringMethod
from domain.scoring.text_normalization import (
    NORMALIZATION_PARAMETER_SPECS,
    normalization_options_from,
    normalized_tokens,
)

BETA_PARAMETER_SPEC = ParameterSpec(
    key="beta",
    label="Beta",
    description=(
        "Weight of recall relative to precision. 1 is the balanced F1; "
        "above 1 favors recall, below 1 favors precision."
    ),
    kind=ParameterKind.DECIMAL,
    default=1.0,
    minimum=0.1,
    maximum=10.0,
    step=0.1,
)


def f_beta_score(precision: float, recall: float, beta: float) -> float:
    beta_squared = beta * beta
    denominator = beta_squared * precision + recall
    if denominator == 0:
        return 0.0
    return (1 + beta_squared) * precision * recall / denominator


class TokenF1ScoringMethod(ScoringMethod):
    identifier = "token_f1"
    display_name = "Token F1"
    column_header = "F1"
    score_kind = ScoreKind.CONTINUOUS
    parameter_specs = NORMALIZATION_PARAMETER_SPECS + (BETA_PARAMETER_SPEC,)

    def score(self, expected_answer: str, given_answer: str) -> float:
        options = normalization_options_from(self.parameters)
        expected_tokens = normalized_tokens(expected_answer, options)
        given_tokens = normalized_tokens(given_answer, options)
        if not expected_tokens or not given_tokens:
            return 1.0 if expected_tokens == given_tokens else 0.0
        shared_token_count = sum((Counter(expected_tokens) & Counter(given_tokens)).values())
        if shared_token_count == 0:
            return 0.0
        precision = shared_token_count / len(given_tokens)
        recall = shared_token_count / len(expected_tokens)
        return f_beta_score(precision, recall, float(self.parameter("beta")))
