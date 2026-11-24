import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QRect, QRectF
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from data.scoring.sacrebleu_statistics_provider import SacrebleuStatisticsProvider
from demo.demo_data import DEMO_ENTRIES
from domain.explanations.timeline import TimelinePosition
from domain.usecases.build_metric_walkthrough import BuildMetricWalkthrough, WalkthroughRequest
from presentation.views.metric_explorer.scenes.bleu_scene import BleuScene
from presentation.views.metric_explorer.scenes.chrf_scene import ChrfScene, balance_geometry
from presentation.views.metric_explorer.scenes.translation_scene_painting import (
    characters_without_spaces,
    chrf_words,
    clipped_match_flags,
)

PAINT_PROGRESSES = (0.0, 0.5, 1.0)
IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480
BOUNDS_MARGIN = 60
BOUNDS_AREAS = ((360.0, 376.0), (534.0, 496.0), (640.0, 480.0))
PLANETS_EXAMPLE = "2"
TOLERANCE = 0.001
NUMBER_PATTERN = re.compile(r"\d+\.\d+")
SCENES = (BleuScene, ChrfScene)
LONGEST_EXAMPLES = tuple(sorted(DEMO_ENTRIES, key=lambda entry: len(entry.given_answer), reverse=True)[:3])
SHORT_EXAMPLES = tuple(entry for entry in DEMO_ENTRIES if len(entry.given_answer) <= len("Seis."))


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


def walkthrough_for(identifier, entry):
    use_case = BuildMetricWalkthrough(SacrebleuStatisticsProvider())
    return use_case.execute(WalkthroughRequest(identifier, entry.expected_answer, entry.given_answer, entry.scores[identifier]))


def entry_named(identifier):
    return next(entry for entry in DEMO_ENTRIES if entry.identifier == identifier)


def numbers_in(text):
    return [float(match) for match in NUMBER_PATTERN.findall(text)]


def contains_number(text, expected):
    return any(abs(value - expected) <= TOLERANCE for value in numbers_in(text))


