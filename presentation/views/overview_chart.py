from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPen

from domain.entities.metric_overview import MetricOverview, MetricOverviewEntry
from domain.scoring.scoring_method import ScoreKind
from presentation.views.branding import (
    APPLICATION_NAME,
    APPLICATION_SUBTITLE,
    BACKGROUND_COLOR,
    BORDER_COLOR,
    LOGO_RESOURCE_PATH,
    PRIMARY_COLOR,
    SECONDARY_TEXT_COLOR,
)
from presentation.views.resources import resolve_asset_path

PIXEL_RATIO = 2
MARGIN = 56
HEADER_HEIGHT = 140
FOOTER_HEIGHT = 70
LOGO_SIZE = 72
PANEL_PADDING = 28
PANEL_RADIUS = 18
PANEL_TITLE_HEIGHT = 64
COLUMN_BAND_HEIGHT = 44
ROW_SLOT_HEIGHT = 64
ROW_GAP = 10
AXIS_HEIGHT = 48
LABEL_COLUMN_WIDTH = 200
BAR_COLUMN_WIDTH = 760
VALUE_LABEL_WIDTH = 76
BAR_THICKNESS = 24
BAR_RADIUS = 6
MEDIAN_MARKER_DIAMETER = 12
GRID_VALUES = (0.0, 0.25, 0.5, 0.75, 1.0)
DARK_TEXT_COLOR = QColor(BACKGROUND_COLOR)
LIGHT_TEXT_COLOR = QColor(255, 255, 255)
SOFT_TEXT_COLOR = QColor(SECONDARY_TEXT_COLOR)
PANEL_FILL_COLOR = QColor(255, 255, 255, 18)
PANEL_BORDER_COLOR = QColor(255, 255, 255, 36)
GRID_LINE_COLOR = QColor(255, 255, 255, 40)


@dataclass(frozen=True)
class _Geometry:
    canvas_width: float
    canvas_height: float
    panel: QRectF
    label_left: float
    bar_left: float
    bar_right: float
    plot_top: float
    plot_bottom: float


def render_overview_chart(overview: MetricOverview) -> QImage:
    geometry = _build_geometry(len(overview.entries))
    image = QImage(
        int(geometry.canvas_width * PIXEL_RATIO),
        int(geometry.canvas_height * PIXEL_RATIO),
        QImage.Format.Format_ARGB32,
    )
    image.setDevicePixelRatio(PIXEL_RATIO)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    _draw_background(painter, geometry)
    _draw_header(painter, overview)
    _draw_panel(painter, geometry.panel)
    _draw_panel_titles(painter, geometry)
    _draw_bar_grid(painter, geometry)
    for index, entry in enumerate(overview.entries):
        center_y = geometry.plot_top + ROW_SLOT_HEIGHT * (index + 0.5)
        _draw_metric_label(painter, entry, center_y, geometry)
        _draw_bar(painter, entry, center_y, geometry)
    _draw_footer(painter, geometry, overview)
    painter.end()
    return image


def _build_geometry(metric_count: int) -> _Geometry:
    rows = max(1, metric_count)
    inner_width = LABEL_COLUMN_WIDTH + BAR_COLUMN_WIDTH
    panel_height = 2 * PANEL_PADDING + PANEL_TITLE_HEIGHT + COLUMN_BAND_HEIGHT + rows * ROW_SLOT_HEIGHT + AXIS_HEIGHT
    label_left = MARGIN + PANEL_PADDING
    plot_top = HEADER_HEIGHT + PANEL_PADDING + PANEL_TITLE_HEIGHT + COLUMN_BAND_HEIGHT
    return _Geometry(
        canvas_width=2 * MARGIN + 2 * PANEL_PADDING + inner_width,
        canvas_height=HEADER_HEIGHT + panel_height + FOOTER_HEIGHT,
        panel=QRectF(MARGIN, HEADER_HEIGHT, 2 * PANEL_PADDING + inner_width, panel_height),
        label_left=label_left,
        bar_left=label_left + LABEL_COLUMN_WIDTH,
        bar_right=label_left + LABEL_COLUMN_WIDTH + BAR_COLUMN_WIDTH - VALUE_LABEL_WIDTH,
        plot_top=plot_top,
        plot_bottom=plot_top + rows * ROW_SLOT_HEIGHT,
    )


def _set_font(painter: QPainter, pixel_size: int, bold: bool = False) -> None:
    font = QFont(painter.font())
    font.setPixelSize(pixel_size)
    font.setBold(bold)
    painter.setFont(font)


def _draw_background(painter: QPainter, geometry: _Geometry) -> None:
    gradient = QLinearGradient(0, 0, geometry.canvas_width, geometry.canvas_height)
    gradient.setColorAt(0.0, QColor(BACKGROUND_COLOR))
    gradient.setColorAt(1.0, QColor(BORDER_COLOR))
    painter.fillRect(QRectF(0, 0, geometry.canvas_width, geometry.canvas_height), gradient)


def _draw_logo(painter: QPainter) -> None:
    logo = QImage(str(resolve_asset_path(LOGO_RESOURCE_PATH)))
    if logo.isNull():
        return
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.drawImage(QRectF(0, 0, LOGO_SIZE, LOGO_SIZE), logo)


