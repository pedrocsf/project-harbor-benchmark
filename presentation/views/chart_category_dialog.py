from collections.abc import Callable, Sequence

from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from domain.scoring.sample_requirements import MetricGroup
from presentation.views.metric_combo_model import GROUP_ORDER, GROUP_TITLES
from presentation.views.theme import MAIN_WINDOW_STYLE

DIALOG_WIDTH = 420
DIALOG_MARGIN = 24
DIALOG_SPACING = 12
FOOTER_MARGIN = 16
FOOTER_SPACING = 10
WINDOW_TITLE = "Export chart"
HEADING_TEXT = "Choose the metric category"
HINT_TEXT = "Each category measures something different, so each one gets its own chart."
CANCEL_TEXT = "Cancel"
EXPORT_TEXT = "Export"
GROUP_DESCRIPTIONS = {
    MetricGroup.ANSWER: "How close the answer is to the expected one.",
    MetricGroup.RETRIEVAL: "Whether the search brought back the right contexts.",
    MetricGroup.GROUNDING: "Whether the answer is supported by the retrieved contexts.",
}

UnavailableReason = Callable[[MetricGroup], str]


class ChartCategoryDialog(QDialog):
    def __init__(
        self,
        available_groups: Sequence[MetricGroup],
        unavailable_reason: UnavailableReason,
    ):
        super().__init__()
        self.setObjectName("chartCategoryDialog")
        self.setStyleSheet(MAIN_WINDOW_STYLE)
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumWidth(DIALOG_WIDTH)
        self._buttons: dict[MetricGroup, QRadioButton] = {}
        self._button_group = QButtonGroup(self)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_body(available_groups, unavailable_reason))
        layout.addWidget(self._build_footer())
        self.setLayout(layout)

    def selected_group(self) -> MetricGroup | None:
        for group, button in self._buttons.items():
            if button.isChecked():
                return group
        return None

    def _build_body(self, available_groups: Sequence[MetricGroup], unavailable_reason: UnavailableReason) -> QFrame:
        heading = QLabel(HEADING_TEXT)
        heading.setObjectName("parameterLabel")
        hint = QLabel(HINT_TEXT)
        hint.setObjectName("parameterHint")
        hint.setWordWrap(True)
        layout = QVBoxLayout()
        layout.setContentsMargins(DIALOG_MARGIN, DIALOG_MARGIN, DIALOG_MARGIN, DIALOG_MARGIN)
        layout.setSpacing(DIALOG_SPACING)
        layout.addWidget(heading)
        layout.addWidget(hint)
        for group in GROUP_ORDER:
            is_available = group in available_groups
            layout.addWidget(self._build_option(group, is_available, unavailable_reason))
        self._select_first_available(available_groups)
        body = QFrame()
        body.setObjectName("chartCategoryBody")
        body.setLayout(layout)
        return body

    def _build_option(self, group: MetricGroup, is_available: bool, unavailable_reason: UnavailableReason) -> QFrame:
        button = QRadioButton(GROUP_TITLES[group])
        button.setObjectName("chartCategoryOption")
        button.setEnabled(is_available)
        self._buttons[group] = button
        self._button_group.addButton(button)
        description = QLabel(GROUP_DESCRIPTIONS[group] if is_available else unavailable_reason(group))
        description.setObjectName("parameterHint")
        description.setWordWrap(True)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(button)
        layout.addWidget(description)
        option = QFrame()
        option.setLayout(layout)
        return option

    def _select_first_available(self, available_groups: Sequence[MetricGroup]) -> None:
        for group in GROUP_ORDER:
            if group in available_groups:
                self._buttons[group].setChecked(True)
                return

    def _build_footer(self) -> QFrame:
        cancel_button = QPushButton(CANCEL_TEXT)
        cancel_button.clicked.connect(self.reject)
        export_button = QPushButton(EXPORT_TEXT)
        export_button.setObjectName("primaryButton")
        export_button.setDefault(True)
        export_button.clicked.connect(self.accept)
        export_button.setEnabled(self.selected_group() is not None)
        layout = QHBoxLayout()
        layout.setContentsMargins(FOOTER_MARGIN, FOOTER_MARGIN, FOOTER_MARGIN, FOOTER_MARGIN)
        layout.setSpacing(FOOTER_SPACING)
        layout.addStretch(1)
        layout.addWidget(cancel_button)
        layout.addWidget(export_button)
        footer = QFrame()
        footer.setObjectName("parametersFooter")
        footer.setLayout(layout)
        return footer
