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
QLabel#infoText {
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