def _draw_header(painter: QPainter, overview: MetricOverview) -> None:
    painter.save()
    painter.translate(MARGIN, 36)
    _draw_logo(painter)
    painter.restore()
    text_left = MARGIN + LOGO_SIZE + 24
    painter.setPen(LIGHT_TEXT_COLOR)
    _set_font(painter, 36, bold=True)
    painter.drawText(QPointF(text_left, 74), APPLICATION_NAME)
    painter.setPen(SOFT_TEXT_COLOR)
    _set_font(painter, 20)
    subtitle = f"Metric overview · {len(overview.questions)} questions · {overview.evaluated_at:%Y-%m-%d %H:%M}"
    painter.drawText(QPointF(text_left, 104), subtitle)


def _draw_panel(painter: QPainter, rect: QRectF) -> None:
    painter.setPen(QPen(PANEL_BORDER_COLOR, 1))
    painter.setBrush(PANEL_FILL_COLOR)
    painter.drawRoundedRect(rect, PANEL_RADIUS, PANEL_RADIUS)


def _draw_panel_titles(painter: QPainter, geometry: _Geometry) -> None:
    inner = geometry.panel.adjusted(PANEL_PADDING, PANEL_PADDING, -PANEL_PADDING, -PANEL_PADDING)
    painter.setPen(LIGHT_TEXT_COLOR)
    _set_font(painter, 24, bold=True)
    painter.drawText(QPointF(inner.left(), inner.top() + 24), "Performance per metric")
    painter.setPen(SOFT_TEXT_COLOR)
    _set_font(painter, 15)
    painter.drawText(
        QPointF(inner.left(), inner.top() + 50),
        "Bar: mean  ·  Dot: median",
    )
    band_baseline = geometry.plot_top - 14
    painter.setPen(LIGHT_TEXT_COLOR)
    _set_font(painter, 17, bold=True)
    painter.drawText(QPointF(geometry.bar_left, band_baseline), "Average score")


def _draw_bar_grid(painter: QPainter, geometry: _Geometry) -> None:
    _set_font(painter, 14)
    axis_width = geometry.bar_right - geometry.bar_left
    for value in GRID_VALUES:
        x = geometry.bar_left + value * axis_width
        painter.setPen(QPen(GRID_LINE_COLOR, 1))
        painter.drawLine(QPointF(x, geometry.plot_top), QPointF(x, geometry.plot_bottom))
        painter.setPen(SOFT_TEXT_COLOR)
        label_rect = QRectF(x - 30, geometry.plot_bottom + 6, 60, AXIS_HEIGHT - 6)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, f"{value:g}")


def _draw_metric_label(painter: QPainter, entry: MetricOverviewEntry, center_y: float, geometry: _Geometry) -> None:
    painter.setPen(LIGHT_TEXT_COLOR)
    _set_font(painter, 17)
    label = painter.fontMetrics().elidedText(
        entry.method.display_name, Qt.TextElideMode.ElideRight, int(LABEL_COLUMN_WIDTH - 20)
    )
    label_rect = QRectF(geometry.label_left, center_y - 16, LABEL_COLUMN_WIDTH - 16, 32)
    painter.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)


def _draw_bar(painter: QPainter, entry: MetricOverviewEntry, center_y: float, geometry: _Geometry) -> None:
    axis_width = geometry.bar_right - geometry.bar_left
    gradient = QLinearGradient(geometry.bar_left, 0, geometry.bar_right, 0)
    gradient.setColorAt(0.0, QColor(PRIMARY_COLOR))
    gradient.setColorAt(1.0, QColor(SECONDARY_TEXT_COLOR))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(gradient)
    bar_width = max(2.0, entry.average_score * axis_width)
    painter.drawRoundedRect(
        QRectF(geometry.bar_left, center_y - BAR_THICKNESS / 2, bar_width, BAR_THICKNESS), BAR_RADIUS, BAR_RADIUS
    )

    median_x = geometry.bar_left + entry.median_score * axis_width
    painter.setPen(QPen(DARK_TEXT_COLOR, 2))
    painter.setBrush(LIGHT_TEXT_COLOR)
    painter.drawEllipse(QPointF(median_x, center_y), MEDIAN_MARKER_DIAMETER / 2, MEDIAN_MARKER_DIAMETER / 2)

    painter.setPen(LIGHT_TEXT_COLOR)
    _set_font(painter, 18, bold=True)
    value_rect = QRectF(geometry.bar_right + 12, center_y - 16, VALUE_LABEL_WIDTH, 32)
    painter.drawText(
        value_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"{entry.average_score:.3f}"
    )


def _draw_footer(painter: QPainter, geometry: _Geometry, overview: MetricOverview) -> None:
    baseline = geometry.canvas_height - 28
    painter.setPen(SOFT_TEXT_COLOR)
    _set_font(painter, 15)
    painter.drawText(QPointF(MARGIN, baseline), f"{APPLICATION_NAME} · {APPLICATION_SUBTITLE}")
    notes = "Scores range from 0 to 1."
    if any(entry.method.score_kind is ScoreKind.BINARY for entry in overview.entries):
        notes += " Binary metrics score each answer 0 or 1."
    notes_rect = QRectF(MARGIN, baseline - 20, geometry.canvas_width - 2 * MARGIN, 28)
    painter.drawText(notes_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, notes)
