from collections.abc import Callable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QComboBox

from domain.scoring.sample_requirements import REQUIREMENT_DESCRIPTIONS, MetricGroup, SampleRequirement
from domain.scoring.scoring_method import ScoringMethod
from presentation.views.branding import SECONDARY_TEXT_COLOR

GROUP_TITLES = {
    MetricGroup.ANSWER: "Answer quality",
    MetricGroup.RETRIEVAL: "Retrieval",
    MetricGroup.GROUNDING: "Grounding in contexts",
}
GROUP_ORDER = (MetricGroup.ANSWER, MetricGroup.RETRIEVAL, MetricGroup.GROUNDING)
HEADER_PREFIX = "— "
HEADER_SUFFIX = " —"
ENABLED_METRIC_FLAGS = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

MissingRequirementsLookup = Callable[[ScoringMethod], Sequence[SampleRequirement]]


def populate_metric_combo(combo: QComboBox, methods: Sequence[ScoringMethod]) -> None:
    model = QStandardItemModel(combo)
    groups = [group for group in GROUP_ORDER if any(method.metric_group is group for method in methods)]
    show_headers = len(groups) > 1
    for group in groups:
        if show_headers:
            model.appendRow(_build_header_item(GROUP_TITLES[group]))
        for method in methods:
            if method.metric_group is group:
                model.appendRow(_build_metric_item(method))
    combo.setModel(model)


def apply_metric_availability(
    combo: QComboBox, methods: Sequence[ScoringMethod], missing_for: MissingRequirementsLookup
) -> None:
    model = combo.model()
    methods_by_identifier = {method.identifier: method for method in methods}
    for row in range(model.rowCount()):
        item = model.item(row)
        method = methods_by_identifier.get(item.data(Qt.ItemDataRole.UserRole))
        if method is None:
            continue
        missing = missing_for(method)
        item.setFlags(ENABLED_METRIC_FLAGS if not missing else Qt.ItemFlag.NoItemFlags)
        item.setToolTip(" ".join(REQUIREMENT_DESCRIPTIONS[requirement] for requirement in missing))


def first_enabled_index(combo: QComboBox) -> int:
    model = combo.model()
    for row in range(model.rowCount()):
        item = model.item(row)
        if item.data(Qt.ItemDataRole.UserRole) is not None and item.isEnabled():
            return row
    return -1


def is_index_enabled(combo: QComboBox, index: int) -> bool:
    item = combo.model().item(index) if index >= 0 else None
    return item is not None and item.isEnabled()


def _build_header_item(title: str) -> QStandardItem:
    item = QStandardItem(HEADER_PREFIX + title + HEADER_SUFFIX)
    item.setFlags(Qt.ItemFlag.NoItemFlags)
    font = QFont()
    font.setBold(True)
    item.setFont(font)
    item.setForeground(QColor(SECONDARY_TEXT_COLOR))
    return item


def _build_metric_item(method: ScoringMethod) -> QStandardItem:
    item = QStandardItem(method.display_name)
    item.setData(method.identifier, Qt.ItemDataRole.UserRole)
    item.setFlags(ENABLED_METRIC_FLAGS)
    return item
