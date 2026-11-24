from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from presentation.controllers.metric_explorer_controller import MetricExplorerController
from presentation.views.metric_explorer.scenes.scene_registry import SceneRegistry

CANVAS_MINIMUM_WIDTH = 320
CANVAS_MINIMUM_HEIGHT = 280


class WalkthroughCanvas(QWidget):
    def __init__(self, controller: MetricExplorerController, scene_registry: SceneRegistry, parent: QWidget | None = None):
        super().__init__(parent)
        self._controller = controller
        self._scene_registry = scene_registry
        self.setObjectName("explorerCanvas")
        self.setMinimumSize(CANVAS_MINIMUM_WIDTH, CANVAS_MINIMUM_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.paint_into(painter, QRectF(self.rect()))
        painter.end()

    def paint_into(self, painter: QPainter, area: QRectF) -> None:
        scene = self._scene_registry.scene_for(self._controller.selected_metric.identifier)
        scene.paint(painter, area, self._controller.current_walkthrough, self._controller.current_position)
