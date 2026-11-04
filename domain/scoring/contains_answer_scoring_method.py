from domain.scoring.scoring_method import ScoreKind, ScoringMethod
from domain.scoring.text_normalization import normalize_answer


class ContainsAnswerScoringMethod(ScoringMethod):
    identifier = "contains_answer"
    display_name = "Contains answer"
    column_header = "Contains"
    score_kind = ScoreKind.BINARY

    def score(self, expected_answer: str, given_answer: str) -> float:
        expected_text = normalize_answer(expected_answer)
        given_text = normalize_answer(given_answer)
        if not expected_text:
            return 1.0 if not given_text else 0.0
        return 1.0 if f" {expected_text} " in f" {given_text} " else 0.0
