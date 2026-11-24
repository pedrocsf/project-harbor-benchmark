import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

COSINE = "cosine"
DOT_PRODUCT = "dot_product"
ANGULAR = "angular"
EUCLIDEAN = "euclidean"
MANHATTAN = "manhattan"
CLIP = "clip"
RESCALE = "rescale"
MINIMUM_SCORE = 0.0
MAXIMUM_SCORE = 1.0
RESCALE_OFFSET = 1.0
RESCALE_DIVISOR = 2.0
DISTANCE_OFFSET = 1.0
RADIANS_TO_DEGREES = 180.0 / math.pi


@dataclass(frozen=True)
class SimilarityOutcome:
    function: str
    raw_value: float
    cosine: float
    angle_degrees: float
    score: float
    was_clipped: bool


def euclidean_norm(vector: Sequence[float]) -> float:
    return math.sqrt(sum(value * value for value in vector))


def dot_product(first: Sequence[float], second: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(first, second))


def normalize(vector: Sequence[float]) -> tuple[float, ...]:
    norm = euclidean_norm(vector)
    if norm == 0:
        return tuple(vector)
    return tuple(value / norm for value in vector)


def cosine_similarity(first: Sequence[float], second: Sequence[float]) -> float:
    norm_product = euclidean_norm(first) * euclidean_norm(second)
    if norm_product == 0:
        return 0.0
    return max(-1.0, min(1.0, dot_product(first, second) / norm_product))


def _apply_negative_handling(value: float, negative_handling: str) -> float:
    if negative_handling == RESCALE:
        return (value + RESCALE_OFFSET) / RESCALE_DIVISOR
    return value


def _raw_and_score(
    function: str,
    first: Sequence[float],
    second: Sequence[float],
    cosine: float,
    angle_radians: float,
    negative_handling: str,
) -> tuple[float, float]:
    if function == COSINE:
        return cosine, _apply_negative_handling(cosine, negative_handling)
    if function == DOT_PRODUCT:
        product = dot_product(first, second)
        return product, _apply_negative_handling(product, negative_handling)
    if function == ANGULAR:
        value = 1.0 - angle_radians / math.pi
        return value, value
    differences = [a - b for a, b in zip(first, second)]
    if function == EUCLIDEAN:
        distance = euclidean_norm(differences)
    else:
        distance = sum(abs(value) for value in differences)
    return distance, DISTANCE_OFFSET / (DISTANCE_OFFSET + distance)


def measure_similarity(
    first: Sequence[float], second: Sequence[float], parameters: Mapping
) -> SimilarityOutcome:
    function = parameters.get("similarity_function", COSINE)
    negative_handling = parameters.get("negative_handling", CLIP)
    cosine = cosine_similarity(first, second)
    angle_radians = math.acos(cosine)
    angle_degrees = angle_radians * RADIANS_TO_DEGREES
    has_zero_vector = euclidean_norm(first) == 0 or euclidean_norm(second) == 0
    if has_zero_vector:
        return SimilarityOutcome(function, 0.0, 0.0, angle_degrees, MINIMUM_SCORE, False)
    if parameters.get("normalize_vectors", True) and function in (DOT_PRODUCT, EUCLIDEAN, MANHATTAN):
        first, second = normalize(first), normalize(second)
    raw_value, score = _raw_and_score(function, first, second, cosine, angle_radians, negative_handling)
    clamped = min(max(score, MINIMUM_SCORE), MAXIMUM_SCORE)
    return SimilarityOutcome(function, raw_value, cosine, angle_degrees, clamped, clamped != score)
