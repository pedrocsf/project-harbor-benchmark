from PySide6.QtCore import QElapsedTimer, QEvent, QSize, Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from domain.scoring.scoring_method import ScoreKind
from presentation.controllers.metric_explorer_controller import (
    PLAYBACK_SPEEDS,
    ExplorerExample,
    ExplorerMetric,
    MetricExplorerController,
)
from presentation.views.animations import fade_in_window
from presentation.views.logo_image import LogoImage
from presentation.views.metric_explorer.control_icons import pause_icon, play_icon, restart_icon
from presentation.views.metric_explorer.scenes.base_scene import WalkthroughScene
from presentation.views.metric_explorer.scenes.scene_registry import SceneRegistry
from presentation.views.metric_explorer.step_timeline import StepTimeline
from presentation.views.metric_explorer.walkthrough_canvas import WalkthroughCanvas
from presentation.views.theme import EXPLORER_WINDOW_STYLE
from presentation.views.themed_combo_box import ThemedComboBox

WINDOW_TITLE = "How it works"
WINDOW_SUBTITLE = "See how each metric turns an answer into a score"
WINDOW_WIDTH = 1180
WINDOW_HEIGHT = 760
WINDOW_MINIMUM_WIDTH = 980
WINDOW_MINIMUM_HEIGHT = 640
HEADER_HEIGHT = 56
HEADER_MARGIN = 24
HEADER_SPACING = 12
HEADER_LOGO_SIZE = 28
NAV_WIDTH = 232
NAV_HORIZONTAL_MARGIN = 12
NAV_VERTICAL_MARGIN = 20
NAV_SPACING = 2
NAV_CAPTION_INDENT = 12
METRIC_BUTTON_MARGIN = 8
METRIC_BUTTON_SPACING = 6
METRIC_INDEX_WIDTH = 20
MAIN_MARGIN = 24
MAIN_VERTICAL_MARGIN = 20
MAIN_SPACING = 16
TITLE_SPACING = 12
STAGE_PADDING = 24
SIDE_PANEL_WIDTH = 300
SIDE_PANEL_SPACING = 12
CARD_PADDING = 16
STEPS_SPACING = 4
STEP_ROW_PADDING = 8
STEP_ROW_SPACING = 10
CARD_BORDER_WIDTH = 1
STEP_BADGE_SIZE = 22
STEP_BODY_WIDTH = (
    SIDE_PANEL_WIDTH - 2 * (CARD_PADDING + CARD_BORDER_WIDTH + STEP_ROW_PADDING) - STEP_BADGE_SIZE - STEP_ROW_SPACING
)
STEP_TEXT_SPACING = 3
SIDE_SCROLLBAR_ALLOWANCE = 14
REVEAL_MARGIN = 8
FORMULA_SPACING = 8
CONTROL_BAR_HEIGHT = 52
CONTROL_BAR_PADDING = 12
CONTROL_BAR_SPACING = 12
ICON_BUTTON_SIZE = 36
ICON_SIZE = 16
STEP_COUNTER_WIDTH = 84
SPEED_GROUP_PADDING = 3
SPEED_GROUP_SPACING = 4
TIMER_INTERVAL_MILLISECONDS = 16
MAXIMUM_TICK_SECONDS = 0.1
MILLISECONDS_PER_SECOND = 1000.0
METRICS_CAPTION = "METRICS"
STEPS_CAPTION = "STEPS"
FORMULA_CAPTION = "FORMULA"
EXAMPLE_LABEL = "Example"
CLOSE_TEXT = "Close"
PREVIOUS_STEP_TEXT = "Previous step"
NEXT_STEP_TEXT = "Next step"
PREVIOUS_STEP_TOOLTIP = "Previous step (Left arrow)"
NEXT_STEP_TOOLTIP = "Next step (Right arrow)"
PLAY_TOOLTIP = "Play (Space)"
PAUSE_TOOLTIP = "Pause (Space)"
RESTART_TOOLTIP = "Restart"
PLAY_ACCESSIBLE_NAME = "Play"
PAUSE_ACCESSIBLE_NAME = "Pause"
SPEED_ACCESSIBLE_FORMAT = "Playback speed {:g}×"
CLOSE_ACCESSIBLE_NAME = "Close How it works"
STEP_COUNTER_FORMAT = "Step {current} of {total}"
METRIC_INDEX_FORMAT = "{:02d}"
EXAMPLE_FORMAT = "Q{identifier} · {question}"
SPEED_FORMAT = "{:g}×"
DONE_MARK = "✓"
KIND_SHORT_LABELS = {ScoreKind.CONTINUOUS: "cont", ScoreKind.BINARY: "bin"}
KIND_CHIP_LABELS = {ScoreKind.CONTINUOUS: "continuous · 0 – 1", ScoreKind.BINARY: "binary · 0 or 1"}
ACTIVE_STATE = "active"
DONE_STATE = "done"
FUTURE_STATE = "future"


