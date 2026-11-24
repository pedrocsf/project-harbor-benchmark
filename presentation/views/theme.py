from string import Template

from presentation.views import branding

_MAIN_WINDOW_TEMPLATE = Template(
    """
QMainWindow, QMessageBox {
    background: $background;
}
QWidget#content {
    background: $background;
}
QLabel {
    color: $text;
}
QLabel:disabled {
    color: $disabled_text;
}
QFrame#header, QFrame#sidebar {
    background: $panel;
    border: none;
}
QFrame#header {
    border-bottom: 1px solid $border;
}
QFrame#sidebar {
    border-right: 1px solid $border;
}
QLabel#brandTitle {
    font-size: 16px;
    font-weight: 600;
}
QLabel#brandSubtitle, QLabel#statusLabel, QLabel#hintLabel, QLabel#metricCaption, QLabel#datasetCount {
    color: $secondary_text;
    font-size: 12px;
}
QLabel#sectionTitle {
    color: $secondary_text;
    font-size: 12px;
    font-weight: 600;
}
QLabel#fieldLabel {
    color: $label_text;
    font-size: 13px;
}
QLabel#datasetName {
    font-weight: 600;
}
QLabel#metricTitle {
    font-size: 20px;
    font-weight: 600;
}
QLabel#emptyTitle {
    font-size: 20px;
    font-weight: 600;
}
QLabel#emptyText {
    color: $secondary_text;
}
QLabel#demoBadge {
    color: $secondary_text;
    background: $surface;
    border: 1px solid $strong_border;
    border-radius: 12px;
    padding: 4px 12px;
    font-weight: 600;
}
QLabel#metricValue {
    font-size: 18px;
    font-weight: 700;
}
QLabel#statusLabel:disabled, QLabel#metricCaption:disabled {
    color: $disabled_text;
}
QFrame#datasetCard {
    background: $surface;
    border: 1px solid $border;
    border-radius: 10px;
}
QFrame#datasetCard[empty="true"] {
    border: 1px dashed $strong_border;
}
QFrame#metricCard {
    background: $surface;
    border: 1px solid $border;
    border-radius: 12px;
}
QFrame#metricCard[primary="true"] {
    border: 1px solid $primary;
}
QFrame#metricCard:disabled {
    background: $panel;
}
QLineEdit {
    background: $background;
    border: 1px solid $strong_border;
    border-radius: 8px;
    padding: 8px 12px;
    color: $text;
    selection-background-color: $primary;
    placeholder-text-color: $disabled_text;
}
QLineEdit:focus {
    border: 1px solid $primary;
}
QLineEdit:disabled {
    border: 1px solid $border;
    color: $disabled_text;
}
QComboBox {
    background: $background;
    border: 1px solid $strong_border;
    border-radius: 8px;
    padding: 8px 12px;
    color: $text;
}
QComboBox:focus, QComboBox:on {
    border: 1px solid $primary;
}
QComboBox:disabled {
    border: 1px solid $border;
    color: $disabled_text;
}
QComboBox::drop-down {
    border: none;
    width: 28px;
}
QComboBox::down-arrow {
    image: none;
    width: 0;
    height: 0;
}
QComboBox QAbstractItemView {
    background: $panel;
    color: $text;
    border: 1px solid $strong_border;
    selection-background-color: $primary;
    selection-color: $text_on_primary;
    outline: none;
}
QComboBox QAbstractItemView::item:disabled {
    color: $disabled_text;
}
QScrollArea#sidebarScroll, QWidget#sidebarForm {
    background: transparent;
    border: none;
}
QScrollArea#sidebarScroll QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollArea#sidebarScroll QScrollBar::handle:vertical {
    background: $strong_border;
    border-radius: 4px;
    min-height: 24px;
}
QScrollArea#sidebarScroll QScrollBar::add-line, QScrollArea#sidebarScroll QScrollBar::sub-line {
    width: 0;
    height: 0;
}
QScrollArea#sidebarScroll QScrollBar::add-page, QScrollArea#sidebarScroll QScrollBar::sub-page {
    background: transparent;
}
QPushButton {
    background: transparent;
    border: 1px solid $strong_border;
    border-radius: 8px;
    padding: 8px 16px;
    color: $text;
    font-weight: 500;
}
QPushButton:hover {
    background: $surface;
}
QPushButton:pressed {
    background: $background;
}
QPushButton:disabled {
    border: 1px solid $border;
    color: $disabled_text;
    background: transparent;
}
QPushButton[emphasis="true"], QPushButton#primaryButton {
    background: $primary;
    border: 1px solid $primary;
    color: $text_on_primary;
    font-weight: 600;
}
QPushButton[emphasis="true"]:hover, QPushButton#primaryButton:hover {
    background: $primary_hover;
    border: 1px solid $primary_hover;
}
QPushButton[emphasis="true"]:pressed, QPushButton#primaryButton:pressed {
    background: $primary_pressed;
    border: 1px solid $primary_pressed;
}
QPushButton#primaryButton {
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 14px;
}
QPushButton#primaryButton:disabled {
    background: $surface;
    border: 1px solid $border;
    color: $disabled_text;
}
QPushButton#stopButton {
    background: transparent;
    border: 1px solid $primary;
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 14px;
    font-weight: 600;
}
QPushButton#stopButton:hover {
    background: $surface;
}
QLabel#percentLabel {
    color: $primary;
    font-size: 12px;
    font-weight: 600;
}
QProgressBar {
    background: $border;
    border: none;
    border-radius: 3px;
    min-height: 6px;
    max-height: 6px;
}
QProgressBar::chunk {
    background: $primary;
    border-radius: 3px;
}
QTableWidget {
    background: $surface;
    color: $text;
    gridline-color: transparent;
    border: 1px solid $border;
    border-radius: 12px;
    selection-background-color: $border;
    selection-color: $text;
    outline: none;
}
QTableWidget::item {
    padding: 8px 10px;
    border-bottom: 1px solid $border;
}
QTableWidget:disabled {
    color: $disabled_text;
}
QHeaderView {
    background: transparent;
    border: none;
}
QHeaderView::section {
    background: $surface;
    color: $secondary_text;
    padding: 10px;
    border: none;
    border-bottom: 1px solid $border;
    font-size: 12px;
    font-weight: 600;
}
QHeaderView::section:disabled {
    color: $disabled_text;
}
QTableCornerButton::section {
    background: transparent;
    border: none;
}
QDialog#parametersDialog, QWidget#parametersContent, QScrollArea#parametersScroll {
    background: $background;
}
QFrame#parametersFooter {
    background: $panel;
    border-top: 1px solid $border;
}
QLabel#parameterLabel {
    font-size: 13px;
    font-weight: 600;
}
QLabel#parameterHint {
    color: $secondary_text;
    font-size: 12px;
}
QLabel#parametersError {
    color: $text;
    background: $surface;
    border-top: 1px solid $primary;
    padding: 8px 24px;
    font-size: 12px;
}
QSpinBox, QDoubleSpinBox, QPlainTextEdit {
    background: $background;
    border: 1px solid $strong_border;
    border-radius: 8px;
    padding: 8px 12px;
    color: $text;
    selection-background-color: $primary;
}
QSpinBox, QDoubleSpinBox {
    padding: 8px 0;
}
QSpinBox::up-button, QDoubleSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::down-button {
    width: 0;
    border: none;
}
QSpinBox QLineEdit, QDoubleSpinBox QLineEdit {
    background: transparent;
    border: none;
}
QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus {
    border: 1px solid $primary;
}
QCheckBox {
    color: $text;
    spacing: 8px;
}
QCheckBox#parameterCheckbox {
    font-size: 13px;
    font-weight: 600;
}
QDialog#infoDialog, QWidget#infoContent, QScrollArea#infoScroll {
    background: $background;
}
QFrame#infoFooter {
    background: $panel;
    border-top: 1px solid $border;
}
QFrame#infoCard {
    background: $surface;
    border: 1px solid $border;
    border-radius: 12px;
}
QLabel#infoTitle {
    font-size: 22px;
    font-weight: 700;
}
QLabel#infoSectionTitle {
    font-size: 18px;
    font-weight: 600;
}
QLabel#infoMetricName {
    font-size: 15px;
    font-weight: 600;
}
QLabel#infoText, QLabel#infoParameter {
    color: $label_text;
    font-size: 13px;
}
QLabel#infoHint, QLabel#infoCaption {
    color: $secondary_text;
    font-size: 12px;
}
QLabel#infoCaption {
    font-weight: 600;
}
QLabel#infoFormula {
    background: $background;
    border: 1px solid $border;
    border-radius: 8px;
    padding: 8px 12px;
    color: $text;
    font-family: monospace;
    font-size: 12px;
}
QLabel#infoPapers {
    color: $label_text;
    font-size: 12px;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: $strong_border;
    border-radius: 4px;
    min-height: 24px;
    min-width: 24px;
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0;
    height: 0;
}
QScrollBar::add-page, QScrollBar::sub-page {
    background: transparent;
}
"""
)

