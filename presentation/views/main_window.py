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
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from domain.entities.evaluation_result import EvaluationResult
from domain.entities.metric_overview import MetricOverview
from domain.scoring.scoring_method import ScoreKind
from presentation.controllers.evaluation_controller import EvaluationController
from presentation.views.animations import build_value_animation, fade_in, fade_in_window
from presentation.views.branding import (
    ACTIVE_ROW_COLOR,
    APPLICATION_NAME,
    APPLICATION_SUBTITLE,
    DISABLED_TEXT_COLOR,
)
from presentation.views.info_dialog import InfoDialog
from presentation.views.logo_image import LogoImage
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
NO_DATASET_TEXT = "No dataset loaded"
NO_DATASET_HINT = "Pick a JSON file to begin"
EMPTY_STATE_TITLE = "Start with a dataset"
EMPTY_STATE_TEXT = (
    "Load a JSON list of questions and expected answers. Then point the app at your model, "
    "choose a metric and run the benchmark. Results, metrics and charts appear here."
)
METRIC_HINT = "Changing the metric re-scores the last run without calling the model again."
FIXED_TABLE_HEADERS = ("#", "Question", "Expected answer", "LLM answer")
NUMBER_COLUMN = 0
NUMBER_COLUMN_WIDTH = 56
SCORE_COLUMN = len(FIXED_TABLE_HEADERS)
SCORE_COLUMN_WIDTH = 190
ANSWER_COLUMN = 3
ANSWERED_TEXT = "Answered"
WAITING_TEXT = "Waiting for the model…"
PENDING_TEXT = "Pending"
IN_PROGRESS_SCORE_TEXT = "…"
PENDING_SCORE_TEXT = "-"
PERCENT_FORMAT = "{:.0%}"
PROGRESS_INDICATOR_SPACING = 8
CONTINUOUS_SCORE_FORMAT = "{:.3f}"
BINARY_SCORE_FORMAT = "{:.0f}"
DATASET_FILTERS = "JSON files (*.json);;All files (*)"
EXPORT_FILTERS = {"JSON (*.json)": ".json", "CSV (*.csv)": ".csv"}
DEFAULT_EXPORT_NAME = "result.json"
CHART_FILTER = "PNG image (*.png)"
CHART_SUFFIX = ".png"
DEFAULT_CHART_NAME = "overview.png"


@dataclass(frozen=True)
class MainWindowOptions:
    dataset_picker: Callable[[], Path | None] | None = None
    initial_endpoint: str = ""
    badge_text: str | None = None