def _repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def _label(text: str, object_name: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    return label


class _MetricButton(QPushButton):
    def __init__(self, position: int, metric: ExplorerMetric):
        super().__init__()
        self.setObjectName("explorerMetricButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.identifier = metric.identifier
        self._name_label = _label(metric.display_name, "explorerMetricName")
        index_label = _label(METRIC_INDEX_FORMAT.format(position + 1), "explorerMetricIndex")
        index_label.setFixedWidth(METRIC_INDEX_WIDTH)
        kind_label = _label(KIND_SHORT_LABELS[metric.score_kind], "explorerMetricKind")
        layout = QHBoxLayout()
        layout.setContentsMargins(METRIC_BUTTON_MARGIN, 0, METRIC_BUTTON_MARGIN, 0)
        layout.setSpacing(METRIC_BUTTON_SPACING)
        for label in (index_label, self._name_label, kind_label):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(index_label)
        layout.addWidget(self._name_label, stretch=1)
        layout.addWidget(kind_label)
        self.setLayout(layout)

    def set_selected(self, is_selected: bool) -> None:
        self.setChecked(is_selected)
        for widget in (self, self._name_label):
            widget.setProperty("selected", is_selected)
            _repolish(widget)


class _StepRow(QFrame):
    def __init__(self, number: int, title: str):
        super().__init__()
        self.setObjectName("explorerStepRow")
        self._number_text = str(number)
        self._badge = _label(self._number_text, "explorerStepBadge")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label = _label(title, "explorerStepTitle")
        self.body_label = _label("", "explorerStepBody")
        self.body_label.setWordWrap(True)
        self.body_label.setFixedWidth(STEP_BODY_WIDTH)
        texts = QVBoxLayout()
        texts.setContentsMargins(0, 0, 0, 0)
        texts.setSpacing(STEP_TEXT_SPACING)
        texts.addWidget(self.title_label)
        texts.addWidget(self.body_label)
        layout = QHBoxLayout()
        layout.setContentsMargins(STEP_ROW_PADDING, STEP_ROW_PADDING, STEP_ROW_PADDING, STEP_ROW_PADDING)
        layout.setSpacing(STEP_ROW_SPACING)
        layout.addWidget(self._badge, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(texts, stretch=1)
        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    @property
    def state(self) -> str:
        return self.property("state") or FUTURE_STATE

    def set_body(self, text: str) -> None:
        self.body_label.setText(text)
        self._fit_body()
        self._refresh_height()

    def _fit_body(self) -> None:
        self.body_label.ensurePolished()
        self.body_label.setFixedHeight(self.body_label.heightForWidth(STEP_BODY_WIDTH))

    def set_state(self, state: str) -> None:
        self._badge.setText(DONE_MARK if state == DONE_STATE else self._number_text)
        self.body_label.setVisible(state == ACTIVE_STATE)
        for widget in (self, self._badge, self.title_label, self.body_label):
            widget.setProperty("state", state)
            _repolish(widget)
        self._fit_body()
        self._refresh_height()

    def _refresh_height(self) -> None:
        self.layout().invalidate()
        self.layout().activate()
        self.updateGeometry()


class MetricExplorerWindow(QWidget):
    def __init__(
        self,
        controller: MetricExplorerController,
        scene_registry: SceneRegistry,
        badge_text: str | None = None,
    ):
        super().__init__(None, Qt.WindowType.Window)
        self._controller = controller
        self._scene_registry = scene_registry
        self._badge_text = badge_text
        self._metric_buttons: list[_MetricButton] = []
        self._step_rows: list[_StepRow] = []
        self._formula_labels: list[QLabel] = []
        self._displayed_step_index = -1
        self._frame_clock = QElapsedTimer()
        self._frame_timer = QTimer(self)
        self._frame_timer.setInterval(TIMER_INTERVAL_MILLISECONDS)
        self._frame_timer.timeout.connect(self._on_frame)
        self.setObjectName("explorerWindow")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(WINDOW_MINIMUM_WIDTH, WINDOW_MINIMUM_HEIGHT)
        self.setStyleSheet(EXPLORER_WINDOW_STYLE)
        self._build_interface()
        self._connect_controller()
        self._show_metric()

    @property
    def frame_timer(self) -> QTimer:
        return self._frame_timer

    @property
    def canvas(self) -> WalkthroughCanvas:
        return self._canvas

    def select_metric(self, identifier: str) -> None:
        self._controller.select_metric(identifier)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not event.spontaneous():
            fade_in_window(self)
        self.setFocus()
        self._update_frame_timer()

    def keyPressEvent(self, event) -> None:
        action = self._key_actions().get(event.key())
        if action is None or event.modifiers() != Qt.KeyboardModifier.NoModifier:
            super().keyPressEvent(event)
            return
        action()
        event.accept()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._update_frame_timer()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._update_frame_timer()

    def _key_actions(self) -> dict:
        return {
            Qt.Key.Key_Space: self._controller.toggle_play,
            Qt.Key.Key_Left: self._controller.previous_step,
            Qt.Key.Key_Right: self._controller.next_step,
        }

    def _build_interface(self) -> None:
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_navigation())
        body.addLayout(self._build_main_area(), stretch=1)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_header())
        layout.addLayout(body, stretch=1)
        self.setLayout(layout)

    def _build_header(self) -> QFrame:
        titles = QVBoxLayout()
        titles.setSpacing(1)
        titles.addWidget(_label(WINDOW_TITLE, "explorerTitle"))
        titles.addWidget(_label(WINDOW_SUBTITLE, "explorerSubtitle"))
        close_button = QPushButton(CLOSE_TEXT)
        close_button.setObjectName("explorerCloseButton")
        close_button.setAccessibleName(CLOSE_ACCESSIBLE_NAME)
        close_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        close_button.clicked.connect(self.close)
        layout = QHBoxLayout()
        layout.setContentsMargins(HEADER_MARGIN, 0, HEADER_MARGIN, 0)
        layout.setSpacing(HEADER_SPACING)
        layout.addWidget(LogoImage(HEADER_LOGO_SIZE))
        layout.addLayout(titles)
        layout.addStretch(1)
        if self._badge_text:
            layout.addWidget(_label(self._badge_text, "explorerBadge"), alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(close_button)
        header = QFrame()
        header.setObjectName("explorerHeader")
        header.setFixedHeight(HEADER_HEIGHT)
        header.setLayout(layout)
        return header

    def _build_navigation(self) -> QFrame:
        caption = _label(METRICS_CAPTION, "explorerCaption")
        caption.setContentsMargins(NAV_CAPTION_INDENT, 0, NAV_CAPTION_INDENT, STEP_ROW_PADDING)
        layout = QVBoxLayout()
        layout.setContentsMargins(NAV_HORIZONTAL_MARGIN, NAV_VERTICAL_MARGIN, NAV_HORIZONTAL_MARGIN, NAV_VERTICAL_MARGIN)
        layout.setSpacing(NAV_SPACING)
        layout.addWidget(caption)
        self._metric_group = QButtonGroup(self)
        self._metric_group.setExclusive(True)
        for position, metric in enumerate(self._controller.metrics):
            button = _MetricButton(position, metric)
            button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            button.setAccessibleName(metric.display_name)
            button.clicked.connect(lambda _checked=False, identifier=metric.identifier: self._controller.select_metric(identifier))
            self._metric_group.addButton(button)
            self._metric_buttons.append(button)
            layout.addWidget(button)
        layout.addStretch(1)
        navigation = QFrame()
        navigation.setObjectName("explorerNav")
        navigation.setFixedWidth(NAV_WIDTH)
        navigation.setLayout(layout)
        return navigation

    def _build_main_area(self) -> QVBoxLayout:
        content = QHBoxLayout()
        content.setSpacing(MAIN_SPACING)
        content.addWidget(self._build_stage(), stretch=1)
        content.addWidget(self._build_side_panel())
        layout = QVBoxLayout()
        layout.setContentsMargins(MAIN_MARGIN, MAIN_VERTICAL_MARGIN, MAIN_MARGIN, MAIN_VERTICAL_MARGIN)
        layout.setSpacing(MAIN_SPACING)
        layout.addLayout(self._build_title_row())
        layout.addLayout(content, stretch=1)
        layout.addWidget(self._build_control_bar())
        return layout

    def _build_title_row(self) -> QHBoxLayout:
        self._metric_title = _label("", "explorerMetricTitle")
        self._kind_chip = _label("", "explorerKindChip")
        self._example_combo = ThemedComboBox()
        self._example_combo.setObjectName("explorerExampleCombo")
        self._example_combo.setSizeAdjustPolicy(ThemedComboBox.SizeAdjustPolicy.AdjustToContents)
        for example in self._controller.examples:
            self._example_combo.addItem(self._example_text(example))
        self._example_combo.setCurrentIndex(self._controller.selected_example_index)
        self._example_combo.currentIndexChanged.connect(self._controller.select_example)
        example_label = _label(EXAMPLE_LABEL, "explorerExampleLabel")
        example_label.setBuddy(self._example_combo)
        row = QHBoxLayout()
        row.setSpacing(TITLE_SPACING)
        row.addWidget(self._metric_title)
        row.addWidget(self._kind_chip, alignment=Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)
        row.addWidget(example_label)
        row.addWidget(self._example_combo)
        return row

    def _build_stage(self) -> QFrame:
        self._canvas = WalkthroughCanvas(self._controller, self._scene_registry)
        layout = QVBoxLayout()
        layout.setContentsMargins(STAGE_PADDING, STAGE_PADDING, STAGE_PADDING, STAGE_PADDING)
        layout.addWidget(self._canvas)
        stage = QFrame()
        stage.setObjectName("explorerStage")
        stage.setLayout(layout)
        return stage

    def _build_side_panel(self) -> QWidget:
        self._formula_layout = QVBoxLayout()
        self._formula_layout.setContentsMargins(CARD_PADDING, CARD_PADDING, CARD_PADDING, CARD_PADDING)
        self._formula_layout.setSpacing(FORMULA_SPACING)
        self._formula_card = formula_card = QFrame()
        formula_card.setObjectName("explorerCard")
        formula_card.setLayout(self._formula_layout)
        formula_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._formula_result = _label("", "explorerFormulaResult")
        self._formula_result.setTextFormat(Qt.TextFormat.RichText)
        self._limitation_label = _label("", "explorerLimitation")
        self._limitation_label.setWordWrap(True)
        self._limitation_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SIDE_PANEL_SPACING)
        layout.addWidget(self._build_steps_card())
        layout.addWidget(formula_card)
        layout.addWidget(self._limitation_label)
        layout.addStretch(1)
        panel = QWidget()
        panel.setObjectName("explorerSidePanel")
        panel.setFixedWidth(SIDE_PANEL_WIDTH)
        panel.setLayout(layout)
        self._side_scroll = QScrollArea()
        self._side_scroll.setObjectName("explorerSideScroll")
        self._side_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._side_scroll.setWidgetResizable(True)
        self._side_scroll.setFixedWidth(SIDE_PANEL_WIDTH + SIDE_SCROLLBAR_ALLOWANCE)
        self._side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._side_scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._side_scroll.setWidget(panel)
        self._side_scroll.viewport().setAutoFillBackground(False)
        return self._side_scroll

    def _build_steps_card(self) -> QFrame:
        self._steps_layout = QVBoxLayout()
        self._steps_layout.setContentsMargins(0, 0, 0, 0)
        self._steps_layout.setSpacing(STEPS_SPACING)
        layout = QVBoxLayout()
        layout.setContentsMargins(CARD_PADDING, CARD_PADDING, CARD_PADDING, CARD_PADDING)
        layout.setSpacing(STEPS_SPACING)
        layout.addWidget(_label(STEPS_CAPTION, "explorerCaption"))
        layout.addLayout(self._steps_layout)
        card = QFrame()
        card.setObjectName("explorerCard")
        card.setLayout(layout)
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        return card

    def _build_control_bar(self) -> QFrame:
        self._timeline = StepTimeline()
        self._step_counter = _label("", "explorerStepCounter")
        self._step_counter.setFixedWidth(STEP_COUNTER_WIDTH)
        layout = QHBoxLayout()
        layout.setContentsMargins(CONTROL_BAR_PADDING, 0, CONTROL_BAR_PADDING, 0)
        layout.setSpacing(CONTROL_BAR_SPACING)
        for button in self._build_transport_buttons():
            layout.addWidget(button)
        layout.addWidget(self._timeline, stretch=1)
        layout.addWidget(self._step_counter)
        if self._controller.motion_enabled:
            layout.addWidget(self._build_speed_group())
        bar = QFrame()
        bar.setObjectName("explorerControlBar")
        bar.setFixedHeight(CONTROL_BAR_HEIGHT)
        bar.setLayout(layout)
        return bar

    def _build_transport_buttons(self) -> list[QPushButton]:
        self._play_button: QPushButton | None = None
        if not self._controller.motion_enabled:
            previous_button = QPushButton(PREVIOUS_STEP_TEXT)
            next_button = QPushButton(NEXT_STEP_TEXT)
            for button, action, tooltip in (
                (previous_button, self._controller.previous_step, PREVIOUS_STEP_TOOLTIP),
                (next_button, self._controller.next_step, NEXT_STEP_TOOLTIP),
            ):
                button.setObjectName("explorerStepButton")
                button.setToolTip(tooltip)
                button.setAccessibleName(button.text())
                button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.clicked.connect(action)
            return [previous_button, next_button]
        self._play_button = self._build_icon_button("explorerPlayButton", PAUSE_TOOLTIP, PAUSE_ACCESSIBLE_NAME)
        self._play_button.clicked.connect(self._controller.toggle_play)
        restart_button = self._build_icon_button("explorerIconButton", RESTART_TOOLTIP, RESTART_TOOLTIP)
        restart_button.setIcon(restart_icon())
        restart_button.clicked.connect(self._controller.restart)
        return [self._play_button, restart_button]

    def _build_icon_button(self, object_name: str, tooltip: str, accessible_name: str) -> QPushButton:
        button = QPushButton()
        button.setObjectName(object_name)
        button.setToolTip(tooltip)
        button.setAccessibleName(accessible_name)
        button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        button.setFixedSize(ICON_BUTTON_SIZE, ICON_BUTTON_SIZE)
        button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def _build_speed_group(self) -> QFrame:
        self._speed_buttons: dict[float, QPushButton] = {}
        group = QButtonGroup(self)
        group.setExclusive(True)
        layout = QHBoxLayout()
        layout.setContentsMargins(SPEED_GROUP_PADDING, SPEED_GROUP_PADDING, SPEED_GROUP_PADDING, SPEED_GROUP_PADDING)
        layout.setSpacing(SPEED_GROUP_SPACING)
        for speed in PLAYBACK_SPEEDS:
            button = QPushButton(SPEED_FORMAT.format(speed))
            button.setObjectName("explorerSpeedButton")
            button.setCheckable(True)
            button.setAccessibleName(SPEED_ACCESSIBLE_FORMAT.format(speed))
            button.setToolTip(SPEED_ACCESSIBLE_FORMAT.format(speed))
            button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, value=speed: self._controller.set_speed(value))
            group.addButton(button)
            self._speed_buttons[speed] = button
            layout.addWidget(button)
        frame = QFrame()
        frame.setObjectName("explorerSpeedGroup")
        frame.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        frame.setLayout(layout)
        return frame

    def _connect_controller(self) -> None:
        self._controller.metric_changed.connect(lambda _identifier: self._show_metric())
        self._controller.example_changed.connect(self._show_example)
        self._controller.playback_changed.connect(self._show_playback)
        self._controller.position_changed.connect(self._show_position)
        self._controller.parameters_refreshed.connect(self._on_parameters_refreshed)

    def _current_scene(self) -> WalkthroughScene:
        return self._scene_registry.scene_for(self._controller.selected_metric.identifier)

    def _example_text(self, example: ExplorerExample) -> str:
        return EXAMPLE_FORMAT.format(identifier=example.identifier, question=example.question)

    def _show_metric(self) -> None:
        metric = self._controller.selected_metric
        scene = self._current_scene()
        for button in self._metric_buttons:
            button.set_selected(button.identifier == metric.identifier)
        self._metric_title.setText(metric.display_name)
        self._kind_chip.setText(KIND_CHIP_LABELS[metric.score_kind])
        self._rebuild_steps(scene)
        self._show_playback()
        self._refresh_step_texts()
        self._show_position()

    def _show_example(self, index: int) -> None:
        if self._example_combo.currentIndex() != index:
            self._example_combo.blockSignals(True)
            self._example_combo.setCurrentIndex(index)
            self._example_combo.blockSignals(False)
        self._refresh_step_texts()
        self._show_position()

    def _on_parameters_refreshed(self) -> None:
        self._refresh_step_texts()
        self._show_position()

    def _show_playback(self) -> None:
        if self._play_button is not None:
            is_playing = self._controller.is_playing
            self._play_button.setIcon(pause_icon() if is_playing else play_icon())
            self._play_button.setToolTip(PAUSE_TOOLTIP if is_playing else PLAY_TOOLTIP)
            self._play_button.setAccessibleName(PAUSE_ACCESSIBLE_NAME if is_playing else PLAY_ACCESSIBLE_NAME)
            self._speed_buttons[self._controller.speed].setChecked(True)
        self._update_frame_timer()

    def _show_position(self) -> None:
        position = self._controller.current_position
        step_count = self._controller.step_count
        self._timeline.set_state(step_count, position)
        self._step_counter.setText(STEP_COUNTER_FORMAT.format(current=position.step_index + 1, total=step_count))
        if position.step_index != self._displayed_step_index:
            self._displayed_step_index = position.step_index
            self._highlight_step(position.step_index)
        self._canvas.update()

    def _rebuild_steps(self, scene: WalkthroughScene) -> None:
        self._clear_layout(self._steps_layout)
        self._step_rows = []
        for number, step in enumerate(scene.steps, start=1):
            row = _StepRow(number, step.title)
            self._step_rows.append(row)
            self._steps_layout.addWidget(row)
        self._displayed_step_index = -1

    def _rebuild_formula(self, scene: WalkthroughScene, walkthrough: MetricWalkthrough) -> None:
        self._formula_layout.removeWidget(self._formula_result)
        self._clear_layout(self._formula_layout)
        self._formula_labels = []
        self._formula_layout.addWidget(_label(FORMULA_CAPTION, "explorerCaption"))
        for line in scene.formula_for(walkthrough):
            label = _label(line, "explorerFormulaLine")
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setWordWrap(True)
            self._formula_labels.append(label)
            self._formula_layout.addWidget(label)
        self._formula_layout.addWidget(self._formula_result)

    def _refresh_step_texts(self) -> None:
        scene = self._current_scene()
        walkthrough = self._controller.current_walkthrough
        self._limitation_label.setText(scene.limitation_for(walkthrough))
        self._rebuild_formula(scene, walkthrough)
        for step_index, row in enumerate(self._step_rows):
            row.set_body(scene.step_body(step_index, walkthrough))
        self._displayed_step_index = -1

    def _highlight_step(self, active_index: int) -> None:
        for step_index, row in enumerate(self._step_rows):
            if step_index < active_index:
                row.set_state(DONE_STATE)
            elif step_index == active_index:
                row.set_state(ACTIVE_STATE)
            else:
                row.set_state(FUTURE_STATE)
        scene = self._current_scene()
        walkthrough = self._controller.current_walkthrough
        highlighted_lines = set(scene.formula_lines_for(active_index, walkthrough))
        for line_index, label in enumerate(self._formula_labels):
            label.setProperty("highlighted", line_index in highlighted_lines)
            _repolish(label)
        result = scene.formula_result(active_index, walkthrough)
        self._formula_result.setText(result)
        self._formula_result.setVisible(bool(result))
        self._refresh_formula_height()
        QTimer.singleShot(0, self, self._reveal_active_step)

    def _refresh_formula_height(self) -> None:
        self._formula_layout.invalidate()
        self._formula_layout.activate()
        self._formula_card.updateGeometry()
        self._side_scroll.widget().layout().invalidate()
        self._side_scroll.widget().layout().activate()

    def _reveal_active_step(self) -> None:
        if not 0 <= self._displayed_step_index < len(self._step_rows):
            return
        if self._displayed_step_index == 0:
            self._side_scroll.verticalScrollBar().setValue(0)
            return
        self._side_scroll.ensureWidgetVisible(self._step_rows[self._displayed_step_index], 0, REVEAL_MARGIN)

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _should_animate(self) -> bool:
        return (
            self._controller.motion_enabled
            and self._controller.is_playing
            and self.isVisible()
            and not self.isMinimized()
        )

    def _update_frame_timer(self) -> None:
        if not self._should_animate():
            self._frame_timer.stop()
            return
        if not self._frame_timer.isActive():
            self._frame_clock.start()
            self._frame_timer.start()

    def _on_frame(self) -> None:
        delta_seconds = self._frame_clock.restart() / MILLISECONDS_PER_SECOND
        self._controller.tick(min(delta_seconds, MAXIMUM_TICK_SECONDS))
