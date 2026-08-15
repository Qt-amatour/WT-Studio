from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
    QTransform,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication


ICON_DIRECTORY = (
    Path(__file__).resolve().parent
    / "resources"
    / "icons"
)


def icon_path(filename: str) -> Path:
    """Return the absolute path of an icon shipped with WT Studio."""
    return ICON_DIRECTORY / filename


def stylesheet_icon_url(filename: str) -> str:
    """Return a QSS-safe absolute URL for an SVG resource."""
    return icon_path(filename).resolve().as_posix()


def _device_pixel_ratio() -> float:
    app = QApplication.instance()
    if app is None:
        return 1.0

    screen = app.primaryScreen()
    if screen is None:
        return 1.0

    return max(1.0, float(screen.devicePixelRatio()))


@lru_cache(maxsize=128)
def _svg_pixmap(
    filename: str,
    size: int,
    ratio_key: int,
) -> QPixmap:
    ratio = max(1.0, ratio_key / 100.0)
    physical_size = max(1, round(size * ratio))

    pixmap = QPixmap(physical_size, physical_size)
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)

    renderer = QSvgRenderer(str(icon_path(filename)))
    if not renderer.isValid():
        return pixmap

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(
        painter,
        QRectF(
            0.0,
            0.0,
            float(physical_size),
            float(physical_size),
        ),
    )
    painter.end()

    return pixmap


@lru_cache(maxsize=64)
def _padded_svg_pixmap(
    filename: str,
    size: int,
    inset: int,
    ratio_key: int,
) -> QPixmap:
    """Render an SVG with a real transparent margin inside its pixmap."""
    ratio = max(1.0, ratio_key / 100.0)
    physical_size = max(1, round(size * ratio))
    physical_inset = max(0, round(inset * ratio))

    pixmap = QPixmap(physical_size, physical_size)
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)

    renderer = QSvgRenderer(str(icon_path(filename)))
    if not renderer.isValid():
        return pixmap

    render_size = max(
        1,
        physical_size - (2 * physical_inset),
    )

    painter = QPainter(pixmap)
    painter.setRenderHint(
        QPainter.RenderHint.Antialiasing,
        True,
    )
    renderer.render(
        painter,
        QRectF(
            float(physical_inset),
            float(physical_inset),
            float(render_size),
            float(render_size),
        ),
    )
    painter.end()

    return pixmap



def svg_icon(filename: str, size: int = 16) -> QIcon:
    ratio_key = int(round(_device_pixel_ratio() * 100.0))
    return QIcon(
        _svg_pixmap(
            filename,
            max(1, int(size)),
            ratio_key,
        )
    )


def application_icon(size: int = 32) -> QIcon:
    """Return the Windows/application icon with the dark circular badge."""
    return svg_icon(
        "wt_studio_background_logo.svg",
        size,
    )


def brand_logo_icon(size: int = 32) -> QIcon:
    """Return the clean orange WT Studio logo used inside the custom UI."""
    return svg_icon(
        "wt_studio_logo.svg",
        size,
    )


def panel_chevron_icon(
    expanded: bool,
    size: int = 12,
    *,
    disabled: bool = False,
) -> QIcon:
    direction = "down" if expanded else "right"
    suffix = "_disabled" if disabled else ""

    return svg_icon(
        f"chevron_{direction}{suffix}.svg",
        size,
    )


def vertical_chevron_icon(
    direction: str,
    size: int = 14,
    *,
    disabled: bool = False,
) -> QIcon:
    """Return the existing slim chevron oriented up or down."""
    normalized = str(direction or "").strip().casefold()
    suffix = "_disabled" if disabled else ""

    base = svg_icon(
        f"chevron_down{suffix}.svg",
        size,
    )

    if normalized != "up":
        return base

    pixmap = base.pixmap(size, size)
    rotated = pixmap.transformed(
        QTransform().rotate(180.0),
        Qt.TransformationMode.SmoothTransformation,
    )
    return QIcon(rotated)


def message_icon(kind: str, size: int = 44) -> QIcon:
    normalized = str(kind or "").strip().casefold()
    filename = {
        "warning": "warning.svg",
        "information": "information.svg",
        "question": "question.svg",
        "critical": "critical.svg",
        "success": "success.svg",
    }.get(normalized, "information.svg")

    ratio_key = int(round(_device_pixel_ratio() * 100.0))

    # Alert icons need a real transparent inset inside the pixmap.
    # Increasing only the QLabel size does not prevent SVG strokes from
    # touching the edge of their own rendered image.
    return QIcon(
        _padded_svg_pixmap(
            filename,
            max(1, int(size)),
            2,
            ratio_key,
        )
    )


def _pixel_canvas(size: int) -> tuple[QPixmap, QPainter, float]:
    """Create a DPR-aware canvas addressed directly in physical pixels."""
    ratio = _device_pixel_ratio()
    physical_size = max(1, round(size * ratio))

    pixmap = QPixmap(physical_size, physical_size)
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    return pixmap, painter, ratio


def window_control_icon(kind: str, size: int = 16) -> QIcon:
    """Render crisp, pixel-aligned title-bar controls at the requested size."""
    pixmap, painter, ratio = _pixel_canvas(size)

    def px(value: float) -> int:
        return int(round(value * ratio))

    stroke = max(1, int(round(ratio)))
    pen = QPen(QColor("#B8B8B8"))
    pen.setWidth(stroke)
    pen.setCapStyle(Qt.PenCapStyle.SquareCap)
    pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if kind == "minimize":
        painter.drawLine(px(4), px(11), px(12), px(11))

    elif kind == "maximize":
        painter.drawRect(
            QRect(
                px(4),
                px(4),
                max(1, px(8)),
                max(1, px(8)),
            )
        )

    elif kind == "restore":
        painter.drawLine(px(6), px(3), px(13), px(3))
        painter.drawLine(px(13), px(3), px(13), px(10))
        painter.drawLine(px(6), px(3), px(6), px(5))
        painter.drawLine(px(10), px(10), px(13), px(10))
        painter.drawRect(
            QRect(
                px(3),
                px(6),
                max(1, px(7)),
                max(1, px(7)),
            )
        )

    elif kind == "close":
        painter.drawLine(px(4), px(4), px(12), px(12))
        painter.drawLine(px(12), px(4), px(4), px(12))

    painter.end()
    return QIcon(pixmap)
