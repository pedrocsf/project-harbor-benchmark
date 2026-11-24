import pytest

from data.scoring.fastembed_text_encoder import WARM_UP_TEXT, FastEmbedTextEncoder
from domain.errors import ModelUnavailableError
from domain.gateways.text_encoder import TextEncoder
from domain.scoring.embedding_scoring_method import EmbeddingScoringMethod


class FakeTextEncoder(TextEncoder):
    def __init__(self, vectors):
        self._vectors = vectors
        self.prepared = False
        self.encoded = []

    def prepare(self):
        self.prepared = True

    def encode(self, texts):
        self.encoded.append(list(texts))
        return [tuple(self._vectors[text]) for text in texts]


def build_method(vectors):
    return EmbeddingScoringMethod(FakeTextEncoder(vectors))


def test_prepare_prepares_the_encoder():
    encoder = FakeTextEncoder({})

    EmbeddingScoringMethod(encoder).prepare()

    assert encoder.prepared


def test_encoder_reports_a_model_that_cannot_be_loaded(tmp_path, monkeypatch):
    def failing_model(**arguments):
        raise OSError("no cached model")

    monkeypatch.setattr("data.scoring.fastembed_text_encoder.TextEmbedding", failing_model)

    with pytest.raises(ModelUnavailableError, match="no cached model"):
        FastEmbedTextEncoder(tmp_path).prepare()


def test_encoder_encodes_the_warm_up_text(tmp_path, monkeypatch):
    class FakeModel:
        def __init__(self, **arguments):
            pass

        def embed(self, texts):
            assert texts == [WARM_UP_TEXT]
            return [[1.0, 2.0]]

    monkeypatch.setattr("data.scoring.fastembed_text_encoder.TextEmbedding", FakeModel)

    FastEmbedTextEncoder(tmp_path).prepare()


def test_identical_direction_scores_one():
    assert build_method({"a": [1.0, 0.0], "b": [2.0, 0.0]}).score("a", "b") == pytest.approx(1.0)


def test_orthogonal_vectors_score_zero():
    assert build_method({"a": [1.0, 0.0], "b": [0.0, 1.0]}).score("a", "b") == pytest.approx(0.0)


def test_opposite_vectors_are_clipped_to_zero():
    assert build_method({"a": [1.0, 0.0], "b": [-1.0, 0.0]}).score("a", "b") == 0.0


def test_rescale_maps_opposite_vectors_to_zero_and_orthogonal_to_half():
    method = build_method({"a": [1.0, 0.0], "b": [0.0, 1.0]})
    method.update_parameters({"negative_handling": "rescale"})

    assert method.score("a", "b") == pytest.approx(0.5)


def test_blank_answer_scores_zero_without_encoding():
    encoder = FakeTextEncoder({})
    method = EmbeddingScoringMethod(encoder)

    assert method.score("a", "   ") == 0.0
    assert method.similarity_outcome("a", "") is None
    assert encoder.encoded == []


def test_similarity_outcome_reports_function_and_angle():
    outcome = build_method({"a": [1.0, 0.0], "b": [0.0, 1.0]}).similarity_outcome("a", "b")

    assert outcome.function == "cosine"
    assert outcome.angle_degrees == pytest.approx(90.0)


def test_demo_vectors_reproduce_demo_embedding_scores():
    from pathlib import Path

    from demo.demo_data import DEMO_ENTRIES
    from demo.demo_text_encoder import DemoTextEncoder, load_demo_vectors

    path = Path(__file__).resolve().parent.parent / "demo" / "demo_embeddings.json"
    method = EmbeddingScoringMethod(DemoTextEncoder(load_demo_vectors(path)))

    for entry in DEMO_ENTRIES:
        assert method.score(entry.expected_answer, entry.given_answer) == pytest.approx(
            entry.scores["embedding"], abs=0.0005
        )
