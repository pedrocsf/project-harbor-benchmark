import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from data.scoring.sacrebleu_statistics_provider import SacrebleuStatisticsProvider
from demo.demo_data import DEMO_ENTRIES
from domain.explanations.timeline import TimelinePosition
from domain.usecases.build_metric_walkthrough import BuildMetricWalkthrough, WalkthroughRequest
from presentation.views.metric_explorer.scenes.contains_answer_scene import ContainsAnswerScene, build_contains_answer_layout
from presentation.views.metric_explorer.scenes.exact_match_scene import ExactMatchScene, build_exact_match_layout
from presentation.views.metric_explorer.scenes.token_f1_scene import TokenF1Scene, build_token_f1_layout
from presentation.views.metric_explorer.scenes.token_recall_scene import TokenRecallScene, build_token_recall_layout

PAINT_PROGRESSES = (0.0, 0.5, 1.0)
STAGE_SIZES = ((532.0, 492.0), (360.0, 376.0))
MARGIN = 40
LONGEST_EXAMPLES = ("3", "4", "5", "8", "11", "12")
SCENE_TYPES = (ExactMatchScene, TokenF1Scene, TokenRecallScene, ContainsAnswerScene)
Q2_IDENTIFIER = "2"


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


def walkthrough_for(identifier, entry):
    use_case = BuildMetricWalkthrough(SacrebleuStatisticsProvider())
    return use_case.execute(WalkthroughRequest(identifier, entry.expected_answer, entry.given_answer, entry.scores[identifier]))


def entry_by_identifier(identifier):
    return next(entry for entry in DEMO_ENTRIES if entry.identifier == identifier)