MAIN_WINDOW_STYLE = _MAIN_WINDOW_TEMPLATE.substitute(
    background=branding.BACKGROUND_COLOR,
    panel=branding.PANEL_COLOR,
    surface=branding.SURFACE_COLOR,
    border=branding.BORDER_COLOR,
    strong_border=branding.STRONG_BORDER_COLOR,
    text=branding.TEXT_COLOR,
    label_text=branding.LABEL_TEXT_COLOR,
    secondary_text=branding.SECONDARY_TEXT_COLOR,
    disabled_text=branding.DISABLED_TEXT_COLOR,
    primary=branding.PRIMARY_COLOR,
    primary_hover=branding.PRIMARY_HOVER_COLOR,
    primary_pressed=branding.PRIMARY_PRESSED_COLOR,
    text_on_primary=branding.TEXT_ON_PRIMARY_COLOR,
)

PRIMARY_TINT_ALPHA = 0.14
MONOSPACE_FONT_STACK = ", ".join(f'"{family}"' for family in branding.MONOSPACE_FONT_FAMILIES)


def _rgba(hex_color: str, alpha: float) -> str:
    red, green, blue = (int(hex_color[position : position + 2], 16) for position in (1, 3, 5))
    return f"rgba({red}, {green}, {blue}, {alpha})"


