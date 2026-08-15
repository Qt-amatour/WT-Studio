from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, Qt, Signal
from PySide6.QtGui import QImage, QMouseEvent, QPixmap, QWheelEvent
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView
from PIL.ImageQt import ImageQt


class TexturePreview(QGraphicsView):
    zoomChanged = Signal(float)

    MIN_ZOOM = 0.05
    MAX_ZOOM = 32.0
    NORMAL_WHEEL_STEP = 1.15
    FAST_WHEEL_STEP = 1.35

    def __init__(self):
        super().__init__()

        self.setObjectName("texturePreview")

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._pixmap_item = QGraphicsPixmapItem()
        self._pixmap_item.setTransformationMode(
            Qt.TransformationMode.SmoothTransformation
        )
        self._scene.addItem(self._pixmap_item)

        self._source_pixmap = QPixmap()
        self._fit_mode = True
        self._panning = False
        self._pan_start = QPoint()
        self._message = "No texture selected"

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.NoAnchor
        )
        self.setResizeAnchor(
            QGraphicsView.ViewportAnchor.NoAnchor
        )

    def show_texture(self, texture):
        self.show_image(getattr(texture, "image", None))

    def show_image(self, image):
        if image is None:
            self.clear_preview("Preview unavailable")
            return

        previous_center = self._normalized_center()
        previous_zoom = self.zoom_percent()
        keep_view = not self._source_pixmap.isNull()

        self._source_pixmap = QPixmap.fromImage(
            QImage(ImageQt(image))
        )
        self._pixmap_item.setPixmap(self._source_pixmap)
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self._message = ""

        if keep_view and not self._fit_mode:
            self.resetTransform()
            self.set_zoom_percent(
                previous_zoom,
                emit_signal=False,
            )
            self._restore_normalized_center(previous_center)
            self._emit_zoom()
        else:
            self.fit_to_view()

        self.viewport().update()

    def clear_preview(self, text="No texture selected"):
        self._source_pixmap = QPixmap()
        self._pixmap_item.setPixmap(QPixmap())
        self._scene.setSceneRect(0, 0, 1, 1)
        self.resetTransform()
        self._fit_mode = True
        self._message = text
        self.zoomChanged.emit(100.0)
        self.viewport().update()

    def fit_to_view(self):
        if self._source_pixmap.isNull():
            return

        rect = self._pixmap_item.boundingRect()
        viewport_rect = self.viewport().rect()

        if (
            rect.isEmpty()
            or viewport_rect.width() <= 0
            or viewport_rect.height() <= 0
        ):
            return

        self.resetTransform()

        scale = min(
            viewport_rect.width() / rect.width(),
            viewport_rect.height() / rect.height(),
        )
        scale = max(self.MIN_ZOOM, min(self.MAX_ZOOM, scale))

        self.scale(scale, scale)
        self.centerOn(self._pixmap_item)
        self._fit_mode = True
        self._emit_zoom()

    def set_zoom_percent(
        self,
        percent: float,
        *,
        anchor_view_pos: QPoint | None = None,
        emit_signal: bool = True,
    ):
        if self._source_pixmap.isNull():
            return

        target_scale = max(
            self.MIN_ZOOM,
            min(self.MAX_ZOOM, float(percent) / 100.0),
        )

        current_scale = self.transform().m11()
        if current_scale <= 0:
            current_scale = 1.0

        if anchor_view_pos is None:
            anchor_view_pos = self.viewport().rect().center()

        scene_before = self.mapToScene(anchor_view_pos)

        self.scale(
            target_scale / current_scale,
            target_scale / current_scale,
        )

        scene_after = self.mapToScene(anchor_view_pos)
        delta = scene_after - scene_before
        self.translate(delta.x(), delta.y())

        self._fit_mode = False

        if emit_signal:
            self._emit_zoom()

    def zoom_percent(self) -> float:
        return self.transform().m11() * 100.0

    def wheelEvent(self, event: QWheelEvent):
        if self._source_pixmap.isNull():
            event.ignore()
            return

        delta = event.angleDelta().y()
        if delta == 0:
            event.ignore()
            return

        fast = bool(
            event.modifiers()
            & Qt.KeyboardModifier.ControlModifier
        )
        step = (
            self.FAST_WHEEL_STEP
            if fast
            else self.NORMAL_WHEEL_STEP
        )
        factor = step if delta > 0 else 1.0 / step

        self.set_zoom_percent(
            self.zoom_percent() * factor,
            anchor_view_pos=event.position().toPoint(),
        )
        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if (
            event.button() == Qt.MouseButton.MiddleButton
            and not self._source_pixmap.isNull()
        ):
            self._panning = True
            self._pan_start = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._panning:
            current = event.position().toPoint()
            delta = current - self._pan_start
            self._pan_start = current

            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if (
            event.button() == Qt.MouseButton.MiddleButton
            and self._panning
        ):
            self._panning = False
            self.unsetCursor()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if not self._source_pixmap.isNull():
            self.fit_to_view()
            event.accept()
            return

        super().mouseDoubleClickEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if self._fit_mode and not self._source_pixmap.isNull():
            self.fit_to_view()

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)

        if not self._source_pixmap.isNull() or not self._message:
            return

        painter.save()
        painter.resetTransform()
        painter.setPen(self.palette().text().color())
        painter.drawText(
            self.viewport().rect(),
            Qt.AlignmentFlag.AlignCenter,
            self._message,
        )
        painter.restore()

    def _normalized_center(self) -> QPointF:
        if self._source_pixmap.isNull():
            return QPointF(0.5, 0.5)

        rect = self._pixmap_item.boundingRect()
        if rect.width() <= 0 or rect.height() <= 0:
            return QPointF(0.5, 0.5)

        center = self.mapToScene(self.viewport().rect().center())

        return QPointF(
            (center.x() - rect.left()) / rect.width(),
            (center.y() - rect.top()) / rect.height(),
        )

    def _restore_normalized_center(self, position: QPointF):
        rect = self._pixmap_item.boundingRect()

        self.centerOn(
            QPointF(
                rect.left() + rect.width() * position.x(),
                rect.top() + rect.height() * position.y(),
            )
        )

    def _emit_zoom(self):
        self.zoomChanged.emit(self.zoom_percent())
