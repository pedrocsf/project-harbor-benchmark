import os
import zlib

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from data.scoring.sacrebleu_statistics_provider import SacrebleuStatisticsProvider
from demo.demo_data import DEMO_ENTRIES
from domain.explanations.timeline import TimelinePosition
from domain.usecases.build_metric_walkthrough import BuildMetricWalkthrough, WalkthroughRequest
from presentation.views.metric_explorer.scenes.embedding_scene import EmbeddingScene
from presentation.views.metric_explorer.scenes.llm_judge_scene import LlmJudgeScene, classify_prompt

PAINT_PROGRESSES = (0.0, 0.5, 1.0)
SCENES = (EmbeddingScene(), LlmJudgeScene())
SCENE_IDENTIFIERS = [scene.identifier for scene in SCENES]
CANVAS_SIZES = ((534, 496), (360, 280), (900, 700))
BOUNDS_MARGIN = 40
ALPHA_BYTE = 3


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def use_case():
    return BuildMetricWalkthrough(SacrebleuStatisticsProvider())


def entry(identifier):
    return next(item for item in DEMO_ENTRIES if item.identifier == identifier)


def build(use_case, scene, demo_entry):
    return use_case.execute(
        WalkthroughRequest(scene.identifier, demo_entry.expected_answer, demo_entry.given_answer, demo_entry.scores[scene.identifier])
    )


