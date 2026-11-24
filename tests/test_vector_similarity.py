import math

import pytest

from domain.scoring.vector_similarity import measure_similarity


def measure(first, second, **parameters):
    return measure_similarity(first, second, parameters)


def test_cosine_clips_negative_values():
    outcome = measure([1.0, 0.0], [-1.0, 0.0], similarity_function="cosine")

    assert outcome.raw_value == pytest.approx(-1.0)
    assert outcome.score == 0.0
    assert outcome.was_clipped


def test_cosine_rescale_maps_range_to_unit_interval():
    outcome = measure([1.0, 0.0], [-1.0, 0.0], similarity_function="cosine", negative_handling="rescale")

    assert outcome.score == 0.0
    assert measure([1.0, 0.0], [0.0, 1.0], negative_handling="rescale").score == pytest.approx(0.5)


def test_dot_product_of_normalized_vectors_equals_cosine():
    outcome = measure([3.0, 0.0], [1.0, 1.0], similarity_function="dot_product")

    assert outcome.score == pytest.approx(math.sqrt(0.5))


def test_dot_product_without_normalization_is_clamped():
    outcome = measure([3.0, 0.0], [2.0, 0.0], similarity_function="dot_product", normalize_vectors=False)

    assert outcome.raw_value == pytest.approx(6.0)
    assert outcome.score == 1.0
    assert outcome.was_clipped


def test_angular_similarity():
    assert measure([1.0, 0.0], [0.0, 1.0], similarity_function="angular").score == pytest.approx(0.5)
    assert measure([1.0, 0.0], [-1.0, 0.0], similarity_function="angular").score == pytest.approx(0.0)
    assert measure([1.0, 0.0], [2.0, 0.0], similarity_function="angular").score == pytest.approx(1.0)


def test_euclidean_similarity_uses_normalized_vectors():
    outcome = measure([5.0, 0.0], [0.0, 2.0], similarity_function="euclidean")

    assert outcome.raw_value == pytest.approx(math.sqrt(2))
    assert outcome.score == pytest.approx(1 / (1 + math.sqrt(2)))


def test_manhattan_similarity_without_normalization():
    outcome = measure([1.0, 1.0], [3.0, 0.0], similarity_function="manhattan", normalize_vectors=False)

    assert outcome.raw_value == pytest.approx(3.0)
    assert outcome.score == pytest.approx(0.25)


def test_identical_vectors_score_one_for_every_function():
    for function in ("cosine", "dot_product", "angular", "euclidean", "manhattan"):
        assert measure([1.0, 2.0], [1.0, 2.0], similarity_function=function).score == pytest.approx(1.0)


def test_zero_vector_scores_zero():
    for function in ("cosine", "dot_product", "angular", "euclidean", "manhattan"):
        assert measure([0.0, 0.0], [1.0, 2.0], similarity_function=function).score == 0.0


def test_clip_of_negative_cosine_marks_outcome_as_clipped():
    outcome = measure([1.0, 0.0], [-1.0, 1.0], similarity_function="cosine", negative_handling="clip")

    assert outcome.score == 0.0
    assert outcome.was_clipped


def test_non_negative_cosine_is_not_marked_as_clipped():
    assert not measure([1.0, 0.0], [1.0, 1.0], similarity_function="cosine").was_clipped