def paint_scene(scene, walkthrough, position, image_size, area):
    image = QImage(image_size[0], image_size[1], QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scene.paint(painter, area, walkthrough, position)
    painter.end()
    return image


def margin_bands(image, area):
    inner = area.toRect()
    return (
        QRect(0, 0, image.width(), inner.top()),
        QRect(0, inner.bottom() + 1, image.width(), image.height() - inner.bottom() - 1),
        QRect(0, inner.top(), inner.left(), inner.height()),
        QRect(inner.right() + 1, inner.top(), image.width() - inner.right() - 1, inner.height()),
    )


def band_is_painted(image, band):
    part = image.copy(band)
    return any(bytes(part.constBits()))


def painted_outside(image, area):
    return any(band_is_painted(image, band) for band in margin_bands(image, area))


@pytest.mark.parametrize("scene_class", SCENES)
@pytest.mark.parametrize("entry", DEMO_ENTRIES, ids=lambda entry: f"Q{entry.identifier}")
def test_scene_paints_every_step_and_progress(application, scene_class, entry):
    scene = scene_class()
    walkthrough = walkthrough_for(scene.identifier, entry)
    area = QRectF(0, 0, IMAGE_WIDTH, IMAGE_HEIGHT)
    for step_index in range(len(scene.steps)):
        assert scene.step_body(step_index, walkthrough)
        assert isinstance(scene.formula_result(step_index, walkthrough), str)
        for progress in PAINT_PROGRESSES:
            paint_scene(scene, walkthrough, TimelinePosition(step_index, progress, False), (IMAGE_WIDTH, IMAGE_HEIGHT), area)


@pytest.mark.parametrize("scene_class", SCENES)
def test_scene_steps_point_at_existing_formula_lines(scene_class):
    scene = scene_class()
    for step in scene.steps:
        assert step.duration_seconds > 0
        assert all(0 <= line < len(scene.formula) for line in step.formula_lines)


def test_bleu_texts_use_the_real_numbers(application):
    scene = BleuScene()
    walkthrough = walkthrough_for(scene.identifier, entry_named(PLANETS_EXAMPLE))
    precision_text = scene.step_body(0, walkthrough) + scene.formula_result(0, walkthrough)
    for expected in (0.714, 0.333, 0.100, 0.0625):
        assert contains_number(precision_text, expected)
    assert "5/7" in precision_text
    assert contains_number(scene.formula_result(1, walkthrough), 0.196)
    assert contains_number(scene.formula_result(2, walkthrough), 1.0)
    assert contains_number(scene.formula_result(3, walkthrough), 0.196)


def test_bleu_mentions_smoothing_and_effective_order(application):
    scene = BleuScene()
    planets = walkthrough_for(scene.identifier, entry_named(PLANETS_EXAMPLE))
    hexagon = walkthrough_for(scene.identifier, entry_named("7"))
    assert "smoothing" in scene.step_body(0, planets).lower()
    assert "only 2 orders" in scene.step_body(0, hexagon)
    assert "Corpus BLEU" in scene.step_body(3, planets)


def test_bleu_penalty_explains_short_answers(application):
    scene = BleuScene()
    walkthrough = walkthrough_for(scene.identifier, entry_named("3"))
    assert "c = 7 < r = 9" in scene.step_body(2, walkthrough)
    assert contains_number(scene.formula_result(2, walkthrough), walkthrough.details.brevity_penalty)


def test_chrf_texts_use_the_real_numbers(application):
    scene = ChrfScene()
    walkthrough = walkthrough_for(scene.identifier, entry_named(PLANETS_EXAMPLE))
    average_text = scene.step_body(2, walkthrough) + scene.formula_result(2, walkthrough)
    assert contains_number(average_text, 0.656)
    assert contains_number(average_text, 0.754)
    assert contains_number(scene.formula_result(3, walkthrough), 0.732)
    assert "0.732" in scene.step_body(3, walkthrough)
    assert contains_number(scene.formula_result(0, walkthrough), 0.824)


def test_chrf_empty_answer_explains_zero_averages(application):
    scene = ChrfScene()
    walkthrough = walkthrough_for(scene.identifier, entry_named("11"))
    assert "P = R = 0" in scene.step_body(2, walkthrough)


@pytest.mark.parametrize("entry", DEMO_ENTRIES, ids=lambda entry: f"Q{entry.identifier}")
def test_bleu_match_flags_agree_with_sacrebleu_counts(entry):
    details = SacrebleuStatisticsProvider().bleu_details(entry.given_answer, entry.expected_answer)
    for order in range(1, len(details.matches_by_order) + 1):
        flags = clipped_match_flags(details.answer_tokens, details.reference_tokens, order)
        assert sum(flags) == details.matches_by_order[order - 1]
        assert len(flags) == details.totals_by_order[order - 1]


@pytest.mark.parametrize("entry", DEMO_ENTRIES, ids=lambda entry: f"Q{entry.identifier}")
def test_chrf_match_flags_agree_with_sacrebleu_counts(entry):
    details = SacrebleuStatisticsProvider().chrf_details(entry.given_answer, entry.expected_answer)
    answer_characters = characters_without_spaces(entry.given_answer)
    reference_characters = characters_without_spaces(entry.expected_answer)
    for statistics in details.character_orders:
        assert sum(clipped_match_flags(answer_characters, reference_characters, statistics.order)) == statistics.match_count
    answer_words = chrf_words(entry.given_answer)
    reference_words = chrf_words(entry.expected_answer)
    for statistics in details.word_orders:
        assert sum(clipped_match_flags(answer_words, reference_words, statistics.order)) == statistics.match_count


@pytest.mark.parametrize("scene_class", SCENES)
@pytest.mark.parametrize("entry", LONGEST_EXAMPLES + SHORT_EXAMPLES, ids=lambda entry: f"Q{entry.identifier}")
@pytest.mark.parametrize("size", BOUNDS_AREAS, ids=lambda size: f"{size[0]:.0f}x{size[1]:.0f}")
def test_scene_never_paints_outside_its_area(application, scene_class, entry, size):
    scene = scene_class()
    walkthrough = walkthrough_for(scene.identifier, entry)
    area = QRectF(BOUNDS_MARGIN, BOUNDS_MARGIN, size[0], size[1])
    image_size = (int(size[0]) + 2 * BOUNDS_MARGIN, int(size[1]) + 2 * BOUNDS_MARGIN)
    for step_index in range(len(scene.steps)):
        for progress in PAINT_PROGRESSES:
            image = paint_scene(scene, walkthrough, TimelinePosition(step_index, progress, False), image_size, area)
            assert not painted_outside(image, area)


SCRATCH_SHOTS = os.environ.get("TRANSLATION_SHOTS_DIR")
BLEU_ORDERS = (1, 2, 4, 6)
BLEU_SMOOTHINGS = ("exp", "floor", "add-k", "none")
CHRF_CHARACTER_ORDERS = (1, 6, 10)
CHRF_WORD_ORDERS = (0, 2, 3)
CHRF_BETAS = (1, 3)
GRID_AREAS = ((760.0, 420.0), (640.0, 480.0))
GRID_PROGRESSES = (0.0, 0.4, 1.0)


def parameterized_walkthrough(identifier, entry, parameters):
    use_case = BuildMetricWalkthrough(SacrebleuStatisticsProvider())
    request = WalkthroughRequest(identifier, entry.expected_answer, entry.given_answer, None, parameters)
    return use_case.execute(request)


def paint_all_steps(scene, walkthrough, size):
    area = QRectF(BOUNDS_MARGIN, BOUNDS_MARGIN, size[0], size[1])
    image_size = (int(size[0]) + 2 * BOUNDS_MARGIN, int(size[1]) + 2 * BOUNDS_MARGIN)
    for step_index in range(len(scene.steps)):
        assert scene.step_body(step_index, walkthrough)
        assert isinstance(scene.formula_result(step_index, walkthrough), str)
        for progress in GRID_PROGRESSES:
            image = paint_scene(scene, walkthrough, TimelinePosition(step_index, progress, False), image_size, area)
            assert not painted_outside(image, area)


@pytest.mark.parametrize("order", BLEU_ORDERS)
@pytest.mark.parametrize("smoothing", BLEU_SMOOTHINGS)
@pytest.mark.parametrize("tokenize", ("13a", "char"))
def test_bleu_scene_paints_every_parameter_combination(application, order, smoothing, tokenize):
    scene = BleuScene()
    parameters = {"max_ngram_order": order, "smooth_method": smoothing, "tokenize": tokenize}
    for entry in DEMO_ENTRIES:
        walkthrough = parameterized_walkthrough("bleu", entry, parameters)
        for size in GRID_AREAS:
            paint_all_steps(scene, walkthrough, size)


@pytest.mark.parametrize("character_order", CHRF_CHARACTER_ORDERS)
@pytest.mark.parametrize("word_order", CHRF_WORD_ORDERS)
@pytest.mark.parametrize("beta", CHRF_BETAS)
def test_chrf_scene_paints_every_parameter_combination(application, character_order, word_order, beta):
    scene = ChrfScene()
    parameters = {"char_order": character_order, "word_order": word_order, "beta": beta, "whitespace": beta == 3, "lowercase": beta == 1}
    for entry in DEMO_ENTRIES:
        walkthrough = parameterized_walkthrough("chrf", entry, parameters)
        for size in GRID_AREAS:
            paint_all_steps(scene, walkthrough, size)


BALANCE_COMBINATIONS = ((10, 3), (10, 0), (6, 3), (4, 0), (6, 2), (1, 1))


@pytest.mark.parametrize("character_order,word_order", BALANCE_COMBINATIONS)
def test_chrf_balance_stays_inside_the_area(application, character_order, word_order):
    scene = ChrfScene()
    parameters = {"char_order": character_order, "word_order": word_order, "beta": 3}
    for entry in DEMO_ENTRIES:
        walkthrough = parameterized_walkthrough("chrf", entry, parameters)
        details = scene._details(walkthrough)
        for size in GRID_AREAS:
            area = QRectF(BOUNDS_MARGIN, BOUNDS_MARGIN, size[0], size[1])
            layout = scene._layout_for(walkthrough, details, area)
            geometry = balance_geometry(layout.balance_rect)
            assert layout.balance_rect.height() > 0
            assert area.adjusted(-0.01, -0.01, 0.01, 0.01).contains(geometry.bounds)
            paint_all_steps(scene, walkthrough, size)
            assert_balance_clear_of_bottom_edge(scene, walkthrough, area, layout.balance_rect)


def assert_balance_clear_of_bottom_edge(scene, walkthrough, area, balance_rect):
    image_size = (int(area.right()) + BOUNDS_MARGIN, int(area.bottom()) + BOUNDS_MARGIN)
    edge = QRect(int(balance_rect.left()), int(area.bottom()) - 2, int(balance_rect.width()), 2)
    for step_index in range(len(scene.steps)):
        for progress in GRID_PROGRESSES:
            image = paint_scene(scene, walkthrough, TimelinePosition(step_index, progress, False), image_size, area)
            assert not band_is_painted(image, edge)


def test_bleu_formula_and_texts_follow_the_parameters(application):
    scene = BleuScene()
    parameters = {"max_ngram_order": 3, "smooth_method": "floor", "floor_value": 0.2, "tokenize": "char", "lowercase": True}
    walkthrough = parameterized_walkthrough("bleu", entry_named(PLANETS_EXAMPLE), parameters)
    assert "1/3" in scene.formula_for(walkthrough)[1]
    assert "n = 1…3" in scene.formula_for(walkthrough)[0]
    body = scene.step_body(0, walkthrough)
    assert "character tokenizer" in body and "ignoring letter case" in body and "Parameters…" in body
    assert "character" in scene.limitation_for(walkthrough)


def test_bleu_without_smoothing_is_explained(application):
    scene = BleuScene()
    walkthrough = parameterized_walkthrough("bleu", entry_named(PLANETS_EXAMPLE), {"smooth_method": "none"})
    assert "Smoothing is off" in scene.step_body(0, walkthrough)
    assert "Smoothing is off" in scene.limitation_for(walkthrough)


def test_chrf_texts_follow_the_parameters(application):
    scene = ChrfScene()
    entry = entry_named(PLANETS_EXAMPLE)
    plain = parameterized_walkthrough("chrf", entry, {"char_order": 4, "word_order": 0, "beta": 1})
    assert "plain chrF" in scene.step_body(1, plain)
    assert "chrF++" not in " ".join(scene.formula_for(plain)) and "char 1–4" in scene.formula_for(plain)[0]
    assert "β = 1" in scene.formula_for(plain)[2]
    assert "equally" in scene.step_body(3, plain)
    plus = parameterized_walkthrough("chrf", entry, {"char_order": 3, "word_order": 3, "beta": 4, "whitespace": True, "eps_smoothing": True})
    assert "word 1–3" in scene.formula_for(plus)[0] and "β = 4" in scene.formula_for(plus)[2]
    assert "spaces kept" in scene.step_body(0, plus) and "Epsilon" in scene.step_body(2, plus)
    assert "chrF++" in scene.step_body(3, plus)


def test_translation_scene_screenshots(application):
    if not SCRATCH_SHOTS:
        pytest.skip("screenshot directory not set")
    os.makedirs(SCRATCH_SHOTS, exist_ok=True)
    cases = (
        ("bleu", {"max_ngram_order": 6, "smooth_method": "add-k", "add_k_value": 2, "lowercase": True}, "bleu_n6_addk"),
        ("bleu", {"max_ngram_order": 1, "smooth_method": "none"}, "bleu_n1"),
        ("bleu", {"max_ngram_order": 4, "tokenize": "char", "smooth_method": "floor"}, "bleu_char_floor"),
        ("chrf", {"char_order": 10, "word_order": 3, "beta": 3, "whitespace": True}, "chrf_c10_w3"),
        ("chrf", {"char_order": 4, "word_order": 0, "beta": 1}, "chrf_plain"),
    )
    for identifier, parameters, name in cases:
        scene = BleuScene() if identifier == "bleu" else ChrfScene()
        walkthrough = parameterized_walkthrough(identifier, entry_named(PLANETS_EXAMPLE), parameters)
        for step_index, progress in ((0, 1.0), (3, 1.0)):
            image = paint_scene(scene, walkthrough, TimelinePosition(step_index, progress, False), (760, 420), QRectF(0, 0, 760, 420))
            image.save(os.path.join(SCRATCH_SHOTS, f"{name}_step{step_index}.png"))
