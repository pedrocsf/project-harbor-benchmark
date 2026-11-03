from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel

from presentation.views.branding import LOGO_RESOURCE_PATH
from presentation.views.resources import resolve_asset_path


class LogoImage(QLabel):
    def __init__(self, size: int):
        super().__init__()
        self.setFixedSize(size, size)
        self.setScaledContents(False)
        pixmap = QPixmap(str(resolve_asset_path(LOGO_RESOURCE_PATH)))
        self.setPixmap(
            pixmap.scaled(
                size * 2,
                size * 2,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.setScaledContents(True)