class MainWindow(QMainWindow):
    def __init__(self, controller: EvaluationController, options: MainWindowOptions | None = None):
        super().__init__()
        self._controller = controller
        self._options = options or MainWindowOptions()
        self._pick_dataset = self._options.dataset_picker or self._pick_dataset_with_dialog
        self._last_directory = Path.home()
        self._pending_chart_destination: Path | None = None
        self._score_delegate: ScoreBarDelegate | None = None
        self._info_dialog: InfoDialog | None = None
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
        layout.addWidget(self._info_button)
        layout.addWidget(self._chart_button)
        layout.addWidget(self._export_button)
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(HEADER_HEIGHT)
        header.setLayout(layout)
        return header

    def _build_sidebar(self) -> QFrame:
        layout = QVBoxLayout()
        layout.setContentsMargins(SIDEBAR_MARGIN, SIDEBAR_MARGIN, SIDEBAR_MARGIN, SIDEBAR_MARGIN)
        layout.setSpacing(SIDEBAR_SPACING)
        layout.addLayout(self._build_dataset_section())
        layout.addLayout(self._build_endpoint_section())
        layout.addLayout(self._build_metric_section())
        layout.addStretch(1)
        layout.addWidget(self._build_run_button())
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

    def _build_endpoint_section(self) -> QVBoxLayout:
        self._endpoint_input = QLineEdit(self._options.initial_endpoint)
        self._endpoint_input.setCursorPosition(0)
        self._endpoint_input.setPlaceholderText(ENDPOINT_PLACEHOLDER)
        self._api_key_input = QLineEdit()
        self._api_key_input.setPlaceholderText(OPTIONAL_API_KEY_PLACEHOLDER)
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._model_input = QLineEdit()
        self._model_input.setPlaceholderText(OPTIONAL_MODEL_PLACEHOLDER)
        section = QVBoxLayout()
        section.setSpacing(FORM_SPACING)
        section.addWidget(self._build_section_title("Model endpoint"))
        section.addLayout(self._build_field("URL", self._endpoint_input))
        section.addLayout(self._build_field("API key (optional)", self._api_key_input))
        section.addLayout(self._build_field("Model (optional)", self._model_input))
        return section

    def _build_metric_section(self) -> QVBoxLayout:
        self._method_combo = self._build_method_combo()
        hint = QLabel(METRIC_HINT)
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        section = QVBoxLayout()
        section.setSpacing(SECTION_SPACING)
        section.addWidget(self._build_section_title("Metric"))
        section.addWidget(self._method_combo)
        section.addWidget(hint)
        return section

    def _build_method_combo(self) -> QComboBox:
        combo = ThemedComboBox()
        for method in self._controller.scoring_methods:
            combo.addItem(method.display_name, method.identifier)
        combo.setCurrentIndex(combo.findData(self._controller.selected_method.identifier))
        combo.currentIndexChanged.connect(self._on_method_changed)
        return combo

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
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._table.setColumnWidth(NUMBER_COLUMN, NUMBER_COLUMN_WIDTH)
        self._table.setColumnWidth(SCORE_COLUMN, SCORE_COLUMN_WIDTH)
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

    def _on_run_clicked(self) -> None:
        self._controller.start_evaluation(
            self._endpoint_input.text(),
            self._api_key_input.text(),
            self._model_input.text(),
        )

    def _on_method_changed(self, index: int) -> None:
        self._controller.select_method(self._method_combo.itemData(index))
        self._set_score_header(self._controller.selected_method.column_header)
        self._metric_title_label.setText(self._controller.selected_method.display_name)

    def _on_info_clicked(self) -> None:
        if self._info_dialog is None:
            self._info_dialog = InfoDialog(self)
        self._info_dialog.show()
        self._info_dialog.raise_()
        self._info_dialog.activateWindow()

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
        self._set_dataset_summary(Path(source).name, f"{question_count} questions", is_empty=False)
        self._dataset_card.setToolTip(source)
        self._show_page(CONTENT_PAGE)
        self._show_ready_state()

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
        configuration_widgets = (
            self._endpoint_input,
            self._api_key_input,
            self._model_input,
            self._method_combo,
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
                answer_text, score_text = WAITING_TEXT, IN_PROGRESS_SCORE_TEXT
            else:
                answer_text, score_text = PENDING_TEXT, PENDING_SCORE_TEXT
            self._table.item(row, ANSWER_COLUMN).setText(answer_text)
            self._table.item(row, SCORE_COLUMN).setText(score_text)
            self._style_progress_row(row, row == completed, row > completed)

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
        for row, score in enumerate(result.scores):
            self._table.setItem(row, NUMBER_COLUMN, QTableWidgetItem(str(score.question.identifier)))
            self._table.setItem(row, 1, QTableWidgetItem(score.question.text))
            self._table.setItem(row, 2, QTableWidgetItem(score.question.expected_answer))
            self._table.setItem(row, 3, QTableWidgetItem(score.given_answer))
            score_item = QTableWidgetItem(score_format.format(score.score))
            score_item.setData(SCORE_FRACTION_ROLE, score.score)
            self._table.setItem(row, SCORE_COLUMN, score_item)
        self._table.resizeRowsToContents()
        self._score_delegate.start_reveal()