def paint_with_margin(scene, walkthrough, position, width, height):
    image = QImage(int(width) + 2 * MARGIN, int(height) + 2 * MARGIN, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scene.paint(painter, QRectF(MARGIN, MARGIN, width, height), walkthrough, position)
    painter.end()
    return image


def pixels_outside_area(image, width, height):
    left, top, right, bottom = MARGIN, MARGIN, MARGIN + int(width), MARGIN + int(height)
    count = 0
    for y in range(0, image.height(), 2):
        for x in range(0, image.width(), 2):
            if left <= x < right and top <= y < bottom:
                continue
            if image.pixelColor(x, y).alpha() > 0:
                count += 1
    return count


@pytest.mark.parametrize("scene_type", SCENE_TYPES)
@pytest.mark.parametrize("stage_size", STAGE_SIZES)
def test_every_example_step_and_progress_paints(application, scene_type, stage_size):
    scene = scene_type()
    width, height = stage_size
    for entry in DEMO_ENTRIES:
        walkthrough = walkthrough_for(scene.identifier, entry)
        for step_index in range(len(scene.steps)):
            assert scene.step_body(step_index, walkthrough)
            assert isinstance(scene.formula_result(step_index, walkthrough), str)
            for progress in PAINT_PROGRESSES:
                image = QImage(int(width), int(height), QImage.Format.Format_ARGB32)
                painter = QPainter(image)
                scene.paint(painter, QRectF(0, 0, width, height), walkthrough, TimelinePosition(step_index, progress, False))
                painter.end()


@pytest.mark.parametrize("scene_type", SCENE_TYPES)
def test_longest_examples_stay_inside_the_area(application, scene_type):
    scene = scene_type()
    width, height = STAGE_SIZES[0]
    for identifier in LONGEST_EXAMPLES:
        walkthrough = walkthrough_for(scene.identifier, entry_by_identifier(identifier))
        for step_index in range(len(scene.steps)):
            image = paint_with_margin(scene, walkthrough, TimelinePosition(step_index, 1.0, False), width, height)
            assert pixels_outside_area(image, width, height) == 0


def layout_bottom_and_limits(identifier, walkthrough, area):
    if identifier == "token_f1":
        layout = build_token_f1_layout(walkthrough, area)
        return [(layout.answer_caption.bottom(), layout.counters[0].top()), (layout.bars[-1].bottom(), area.bottom())]
    if identifier == "token_recall":
        layout = build_token_recall_layout(walkthrough, area)
        return [(layout.note_rect.bottom(), layout.counters[0].top()), (layout.bar.bottom(), area.bottom())]
    if identifier == "exact_match":
        layout = build_exact_match_layout(walkthrough, area)
        return [(layout.rows[-1].answer_rect.bottom(), layout.compare_caption.top()), (layout.verdict.score.bottom(), area.bottom())]
    layout = build_contains_answer_layout(walkthrough, area)
    return [(layout.note_rect.bottom(), layout.verdict.mark.top()), (layout.verdict.score.bottom(), area.bottom())]


@pytest.mark.parametrize("scene_type", SCENE_TYPES)
@pytest.mark.parametrize("stage_size", STAGE_SIZES)
def test_layouts_fit_without_overlapping(application, scene_type, stage_size):
    scene = scene_type()
    area = QRectF(0, 0, *stage_size)
    for entry in DEMO_ENTRIES:
        walkthrough = walkthrough_for(scene.identifier, entry)
        for content_bottom, limit in layout_bottom_and_limits(scene.identifier, walkthrough, area):
            assert content_bottom <= limit + 0.5, (entry.identifier, content_bottom, limit)


def test_token_f1_texts_use_the_real_numbers(application):
    scene = TokenF1Scene()
    walkthrough = walkthrough_for(scene.identifier, entry_by_identifier(Q2_IDENTIFIER))

    assert "4 tokens are shared" in scene.step_body(1, walkthrough)
    assert "4 of 6" in scene.step_body(2, walkthrough)
    assert "4 of 6" in scene.step_body(3, walkthrough)
    assert "0.667" in scene.step_body(4, walkthrough)
    assert "P = 4 / 6 = " in scene.formula_result(2, walkthrough)
    assert "R = 4 / 6 = " in scene.formula_result(3, walkthrough)
    assert "0.667" in scene.formula_result(4, walkthrough)
    assert scene.formula_result(0, walkthrough) == ""


def test_token_recall_texts_use_the_real_numbers(application):
    scene = TokenRecallScene()
    walkthrough = walkthrough_for(scene.identifier, entry_by_identifier(Q2_IDENTIFIER))

    assert "6 expected and 6 answer tokens" in scene.step_body(0, walkthrough)
    assert "4 of 6 are found" in scene.step_body(1, walkthrough)
    assert "4 of 6" in scene.step_body(2, walkthrough)
    assert "R = 4 / 6 = " in scene.formula_result(2, walkthrough)
    assert "0.667" in scene.formula_result(2, walkthrough)


def test_exact_match_texts_use_the_real_numbers(application):
    scene = ExactMatchScene()
    walkthrough = walkthrough_for(scene.identifier, entry_by_identifier(Q2_IDENTIFIER))

    assert "differ at character 1" in scene.step_body(1, walkthrough)
    assert "scores 0" in scene.step_body(2, walkthrough)
    assert "≠" in scene.formula_result(1, walkthrough)
    assert "EM = " in scene.formula_result(2, walkthrough)


def test_contains_answer_texts_use_the_real_numbers(application):
    scene = ContainsAnswerScene()
    walkthrough = walkthrough_for(scene.identifier, entry_by_identifier(Q2_IDENTIFIER))

    assert "6 expected and 6 answer tokens" in scene.step_body(0, walkthrough)
    assert "(6 tokens)" in scene.step_body(1, walkthrough)
    assert "1 position tried" in scene.step_body(1, walkthrough)
    assert "not found" in scene.formula_result(1, walkthrough)
    assert "scores 0" in scene.step_body(2, walkthrough)


def test_contains_answer_explains_a_shorter_answer(application):
    scene = ContainsAnswerScene()
    walkthrough = walkthrough_for(scene.identifier, entry_by_identifier("5"))

    layout = build_contains_answer_layout(walkthrough, QRectF(0, 0, *STAGE_SIZES[0]))

    assert "shorter than the expected text" in layout.note
    assert "fits in no position" in scene.step_body(1, walkthrough)


def test_contains_answer_finds_an_identical_answer(application):
    scene = ContainsAnswerScene()
    walkthrough = walkthrough_for(scene.identifier, entry_by_identifier("1"))

    assert "found at token 1" in scene.formula_result(1, walkthrough)


PARAMETER_GRID = (
    {"remove_articles": "none"},
    {"remove_articles": "portuguese"},
    {"strip_accents": True},
    {"lowercase": False},
    {"remove_punctuation": False},
    {"beta": 0.5},
    {"beta": 2.0},
    {"match_mode": "substring"},
    {"match_mode": "substring", "lowercase": False, "remove_articles": "none", "remove_punctuation": False},
)


def parameterized_walkthrough(identifier, entry, overrides):
    method_keys = {
        "exact_match": {"lowercase", "strip_accents", "remove_punctuation", "remove_articles"},
        "token_f1": {"lowercase", "strip_accents", "remove_punctuation", "remove_articles", "beta"},
        "token_recall": {"lowercase", "strip_accents", "remove_punctuation", "remove_articles"},
        "contains_answer": {"lowercase", "strip_accents", "remove_punctuation", "remove_articles", "match_mode"},
    }[identifier]
    parameters = {key: value for key, value in overrides.items() if key in method_keys}
    use_case = BuildMetricWalkthrough(SacrebleuStatisticsProvider())
    return use_case.execute(WalkthroughRequest(identifier, entry.expected_answer, entry.given_answer, entry.scores[identifier], parameters))


@pytest.mark.parametrize("scene_type", SCENE_TYPES)
@pytest.mark.parametrize("overrides", PARAMETER_GRID)
def test_parameter_combinations_paint_inside_the_area(application, scene_type, overrides):
    scene = scene_type()
    width, height = STAGE_SIZES[0]
    for entry in DEMO_ENTRIES:
        walkthrough = parameterized_walkthrough(scene.identifier, entry, overrides)
        assert scene.formula_for(walkthrough)
        assert scene.limitation_for(walkthrough)
        for step_index in range(len(scene.steps)):
            assert scene.step_body(step_index, walkthrough)
            for progress in PAINT_PROGRESSES:
                image = paint_with_margin(scene, walkthrough, TimelinePosition(step_index, progress, False), width, height)
                assert pixels_outside_area(image, width, height) == 0


def test_token_f1_formula_and_text_follow_beta(application):
    scene = TokenF1Scene()
    entry = entry_by_identifier(Q2_IDENTIFIER)
    classic = parameterized_walkthrough("token_f1", entry, {})
    weighted = parameterized_walkthrough("token_f1", entry, {"beta": 2.0})

    assert "F1 = 2·P·R" in scene.formula_for(classic)[-1]
    assert "β" in scene.formula_for(weighted)[-1]
    assert "β = 2" in scene.formula_for(weighted)[-1]
    assert "β = 2" in scene.step_body(4, weighted)
    assert len(scene.formula_for(classic)) == len(scene.formula_for(weighted))


def test_normalization_text_lists_active_and_skipped_options(application):
    scene = ExactMatchScene()
    entry = entry_by_identifier(Q2_IDENTIFIER)
    walkthrough = parameterized_walkthrough("exact_match", entry, {"remove_articles": "none", "strip_accents": True})

    body = scene.step_body(0, walkthrough)
    assert "strip accents" in body.split("Off:")[0]
    assert "drop articles" in body.split("Off:")[1]
    assert "Parameters…" in body
    assert "drop_articles" not in scene.formula_for(walkthrough)[0]
    assert "strip_accents" in scene.formula_for(walkthrough)[0]


def test_contains_answer_substring_mode_explains_the_character_match(application):
    scene = ContainsAnswerScene()
    entry = entry_by_identifier("1")
    walkthrough = parameterized_walkthrough("contains_answer", entry, {"match_mode": "substring"})

    assert "character" in scene.step_body(1, walkthrough)
    assert "substring" in scene.formula_for(walkthrough)[1]
    assert "found at character 1" in scene.formula_result(1, walkthrough)
