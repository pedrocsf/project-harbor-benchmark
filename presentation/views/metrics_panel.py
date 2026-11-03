from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from domain.entities.evaluation_metrics import EvaluationMetrics
from domain.entities.question_score import QuestionScore
from domain.scoring.scoring_method import ScoreKind, ScoringMethod

CARDS_PER_ROW = 6
CARD_SPACING = 12
CARD_PADDING = 14
CARD_INNER_SPACING = 6
EMPTY_VALUE = "—"
GENERIC_HEADER = "score"
SCORE_FORMAT = "{:.3f}"
PERCENTAGE_FORMAT = "{:.1%}"
SECONDS_FORMAT = "{:.2f} s"
LENGTH_FORMAT = "{:.0f} chars"

COMMON_CARD_KEYS = (
    "empty_answers",
    "average_response",
    "fastest_response",
    "slowest_response",
    "total_response",
    "average_length",
)


def _captions(header: str, score_kind: ScoreKind = ScoreKind.CONTINUOUS) -> dict[str, str]:
    average_caption = header if score_kind is ScoreKind.BINARY else f"Average {header}"
    return {
        "average": average_caption,
        "question_count": "Questions",
        "median": f"Median {header}",
        "highest": f"Highest {header}",
        "lowest": f"Lowest {header}",
        "corpus": f"Corpus {header}",
        "correct": "Correct",
        "incorrect": "Incorrect",
        "empty_answers": "Empty answers",
        "average_response": "Avg response time",
        "fastest_response": "Fastest response",
        "slowest_response": "Slowest response",
        "total_response": "Total LLM time",
        "average_length": "Avg answer length",
    }


def _card_order(score_kind: ScoreKind, has_corpus_score: bool) -> list[str]:
    if score_kind is ScoreKind.BINARY:
        return ["average", "question_count", "correct", "incorrect", *COMMON_CARD_KEYS]
    leading_keys = ["average", "question_count", "median", "highest", "lowest"]
    if has_corpus_score:
        leading_keys.append("corpus")
    return [*leading_keys, *COMMON_CARD_KEYS]


def _format_scored_entry(entry: QuestionScore) -> str:
    return f"{SCORE_FORMAT.format(entry.score)} (Q{entry.question.identifier})"


def _format_values(metrics: EvaluationMetrics, average_score: float, score_kind: ScoreKind) -> dict[str, str]:
    average_text = (
        PERCENTAGE_FORMAT.format(average_score)
        if score_kind is ScoreKind.BINARY
        else SCORE_FORMAT.format(average_score)
    )
    values = {
        "average": average_text,
        "question_count": str(metrics.question_count),
        "median": SCORE_FORMAT.format(metrics.median_score),
        "highest": _format_scored_entry(metrics.highest),
        "lowest": _format_scored_entry(metrics.lowest),
        "correct": f"{metrics.correct_count} ({PERCENTAGE_FORMAT.format(metrics.correct_count / metrics.question_count)})",
        "incorrect": str(metrics.question_count - metrics.correct_count),
        "empty_answers": str(metrics.empty_answer_count),
        "average_response": SECONDS_FORMAT.format(metrics.average_response_seconds),
        "fastest_response": SECONDS_FORMAT.format(metrics.fastest_response_seconds),
        "slowest_response": SECONDS_FORMAT.format(metrics.slowest_response_seconds),
        "total_response": SECONDS_FORMAT.format(metrics.total_response_seconds),
        "average_length": LENGTH_FORMAT.format(metrics.average_answer_length),
    }
    if metrics.corpus_score is not None:
        values["corpus"] = SCORE_FORMAT.format(metrics.corpus_score)
    return values


class MetricsPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._cards: dict[str, QFrame] = {}
        self._caption_labels: dict[str, QLabel] = {}
        self._value_labels: dict[str, QLabel] = {}
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(CARD_SPACING)
        for column in range(CARDS_PER_ROW):
            self._grid.setColumnStretch(column, 1)
        for key in _captions(GENERIC_HEADER):
            self._cards[key] = self._build_card(key)
        self.clear()

    def show_metrics(self, metrics: EvaluationMetrics, method: ScoringMethod, average_score: float) -> None:
        order = _card_order(method.score_kind, metrics.corpus_score is not None)
        self._arrange(order, _captions(method.column_header, method.score_kind))
        for key, text in _format_values(metrics, average_score, method.score_kind).items():
            self._value_labels[key].setText(text)

    def clear(self) -> None:
        self._arrange(_card_order(ScoreKind.CONTINUOUS, has_corpus_score=False), _captions(GENERIC_HEADER))
        for value_label in self._value_labels.values():
            value_label.setText(EMPTY_VALUE)

    def _arrange(self, order: list[str], captions: dict[str, str]) -> None:
        for card in self._cards.values():
            self._grid.removeWidget(card)
            card.hide()
        for index, key in enumerate(order):
            self._caption_labels[key].setText(captions[key])
            self._grid.addWidget(self._cards[key], index // CARDS_PER_ROW, index % CARDS_PER_ROW)
            self._cards[key].show()

    def _build_card(self, key: str) -> QFrame:
        caption_label = QLabel()
        caption_label.setObjectName("metricCaption")
        value_label = QLabel()
        value_label.setObjectName("metricValue")
        self._caption_labels[key] = caption_label
        self._value_labels[key] = value_label
        layout = QVBoxLayout()
        layout.setContentsMargins(CARD_PADDING, CARD_PADDING, CARD_PADDING, CARD_PADDING)
        layout.setSpacing(CARD_INNER_SPACING)
        layout.addWidget(caption_label)
        layout.addWidget(value_label)
        card = QFrame()
        card.setObjectName("metricCard")
        card.setProperty("primary", key == "average")
        card.setLayout(layout)
        return card
