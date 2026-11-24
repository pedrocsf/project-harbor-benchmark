import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QPoint, QRect, QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QPushButton

from data.scoring.sacrebleu_statistics_provider import SacrebleuStatisticsProvider
from demo.demo_data import DEMO_ENTRIES
from domain.explanations.timeline import TimelinePosition
from domain.usecases.build_metric_walkthrough import BuildMetricWalkthrough, WalkthroughRequest
from main_demo import build_controllers, build_demo_methods, build_demo_text_encoder, build_metric_explorer
from presentation.views.animations import REDUCE_MOTION_VARIABLE
from presentation.views.main_window import EXPLORER_BUTTON_TEXT, MainWindow, MainWindowOptions
from presentation.views.metric_explorer.metric_explorer_window import (
    NEXT_STEP_TEXT,
    PREVIOUS_STEP_TEXT,
    MetricExplorerWindow,
)
from presentation.views.metric_explorer.scenes.scene_registry import build_scene_registry

PAINT_PROGRESSES = (0.0, 0.5, 1.0)
IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480


def open_explorer():
    text_encoder = build_demo_text_encoder()
    _, evaluation_controller = build_controllers(text_encoder)
    return build_metric_explorer(evaluation_controller, text_encoder)


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def motion(monkeypatch):
    monkeypatch.delenv(REDUCE_MOTION_VARIABLE, raising=False)


def labels_text(window):
    return [label.text() for label in window.findChildren(QLabel) if label.isVisibleTo(window)]


def buttons_text(widget):
    return [button.text() for button in widget.findChildren(QPushButton)]


def test_registry_has_a_scene_for_every_metric():
    registry = build_scene_registry()

    assert set(registry.identifiers) == {method.identifier for method in build_demo_methods()}


def test_window_lists_every_demo_metric(application, motion):
    window = open_explorer()

    texts = labels_text(window)

    assert isinstance(window, MetricExplorerWindow)
    for method in build_demo_methods():
        assert method.display_name in texts
    assert len([label for label in window.findChildren(QLabel) if label.objectName() == "explorerMetricName"]) == len(build_demo_methods())


def test_switching_metric_updates_title_and_steps(application, motion):
    window = open_explorer()
    registry = build_scene_registry()

    window.select_metric("rouge_l")

    texts = labels_text(window)
    assert "ROUGE-L" in [label.text() for label in window.findChildren(QLabel) if label.objectName() == "explorerMetricTitle"]
    for step in registry.scene_for("rouge_l").steps:
        assert step.title in texts
    assert registry.scene_for("rouge_l").limitation in texts


def test_timer_runs_only_while_the_window_is_visible(application, motion):
    window = open_explorer()

    assert not window.frame_timer.isActive()
    window.show()
    assert window.frame_timer.isActive()
    window.findChild(QPushButton, "explorerPlayButton").click()
    assert not window.frame_timer.isActive()
    window.findChild(QPushButton, "explorerPlayButton").click()
    window.hide()
    assert not window.frame_timer.isActive()


def test_reduce_motion_shows_step_buttons_and_no_timer(application, monkeypatch):
    monkeypatch.setenv(REDUCE_MOTION_VARIABLE, "1")
    window = open_explorer()
    window.show()

    texts = buttons_text(window)

    assert PREVIOUS_STEP_TEXT in texts
    assert NEXT_STEP_TEXT in texts
    assert window.findChild(QPushButton, "explorerPlayButton") is None
    assert not window.frame_timer.isActive()
    window.findChild(QPushButton, "explorerStepButton").click()
    window.hide()


def test_the_canvas_paints_into_an_image(application, motion):
    window = open_explorer()
    image = QImage(IMAGE_WIDTH, IMAGE_HEIGHT, QImage.Format.Format_ARGB32)
    painter = QPainter(image)

    window.canvas.paint_into(painter, QRectF(0, 0, IMAGE_WIDTH, IMAGE_HEIGHT))

    painter.end()


