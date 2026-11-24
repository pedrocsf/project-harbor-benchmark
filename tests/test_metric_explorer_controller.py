import pytest

from data.scoring.sacrebleu_statistics_provider import SacrebleuStatisticsProvider
from domain.explanations.timeline import TimelinePosition
from domain.usecases.build_metric_walkthrough import BuildMetricWalkthrough
from main_demo import build_demo_methods, build_demo_text_encoder, build_explorer_examples
from presentation.controllers.metric_explorer_controller import HOLD_SECONDS, MetricExplorerController

DURATIONS = (1.0, 2.0, 3.0)


@pytest.fixture(scope="module")
def use_case():
    return BuildMetricWalkthrough(SacrebleuStatisticsProvider(), text_encoder=build_demo_text_encoder())


def build_controller(use_case, motion_enabled=True):
    return MetricExplorerController(
        build_demo_methods(),
        build_explorer_examples(),
        use_case,
        lambda identifier: DURATIONS,
        motion_enabled,
    )


def test_lists_the_metrics_in_the_main_combo_order(use_case):
    controller = build_controller(use_case)

    assert [metric.identifier for metric in controller.metrics] == [method.identifier for method in build_demo_methods()]
    assert controller.selected_metric.identifier == "embedding"


def test_tick_advances_time_scaled_by_speed(use_case):
    controller = build_controller(use_case)
    controller.set_speed(2.0)

    controller.tick(0.75)

    assert controller.elapsed_seconds == pytest.approx(1.5)
    assert controller.current_position.step_index == 1
    assert controller.current_position.step_progress == pytest.approx(0.25)


def test_tick_loops_after_the_hold(use_case):
    controller = build_controller(use_case)

    controller.tick(sum(DURATIONS) + HOLD_SECONDS + 0.5)

    assert controller.current_position == TimelinePosition(0, 0.5, False)


def test_paused_controller_ignores_ticks(use_case):
    controller = build_controller(use_case)
    events = []
    controller.playback_changed.connect(lambda: events.append("playback"))

    controller.toggle_play()
    controller.tick(1.0)

    assert not controller.is_playing
    assert controller.elapsed_seconds == 0.0
    assert events == ["playback"]


def test_changing_metric_or_example_restarts_the_timeline(use_case):
    controller = build_controller(use_case)
    changed = []
    controller.metric_changed.connect(changed.append)
    controller.tick(2.0)

    controller.select_metric("token_f1")

    assert changed == ["token_f1"]
    assert controller.elapsed_seconds == 0.0
    controller.tick(2.0)
    controller.select_example(3)
    assert controller.elapsed_seconds == 0.0
    assert controller.selected_example_index == 3


def test_restart_goes_back_to_the_first_step(use_case):
    controller = build_controller(use_case)
    controller.tick(4.0)

    controller.restart()

    assert controller.current_position == TimelinePosition(0, 0.0, False)


def test_current_walkthrough_follows_the_selection(use_case):
    controller = build_controller(use_case)
    controller.select_metric("token_f1")

    walkthrough = controller.current_walkthrough

    assert walkthrough.identifier == "token_f1"
    assert walkthrough.expected_answer == controller.selected_example.expected_answer
    assert round(walkthrough.final_score, 3) == controller.selected_example.scores["token_f1"]


def test_next_and_previous_step_jump_between_steps(use_case):
    controller = build_controller(use_case)

    controller.next_step()
    assert controller.current_position.step_index == 1
    controller.next_step()
    controller.next_step()
    assert controller.current_position.step_index == 0
    controller.previous_step()
    assert controller.current_position.step_index == 2


def test_reduce_motion_shows_each_step_complete_and_never_plays(use_case):
    controller = build_controller(use_case, motion_enabled=False)

    assert not controller.is_playing
    controller.toggle_play()
    controller.tick(5.0)
    assert controller.current_position == TimelinePosition(0, 1.0, False)
    controller.next_step()
    assert controller.current_position == TimelinePosition(1, 1.0, False)
    controller.previous_step()
    controller.previous_step()
    assert controller.current_position == TimelinePosition(2, 1.0, False)


def test_rejects_unknown_choices(use_case):
    controller = build_controller(use_case)

    with pytest.raises(ValueError):
        controller.select_metric("meteor")
    with pytest.raises(ValueError):
        controller.select_example(99)
    with pytest.raises(ValueError):
        controller.set_speed(3.0)


def test_refresh_parameters_rebuilds_the_selected_walkthrough_with_the_live_parameters(use_case):
    methods = build_demo_methods()
    controller = MetricExplorerController(
        methods, build_explorer_examples(), use_case, lambda identifier: DURATIONS, False
    )
    controller.select_metric("rouge_1")
    refreshed = []
    controller.parameters_refreshed.connect(lambda: refreshed.append(True))
    before = controller.current_walkthrough

    next(method for method in methods if method.identifier == "rouge_1").update_parameters({"score_type": "recall"})
    controller.refresh_parameters("rouge_1")

    assert refreshed == [True]
    assert controller.current_walkthrough is not before


def test_refresh_parameters_ignores_other_metrics(use_case):
    controller = build_controller(use_case)
    refreshed = []
    controller.parameters_refreshed.connect(lambda: refreshed.append(True))

    controller.refresh_parameters("exact_match")
    controller.refresh_parameters("unknown")

    assert refreshed == []
