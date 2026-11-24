from domain.scoring.scoring_method import ScoreKind, ScoringMethod
from domain.scoring.text_normalization import (
    NORMALIZATION_PARAMETER_SPECS,
    normalization_options_from,
    normalize_answer,
)


class ExactMatchScoringMethod(ScoringMethod):
    identifier = "exact_match"
    display_name = "Exact match"
    column_header = "Exact match"
    score_kind = ScoreKind.BINARY
    parameter_specs = NORMALIZATION_PARAMETER_SPECS

    def score(self, expected_answer: str, given_answer: str) -> float:
        options = normalization_options_from(self.parameters)
        expected_text = normalize_answer(expected_answer, options)
        return 1.0 if expected_text == normalize_answer(given_answer, options) else 0.0
