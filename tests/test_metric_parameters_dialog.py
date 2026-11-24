import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QLocale, Qt
from PySide6.QtWidgets import QApplication, QCheckBox, QDoubleSpinBox, QLabel, QPlainTextEdit, QPushButton, QSpinBox

from domain.entities.language_model_settings import LanguageModelSettings
from domain.scoring.metric_parameters import ParameterChoice, ParameterKind, ParameterSpec
from domain.scoring.scoring_method import ScoreKind, ScoringMethod
from presentation.views.metric_parameters_dialog import MetricParametersDialog
from presentation.views.themed_combo_box import ThemedComboBox

SPECS = (
    ParameterSpec("flag", "Flag", "A flag.", ParameterKind.BOOLEAN, True),
    ParameterSpec("count", "Count", "A count.", ParameterKind.INTEGER, 3, minimum=1, maximum=9),
    ParameterSpec("ratio", "Ratio", "A ratio.", ParameterKind.DECIMAL, 0.5, minimum=0.0, maximum=1.0, step=0.1, decimals=1),
    ParameterSpec(
        "mode", "Mode", "A mode.", ParameterKind.CHOICE, "a",
        choices=(ParameterChoice("a", "Alpha"), ParameterChoice("b", "Beta")),
    ),
    ParameterSpec("note", "Note", "A note.", ParameterKind.TEXT, "hi"),
)


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


def build_dialog(values=None):
    return MetricParametersDialog("Demo", SPECS, values or {})


def test_title_uses_the_metric_name(application):
    assert build_dialog().windowTitle() == "Demo parameters"


def test_each_kind_maps_to_its_widget(application):
    dialog = build_dialog()
    assert dialog.findChildren(QCheckBox)
    assert dialog.findChildren(QSpinBox)
    assert dialog.findChildren(QDoubleSpinBox)
    assert dialog.findChildren(ThemedComboBox)
    assert dialog.findChildren(QPlainTextEdit)


def test_values_start_from_the_current_values(application):
    dialog = build_dialog({"flag": False, "count": 7, "ratio": 0.2, "mode": "b", "note": "x"})
    assert dialog.values() == {"flag": False, "count": 7, "ratio": 0.2, "mode": "b", "note": "x"}


def test_restore_defaults_fills_widgets_without_applying(application):
    dialog = build_dialog({"flag": False, "count": 7, "ratio": 0.2, "mode": "b", "note": "x"})
    applied = []
    dialog.applied.connect(applied.append)

    dialog.restore_defaults()

    assert dialog.values() == {"flag": True, "count": 3, "ratio": 0.5, "mode": "a", "note": "hi"}
    assert applied == []


def test_apply_emits_the_values(application):
    dialog = build_dialog()
    applied = []
    dialog.applied.connect(applied.append)

    dialog.apply()

    assert applied == [dialog.values()]


def test_shows_and_clears_the_error(application):
    dialog = build_dialog()
    dialog.show_error("bad")
    assert dialog._error_label.text() == "bad" and not dialog._error_label.isHidden()
    dialog.clear_error()
    assert dialog._error_label.isHidden()


def test_has_the_three_buttons(application):
    dialog = build_dialog()
    texts = {button.text() for button in dialog.findChildren(QPushButton)}
    assert texts == {"Restore defaults", "Cancel", "Apply"}


def test_numeric_widgets_use_a_dot_decimal_separator(application):
    dialog = build_dialog()
    for editor in dialog.findChildren(QDoubleSpinBox) + dialog.findChildren(QSpinBox):
        assert editor.locale().decimalPoint() == "."
        assert editor.locale().numberOptions() & QLocale.NumberOption.OmitGroupSeparator
    for editor in dialog.findChildren(QDoubleSpinBox):
        assert "," not in editor.text()


def test_boolean_rows_show_the_label_only_once(application):
    dialog = build_dialog()
    boolean_labels = [spec.label for spec in SPECS if spec.kind is ParameterKind.BOOLEAN]
    shown = [label.text() for label in dialog.findChildren(QLabel) if label.objectName() == "parameterLabel"]
    assert boolean_labels
    for text in boolean_labels:
        assert text not in shown
        assert any(box.text() == text for box in dialog.findChildren(QCheckBox))


def test_spinbox_text_has_horizontal_margins(application):
    dialog = build_dialog()
    for editor in dialog.findChildren(QDoubleSpinBox) + dialog.findChildren(QSpinBox):
        assert editor.lineEdit().textMargins().left() > 0


def test_dialog_is_a_parentless_application_modal_window(application):
    dialog = build_dialog()
    assert dialog.parentWidget() is None
    assert dialog.windowModality() == Qt.WindowModality.ApplicationModal
