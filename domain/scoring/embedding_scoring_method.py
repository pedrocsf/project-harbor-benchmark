from domain.gateways.text_encoder import TextEncoder
from domain.scoring.metric_parameters import ParameterChoice, ParameterKind, ParameterSpec
from domain.scoring.scoring_method import ScoreKind, ScoringMethod
from domain.scoring.vector_similarity import (
    ANGULAR,
    CLIP,
    COSINE,
    DOT_PRODUCT,
    EUCLIDEAN,
    MANHATTAN,
    RESCALE,
    SimilarityOutcome,
    measure_similarity,
)

MINIMUM_SIMILARITY = 0.0

SIMILARITY_FUNCTION_SPEC = ParameterSpec(
    key="similarity_function",
    label="Similarity function",
    description=(
        "How the two answer vectors are compared. Cosine and angular measure direction, "
        "dot product also reacts to vector length, and Euclidean and Manhattan turn a distance "
        "into a score in (0, 1]."
    ),
    kind=ParameterKind.CHOICE,
    default=COSINE,
    choices=(
        ParameterChoice(COSINE, "Cosine similarity (-1 to 1)"),
        ParameterChoice(DOT_PRODUCT, "Dot product (unbounded)"),
        ParameterChoice(ANGULAR, "Angular similarity (0 to 1)"),
        ParameterChoice(EUCLIDEAN, "Euclidean distance (1 / (1 + distance))"),
        ParameterChoice(MANHATTAN, "Manhattan distance (1 / (1 + distance))"),
    ),
)

NEGATIVE_HANDLING_SPEC = ParameterSpec(
    key="negative_handling",
    label="Negative values",
    description=(
        "Applies only to cosine and dot product, which can be negative. Clip sets negative "
        "values to 0, while rescale maps the range -1 to 1 onto 0 to 1."
    ),
    kind=ParameterKind.CHOICE,
    default=CLIP,
    choices=(
        ParameterChoice(CLIP, "Clip negatives to 0"),
        ParameterChoice(RESCALE, "Rescale (value + 1) / 2"),
    ),
)

NORMALIZE_VECTORS_SPEC = ParameterSpec(
    key="normalize_vectors",
    label="Normalize vectors",
    description=(
        "Scales each vector to unit length before dot product, Euclidean and Manhattan, so the "
        "result depends only on direction and stays comparable between answers."
    ),
    kind=ParameterKind.BOOLEAN,
    default=True,
)


class EmbeddingScoringMethod(ScoringMethod):
    identifier = "embedding"
    display_name = "Embedding similarity"
    column_header = "Similarity"
    score_kind = ScoreKind.CONTINUOUS
    parameter_specs = (SIMILARITY_FUNCTION_SPEC, NEGATIVE_HANDLING_SPEC, NORMALIZE_VECTORS_SPEC)

    def __init__(self, text_encoder: TextEncoder):
        self._text_encoder = text_encoder

    def prepare(self) -> None:
        self._text_encoder.prepare()

    def score(self, expected_answer: str, given_answer: str) -> float:
        outcome = self.similarity_outcome(expected_answer, given_answer)
        if outcome is None:
            return MINIMUM_SIMILARITY
        return outcome.score

    def similarity_outcome(self, expected_answer: str, given_answer: str) -> SimilarityOutcome | None:
        if not given_answer.strip():
            return None
        expected_vector, given_vector = self._text_encoder.encode([expected_answer, given_answer])
        return measure_similarity(expected_vector, given_vector, self.parameters)
