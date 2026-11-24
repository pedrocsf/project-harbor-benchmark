from collections import Counter

from domain.scoring.metric_parameters import ParameterChoice, ParameterKind, ParameterSpec
from domain.scoring.scoring_method import ScoreKind, ScoringMethod
from domain.scoring.text_normalization import word_tokens
from domain.scoring.token_f1_scoring_method import BETA_PARAMETER_SPEC, f_beta_score

SCORE_TYPE_F_MEASURE = "f_measure"
SCORE_TYPE_PRECISION = "precision"
SCORE_TYPE_RECALL = "recall"

ROUGE_PARAMETER_SPECS: tuple[ParameterSpec, ...] = (
    ParameterSpec(
        key="score_type",
        label="Score type",
        description=(
            "Precision is the share of the answer that overlaps the reference, recall is the "
            "share of the reference that is covered, and F-measure combines both."
        ),
        kind=ParameterKind.CHOICE,
        default=SCORE_TYPE_F_MEASURE,
        choices=(
            ParameterChoice(SCORE_TYPE_F_MEASURE, "F-measure"),
            ParameterChoice(SCORE_TYPE_PRECISION, "Precision"),
            ParameterChoice(SCORE_TYPE_RECALL, "Recall"),
        ),
    ),
    ParameterSpec(
        key="beta",
        label="Beta",
        description=(
            "Weight of recall relative to precision in the F-measure. "
            "Ignored unless the score type is F-measure."
        ),
        kind=ParameterKind.DECIMAL,
        default=BETA_PARAMETER_SPEC.default,
        minimum=BETA_PARAMETER_SPEC.minimum,
        maximum=BETA_PARAMETER_SPEC.maximum,
        step=BETA_PARAMETER_SPEC.step,
    ),
    ParameterSpec(
        key="lowercase",
        label="Lowercase",
        description="Convert text to lowercase before splitting it into words.",
        kind=ParameterKind.BOOLEAN,
        default=True,
    ),
)


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _f_measure(
    overlap: int, candidate_size: int, reference_size: int, beta: float = 1.0
) -> float:
    if overlap == 0:
        return 0.0
    return f_beta_score(overlap / candidate_size, overlap / reference_size, beta)


def _rouge_score(
    parameters: dict, overlap: int, candidate_size: int, reference_size: int
) -> float:
    score_type = parameters["score_type"]
    if score_type == SCORE_TYPE_PRECISION:
        return _ratio(overlap, candidate_size)
    if score_type == SCORE_TYPE_RECALL:
        return _ratio(overlap, reference_size)
    return _f_measure(overlap, candidate_size, reference_size, float(parameters["beta"]))


def _ngram_counts(tokens: list[str], order: int) -> Counter:
    return Counter(tuple(tokens[start : start + order]) for start in range(len(tokens) - order + 1))


def _longest_common_subsequence_length(first: list[str], second: list[str]) -> int:
    previous_row = [0] * (len(second) + 1)
    for first_token in first:
        current_row = [0]
        for column, second_token in enumerate(second, start=1):
            if first_token == second_token:
                current_row.append(previous_row[column - 1] + 1)
            else:
                current_row.append(max(previous_row[column], current_row[column - 1]))
        previous_row = current_row
    return previous_row[-1]


class RougeNScoringMethod(ScoringMethod):
    score_kind = ScoreKind.CONTINUOUS
    parameter_specs = ROUGE_PARAMETER_SPECS

    def __init__(self, order: int):
        self._order = order
        self.identifier = f"rouge_{order}"
        self.display_name = f"ROUGE-{order}"
        self.column_header = f"ROUGE-{order}"

    def score(self, expected_answer: str, given_answer: str) -> float:
        parameters = self.parameters
        lowercase = parameters["lowercase"]
        reference_ngrams = _ngram_counts(word_tokens(expected_answer, lowercase), self._order)
        candidate_ngrams = _ngram_counts(word_tokens(given_answer, lowercase), self._order)
        overlap = sum((reference_ngrams & candidate_ngrams).values())
        return _rouge_score(
            parameters, overlap, sum(candidate_ngrams.values()), sum(reference_ngrams.values())
        )


class RougeLScoringMethod(ScoringMethod):
    identifier = "rouge_l"
    display_name = "ROUGE-L"
    column_header = "ROUGE-L"
    score_kind = ScoreKind.CONTINUOUS
    parameter_specs = ROUGE_PARAMETER_SPECS

    def score(self, expected_answer: str, given_answer: str) -> float:
        parameters = self.parameters
        lowercase = parameters["lowercase"]
        reference_tokens = word_tokens(expected_answer, lowercase)
        candidate_tokens = word_tokens(given_answer, lowercase)
        overlap = _longest_common_subsequence_length(reference_tokens, candidate_tokens)
        return _rouge_score(parameters, overlap, len(candidate_tokens), len(reference_tokens))
