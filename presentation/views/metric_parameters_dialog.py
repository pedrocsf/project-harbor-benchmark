from collections.abc import Callable, Sequence

from PySide6.QtCore import QLocale, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from domain.scoring.metric_parameters import ParameterKind, ParameterSpec, ParameterValue, ParameterValues
from presentation.views.themed_combo_box import ThemedComboBox

DIALOG_WIDTH = 460
DIALOG_MAX_HEIGHT = 640
DIALOG_MARGIN = 24
DIALOG_SPACING = 16
ROW_SPACING = 6
FOOTER_MARGIN = 16
FOOTER_SPACING = 10
TEXT_EDITOR_HEIGHT = 80
FALLBACK_MINIMUM = -1_000_000
FALLBACK_MAXIMUM = 1_000_000
FALLBACK_STEP = 1.0
TITLE_TEMPLATE = "{name} parameters"
RESTORE_TEXT = "Restore defaults"
CANCEL_TEXT = "Cancel"
APPLY_TEXT = "Apply"

ValueReader = Callable[[], ParameterValue]
ValueWriter = Callable[[ParameterValue], None]

SPINBOX_TEXT_MARGINS = (12, 0, 12, 0)


class MetricParametersDialog(QDialog):
    applied = Signal(object)

    def __init__(
        self,
        metric_name: str,
        specs: Sequence[ParameterSpec],
        current_values: ParameterValues,
    ):
        super().__init__()
        self.setObjectName("parametersDialog")
        self.setWindowTitle(TITLE_TEMPLATE.format(name=metric_name))
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumWidth(DIALOG_WIDTH)
        self._specs = tuple(specs)
        self._readers: dict[str, ValueReader] = {}
        self._writers: dict[str, ValueWriter] = {}
        self._error_label = self._build_error_label()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_scroll_area(), stretch=1)
        layout.addWidget(self._error_label)
        layout.addWidget(self._build_footer())
        self.setLayout(layout)
        self.set_values(current_values)
        self.setMaximumHeight(DIALOG_MAX_HEIGHT)

    def values(self) -> dict[str, ParameterValue]:
        return {key: read() for key, read in self._readers.items()}

    def set_values(self, values: ParameterValues) -> None:
        for spec in self._specs:
            self._writers[spec.key](values.get(spec.key, spec.default))

    def restore_defaults(self) -> None:
        self.set_values({spec.key: spec.default for spec in self._specs})
        self.clear_error()

    def show_error(self, message: str) -> None:
        self._error_label.setText(message)
        self._error_label.show()

    def clear_error(self) -> None:
        self._error_label.clear()
        self._error_label.hide()

    def apply(self) -> None:
        self.clear_error()
        self.applied.emit(self.values())

    def _build_error_label(self) -> QLabel:
        label = QLabel()
        label.setObjectName("parametersError")
        label.setWordWrap(True)
        label.hide()
        return label

    def _build_scroll_area(self) -> QScrollArea:
        content = QWidget()
        content.setObjectName("parametersContent")
        layout = QVBoxLayout()
        layout.setContentsMargins(DIALOG_MARGIN, DIALOG_MARGIN, DIALOG_MARGIN, DIALOG_MARGIN)
        layout.setSpacing(DIALOG_SPACING)
        for spec in self._specs:
            layout.addLayout(self._build_row(spec))
        layout.addStretch(1)
        content.setLayout(layout)
        scroll_area = QScrollArea()
        scroll_area.setObjectName("parametersScroll")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setWidget(content)
        return scroll_area

    def _build_row(self, spec: ParameterSpec) -> QVBoxLayout:
        editor = self._build_editor(spec)
        description = QLabel(spec.description)
        description.setObjectName("parameterHint")
        description.setWordWrap(True)
        row = QVBoxLayout()
        row.setSpacing(ROW_SPACING)
        if spec.kind is not ParameterKind.BOOLEAN:
            row.addWidget(self._build_title(spec))
        row.addWidget(editor)
        row.addWidget(description)
        return row

    def _build_title(self, spec: ParameterSpec) -> QLabel:
        title = QLabel(spec.label)
        title.setObjectName("parameterLabel")
        return title

    def _build_editor(self, spec: ParameterSpec) -> QWidget:
        builders = {
            ParameterKind.BOOLEAN: self._build_checkbox,
            ParameterKind.INTEGER: self._build_integer_editor,
            ParameterKind.DECIMAL: self._build_decimal_editor,
            ParameterKind.CHOICE: self._build_choice_editor,
            ParameterKind.TEXT: self._build_text_editor,
        }
        return builders[spec.kind](spec)

    def _build_checkbox(self, spec: ParameterSpec) -> QWidget:
        editor = QCheckBox(spec.label)
        editor.setObjectName("parameterCheckbox")
        self._register(spec, editor.isChecked, lambda value: editor.setChecked(bool(value)))
        return editor

    def _build_integer_editor(self, spec: ParameterSpec) -> QWidget:
        editor = QSpinBox()
        editor.setLocale(QLocale.c())
        editor.lineEdit().setTextMargins(*SPINBOX_TEXT_MARGINS)
        editor.setRange(
            int(FALLBACK_MINIMUM if spec.minimum is None else spec.minimum),
            int(FALLBACK_MAXIMUM if spec.maximum is None else spec.maximum),
        )
        editor.setSingleStep(int(spec.step or 1))
        self._register(spec, editor.value, lambda value: editor.setValue(int(value)))
        return editor

    def _build_decimal_editor(self, spec: ParameterSpec) -> QWidget:
        editor = QDoubleSpinBox()
        editor.setLocale(QLocale.c())
        editor.lineEdit().setTextMargins(*SPINBOX_TEXT_MARGINS)
        editor.setDecimals(spec.decimals)
        editor.setRange(
            float(FALLBACK_MINIMUM if spec.minimum is None else spec.minimum),
            float(FALLBACK_MAXIMUM if spec.maximum is None else spec.maximum),
        )
        editor.setSingleStep(spec.step or FALLBACK_STEP)
        self._register(spec, editor.value, lambda value: editor.setValue(float(value)))
        return editor

    def _build_choice_editor(self, spec: ParameterSpec) -> QWidget:
        editor = ThemedComboBox()
        for choice in spec.choices:
            editor.addItem(choice.label, choice.value)
        self._register(
            spec,
            editor.currentData,
            lambda value: editor.setCurrentIndex(max(editor.findData(value), 0)),
        )
        return editor

    def _build_text_editor(self, spec: ParameterSpec) -> QWidget:
        editor = QPlainTextEdit()
        editor.setFixedHeight(TEXT_EDITOR_HEIGHT)
        self._register(spec, editor.toPlainText, lambda value: editor.setPlainText(str(value)))
        return editor

    def _register(self, spec: ParameterSpec, reader: ValueReader, writer: ValueWriter) -> None:
        self._readers[spec.key] = reader
        self._writers[spec.key] = writer

    def _build_footer(self) -> QFrame:
        restore_button = QPushButton(RESTORE_TEXT)
        restore_button.clicked.connect(self.restore_defaults)
        cancel_button = QPushButton(CANCEL_TEXT)
        cancel_button.clicked.connect(self.reject)
        apply_button = QPushButton(APPLY_TEXT)
        apply_button.setObjectName("primaryButton")
        apply_button.setDefault(True)
        apply_button.clicked.connect(self.apply)
        layout = QHBoxLayout()
        layout.setContentsMargins(FOOTER_MARGIN, FOOTER_MARGIN, FOOTER_MARGIN, FOOTER_MARGIN)
        layout.setSpacing(FOOTER_SPACING)
        layout.addWidget(restore_button)
        layout.addStretch(1)
        layout.addWidget(cancel_button)
        layout.addWidget(apply_button)
        footer = QFrame()
        footer.setObjectName("parametersFooter")
        footer.setLayout(layout)
        return footer