ANSWER_SCENE_IDENTIFIERS = tuple(
    identifier
    for identifier in build_scene_registry().identifiers
    if identifier in BuildMetricWalkthrough(SacrebleuStatisticsProvider()).supported_identifiers
)


@pytest.mark.parametrize("identifier", ANSWER_SCENE_IDENTIFIERS)
def test_every_scene_paints_every_step_for_every_example(application, identifier):
    scene = build_scene_registry().scene_for(identifier)
    use_case = BuildMetricWalkthrough(SacrebleuStatisticsProvider())
    assert scene.steps
    assert scene.formula
    assert scene.limitation
    for step in scene.steps:
        assert all(0 <= line < len(scene.formula) for line in step.formula_lines)
    for entry in DEMO_ENTRIES:
        walkthrough = use_case.execute(
            WalkthroughRequest(identifier, entry.expected_answer, entry.given_answer, entry.scores[identifier])
        )
        for step_index in range(len(scene.steps)):
            assert isinstance(scene.step_body(step_index, walkthrough), str)
            assert isinstance(scene.formula_result(step_index, walkthrough), str)
            for progress in PAINT_PROGRESSES:
                image = QImage(IMAGE_WIDTH, IMAGE_HEIGHT, QImage.Format.Format_ARGB32)
                painter = QPainter(image)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                scene.paint(painter, QRectF(0, 0, IMAGE_WIDTH, IMAGE_HEIGHT), walkthrough, TimelinePosition(step_index, progress, False))
                painter.end()


def test_normal_main_window_has_no_explorer_button(application):
    _, evaluation_controller = build_controllers()

    window = MainWindow(evaluation_controller)

    assert EXPLORER_BUTTON_TEXT not in buttons_text(window)


def test_demo_main_window_opens_the_explorer_on_the_selected_metric(application, motion):
    text_encoder = build_demo_text_encoder()
    _, evaluation_controller = build_controllers(text_encoder)
    created = []

    def factory():
        explorer = build_metric_explorer(evaluation_controller, text_encoder)
        created.append(explorer)
        return explorer

    window = MainWindow(evaluation_controller, MainWindowOptions(metric_explorer_factory=factory))
    button = next(button for button in window.findChildren(QPushButton) if button.text() == EXPLORER_BUTTON_TEXT)
    combo = window.findChild(QComboBox)
    combo.setCurrentIndex(combo.findData("bleu"))

    button.click()
    button.click()

    assert len(created) == 1
    assert created[0].isVisible()
    titles = [label.text() for label in created[0].findChildren(QLabel) if label.objectName() == "explorerMetricTitle"]
    assert titles == ["BLEU"]
    created[0].close()


def formula_lines(window):
    return [label.text() for label in window.findChildren(QLabel) if label.objectName() == "explorerFormulaLine"]


def test_changing_parameters_updates_the_formula_text(application, motion):
    text_encoder = build_demo_text_encoder()
    _, evaluation_controller = build_controllers(text_encoder)
    window = build_metric_explorer(evaluation_controller, text_encoder)
    window.select_metric("token_f1")
    assert any("F1 = 2·P·R" in line for line in formula_lines(window))

    evaluation_controller.update_method_parameters("token_f1", {"beta": 2.0})

    assert any("β = 2" in line for line in formula_lines(window))
    evaluation_controller.reset_method_parameters("token_f1")
    assert any("F1 = 2·P·R" in line for line in formula_lines(window))


def test_changing_normalization_updates_the_normalization_formula(application, motion):
    text_encoder = build_demo_text_encoder()
    _, evaluation_controller = build_controllers(text_encoder)
    window = build_metric_explorer(evaluation_controller, text_encoder)
    window.select_metric("exact_match")
    assert any("drop_articles" in line for line in formula_lines(window))

    evaluation_controller.update_method_parameters("exact_match", {"remove_articles": "none"})

    assert not any("drop_articles" in line for line in formula_lines(window))


