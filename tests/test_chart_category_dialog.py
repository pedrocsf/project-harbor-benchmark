import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from domain.scoring.sample_requirements import MetricGroup
from presentation.views.chart_category_dialog import ChartCategoryDialog

REASON = "Needs retrieved contexts."


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


def build_dialog(available_groups):
    return ChartCategoryDialog(available_groups, lambda group: REASON)


def test_preselects_the_first_available_category(application):
    dialog = build_dialog((MetricGroup.RETRIEVAL, MetricGroup.GROUNDING))

    assert dialog.selected_group() is MetricGroup.RETRIEVAL


def test_unavailable_categories_are_disabled(application):
    dialog = build_dialog((MetricGroup.ANSWER,))

    buttons = dialog._buttons

    assert buttons[MetricGroup.ANSWER].isEnabled()
    assert not buttons[MetricGroup.RETRIEVAL].isEnabled()
    assert not buttons[MetricGroup.GROUNDING].isEnabled()


def test_changing_the_choice_changes_the_selected_category(application):
    dialog = build_dialog(tuple(MetricGroup))

    dialog._buttons[MetricGroup.GROUNDING].setChecked(True)

    assert dialog.selected_group() is MetricGroup.GROUNDING