_EXPLORER_TEMPLATE = Template(
    """
QWidget#explorerWindow {
    background: $background;
}
QFrame#explorerHeader {
    background: $panel;
    border: none;
    border-bottom: 1px solid $border;
}
QLabel#explorerTitle {
    font-size: 16px;
    font-weight: 600;
}
QLabel#explorerSubtitle, QLabel#explorerExampleLabel, QLabel#explorerStepCounter, QLabel#explorerLimitation {
    color: $secondary_text;
    font-size: 12px;
}
QLabel#explorerBadge {
    color: $warning;
    border: 1px solid $warning;
    border-radius: 11px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
}
QPushButton#explorerCloseButton {
    background: $surface;
    border: 1px solid $strong_border;
    font-size: 13px;
}
QPushButton#explorerCloseButton:hover {
    background: $border;
}
QFrame#explorerNav {
    background: $panel;
    border: none;
    border-right: 1px solid $border;
}
QLabel#explorerCaption {
    color: $secondary_text;
    font-size: 11px;
    font-weight: 600;
}
QPushButton#explorerMetricButton {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 0;
    min-height: 40px;
    max-height: 40px;
}
QPushButton#explorerMetricButton:hover {
    background: $active_row;
}
QPushButton#explorerMetricButton[selected="true"] {
    background: $surface;
}
QLabel#explorerMetricIndex {
    color: $disabled_text;
    font-family: $monospace;
    font-size: 11px;
}
QLabel#explorerMetricName {
    color: $label_text;
    font-size: 13px;
}
QLabel#explorerMetricName[selected="true"] {
    color: $primary_hover;
    font-weight: 600;
}
QLabel#explorerMetricKind {
    color: $disabled_text;
    font-size: 10px;
}
QLabel#explorerMetricTitle {
    font-size: 22px;
    font-weight: 700;
}
QLabel#explorerKindChip {
    color: $label_text;
    background: $surface;
    border: 1px solid $border;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
}
QComboBox#explorerExampleCombo {
    background: $surface;
    border: 1px solid $border;
    padding: 6px 12px;
    font-size: 13px;
}
QComboBox#explorerExampleCombo:focus, QComboBox#explorerExampleCombo:on {
    border: 1px solid $primary;
}
QFrame#explorerStage, QFrame#explorerCard, QFrame#explorerControlBar {
    background: $panel;
    border: 1px solid $border;
    border-radius: 12px;
}
QScrollArea#explorerSideScroll, QWidget#explorerSidePanel {
    background: transparent;
    border: none;
}
QScrollArea#explorerSideScroll QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollArea#explorerSideScroll QScrollBar::handle:vertical {
    background: $strong_border;
    border-radius: 4px;
    min-height: 24px;
}
QScrollArea#explorerSideScroll QScrollBar::add-line, QScrollArea#explorerSideScroll QScrollBar::sub-line {
    width: 0;
    height: 0;
}
QScrollArea#explorerSideScroll QScrollBar::add-page, QScrollArea#explorerSideScroll QScrollBar::sub-page {
    background: transparent;
}
QFrame#explorerStepRow {
    background: transparent;
    border: none;
    border-radius: 8px;
}
QFrame#explorerStepRow[state="active"] {
    background: $surface;
}
QLabel#explorerStepBadge {
    min-width: 22px;
    max-width: 22px;
    min-height: 22px;
    max-height: 22px;
    border-radius: 11px;
    font-size: 11px;
    font-weight: 700;
    color: $secondary_text;
    border: 1px solid $strong_border;
    background: transparent;
}
QLabel#explorerStepBadge[state="active"] {
    color: $text_on_primary;
    background: $primary;
    border: 1px solid $primary;
}
QLabel#explorerStepBadge[state="done"] {
    color: $success;
    background: $border;
    border: 1px solid $border;
}
QLabel#explorerStepBadge[state="future"] {
    color: $disabled_text;
    border: 1px solid $border;
}
QLabel#explorerStepTitle {
    font-size: 13px;
    font-weight: 600;
}
QLabel#explorerStepTitle[state="future"] {
    color: $disabled_text;
}
QLabel#explorerStepBody {
    color: $secondary_text;
    font-size: 12px;
}
QLabel#explorerStepBody[state="active"] {
    color: $label_text;
}
QLabel#explorerStepBody[state="future"] {
    color: $disabled_text;
}
QLabel#explorerFormulaLine {
    color: $disabled_text;
    font-family: $monospace;
    font-size: 13px;
    padding: 4px 8px;
    border-radius: 6px;
    background: transparent;
}
QLabel#explorerFormulaLine[highlighted="true"] {
    color: $text;
    background: $primary_tint;
}
QLabel#explorerFormulaResult {
    color: $label_text;
    font-family: $monospace;
    font-size: 13px;
    padding: 6px 8px 0 8px;
    border: none;
    border-top: 1px solid $border;
}
QPushButton#explorerPlayButton {
    background: $primary;
    border: none;
    border-radius: 8px;
    padding: 0;
}
QPushButton#explorerPlayButton:hover {
    background: $primary_hover;
}
QPushButton#explorerIconButton {
    background: $surface;
    border: 1px solid $border;
    border-radius: 8px;
    padding: 0;
}
QPushButton#explorerIconButton:hover {
    background: $border;
}
QPushButton#explorerStepButton {
    background: $surface;
    border: 1px solid $border;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
}
QFrame#explorerSpeedGroup {
    background: $surface;
    border: none;
    border-radius: 8px;
}
QPushButton#explorerSpeedButton {
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 0 10px;
    min-height: 30px;
    max-height: 30px;
    color: $secondary_text;
    font-size: 12px;
}
QPushButton#explorerSpeedButton:checked {
    background: $border;
    color: $text;
    font-weight: 600;
}
"""
)

EXPLORER_WINDOW_STYLE = MAIN_WINDOW_STYLE + _EXPLORER_TEMPLATE.substitute(
    background=branding.BACKGROUND_COLOR,
    panel=branding.PANEL_COLOR,
    surface=branding.SURFACE_COLOR,
    active_row=branding.ACTIVE_ROW_COLOR,
    border=branding.BORDER_COLOR,
    strong_border=branding.STRONG_BORDER_COLOR,
    text=branding.TEXT_COLOR,
    label_text=branding.LABEL_TEXT_COLOR,
    secondary_text=branding.SECONDARY_TEXT_COLOR,
    disabled_text=branding.DISABLED_TEXT_COLOR,
    primary=branding.PRIMARY_COLOR,
    primary_hover=branding.PRIMARY_HOVER_COLOR,
    primary_tint=_rgba(branding.PRIMARY_COLOR, PRIMARY_TINT_ALPHA),
    text_on_primary=branding.TEXT_ON_PRIMARY_COLOR,
    success=branding.SUCCESS_COLOR,
    warning=branding.WARNING_COLOR,
    monospace=MONOSPACE_FONT_STACK,
)