def paint(scene, walkthrough, position, image_size, area):
    image = QImage(*image_size, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scene.paint(painter, area, walkthrough, position)
    painter.end()
    return image


def alpha_channel(image):
    pixels = np.frombuffer(image.constBits(), dtype=np.uint8).reshape(image.height(), image.bytesPerLine())
    return pixels[:, : image.width() * 4].reshape(image.height(), image.width(), 4)[:, :, ALPHA_BYTE]


def has_ink_outside(image, area):
    alpha = alpha_channel(image).copy()
    alpha[int(area.top()) : int(area.bottom()), int(area.left()) : int(area.right())] = 0
    return bool(alpha.any())


@pytest.mark.parametrize("scene", SCENES, ids=SCENE_IDENTIFIERS)
def test_every_step_paints_for_every_example(application, use_case, scene):
    for demo_entry in DEMO_ENTRIES:
        walkthrough = build(use_case, scene, demo_entry)
        for step_index in range(len(scene.steps)):
            assert scene.step_body(step_index, walkthrough)
            assert isinstance(scene.formula_result(step_index, walkthrough), str)
            for progress in PAINT_PROGRESSES:
                for width, height in CANVAS_SIZES:
                    paint(scene, walkthrough, TimelinePosition(step_index, progress, False), (width, height), QRectF(0, 0, width, height))


@pytest.mark.parametrize("scene", SCENES, ids=SCENE_IDENTIFIERS)
def test_steps_point_at_existing_formula_lines(scene):
    for step in scene.steps:
        assert all(0 <= line < len(scene.formula) for line in step.formula_lines)


@pytest.mark.parametrize("scene", SCENES, ids=SCENE_IDENTIFIERS)
@pytest.mark.parametrize("identifier", ["2", "5", "11", "7"])
def test_nothing_is_painted_outside_the_area(application, use_case, scene, identifier):
    walkthrough = build(use_case, scene, entry(identifier))
    for width, height in ((360, 280), (534, 496)):
        area = QRectF(BOUNDS_MARGIN, BOUNDS_MARGIN, width, height)
        image_size = (width + BOUNDS_MARGIN * 2, height + BOUNDS_MARGIN * 2)
        for step_index in range(len(scene.steps)):
            for progress in PAINT_PROGRESSES:
                image = paint(scene, walkthrough, TimelinePosition(step_index, progress, False), image_size, area)
                assert not has_ink_outside(image, area), (step_index, progress, width, height)


def test_scenes_paint_something(application, use_case):
    for scene in SCENES:
        walkthrough = build(use_case, scene, entry("2"))
        image = paint(scene, walkthrough, TimelinePosition(len(scene.steps) - 1, 1.0, True), (534, 496), QRectF(0, 0, 534, 496))
        assert alpha_channel(image).any()


def test_embedding_texts_use_the_real_cosine(use_case):
    scene = EmbeddingScene()
    walkthrough = build(use_case, scene, entry("2"))

    assert "0.989" in scene.formula_result(2, walkthrough)
    assert "8.5°" in scene.formula_result(2, walkthrough)
    assert "0.989" in scene.step_body(2, walkthrough)
    assert "= 0.989" in scene.formula_result(3, walkthrough)


def test_embedding_texts_explain_the_empty_answer(use_case):
    scene = EmbeddingScene()
    walkthrough = build(use_case, scene, entry("11"))

    assert "empty" in scene.step_body(0, walkthrough).lower()
    assert "score = 0" in scene.formula_result(3, walkthrough)


def test_llm_judge_texts_use_the_real_rating(use_case):
    scene = LlmJudgeScene()
    walkthrough = build(use_case, scene, entry("5"))

    assert scene.formula_result(2, walkthrough) == "rating = 9"
    assert "9 / 10 = 0.9" in scene.formula_result(3, walkthrough)
    assert "9 / 10 = 0.9" in scene.step_body(3, walkthrough)


def test_llm_judge_texts_show_the_shortcut_for_an_empty_answer(use_case):
    scene = LlmJudgeScene()
    walkthrough = build(use_case, scene, entry("11"))

    assert "not called" in scene.step_body(1, walkthrough)
    assert "without calling the model" in scene.step_body(3, walkthrough)
    assert "no model call" in scene.formula_result(2, walkthrough)
    assert "score = 0" in scene.formula_result(3, walkthrough)


def test_the_prompt_marks_both_answers(use_case):
    walkthrough = build(use_case, LlmJudgeScene(), entry("5"))

    lines = classify_prompt(walkthrough.details.prompt_preview)

    assert [line.text for line in lines if line.kind.value == "reference"] == [entry("5").expected_answer]
    assert [line.text for line in lines if line.kind.value == "candidate"] == [entry("5").given_answer]


def test_the_prompt_shows_a_placeholder_for_an_empty_candidate(use_case):
    walkthrough = build(use_case, LlmJudgeScene(), entry("11"))

    candidates = [line for line in classify_prompt(walkthrough.details.prompt_preview) if line.kind.value == "candidate"]

    assert len(candidates) == 1
    assert candidates[0].is_placeholder


SIMILARITY_FUNCTIONS = ("cosine", "dot_product", "angular", "euclidean", "manhattan")
NEGATIVE_HANDLINGS = ("clip", "rescale")
RATING_SCALES = (4, 10, 100)
SAMPLE_COUNTS = (1, 3)
VECTOR_DIMENSIONS = 384
GRID_SIZE = (534, 496)
SCREENSHOT_SIZE = (760, 420)
SCREENSHOT_DIRECTORY = "/tmp/claude-1000/-home-pedro-Github-project-harbor-benchmark/e999c6a2-7661-407e-93bb-d950dd05c31d/scratchpad/shots/params/semantic"


class StubTextEncoder:
    def encode(self, texts):
        vectors = []
        for text in texts:
            generator = np.random.default_rng(zlib.crc32(text.split()[0].encode() if text.split() else b""))
            vectors.append(tuple(float(value) for value in generator.normal(size=VECTOR_DIMENSIONS)))
        return vectors


def build_with(scene, demo_entry, parameters, text_encoder=None):
    builder = BuildMetricWalkthrough(SacrebleuStatisticsProvider(), text_encoder)
    return builder.execute(
        WalkthroughRequest(scene.identifier, demo_entry.expected_answer, demo_entry.given_answer, demo_entry.scores[scene.identifier], parameters)
    )


def embedding_grid():
    for function in SIMILARITY_FUNCTIONS:
        for handling in NEGATIVE_HANDLINGS:
            for normalize in (True, False):
                yield {"similarity_function": function, "negative_handling": handling, "normalize_vectors": normalize}


def judge_grid():
    for maximum in RATING_SCALES:
        for samples in SAMPLE_COUNTS:
            yield {"rating_scale_max": maximum, "samples": samples}


def paint_all_steps(scene, walkthrough):
    area = QRectF(BOUNDS_MARGIN, BOUNDS_MARGIN, *GRID_SIZE)
    image_size = (GRID_SIZE[0] + BOUNDS_MARGIN * 2, GRID_SIZE[1] + BOUNDS_MARGIN * 2)
    for step_index in range(len(scene.steps)):
        assert scene.step_body(step_index, walkthrough)
        assert isinstance(scene.formula_result(step_index, walkthrough), str)
        for line in scene.formula_lines_for(step_index, walkthrough):
            assert 0 <= line < len(scene.formula_for(walkthrough))
        for progress in PAINT_PROGRESSES:
            image = paint(scene, walkthrough, TimelinePosition(step_index, progress, False), image_size, area)
            assert not has_ink_outside(image, area), (step_index, progress)


@pytest.mark.parametrize("with_encoder", [False, True])
def test_embedding_scene_paints_every_parameter_combination(application, with_encoder):
    scene = EmbeddingScene()
    encoder = StubTextEncoder() if with_encoder else None
    for parameters in embedding_grid():
        for demo_entry in DEMO_ENTRIES:
            paint_all_steps(scene, build_with(scene, demo_entry, parameters, encoder))


def test_llm_judge_scene_paints_every_parameter_combination(application):
    scene = LlmJudgeScene()
    for parameters in judge_grid():
        for demo_entry in DEMO_ENTRIES:
            paint_all_steps(scene, build_with(scene, demo_entry, parameters))


def test_embedding_formula_follows_the_parameters(application):
    scene = EmbeddingScene()
    formulas = set()
    for parameters in embedding_grid():
        walkthrough = build_with(scene, entry("2"), parameters, StubTextEncoder())
        formulas.add(scene.formula_for(walkthrough))
        assert len(scene.formula_for(walkthrough)) == len(scene.formula)
    assert len(formulas) > len(SIMILARITY_FUNCTIONS)
    rescale = build_with(scene, entry("2"), {"similarity_function": "cosine", "negative_handling": "rescale"}, StubTextEncoder())
    assert "+ 1) / 2" in scene.formula_for(rescale)[1]
    assert "Parameters" in scene.limitation_for(rescale)


def test_embedding_texts_use_the_real_raw_value(application):
    scene = EmbeddingScene()
    walkthrough = build_with(scene, entry("2"), {"similarity_function": "euclidean"}, StubTextEncoder())
    raw = f"{walkthrough.details.raw_value:.3f}"
    assert raw in scene.step_body(2, walkthrough)
    assert f"1 / (1 + {raw})" in scene.formula_result(3, walkthrough)


def test_llm_judge_formula_and_texts_follow_the_scale(application):
    scene = LlmJudgeScene()
    walkthrough = build_with(scene, entry("5"), {"rating_scale_max": 100, "samples": 3})
    assert "0…100" in scene.formula_for(walkthrough)[0]
    assert "/ 100" in scene.formula_for(walkthrough)[1] or "100" in scene.formula_for(walkthrough)[1]
    assert "3" in scene.formula_for(walkthrough)[1]
    assert "/ 100 =" in scene.formula_result(3, walkthrough)
    assert "averaged" in scene.step_body(3, walkthrough)
    assert scene.formula_for(walkthrough) != scene.formula_for(build_with(scene, entry("5"), {}))


def test_llm_judge_shortcut_highlights_the_shortcut_formula_line(application):
    scene = LlmJudgeScene()
    walkthrough = build_with(scene, entry("11"), {"rating_scale_max": 100, "samples": 3})
    lines = scene.formula_for(walkthrough)
    for step_index in (1, 2, 3):
        assert [lines[index] for index in scene.formula_lines_for(step_index, walkthrough)] == [lines[2]]
    assert "no model call" in lines[2]


def test_render_parameter_screenshots(application):
    os.makedirs(SCREENSHOT_DIRECTORY, exist_ok=True)
    embedding, judge = EmbeddingScene(), LlmJudgeScene()
    cases = (
        (embedding, {"similarity_function": "euclidean"}, 2),
        (embedding, {"similarity_function": "manhattan", "normalize_vectors": False}, 3),
        (embedding, {"similarity_function": "dot_product", "normalize_vectors": False, "negative_handling": "rescale"}, 2),
        (embedding, {"similarity_function": "angular"}, 3),
        (judge, {"rating_scale_max": 100, "samples": 3}, 3),
        (judge, {"rating_scale_max": 4}, 2),
    )
    for index, (scene, parameters, step_index) in enumerate(cases):
        walkthrough = build_with(scene, entry("5"), parameters, StubTextEncoder() if scene is embedding else None)
        image = paint(scene, walkthrough, TimelinePosition(step_index, 1.0, False), SCREENSHOT_SIZE, QRectF(0, 0, *SCREENSHOT_SIZE))
        background = QImage(*SCREENSHOT_SIZE, QImage.Format.Format_ARGB32)
        background.fill(QColor("#ffffff"))
        painter = QPainter(background)
        painter.drawImage(0, 0, image)
        painter.end()
        assert background.save(f"{SCREENSHOT_DIRECTORY}/{scene.identifier}_{index}.png")
