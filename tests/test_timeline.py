import pytest

from domain.explanations.timeline import TimelinePosition, position_at, step_start_seconds, total_cycle_seconds

DURATIONS = (1.0, 2.0, 4.0)
HOLD = 2.0


def test_cycle_lasts_every_step_plus_the_hold():
    assert total_cycle_seconds(DURATIONS, HOLD) == 9.0


def test_starts_at_the_beginning_of_the_first_step():
    assert position_at(0.0, DURATIONS, HOLD) == TimelinePosition(0, 0.0, False)


def test_reports_progress_inside_a_step():
    position = position_at(2.0, DURATIONS, HOLD)

    assert position.step_index == 1
    assert position.step_progress == pytest.approx(0.5)
    assert not position.is_holding


def test_a_step_boundary_belongs_to_the_next_step():
    assert position_at(1.0, DURATIONS, HOLD) == TimelinePosition(1, 0.0, False)
    assert position_at(3.0, DURATIONS, HOLD) == TimelinePosition(2, 0.0, False)


def test_holds_the_last_step_complete_after_it_ends():
    assert position_at(7.0, DURATIONS, HOLD) == TimelinePosition(2, 1.0, True)
    assert position_at(8.9, DURATIONS, HOLD) == TimelinePosition(2, 1.0, True)


def test_loops_back_to_the_start_after_the_hold():
    assert position_at(9.0, DURATIONS, HOLD) == TimelinePosition(0, 0.0, False)
    assert position_at(9.5 + 9.0 * 3, DURATIONS, HOLD).step_progress == pytest.approx(0.5)


def test_works_without_a_hold():
    assert position_at(7.0, DURATIONS, 0.0) == TimelinePosition(0, 0.0, False)


def test_step_start_seconds_sums_previous_steps():
    assert step_start_seconds(DURATIONS, 0) == 0.0
    assert step_start_seconds(DURATIONS, 2) == 3.0


@pytest.mark.parametrize("durations", [(), (1.0, 0.0), (1.0, -2.0)])
def test_rejects_invalid_durations(durations):
    with pytest.raises(ValueError):
        position_at(0.0, durations, HOLD)


def test_rejects_a_negative_hold_and_negative_time():
    with pytest.raises(ValueError):
        total_cycle_seconds(DURATIONS, -1.0)
    with pytest.raises(ValueError):
        position_at(-0.1, DURATIONS, HOLD)


def test_rejects_a_step_outside_the_timeline():
    with pytest.raises(ValueError):
        step_start_seconds(DURATIONS, 3)
