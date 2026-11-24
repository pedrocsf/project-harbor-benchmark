from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from domain.entities.rag_endpoint_settings import DEFAULT_ANSWER_FIELD, DEFAULT_CONTEXTS_FIELD
from presentation.controllers.answer_source import ANSWER_SOURCE_LABELS, AnswerSource, RagEndpointInput
from presentation.views.themed_combo_box import ThemedComboBox

FIELD_SPACING = 6
FORM_SPACING = 12
SECTION_SPACING = 8
RAG_ENDPOINT_PLACEHOLDER = "http://127.0.0.1:8000/rag"
OPTIONAL_PLACEHOLDER = "Optional"
NO_RUN_TEXT = "No run loaded"
NO_RUN_HINT = "JSON or JSONL with id, answer, contexts"
RUN_COUNT_TEXT = "{count} answers · {contexts}"
WITH_CONTEXTS_TEXT = "with contexts"
WITHOUT_CONTEXTS_TEXT = "no contexts"
RAG_FIELDS_HINT = (
    "Receives {\"question\": …} and reads the answer and the contexts from these fields. "
    "Use dots for nested fields. A URL ending in /chat/completions is called like an OpenAI model."
)


def _build_field(caption: str, widget: QWidget) -> QVBoxLayout:
    label = QLabel(caption)
    label.setObjectName("fieldLabel")
    field = QVBoxLayout()
    field.setSpacing(FIELD_SPACING)
    field.addWidget(label)
    field.addWidget(widget)
    return field


class AnswerSourcePanel(QWidget):
    source_changed = Signal(object)
    load_run_requested = Signal()

    def __init__(self, supports_run_import: bool, parent: QWidget | None = None):
        super().__init__(parent)
        self._source_combo = ThemedComboBox()
        for source, label in ANSWER_SOURCE_LABELS.items():
            self._source_combo.addItem(label, source)
        if not supports_run_import:
            self._disable_source(AnswerSource.IMPORTED_RUN)
        self._source_combo.currentIndexChanged.connect(self._on_source_changed)
        self._rag_fields = self._build_rag_fields()
        self._run_fields = self._build_run_fields()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(FORM_SPACING)
        layout.addWidget(self._source_combo)
        layout.addWidget(self._rag_fields)
        layout.addWidget(self._run_fields)
        self.setLayout(layout)
        self._show_fields_for(self.source)

    @property
    def source(self) -> AnswerSource:
        return self._source_combo.currentData()

    @property
    def source_combo(self) -> ThemedComboBox:
        return self._source_combo

    def rag_input(self) -> RagEndpointInput:
        return RagEndpointInput(
            url=self._rag_url_input.text(),
            api_key=self._rag_api_key_input.text(),
            answer_field=self._answer_field_input.text(),
            contexts_field=self._contexts_field_input.text(),
        )

    def select_source(self, source: AnswerSource) -> None:
        self._source_combo.setCurrentIndex(self._source_combo.findData(source))

    def set_rag_url(self, url: str) -> None:
        self._rag_url_input.setText(url)
        self._rag_url_input.setCursorPosition(0)

    def show_imported_run(self, name: str, answer_count: int, has_contexts: bool) -> None:
        contexts_text = WITH_CONTEXTS_TEXT if has_contexts else WITHOUT_CONTEXTS_TEXT
        self._run_name_label.setText(name)
        self._run_count_label.setText(RUN_COUNT_TEXT.format(count=answer_count, contexts=contexts_text))
        self._run_card.setProperty("empty", False)
        self._repolish(self._run_card)

    def set_inputs_enabled(self, is_enabled: bool) -> None:
        widgets = (
            self._source_combo,
            self._rag_url_input,
            self._rag_api_key_input,
            self._answer_field_input,
            self._contexts_field_input,
            self._load_run_button,
        )
        for widget in widgets:
            widget.setEnabled(is_enabled)

    def _build_rag_fields(self) -> QWidget:
        self._rag_url_input = QLineEdit()
        self._rag_url_input.setPlaceholderText(RAG_ENDPOINT_PLACEHOLDER)
        self._rag_api_key_input = QLineEdit()
        self._rag_api_key_input.setPlaceholderText(OPTIONAL_PLACEHOLDER)
        self._rag_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._answer_field_input = QLineEdit(DEFAULT_ANSWER_FIELD)
        self._contexts_field_input = QLineEdit(DEFAULT_CONTEXTS_FIELD)
        field_row = QHBoxLayout()
        field_row.setSpacing(FORM_SPACING)
        field_row.addLayout(_build_field("Answer field", self._answer_field_input))
        field_row.addLayout(_build_field("Contexts field", self._contexts_field_input))
        hint = QLabel(RAG_FIELDS_HINT)
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(FORM_SPACING)
        layout.addLayout(_build_field("RAG URL", self._rag_url_input))
        layout.addLayout(_build_field("API key (optional)", self._rag_api_key_input))
        layout.addLayout(field_row)
        layout.addWidget(hint)
        container = QWidget()
        container.setLayout(layout)
        return container

    def _build_run_fields(self) -> QWidget:
        self._run_name_label = QLabel(NO_RUN_TEXT)
        self._run_name_label.setObjectName("datasetName")
        self._run_count_label = QLabel(NO_RUN_HINT)
        self._run_count_label.setObjectName("datasetCount")
        self._run_count_label.setWordWrap(True)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(2)
        card_layout.addWidget(self._run_name_label)
        card_layout.addWidget(self._run_count_label)
        self._run_card = QFrame()
        self._run_card.setObjectName("datasetCard")
        self._run_card.setProperty("empty", True)
        self._run_card.setLayout(card_layout)
        self._load_run_button = QPushButton("Load run…")
        self._load_run_button.clicked.connect(self.load_run_requested)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SECTION_SPACING)
        layout.addWidget(self._run_card)
        layout.addWidget(self._load_run_button)
        container = QWidget()
        container.setLayout(layout)
        return container

    def _disable_source(self, source: AnswerSource) -> None:
        model = self._source_combo.model()
        if isinstance(model, QStandardItemModel):
            model.item(self._source_combo.findData(source)).setFlags(Qt.ItemFlag.NoItemFlags)

    def _on_source_changed(self, index: int) -> None:
        self._show_fields_for(self.source)
        self.source_changed.emit(self.source)

    def _show_fields_for(self, source: AnswerSource) -> None:
        self._rag_fields.setVisible(source is AnswerSource.RAG_ENDPOINT)
        self._run_fields.setVisible(source is AnswerSource.IMPORTED_RUN)

    def _repolish(self, widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
