from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from domain.entities.evaluation_result import EvaluationResult
from domain.entities.metric_overview import MetricOverview
from domain.scoring.scoring_method import ScoreKind, ScoringMethod
from presentation.controllers.answer_source import AnswerSource
from presentation.controllers.evaluation_controller import EvaluationController
from presentation.views.animations import build_value_animation, fade_in, fade_in_window
from presentation.views.answer_source_panel import AnswerSourcePanel
from presentation.views.branding import (
    ACTIVE_ROW_COLOR,
    APPLICATION_NAME,
    APPLICATION_SUBTITLE,
    DISABLED_TEXT_COLOR,
)
from presentation.views.context_tooltip import context_count_text, contexts_tooltip
from presentation.views.info_dialog import InfoDialog
from presentation.views.logo_image import LogoImage
from presentation.views.metric_combo_model import (
    apply_metric_availability,
    first_enabled_index,
    is_index_enabled,
    populate_metric_combo,
)
from presentation.views.metric_parameters_dialog import MetricParametersDialog
from presentation.views.metrics_panel import MetricsPanel
from presentation.views.overview_chart import render_overview_chart
from presentation.views.score_bar_delegate import SCORE_FRACTION_ROLE, ScoreBarDelegate
from presentation.views.spinner_indicator import SpinnerIndicator
from presentation.views.theme import MAIN_WINDOW_STYLE
from presentation.views.themed_combo_box import ThemedComboBox

WINDOW_TITLE = "Project Harbor Benchmark - v1.0"
DEMO_TITLE_SUFFIX = " (Demo)"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 820
HEADER_HEIGHT = 64
HEADER_LOGO_SIZE = 32
HEADER_HORIZONTAL_MARGIN = 24
SIDEBAR_WIDTH = 304
SIDEBAR_MARGIN = 24
SIDEBAR_SPACING = 20
FIELD_SPACING = 6
SECTION_SPACING = 8
FORM_SPACING = 12
CONTENT_MARGIN = 24
CONTENT_SPACING = 20
PROGRESS_BAR_WIDTH = 220
EMPTY_STATE_MAX_WIDTH = 460
EMPTY_STATE_PAGE = 0
CONTENT_PAGE = 1
ENDPOINT_PLACEHOLDER = "http://127.0.0.1:1234/v1/chat/completions"
OPTIONAL_API_KEY_PLACEHOLDER = "Optional"
OPTIONAL_MODEL_PLACEHOLDER = "Optional"
OPTIONAL_JUDGE_URL_PLACEHOLDER = "Optional"
NO_DATASET_TEXT = "No dataset loaded"
NO_DATASET_HINT = "Pick a JSON file to begin"
EMPTY_STATE_TITLE = "Start with a dataset"
EMPTY_STATE_TEXT = (
    "Load a JSON list of questions and expected answers. Then point the app at your model, "
    "choose a metric and run the benchmark. Results, metrics and charts appear here."
)
PARAMETERS_BUTTON_TEXT = "Parameters…"
DEFAULT_PARAMETERS_TEXT = "Default parameters"
CUSTOM_PARAMETER_TEXT = "{count} custom parameter"
CUSTOM_PARAMETERS_TEXT = "{count} custom parameters"
PARAMETERS_SPACING = 6
METRIC_HINT = "Changing the metric re-scores the last run without calling the model again."
JUDGE_CALLS_HINT = "Calls the judge model about {count} times per question ({total} for this dataset)."
JUDGE_CALL_HINT = "Calls the judge model about once per question ({total} for this dataset)."
JUDGE_CALLS_PER_CONTEXT_HINT = "Calls the judge model once per retrieved context."
JUDGE_MODEL_HINT = "Optional. Used only by metrics that call a judge model."
MODEL_SECTION_TITLE = "Model endpoint"
JUDGE_SECTION_TITLE = "Judge model"
FIXED_TABLE_HEADERS = ("#", "Question", "Expected answer", "LLM answer", "Contexts")
NUMBER_COLUMN = 0
NUMBER_COLUMN_WIDTH = 56
SCORE_COLUMN = len(FIXED_TABLE_HEADERS)
SCORE_COLUMN_WIDTH = 190
ANSWER_COLUMN = 3
CONTEXTS_COLUMN = 4
CONTEXTS_COLUMN_WIDTH = 96
ANSWERED_TEXT = "Answered"
WAITING_TEXT = "Waiting for the model…"
WAITING_RAG_TEXT = "Waiting for the RAG endpoint…"
SCORING_ROW_TEXT = "Scoring…"
PENDING_TEXT = "Pending"
IN_PROGRESS_SCORE_TEXT = "…"
PENDING_SCORE_TEXT = "-"
PERCENT_FORMAT = "{:.0%}"
PROGRESS_INDICATOR_SPACING = 8
CONTINUOUS_SCORE_FORMAT = "{:.3f}"
BINARY_SCORE_FORMAT = "{:.0f}"
DATASET_FILTERS = "JSON files (*.json);;All files (*)"
RUN_FILTERS = "Run files (*.json *.jsonl);;All files (*)"
EXPORT_FILTERS = {"JSON (*.json)": ".json", "CSV (*.csv)": ".csv"}
DEFAULT_EXPORT_NAME = "result.json"
CHART_FILTER = "PNG image (*.png)"
CHART_SUFFIX = ".png"
DEFAULT_CHART_NAME = "overview.png"
EXPLORER_BUTTON_TEXT = "How it works"


