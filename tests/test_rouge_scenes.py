import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy
import pytest
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from data.scoring.sacrebleu_statistics_provider import SacrebleuStatisticsProvider
from demo.demo_data import DEMO_ENTRIES
from domain.explanations.timeline import TimelinePosition
from domain.usecases.build_metric_walkthrough import BuildMetricWalkthrough, WalkthroughRequest
from presentation.views.metric_explorer.scenes.rouge_l_scene import RougeLScene
from presentation.views.metric_explorer.scenes.rouge_n_scene import RougeNScene

PAINT_PROGRESSES = (0.0, 0.5, 1.0)
IMAGE_WIDTH = 580
IMAGE_HEIGHT = 540
BOUNDS_MARGIN = 40
BOUNDS_SIZES = ((580, 540), (420, 330), (360, 280))
ALPHA_CHANNEL = 3
ROUGE_IDENTIFIERS = ("rouge_1", "rouge_2", "rouge_l")
MONA_LISA_IDENTIFIER = "9"
PLANETS_IDENTIFIER = "2"
LONG_EXPECTED = " ".join(f"palavra{index}" for index in range(20))
LONG_ANSWER = " ".join(f"palavra{index}" for index in range(0, 36, 2))


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


def build_scene(identifier):
    if identifier == "rouge_l":
        return RougeLScene()
    return RougeNScene(int(identifier.removeprefix("rouge_")))


def walkthrough_for(identifier, expected_answer, given_answer):
    use_case = BuildMetricWalkthrough(SacrebleuStatisticsProvider())
    return use_case.execute(WalkthroughRequest(identifier, expected_answer, given_answer))


def demo_entry(identifier):
    return next(entry for entry in DEMO_ENTRIES if entry.identifier == identifier)


def demo_walkthrough(metric_identifier, entry_identifier):
    entry = demo_entry(entry_identifier)
    return walkthrough_for(metric_identifier, entry.expected_answer, entry.given_answer)


def paint_scene(scene, walkthrough, position, image, area):
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    scene.paint(painter, area, walkthrough, position)
    painter.end()


def transparent_image(width, height):
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    return image


