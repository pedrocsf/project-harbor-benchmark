from collections.abc import Sequence
from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from presentation.views.animations import fade_in_window
from presentation.views.branding import APPLICATION_NAME, APPLICATION_SUBTITLE, PRIMARY_HOVER_COLOR
from domain.scoring.metric_parameters import ParameterKind, ParameterSpec
from domain.scoring.scoring_method import ScoringMethod
from presentation.views.info_content import (
    METRIC_INFOS,
    METRICS_INTRO,
    METRICS_TITLE,
    PAPERS_CAPTION,
    PARAMETERS_CAPTION,
    PROJECT_DESCRIPTION,
    PROJECT_NOTES,
    PROJECT_TITLE,
    MetricInfo,
    PaperReference,
)
from presentation.views.logo_image import LogoImage

INFO_WINDOW_TITLE = "Info - " + APPLICATION_NAME
INFO_WINDOW_WIDTH = 760
INFO_WINDOW_HEIGHT = 720
INFO_MARGIN = 28
INFO_SPACING = 16
CARD_MARGIN = 16
CARD_SPACING = 8
LOGO_SIZE = 40
CLOSE_BUTTON_TEXT = "Close"
PAPER_SPACING = 6
BULLET = "•"
LONG_TEXT_LIMIT = 60
LONG_TEXT_DEFAULT = "built-in text"
BOOLEAN_LABELS = {True: "on", False: "off"}
PARAMETER_LINE = "{label} (default: {default}{range}): {description}"
RANGE_TEXT = ", allowed {minimum} to {maximum}"
MINIMUM_ONLY_TEXT = ", allowed from {minimum}"
MAXIMUM_ONLY_TEXT = ", allowed up to {maximum}"


class InfoDialog(QDialog):
    def __init__(self, scoring_methods: Sequence[ScoringMethod]):
        super().__init__()
        self._parameter_specs_by_identifier = {
            method.identifier: method.parameter_specs for method in scoring_methods
        }
        self.setObjectName("infoDialog")
        self.setWindowTitle(INFO_WINDOW_TITLE)
        self.resize(INFO_WINDOW_WIDTH, INFO_WINDOW_HEIGHT)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_scroll_area(), stretch=1)
        layout.addWidget(self._build_footer())
        self.setLayout(layout)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not event.spontaneous():
            fade_in_window(self)

    def _build_scroll_area(self) -> QScrollArea:
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(INFO_MARGIN, INFO_MARGIN, INFO_MARGIN, INFO_MARGIN)
        content_layout.setSpacing(INFO_SPACING)
        content_layout.addLayout(self._build_project_header())
        content_layout.addWidget(self._build_paragraph(PROJECT_DESCRIPTION, "infoText"))
        content_layout.addWidget(self._build_paragraph(PROJECT_NOTES, "infoHint"))
        content_layout.addSpacing(INFO_SPACING)
        content_layout.addWidget(self._build_paragraph(METRICS_TITLE, "infoSectionTitle"))
        content_layout.addWidget(self._build_paragraph(METRICS_INTRO, "infoHint"))
        for metric_info in METRIC_INFOS:
            content_layout.addWidget(self._build_metric_card(metric_info))
        content_layout.addStretch(1)
        content = QWidget()
        content.setObjectName("infoContent")
        content.setLayout(content_layout)
        scroll_area = QScrollArea()
        scroll_area.setObjectName("infoScroll")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setWidget(content)
        return scroll_area

    def _build_project_header(self) -> QHBoxLayout:
        title = QLabel(PROJECT_TITLE)
        title.setObjectName("infoTitle")
        version = QLabel(f"{APPLICATION_NAME} {APPLICATION_SUBTITLE}")
        version.setObjectName("infoHint")
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(title)
        titles.addWidget(version)
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(LogoImage(LOGO_SIZE))
        row.addLayout(titles)
        row.addStretch(1)
        return row

    def _build_paragraph(self, text: str, object_name: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return label

    def _build_metric_card(self, metric_info: MetricInfo) -> QFrame:
        layout = QVBoxLayout()
        layout.setContentsMargins(CARD_MARGIN, CARD_MARGIN, CARD_MARGIN, CARD_MARGIN)
        layout.setSpacing(CARD_SPACING)
        layout.addWidget(self._build_paragraph(metric_info.name, "infoMetricName"))
        layout.addWidget(self._build_paragraph(metric_info.formula, "infoFormula"))
        layout.addWidget(self._build_paragraph(metric_info.explanation, "infoText"))
        specs = self._parameter_specs_by_identifier.get(metric_info.identifier, ())
        if specs:
            layout.addWidget(self._build_paragraph(PARAMETERS_CAPTION, "infoCaption"))
            for spec in specs:
                layout.addWidget(self._build_paragraph(self._format_parameter(spec), "infoParameter"))
        layout.addWidget(self._build_paragraph(PAPERS_CAPTION, "infoCaption"))
        layout.addWidget(self._build_papers_label(metric_info))
        card = QFrame()
        card.setObjectName("infoCard")
        card.setLayout(layout)
        return card

    def _format_parameter(self, spec: ParameterSpec) -> str:
        return PARAMETER_LINE.format(
            label=spec.label,
            default=self._format_default(spec),
            range=self._format_range(spec),
            description=spec.description,
        )

    def _format_default(self, spec: ParameterSpec) -> str:
        if spec.kind is ParameterKind.BOOLEAN:
            return BOOLEAN_LABELS[bool(spec.default)]
        if spec.kind is ParameterKind.CHOICE:
            return next((choice.label for choice in spec.choices if choice.value == spec.default), str(spec.default))
        if spec.kind is ParameterKind.TEXT and len(str(spec.default)) > LONG_TEXT_LIMIT:
            return LONG_TEXT_DEFAULT
        return str(spec.default)

    def _format_range(self, spec: ParameterSpec) -> str:
        if spec.minimum is not None and spec.maximum is not None:
            return RANGE_TEXT.format(minimum=spec.minimum, maximum=spec.maximum)
        if spec.minimum is not None:
            return MINIMUM_ONLY_TEXT.format(minimum=spec.minimum)
        if spec.maximum is not None:
            return MAXIMUM_ONLY_TEXT.format(maximum=spec.maximum)
        return ""

    def _build_papers_label(self, metric_info: MetricInfo) -> QWidget:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(PAPER_SPACING)
        for paper in metric_info.papers:
            layout.addWidget(self._build_paper_label(paper))
        container = QWidget()
        container.setLayout(layout)
        return container

    def _build_paper_label(self, paper: PaperReference) -> QLabel:
        link = f'<a href="{escape(paper.url, quote=True)}">{escape(paper.citation)}</a>'
        coverage = escape(paper.coverage)
        label = QLabel(f"<style>a {{ color: {PRIMARY_HOVER_COLOR}; }}</style>{BULLET} {link}<br>{coverage}")
        label.setObjectName("infoPapers")
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)
        label.setOpenExternalLinks(True)
        return label

    def _build_footer(self) -> QFrame:
        close_button = QPushButton(CLOSE_BUTTON_TEXT)
        close_button.setObjectName("primaryButton")
        close_button.clicked.connect(self.close)
        layout = QHBoxLayout()
        layout.setContentsMargins(INFO_MARGIN, 12, INFO_MARGIN, 12)
        layout.addStretch(1)
        layout.addWidget(close_button)
        footer = QFrame()
        footer.setObjectName("infoFooter")
        footer.setLayout(layout)
        return footer
