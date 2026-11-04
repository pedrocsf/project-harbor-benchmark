from sacrebleu import sentence_chrf

from domain.scoring.scoring_method import ScoreKind, ScoringMethod

SACREBLEU_SCALE = 100.0
WORD_ORDER = 2


class ChrfScoringMethod(ScoringMethod):
    identifier = "chrf"
    display_name = "chrF++"
    column_header = "chrF++"
    score_kind = ScoreKind.CONTINUOUS

    def score(self, expected_answer: str, given_answer: str) -> float:
        if not given_answer.strip():
            return 0.0
        return sentence_chrf(given_answer, [expected_answer], word_order=WORD_ORDER).score / SACREBLEU_SCALE