def alpha_channel(image):
    pixels = numpy.frombuffer(image.constBits(), dtype=numpy.uint8, count=image.sizeInBytes())
    rows = pixels.reshape(image.height(), image.bytesPerLine() // 4, 4)
    return rows[:, : image.width(), ALPHA_CHANNEL]


def painted_outside(image, area):
    alpha = alpha_channel(image)
    inside = numpy.zeros(alpha.shape, dtype=bool)
    inside[int(area.top()) : int(area.bottom()), int(area.left()) : int(area.right())] = True
    return int(numpy.count_nonzero(alpha[~inside]))


@pytest.mark.parametrize("identifier", ROUGE_IDENTIFIERS)
def test_every_step_paints_for_every_demo_example(application, identifier):
    scene = build_scene(identifier)
    for entry in DEMO_ENTRIES:
        walkthrough = walkthrough_for(identifier, entry.expected_answer, entry.given_answer)
        for step_index in range(len(scene.steps)):
            assert scene.step_body(step_index, walkthrough)
            assert isinstance(scene.formula_result(step_index, walkthrough), str)
            for progress in PAINT_PROGRESSES:
                image = QImage(IMAGE_WIDTH, IMAGE_HEIGHT, QImage.Format.Format_ARGB32)
                paint_scene(scene, walkthrough, TimelinePosition(step_index, progress, False), image, QRectF(0, 0, IMAGE_WIDTH, IMAGE_HEIGHT))


def test_scene_identifiers_and_steps_follow_the_order():
    unigram, bigram = RougeNScene(1), RougeNScene(2)

    assert unigram.identifier == "rouge_1"
    assert bigram.identifier == "rouge_2"
    assert unigram.steps[0].title != bigram.steps[0].title
    assert unigram.limitation != bigram.limitation
    for scene in (unigram, bigram, RougeLScene()):
        for step in scene.steps:
            assert all(0 <= line < len(scene.formula) for line in step.formula_lines)


def test_rouge_1_texts_use_the_real_counts(application):
    scene = RougeNScene(1)
    walkthrough = demo_walkthrough("rouge_1", MONA_LISA_IDENTIFIER)

    ratios = scene.formula_result(2, walkthrough)

    assert "6 / 7" in ratios
    assert "6 / 9" in ratios
    assert "0.857" in ratios
    assert "0.667" in ratios
    assert "0.750" in scene.formula_result(3, walkthrough)
    assert "6 shared" in scene.step_body(1, walkthrough)
    assert "9 expected" in scene.step_body(0, walkthrough)


def test_rouge_2_texts_use_the_real_counts(application):
    scene = RougeNScene(2)
    walkthrough = demo_walkthrough("rouge_2", MONA_LISA_IDENTIFIER)

    assert scene.formula_result(1, walkthrough) == "overlap = 5"
    assert "5 / 6" in scene.formula_result(2, walkthrough)
    assert "5 / 8" in scene.formula_result(2, walkthrough)
    assert "0.714" in scene.formula_result(3, walkthrough)
    assert "8 expected" in scene.step_body(0, walkthrough)
    assert "6 in the answer" in scene.step_body(0, walkthrough)


def test_rouge_l_texts_use_the_real_lcs(application):
    scene = RougeLScene()
    walkthrough = demo_walkthrough("rouge_l", PLANETS_IDENTIFIER)

    assert scene.formula_result(2, walkthrough) == "LCS = 2"
    assert "2 shared words" in scene.step_body(2, walkthrough)
    assert "2 / 6" in scene.formula_result(3, walkthrough)
    assert "0.333" in scene.formula_result(4, walkthrough)


def bounds_cases():
    longest = sorted(DEMO_ENTRIES, key=lambda entry: len(entry.expected_answer) + len(entry.given_answer), reverse=True)[:3]
    edge_cases = [demo_entry(identifier) for identifier in ("7", "10", "11")]
    pairs = [(entry.expected_answer, entry.given_answer) for entry in longest + edge_cases]
    return pairs + [(LONG_EXPECTED, LONG_ANSWER)]


@pytest.mark.parametrize("identifier", ROUGE_IDENTIFIERS)
def test_scenes_never_paint_outside_their_area(application, identifier):
    scene = build_scene(identifier)
    for expected_answer, given_answer in bounds_cases():
        walkthrough = walkthrough_for(identifier, expected_answer, given_answer)
        for width, height in BOUNDS_SIZES:
            area = QRectF(BOUNDS_MARGIN, BOUNDS_MARGIN, width, height)
            for step_index in range(len(scene.steps)):
                for progress in PAINT_PROGRESSES:
                    image = transparent_image(width + 2 * BOUNDS_MARGIN, height + 2 * BOUNDS_MARGIN)
                    paint_scene(scene, walkthrough, TimelinePosition(step_index, progress, False), image, area)
                    assert painted_outside(image, area) == 0, (identifier, given_answer, width, step_index, progress)


def test_rouge_l_paints_something_for_a_truncated_matrix(application):
    scene = RougeLScene()
    walkthrough = walkthrough_for("rouge_l", LONG_EXPECTED, LONG_ANSWER)
    image = transparent_image(IMAGE_WIDTH, IMAGE_HEIGHT)

    paint_scene(scene, walkthrough, TimelinePosition(4, 1.0, False), image, QRectF(0, 0, IMAGE_WIDTH, IMAGE_HEIGHT))

    assert numpy.count_nonzero(alpha_channel(image)) > 0


SCORE_TYPES = ("f_measure", "precision", "recall")
BETA_VALUES = (0.5, 1.0, 2.0)
SHOTS_DIRECTORY = "/tmp/claude-1000/-home-pedro-Github-project-harbor-benchmark/e999c6a2-7661-407e-93bb-d950dd05c31d/scratchpad/shots/params/rouge"
SHOT_WIDTH = 760
SHOT_HEIGHT = 420


def parameter_grid():
    return [(score_type, beta, lowercase) for score_type in SCORE_TYPES for beta in BETA_VALUES for lowercase in (True, False)]


def parameterized_walkthrough(identifier, entry, score_type, beta, lowercase):
    parameters = {"score_type": score_type, "beta": beta, "lowercase": lowercase}
    use_case = BuildMetricWalkthrough(SacrebleuStatisticsProvider())
    request = WalkthroughRequest(identifier, entry.expected_answer, entry.given_answer, parameters=parameters)
    return use_case.execute(request)


@pytest.mark.parametrize("identifier", ROUGE_IDENTIFIERS)
def test_every_parameter_combination_paints_within_bounds(application, identifier):
    scene = build_scene(identifier)
    area = QRectF(BOUNDS_MARGIN, BOUNDS_MARGIN, IMAGE_WIDTH, IMAGE_HEIGHT)
    for score_type, beta, lowercase in parameter_grid():
        for entry in DEMO_ENTRIES:
            walkthrough = parameterized_walkthrough(identifier, entry, score_type, beta, lowercase)
            formula = scene.formula_for(walkthrough)
            for step_index in range(len(scene.steps)):
                assert scene.step_body(step_index, walkthrough)
                assert all(0 <= line < len(formula) for line in scene.formula_lines_for(step_index, walkthrough))
                for progress in PAINT_PROGRESSES:
                    image = transparent_image(IMAGE_WIDTH + 2 * BOUNDS_MARGIN, IMAGE_HEIGHT + 2 * BOUNDS_MARGIN)
                    paint_scene(scene, walkthrough, TimelinePosition(step_index, progress, False), image, area)
                    assert painted_outside(image, area) == 0


@pytest.mark.parametrize("identifier", ROUGE_IDENTIFIERS)
def test_formula_follows_score_type_and_beta(application, identifier):
    scene = build_scene(identifier)
    entry = demo_entry(MONA_LISA_IDENTIFIER)
    formulas = {
        (score_type, beta): scene.formula_for(parameterized_walkthrough(identifier, entry, score_type, beta, True))
        for score_type in SCORE_TYPES
        for beta in BETA_VALUES
    }

    assert len(formulas[("precision", 1.0)]) == len(formulas[("f_measure", 1.0)]) - 1
    assert formulas[("precision", 1.0)] == formulas[("recall", 2.0)]
    assert "2·P·R / (P + R)" in formulas[("f_measure", 1.0)][-1]
    assert "β = 2" in formulas[("f_measure", 2.0)][-1]
    assert "β = 0.5" in formulas[("f_measure", 0.5)][-1]
    assert formulas[("f_measure", 2.0)] != formulas[("f_measure", 0.5)]


@pytest.mark.parametrize("identifier", ROUGE_IDENTIFIERS)
def test_final_step_highlights_the_selected_line_and_value(application, identifier):
    scene = build_scene(identifier)
    entry = demo_entry(MONA_LISA_IDENTIFIER)
    final_step = len(scene.steps) - 1
    base_count = len(scene.formula) - 1
    precision = parameterized_walkthrough(identifier, entry, "precision", 1.0, True)
    recall = parameterized_walkthrough(identifier, entry, "recall", 1.0, True)
    weighted = parameterized_walkthrough(identifier, entry, "f_measure", 2.0, True)

    assert scene.formula_lines_for(final_step, precision) == (base_count - 2,)
    assert scene.formula_lines_for(final_step, recall) == (base_count - 1,)
    assert scene.formula_lines_for(final_step, weighted) == (base_count,)
    assert f"{precision.final_score:.3f}" in scene.formula_result(final_step, precision)
    assert f"{weighted.final_score:.3f}" in scene.formula_result(final_step, weighted)
    assert "Parameters" in scene.step_body(final_step, precision)


def test_lowercase_off_is_explained(application):
    scene = RougeNScene(1)
    entry = demo_entry(MONA_LISA_IDENTIFIER)

    lowered = scene.step_body(0, parameterized_walkthrough("rouge_1", entry, "f_measure", 1.0, True))
    kept = scene.step_body(0, parameterized_walkthrough("rouge_1", entry, "f_measure", 1.0, False))

    assert "lowercased" in lowered
    assert "Case is kept" in kept


def test_parameterized_screenshots_are_rendered(application):
    os.makedirs(SHOTS_DIRECTORY, exist_ok=True)
    entry = demo_entry(MONA_LISA_IDENTIFIER)
    cases = (("rouge_1", "precision", 1.0, True), ("rouge_2", "f_measure", 2.0, False), ("rouge_l", "recall", 0.5, True))
    for identifier, score_type, beta, lowercase in cases:
        scene = build_scene(identifier)
        walkthrough = parameterized_walkthrough(identifier, entry, score_type, beta, lowercase)
        image = QImage(SHOT_WIDTH, SHOT_HEIGHT, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.white)
        paint_scene(scene, walkthrough, TimelinePosition(len(scene.steps) - 1, 1.0, False), image, QRectF(0, 0, SHOT_WIDTH, SHOT_HEIGHT))
        assert image.save(f"{SHOTS_DIRECTORY}/{identifier}_{score_type}.png")
