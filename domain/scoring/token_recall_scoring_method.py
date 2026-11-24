from collections import Counter

from domain.scoring.scoring_method import ScoreKind, ScoringMethod
from domain.scoring.text_normalization import (
    NORMALIZATION_PARAMETER_SPECS,
    normalization_options_from,
    normalized_tokens,
)


class TokenRecallScoringMethod(ScoringMethod):
    identifier = "token_recall"
    display_name = "Token recall"
    column_header = "Recall"
    score_kind = ScoreKind.CONTINUOUS
    parameter_specs = NORMALIZATION_PARAMETER_SPECS

    def score(self, expected_answer: str, given_answer: str) -> float:
        options = normalization_options_from(self.parameters)
        expected_tokens = normalized_tokens(expected_answer, options)
        given_tokens = normalized_tokens(given_answer, options)
        if not expected_tokens:
            return 1.0 if not given_tokens else 0.0
        shared_token_count = sum((Counter(expected_tokens) & Counter(given_tokens)).values())
        return shared_token_count / len(expected_tokens)
