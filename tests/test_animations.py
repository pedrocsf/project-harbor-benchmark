import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QFrame

from presentation.views.animations import (
    MAXIMUM_STAGGERED_ROWS,
    REDUCE_MOTION_VARIABLE,
    fade_in,
    motion_enabled,
    row_reveal_progress,
)


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


def test_row_reveal_starts_empty_and_ends_full_for_every_row():
    for row in (0, 5, MAXIMUM_STAGGERED_ROWS, 500):
        assert row_reveal_progress(0.0, row) == 0.0
        assert row_reveal_progress(1.0, row) == 1.0


def test_later_rows_start_filling_after_earlier_ones():
    assert row_reveal_progress(0.3, 0) > row_reveal_progress(0.3, 10)


def test_reduce_motion_variable_disables_motion(monkeypatch):
    monkeypatch.setenv(REDUCE_MOTION_VARIABLE, "1")

    assert not motion_enabled()


def test_motion_is_enabled_by_default(monkeypatch):
    monkeypatch.delenv(REDUCE_MOTION_VARIABLE, raising=False)

    assert motion_enabled()


def test_fade_in_leaves_no_effect_when_motion_is_reduced(application, monkeypatch):
    monkeypatch.setenv(REDUCE_MOTION_VARIABLE, "1")
    frame = QFrame()

    fade_in(frame)

    assert frame.graphicsEffect() is None


def test_fade_in_applies_a_temporary_effect(application, monkeypatch):
    monkeypatch.delenv(REDUCE_MOTION_VARIABLE, raising=False)
    frame = QFrame()

    fade_in(frame)

    assert frame.graphicsEffect() is not None