LAYOUT_WINDOW_SIZES = ((980, 640), (1180, 760))
LONG_FORMULA_PARAMETERS = {
    "token_f1": {"beta": 2.0},
    "rouge_l": {"score_type": "precision"},
    "bleu": {"max_ngram_order": 6},
    "llm_judge": {"samples": 3},
}
LAYOUT_SHOTS_DIRECTORY = os.environ.get("EXPLORER_LAYOUT_SHOTS")


def open_with_long_formulas(width, height):
    text_encoder = build_demo_text_encoder()
    _, evaluation_controller = build_controllers(text_encoder)
    window = build_metric_explorer(evaluation_controller, text_encoder)
    for identifier, values in LONG_FORMULA_PARAMETERS.items():
        evaluation_controller.update_method_parameters(identifier, values)
    window.resize(width, height)
    window.show()
    return window


@pytest.fixture(autouse=False)
def still(monkeypatch):
    monkeypatch.setenv(REDUCE_MOTION_VARIABLE, "1")


def dispose(window):
    window.close()


def settle(window):
    QApplication.processEvents()
    QApplication.processEvents()


def inside_viewport(window, widget):
    scroll = window._side_scroll
    top_left = widget.mapTo(scroll.viewport(), QPoint(0, 0))
    return scroll.viewport().rect().contains(QRect(top_left, widget.size()))


@pytest.mark.parametrize("width,height", LAYOUT_WINDOW_SIZES)
@pytest.mark.parametrize("identifier", build_scene_registry().identifiers)
def test_active_step_and_formula_are_fully_visible(application, still, width, height, identifier):
    window = open_with_long_formulas(width, height)
    window.select_metric(identifier)
    controller = window._controller
    for step_index in range(controller.step_count):
        settle(window)
        row = window._step_rows[controller.current_position.step_index]
        assert row.body_label.height() >= row.body_label.heightForWidth(row.body_label.width())
        assert inside_viewport(window, row.body_label)
        assert inside_viewport(window, row.title_label)
        controller.next_step()
    for label in window._formula_labels:
        assert label.height() >= label.heightForWidth(label.width())
    dispose(window)


@pytest.mark.parametrize("identifier", build_scene_registry().identifiers)
def test_step_rows_follow_their_size_hint_after_switching_examples(application, still, identifier):
    window = open_with_long_formulas(*LAYOUT_WINDOW_SIZES[0])
    window.select_metric(identifier)
    controller = window._controller
    for example_index in range(len(controller.examples)):
        controller.select_example(example_index)
        controller.next_step()
        settle(window)
        for row in window._step_rows:
            assert row.height() <= row.sizeHint().height()
    dispose(window)


def test_layout_screenshots(application, still):
    if not LAYOUT_SHOTS_DIRECTORY:
        pytest.skip("screenshot directory not configured")
    os.makedirs(LAYOUT_SHOTS_DIRECTORY, exist_ok=True)
    window = open_with_long_formulas(*LAYOUT_WINDOW_SIZES[0])
    for identifier in LONG_FORMULA_PARAMETERS:
        window.select_metric(identifier)
        window._controller.next_step()
        window._controller.next_step()
        settle(window)
        window.grab().save(os.path.join(LAYOUT_SHOTS_DIRECTORY, f"{identifier}_step3.png"))
    dispose(window)


def test_explorer_is_a_parentless_window(application, motion):
    text_encoder = build_demo_text_encoder()
    _, evaluation_controller = build_controllers(text_encoder)
    window = build_metric_explorer(evaluation_controller, text_encoder)
    assert window.parentWidget() is None
    window.close()


def test_standalone_explorer_window_carries_theme_background(application, motion):
    from presentation.views.branding import BACKGROUND_COLOR

    assert BACKGROUND_COLOR in open_explorer().styleSheet()