@dataclass(frozen=True)
class MainWindowOptions:
    dataset_picker: Callable[[], Path | None] | None = None
    run_picker: Callable[[], Path | None] | None = None
    initial_endpoint: str = ""
    initial_rag_endpoint: str = ""
    badge_text: str | None = None
    metric_explorer_factory: Callable[[], QWidget] | None = None


class MainWindow(QMainWindow):
    def __init__(self, controller: EvaluationController, options: MainWindowOptions | None = None):
        super().__init__()
        self._controller = controller
        self._options = options or MainWindowOptions()
        self._pick_dataset = self._options.dataset_picker or self._pick_dataset_with_dialog
        self._pick_run = self._options.run_picker or self._pick_run_with_dialog
        self._last_directory = Path.home()
        self._pending_chart_destination: Path | None = None
        self._score_delegate: ScoreBarDelegate | None = None
        self._info_dialog: InfoDialog | None = None
        self._metric_explorer: QWidget | None = None
        self._parameters_dialog: MetricParametersDialog | None = None
        self._explorer_button: QPushButton | None = None
        self._build_interface()
        self._connect_controller()
        self._show_awaiting_dataset_state()

    def _build_interface(self) -> None:
        self.setWindowTitle(WINDOW_TITLE + (DEMO_TITLE_SUFFIX if self._options.badge_text else ""))
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setStyleSheet(MAIN_WINDOW_STYLE)
        self._metrics_panel = MetricsPanel()
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())
        body.addWidget(self._build_content_area(), stretch=1)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_header())
        layout.addLayout(body, stretch=1)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def _build_header(self) -> QFrame:
        title_label = QLabel(APPLICATION_NAME)
        title_label.setObjectName("brandTitle")
        subtitle_label = QLabel(APPLICATION_SUBTITLE)
        subtitle_label.setObjectName("brandSubtitle")
        self._info_button = QPushButton("Info")
        self._info_button.clicked.connect(self._on_info_clicked)
        self._export_button = QPushButton("Export…")
        self._chart_button = QPushButton("Export chart…")
        self._export_button.clicked.connect(self._on_export_clicked)
        self._chart_button.clicked.connect(self._on_export_chart_clicked)
        layout = QHBoxLayout()
        layout.setContentsMargins(HEADER_HORIZONTAL_MARGIN, 0, HEADER_HORIZONTAL_MARGIN, 0)
        layout.setSpacing(12)
        layout.addWidget(LogoImage(HEADER_LOGO_SIZE))
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addStretch(1)
        if self._options.badge_text:
            badge = QLabel(self._options.badge_text)
            badge.setObjectName("demoBadge")
            layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignVCenter)
        if self._options.metric_explorer_factory is not None:
            self._explorer_button = QPushButton(EXPLORER_BUTTON_TEXT)
            self._explorer_button.clicked.connect(self._on_explorer_clicked)
            layout.addWidget(self._explorer_button)
        layout.addWidget(self._info_button)
        layout.addWidget(self._chart_button)
        layout.addWidget(self._export_button)
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(HEADER_HEIGHT)
        header.setLayout(layout)
        return header

    def _build_sidebar(self) -> QFrame:
        form_layout = QVBoxLayout()
        form_layout.setContentsMargins(SIDEBAR_MARGIN, SIDEBAR_MARGIN, SIDEBAR_MARGIN, SIDEBAR_SPACING)
        form_layout.setSpacing(SIDEBAR_SPACING)
        form_layout.addLayout(self._build_dataset_section())
        form_layout.addLayout(self._build_metric_section())
        form_layout.addLayout(self._build_answer_source_section())
        form_layout.addLayout(self._build_endpoint_section())
        form_layout.addStretch(1)
        form = QWidget()
        form.setObjectName("sidebarForm")
        form.setLayout(form_layout)
        scroll = QScrollArea()
        scroll.setObjectName("sidebarScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(form)
        run_layout = QVBoxLayout()
        run_layout.setContentsMargins(SIDEBAR_MARGIN, 0, SIDEBAR_MARGIN, SIDEBAR_MARGIN)
        run_layout.addWidget(self._build_run_button())
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(scroll, stretch=1)
        layout.addLayout(run_layout)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(SIDEBAR_WIDTH)
        sidebar.setLayout(layout)
        return sidebar

    def _build_section_title(self, text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setObjectName("sectionTitle")
        return label

    def _build_field(self, caption: str, widget: QWidget) -> QVBoxLayout:
        label = QLabel(caption)
        label.setObjectName("fieldLabel")
        field = QVBoxLayout()
        field.setSpacing(FIELD_SPACING)
        field.addWidget(label)
        field.addWidget(widget)
        return field

    def _build_dataset_section(self) -> QVBoxLayout:
        self._dataset_name_label = QLabel()
        self._dataset_name_label.setObjectName("datasetName")
        self._dataset_count_label = QLabel()
        self._dataset_count_label.setObjectName("datasetCount")
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(2)
        card_layout.addWidget(self._dataset_name_label)
        card_layout.addWidget(self._dataset_count_label)
        self._dataset_card = QFrame()
        self._dataset_card.setObjectName("datasetCard")
        self._dataset_card.setLayout(card_layout)
        self._load_button = QPushButton("Load dataset…")
        self._load_button.clicked.connect(self._on_load_clicked)
        section = QVBoxLayout()
        section.setSpacing(SECTION_SPACING)
        section.addWidget(self._build_section_title("Dataset"))
        section.addWidget(self._dataset_card)
        section.addWidget(self._load_button)
        return section

    def _build_answer_source_section(self) -> QVBoxLayout:
        self._source_panel = AnswerSourcePanel(self._controller.supports_run_import)
        self._source_panel.set_rag_url(self._options.initial_rag_endpoint)
        self._source_panel.source_changed.connect(self._on_source_changed)
        self._source_panel.load_run_requested.connect(self._on_load_run_clicked)
        section = QVBoxLayout()
        section.setSpacing(SECTION_SPACING)
        section.addWidget(self._build_section_title("Answers from"))
        section.addWidget(self._source_panel)
        return section

    def _build_endpoint_section(self) -> QVBoxLayout:
        self._endpoint_input = QLineEdit(self._options.initial_endpoint)
        self._endpoint_input.setCursorPosition(0)
        self._endpoint_input.setPlaceholderText(ENDPOINT_PLACEHOLDER)
        self._api_key_input = QLineEdit()
        self._api_key_input.setPlaceholderText(OPTIONAL_API_KEY_PLACEHOLDER)
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._model_input = QLineEdit()
        self._model_input.setPlaceholderText(OPTIONAL_MODEL_PLACEHOLDER)
        self._endpoint_title = self._build_section_title(MODEL_SECTION_TITLE)
        self._judge_hint = QLabel(JUDGE_MODEL_HINT)
        self._judge_hint.setObjectName("hintLabel")
        self._judge_hint.setWordWrap(True)
        self._judge_hint.hide()
        section = QVBoxLayout()
        section.setSpacing(FORM_SPACING)
        section.addWidget(self._endpoint_title)
        section.addWidget(self._judge_hint)
        section.addLayout(self._build_field("URL", self._endpoint_input))
        section.addLayout(self._build_field("API key (optional)", self._api_key_input))
        section.addLayout(self._build_field("Model (optional)", self._model_input))
        return section

    def _build_metric_section(self) -> QVBoxLayout:
        self._method_combo = self._build_method_combo()
        self._judge_calls_hint = QLabel()
        self._judge_calls_hint.setObjectName("hintLabel")
        self._judge_calls_hint.setWordWrap(True)
        hint = QLabel(METRIC_HINT)
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        section = QVBoxLayout()
        section.setSpacing(SECTION_SPACING)
        section.addWidget(self._build_section_title("Metric"))
        section.addWidget(self._method_combo)
        section.addWidget(self._build_parameters_controls())
        section.addWidget(self._judge_calls_hint)
        section.addWidget(hint)
        self._refresh_judge_calls_hint()
        return section

    def _refresh_judge_calls_hint(self) -> None:
        text = self._judge_calls_text(self._controller.selected_method)
        self._judge_calls_hint.setText(text)
        self._judge_calls_hint.setVisible(bool(text))

    def _judge_calls_text(self, method: ScoringMethod) -> str:
        if not method.uses_language_model:
            return ""
        calls = method.judge_calls_per_question()
        if calls is None:
            return JUDGE_CALLS_PER_CONTEXT_HINT
        total = calls * len(self._controller.questions)
        if calls == 1:
            return JUDGE_CALL_HINT.format(total=total)
        return JUDGE_CALLS_HINT.format(count=calls, total=total)

    def _build_parameters_controls(self) -> QWidget:
        self._parameters_button = QPushButton(PARAMETERS_BUTTON_TEXT)
        self._parameters_button.setObjectName("parametersButton")
        self._parameters_button.clicked.connect(self._on_parameters_clicked)
        self._parameters_hint = QLabel()
        self._parameters_hint.setObjectName("hintLabel")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(PARAMETERS_SPACING)
        layout.addWidget(self._parameters_button)
        layout.addWidget(self._parameters_hint)
        self._parameters_controls = QWidget()
        self._parameters_controls.setLayout(layout)
        self._refresh_parameters_controls()
        return self._parameters_controls

    def _refresh_parameters_controls(self) -> None:
        method = self._controller.selected_method
        self._parameters_controls.setVisible(bool(method.parameter_specs))
        custom_count = sum(
            1 for spec in method.parameter_specs if method.parameters.get(spec.key) != spec.default
        )
        self._parameters_hint.setText(
            DEFAULT_PARAMETERS_TEXT if custom_count == 0 else self._custom_parameters_text(custom_count)
        )

    def _on_parameters_clicked(self) -> None:
        method = self._controller.selected_method
        dialog = MetricParametersDialog(method.display_name, method.parameter_specs, method.parameters)
        self._parameters_dialog = dialog
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._center_dialog(dialog)
        dialog.applied.connect(lambda values: self._controller.update_method_parameters(method.identifier, values))
        self._controller.parameters_changed.connect(dialog.accept)
        self._controller.parameters_failed.connect(dialog.show_error)
        dialog.finished.connect(lambda _: self._disconnect_parameters_dialog(dialog))
        dialog.show()

    def _disconnect_parameters_dialog(self, dialog: MetricParametersDialog) -> None:
        self._controller.parameters_changed.disconnect(dialog.accept)
        self._controller.parameters_failed.disconnect(dialog.show_error)
        dialog.deleteLater()
        self._parameters_dialog = None

    def _center_dialog(self, dialog: MetricParametersDialog) -> None:
        frame = dialog.frameGeometry()
        frame.moveCenter(self.geometry().center())
        dialog.move(frame.topLeft())

    def closeEvent(self, event) -> None:
        for window in (self._info_dialog, self._metric_explorer, self._parameters_dialog):
            if window is not None:
                window.close()
        super().closeEvent(event)

    def _build_method_combo(self) -> QComboBox:
        combo = ThemedComboBox()
        populate_metric_combo(combo, self._controller.scoring_methods)
        combo.setCurrentIndex(combo.findData(self._controller.selected_method.identifier))
        combo.currentIndexChanged.connect(self._on_method_changed)
        return combo

    def _refresh_metric_availability(self) -> None:
        apply_metric_availability(
            self._method_combo, self._controller.scoring_methods, self._controller.missing_requirements_for
        )
        if not is_index_enabled(self._method_combo, self._method_combo.currentIndex()):
            self._method_combo.setCurrentIndex(first_enabled_index(self._method_combo))
        self._refresh_judge_calls_hint()

    def _build_run_button(self) -> QWidget:
        self._run_button = QPushButton("Run benchmark")
        self._run_button.setObjectName("primaryButton")
        self._run_button.clicked.connect(self._on_run_clicked)
        self._cancel_button = QPushButton("Stop run")
        self._cancel_button.setObjectName("stopButton")
        self._cancel_button.clicked.connect(self._controller.cancel_evaluation)
        self._cancel_button.hide()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._run_button)
        layout.addWidget(self._cancel_button)
        container = QWidget()
        container.setLayout(layout)
        return container

    def _build_content_area(self) -> QWidget:
        self._content_stack = QStackedWidget()
        self._content_stack.addWidget(self._build_empty_state())
        self._content_stack.addWidget(self._build_results_page())
        self._content_stack.setObjectName("content")
        return self._content_stack

    def _build_empty_state(self) -> QWidget:
        title = QLabel(EMPTY_STATE_TITLE)
        title.setObjectName("emptyTitle")
        text = QLabel(EMPTY_STATE_TEXT)
        text.setObjectName("emptyText")
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setFixedWidth(EMPTY_STATE_MAX_WIDTH)
        text.setMinimumHeight(text.heightForWidth(EMPTY_STATE_MAX_WIDTH))
        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.addStretch(1)
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(text, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        page = QWidget()
        page.setLayout(layout)
        return page

    def _build_results_page(self) -> QWidget:
        layout = QVBoxLayout()
        layout.setContentsMargins(CONTENT_MARGIN, CONTENT_MARGIN, CONTENT_MARGIN, CONTENT_MARGIN)
        layout.setSpacing(CONTENT_SPACING)
        layout.addLayout(self._build_results_title_row())
        layout.addWidget(self._metrics_panel)
        layout.addWidget(self._build_results_table(), stretch=1)
        page = QWidget()
        page.setLayout(layout)
        return page

    def _build_results_title_row(self) -> QHBoxLayout:
        self._metric_title_label = QLabel(self._controller.selected_method.display_name)
        self._metric_title_label.setObjectName("metricTitle")
        self._status_label = QLabel()
        self._status_label.setObjectName("statusLabel")
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(self._metric_title_label)
        titles.addWidget(self._status_label)
        self._progress_bar = QProgressBar()
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedWidth(PROGRESS_BAR_WIDTH)
        self._progress_animation = build_value_animation(self._progress_bar, b"value")
        row = QHBoxLayout()
        row.addLayout(titles)
        row.addStretch(1)
        row.addWidget(self._progress_bar, alignment=Qt.AlignmentFlag.AlignVCenter)
        row.addSpacing(PROGRESS_INDICATOR_SPACING)
        row.addWidget(self._build_progress_indicator())
        return row

    def _build_progress_indicator(self) -> QWidget:
        self._spinner = SpinnerIndicator()
        self._percent_label = QLabel()
        self._percent_label.setObjectName("percentLabel")
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(PROGRESS_INDICATOR_SPACING)
        layout.addWidget(self._spinner)
        layout.addWidget(self._percent_label)
        self._progress_indicator = QWidget()
        self._progress_indicator.setLayout(layout)
        self._progress_indicator.hide()
        return self._progress_indicator

    def _build_results_table(self) -> QTableWidget:
        self._table = QTableWidget(0, len(FIXED_TABLE_HEADERS) + 1)
        self._table.setMouseTracking(True)
        self._set_score_header(self._controller.selected_method.column_header)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.setWordWrap(True)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._score_delegate = ScoreBarDelegate(self._table)
        self._table.setItemDelegateForColumn(SCORE_COLUMN, self._score_delegate)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(NUMBER_COLUMN, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(SCORE_COLUMN, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(CONTEXTS_COLUMN, QHeaderView.ResizeMode.Fixed)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._table.setColumnWidth(NUMBER_COLUMN, NUMBER_COLUMN_WIDTH)
        self._table.setColumnWidth(SCORE_COLUMN, SCORE_COLUMN_WIDTH)
        self._table.setColumnWidth(CONTEXTS_COLUMN, CONTEXTS_COLUMN_WIDTH)
        self._table.setColumnHidden(CONTEXTS_COLUMN, True)
        return self._table

    def _connect_controller(self) -> None:
        self._controller.dataset_loaded.connect(self._show_dataset_loaded)
        self._controller.dataset_failed.connect(self._show_dataset_failure)
        self._controller.started.connect(self._show_running_state)
        self._controller.progressed.connect(self._show_progress)
        self._controller.completed.connect(self._show_result)
        self._controller.failed.connect(self._show_failure)
        self._controller.cancelled.connect(self._show_cancelled)
        self._controller.exported.connect(self._show_export_success)
        self._controller.export_failed.connect(self._show_export_failure)
        self._controller.overview_ready.connect(self._save_overview_chart)
        self._controller.overview_failed.connect(self._show_overview_failure)
        self._controller.parameters_changed.connect(self._refresh_parameters_controls)
        self._controller.parameters_changed.connect(self._refresh_judge_calls_hint)
        self._controller.availability_changed.connect(self._refresh_metric_availability)
        self._controller.run_import_loaded.connect(self._show_run_import_loaded)
        self._controller.run_import_failed.connect(self._show_run_import_failure)

    def _on_load_clicked(self) -> None:
        selected_source = self._pick_dataset()
        if selected_source is not None:
            self._controller.load_dataset(selected_source)

    def _pick_dataset_with_dialog(self) -> Path | None:
        selected_path, _ = QFileDialog.getOpenFileName(
            self, "Load dataset", str(self._last_directory), DATASET_FILTERS
        )
        if not selected_path:
            return None
        self._last_directory = Path(selected_path).parent
        return Path(selected_path)

    def _pick_run_with_dialog(self) -> Path | None:
        selected_path, _ = QFileDialog.getOpenFileName(
            self, "Load run", str(self._last_directory), RUN_FILTERS
        )
        if not selected_path:
            return None
        self._last_directory = Path(selected_path).parent
        return Path(selected_path)

    def _on_load_run_clicked(self) -> None:
        selected_source = self._pick_run()
        if selected_source is not None:
            self._controller.load_imported_run(selected_source)

    def _show_run_import_loaded(self, name: str, answer_count: int, has_contexts: bool) -> None:
        self._source_panel.show_imported_run(name, answer_count, has_contexts)
        if self._controller.answer_source is AnswerSource.IMPORTED_RUN:
            self._discard_results()

    def _show_run_import_failure(self, message: str) -> None:
        QMessageBox.critical(self, WINDOW_TITLE, message)

    def _on_source_changed(self, source: AnswerSource) -> None:
        self._controller.set_answer_source(source)
        is_model_source = source is AnswerSource.MODEL_ENDPOINT
        self._endpoint_title.setText((MODEL_SECTION_TITLE if is_model_source else JUDGE_SECTION_TITLE).upper())
        self._judge_hint.setVisible(not is_model_source)
        self._endpoint_input.setPlaceholderText(ENDPOINT_PLACEHOLDER if is_model_source else OPTIONAL_JUDGE_URL_PLACEHOLDER)
        self._discard_results()

    def _discard_results(self) -> None:
        if self._controller.questions:
            self._clear_results()
            self._reset_progress()
            self._status_label.clear()
            self._set_exports_enabled(False)

    def _on_run_clicked(self) -> None:
        rag_input = None
        if self._controller.answer_source is AnswerSource.RAG_ENDPOINT:
            rag_input = self._source_panel.rag_input()
        self._controller.start_evaluation(
            self._endpoint_input.text(),
            self._api_key_input.text(),
            self._model_input.text(),
            rag_input,
        )

    def _on_method_changed(self, index: int) -> None:
        identifier = self._method_combo.itemData(index)
        if identifier is None:
            return
        self._controller.select_method(identifier)
        self._set_score_header(self._controller.selected_method.column_header)
        self._metric_title_label.setText(self._controller.selected_method.display_name)
        self._refresh_parameters_controls()
        self._refresh_judge_calls_hint()

    def _custom_parameters_text(self, custom_count: int) -> str:
        template = CUSTOM_PARAMETER_TEXT if custom_count == 1 else CUSTOM_PARAMETERS_TEXT
        return template.format(count=custom_count)

    def _on_info_clicked(self) -> None:
        if self._info_dialog is None:
            self._info_dialog = InfoDialog(self._controller.scoring_methods)
        self._info_dialog.show()
        self._info_dialog.raise_()
        self._info_dialog.activateWindow()

    def _on_explorer_clicked(self) -> None:
        if self._options.metric_explorer_factory is None:
            return
        if self._metric_explorer is None:
            self._metric_explorer = self._options.metric_explorer_factory()
        self._metric_explorer.select_metric(self._method_combo.currentData())
        self._metric_explorer.show()
        self._metric_explorer.raise_()
        self._metric_explorer.activateWindow()

    def _on_export_clicked(self) -> None:
        selected_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Export result", DEFAULT_EXPORT_NAME, ";;".join(EXPORT_FILTERS)
        )
        if not selected_path:
            return
        destination = Path(selected_path)
        if not destination.suffix:
            destination = destination.with_suffix(EXPORT_FILTERS[selected_filter])
        self._controller.export_last_result(destination)

    def _on_export_chart_clicked(self) -> None:
        selected_path, _ = QFileDialog.getSaveFileName(
            self, "Export chart", DEFAULT_CHART_NAME, CHART_FILTER
        )
        if not selected_path:
            return
        self._pending_chart_destination = Path(selected_path).with_suffix(CHART_SUFFIX)
        self._show_building_chart_state()
        self._controller.build_overview()

    def _show_building_chart_state(self) -> None:
        self._set_configuration_enabled(False)
        self._load_button.setEnabled(False)
        self._set_exports_enabled(False)
        self._status_label.setText("Building chart…")

    def _save_overview_chart(self, overview: MetricOverview) -> None:
        destination = self._pending_chart_destination
        self._show_ready_state()
        self._set_exports_enabled(True)
        if destination is None:
            return
        if not render_overview_chart(overview).save(str(destination)):
            self._status_label.setText("Failed.")
            QMessageBox.critical(self, WINDOW_TITLE, f"Could not save the chart to {destination}.")
            return
        self._status_label.setText(f"Chart saved to {destination}")

    def _show_overview_failure(self, message: str) -> None:
        self._show_ready_state()
        self._set_exports_enabled(True)
        self._status_label.setText("Failed.")
        QMessageBox.critical(self, WINDOW_TITLE, message)

    def _show_awaiting_dataset_state(self) -> None:
        self._set_configuration_enabled(False)
        self._load_button.setEnabled(True)
        self._set_running_controls(False)
        self._set_exports_enabled(False)
        self._set_results_enabled(False)
        self._reset_progress()
        self._status_label.clear()
        self._set_dataset_summary(NO_DATASET_TEXT, NO_DATASET_HINT, is_empty=True)
        self._show_page(EMPTY_STATE_PAGE)

    def _show_ready_state(self) -> None:
        self._set_configuration_enabled(True)
        self._load_button.setEnabled(True)
        self._set_running_controls(False)
        self._set_exports_enabled(False)

    def _show_running_state(self, status_text: str, is_cancellable: bool) -> None:
        self._set_configuration_enabled(False)
        self._load_button.setEnabled(False)
        self._set_running_controls(True, is_cancellable)
        self._set_exports_enabled(False)
        self._clear_results()
        self._reset_progress()
        self._percent_label.setText(PERCENT_FORMAT.format(0))
        self._status_label.setText(status_text)
        if is_cancellable:
            self._show_pending_questions()

    def _show_dataset_loaded(self, source: str, question_count: int) -> None:
        self._clear_results()
        self._reset_progress()
        self._status_label.clear()
        self._set_dataset_summary(Path(source).name, self._dataset_detail(question_count), is_empty=False)
        self._dataset_card.setToolTip(source)
        self._show_page(CONTENT_PAGE)
        self._show_ready_state()

    def _dataset_detail(self, question_count: int) -> str:
        labelled_count = sum(1 for question in self._controller.questions if question.has_relevance_labels)
        if labelled_count == 0:
            return f"{question_count} questions"
        return f"{question_count} questions · {labelled_count} with relevance labels"

    def _show_page(self, page_index: int) -> None:
        if self._content_stack.currentIndex() == page_index:
            return
        self._content_stack.setCurrentIndex(page_index)
        fade_in(self._content_stack.currentWidget())

    def _reset_progress(self) -> None:
        self._progress_animation.stop()
        self._progress_bar.setValue(0)

    def _animate_progress(self, value: int) -> None:
        self._progress_animation.stop()
        self._progress_animation.setStartValue(self._progress_bar.value())
        self._progress_animation.setEndValue(value)
        self._progress_animation.start()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not event.spontaneous():
            fade_in_window(self)

    def _show_dataset_failure(self, message: str) -> None:
        QMessageBox.critical(self, WINDOW_TITLE, message)

    def _show_progress(self, completed: int, total: int) -> None:
        self._progress_bar.setMaximum(total)
        self._animate_progress(completed)
        self._percent_label.setText(PERCENT_FORMAT.format(completed / total))
        self._status_label.setText(f"Running · {completed} of {total} questions")
        self._mark_progress(completed)

    def _show_result(self, result: EvaluationResult) -> None:
        self._show_ready_state()
        self._set_exports_enabled(True)
        self._select_method_silently(result.method.identifier)
        self._refresh_metric_availability()
        self._set_score_header(result.method.column_header)
        self._metric_title_label.setText(result.method.display_name)
        self._fill_table(result)
        self._metrics_panel.show_metrics(result.metrics, result.method, result.average_score)
        self._set_results_enabled(True)
        self._status_label.setText("Done.")

    def _show_failure(self, message: str) -> None:
        self._show_ready_state()
        self._status_label.setText("Failed.")
        QMessageBox.critical(self, WINDOW_TITLE, message)

    def _show_cancelled(self) -> None:
        self._show_ready_state()
        self._status_label.setText("Cancelled.")

    def _show_export_success(self, destination: str) -> None:
        self._status_label.setText(f"Result saved to {destination}")

    def _show_export_failure(self, message: str) -> None:
        QMessageBox.critical(self, WINDOW_TITLE, message)

    def _set_configuration_enabled(self, is_enabled: bool) -> None:
        self._source_panel.set_inputs_enabled(is_enabled)
        configuration_widgets = (
            self._endpoint_input,
            self._api_key_input,
            self._model_input,
            self._method_combo,
            self._parameters_button,
            self._run_button,
        )
        for widget in configuration_widgets:
            widget.setEnabled(is_enabled)

    def _set_running_controls(self, is_running: bool, is_cancellable: bool = False) -> None:
        self._run_button.setVisible(not (is_running and is_cancellable))
        self._cancel_button.setVisible(is_running and is_cancellable)
        self._progress_indicator.setVisible(is_running)

    def _show_pending_questions(self) -> None:
        questions = self._controller.questions
        self._table.setRowCount(len(questions))
        for row, question in enumerate(questions):
            self._table.setItem(row, NUMBER_COLUMN, QTableWidgetItem(str(question.identifier)))
            self._table.setItem(row, 1, QTableWidgetItem(question.text))
            self._table.setItem(row, 2, QTableWidgetItem(question.expected_answer))
            self._table.setItem(row, ANSWER_COLUMN, QTableWidgetItem())
            self._table.setItem(row, CONTEXTS_COLUMN, QTableWidgetItem())
            self._table.setItem(row, SCORE_COLUMN, QTableWidgetItem())
            self._table.item(row, SCORE_COLUMN).setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._table.resizeRowsToContents()
        self._table.setEnabled(True)
        self._mark_progress(0)

    def _mark_progress(self, completed: int) -> None:
        for row in range(self._table.rowCount()):
            if row < completed:
                answer_text, score_text = ANSWERED_TEXT, ""
            elif row == completed:
                answer_text, score_text = self._waiting_text(), IN_PROGRESS_SCORE_TEXT
            else:
                answer_text, score_text = PENDING_TEXT, PENDING_SCORE_TEXT
            self._table.item(row, ANSWER_COLUMN).setText(answer_text)
            self._table.item(row, SCORE_COLUMN).setText(score_text)
            self._style_progress_row(row, row == completed, row > completed)

    def _waiting_text(self) -> str:
        source = self._controller.answer_source
        if source is AnswerSource.IMPORTED_RUN:
            return SCORING_ROW_TEXT
        if source is AnswerSource.RAG_ENDPOINT:
            return WAITING_RAG_TEXT
        return WAITING_TEXT

    def _style_progress_row(self, row: int, is_active: bool, is_pending: bool) -> None:
        background = QColor(ACTIVE_ROW_COLOR) if is_active else QColor(0, 0, 0, 0)
        for column in range(self._table.columnCount()):
            item = self._table.item(row, column)
            item.setBackground(background)
            if is_pending:
                item.setForeground(QColor(DISABLED_TEXT_COLOR))
            else:
                item.setData(Qt.ItemDataRole.ForegroundRole, None)

    def _set_exports_enabled(self, is_enabled: bool) -> None:
        for widget in (self._export_button, self._chart_button):
            widget.setEnabled(is_enabled)

    def _set_results_enabled(self, is_enabled: bool) -> None:
        for widget in (self._table, self._metrics_panel):
            widget.setEnabled(is_enabled)

    def _clear_results(self) -> None:
        self._table.setRowCount(0)
        self._metrics_panel.clear()
        self._set_results_enabled(False)

    def _select_method_silently(self, identifier: str) -> None:
        self._method_combo.blockSignals(True)
        self._method_combo.setCurrentIndex(self._method_combo.findData(identifier))
        self._method_combo.blockSignals(False)

    def _set_score_header(self, header: str) -> None:
        self._table.setHorizontalHeaderLabels([*FIXED_TABLE_HEADERS, header])

    def _set_dataset_summary(self, name: str, detail: str, is_empty: bool) -> None:
        self._dataset_name_label.setText(name)
        self._dataset_count_label.setText(detail)
        self._dataset_card.setToolTip("")
        self._dataset_card.setProperty("empty", is_empty)
        self._load_button.setProperty("emphasis", is_empty)
        for widget in (self._dataset_card, self._load_button):
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def _fill_table(self, result: EvaluationResult) -> None:
        score_format = (
            BINARY_SCORE_FORMAT if result.method.score_kind is ScoreKind.BINARY else CONTINUOUS_SCORE_FORMAT
        )
        self._table.setRowCount(len(result.scores))
        self._table.setColumnHidden(CONTEXTS_COLUMN, all(score.contexts is None for score in result.scores))
        for row, score in enumerate(result.scores):
            self._table.setItem(row, NUMBER_COLUMN, QTableWidgetItem(str(score.question.identifier)))
            self._table.setItem(row, 1, QTableWidgetItem(score.question.text))
            self._table.setItem(row, 2, QTableWidgetItem(score.question.expected_answer))
            self._table.setItem(row, 3, QTableWidgetItem(score.given_answer))
            contexts_item = QTableWidgetItem(context_count_text(score.contexts))
            contexts_item.setToolTip(contexts_tooltip(score.contexts))
            self._table.setItem(row, CONTEXTS_COLUMN, contexts_item)
            score_item = QTableWidgetItem(score_format.format(score.score))
            score_item.setData(SCORE_FRACTION_ROLE, score.score)
            self._table.setItem(row, SCORE_COLUMN, score_item)
        self._table.resizeRowsToContents()
        self._score_delegate.start_reveal()
