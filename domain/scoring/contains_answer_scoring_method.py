from domain.scoring.metric_parameters import ParameterChoice, ParameterKind, ParameterSpec
from domain.scoring.scoring_method import ScoreKind, ScoringMethod
from domain.scoring.text_normalization import (
    NORMALIZATION_PARAMETER_SPECS,
    normalization_options_from,
    normalize_answer,
)

MATCH_MODE_WHOLE_WORDS = "whole_words"
MATCH_MODE_SUBSTRING = "substring"

MATCH_MODE_PARAMETER_SPEC = ParameterSpec(
    key="match_mode",
    label="Match mode",
    description=(
        "Whole words requires the expected answer to appear as complete words. "
        "Substring also accepts it inside longer words, so 'cat' matches 'category'."
    ),
    kind=ParameterKind.CHOICE,
    default=MATCH_MODE_WHOLE_WORDS,
    choices=(
        ParameterChoice(MATCH_MODE_WHOLE_WORDS, "Whole words"),
        ParameterChoice(MATCH_MODE_SUBSTRING, "Substring"),
    ),
)


class ContainsAnswerScoringMethod(ScoringMethod):
    identifier = "contains_answer"
    display_name = "Contains answer"
    column_header = "Contains"
    score_kind = ScoreKind.BINARY
    parameter_specs = NORMALIZATION_PARAMETER_SPECS + (MATCH_MODE_PARAMETER_SPEC,)

    def score(self, expected_answer: str, given_answer: str) -> float:
        options = normalization_options_from(self.parameters)
        expected_text = normalize_answer(expected_answer, options)
        given_text = normalize_answer(given_answer, options)
        if not expected_text:
            return 1.0 if not given_text else 0.0
        if self.parameter("match_mode") == MATCH_MODE_SUBSTRING:
            return 1.0 if expected_text in given_text else 0.0
        return 1.0 if f" {expected_text} " in f" {given_text} " else 0.0
