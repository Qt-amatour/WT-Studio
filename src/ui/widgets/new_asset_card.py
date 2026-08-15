from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.models.new_asset_material import NewAssetMaterial
from app.models.new_asset_types import NewAssetSlotType, NewAssetType
from app.services.new_asset_builder import (
    NewAssetBuilder,
    NewAssetSlotLoadError,
)
from app.services.path_settings import PathSettings
from ui.widgets.downward_combo_box import DownwardComboBox
from ui.widgets.message_box import QMessageBox


class NewAssetSlotRow(QWidget):
    changed = Signal()

    FILE_FILTER = (
        "Textures (*.dds *.tga *.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp);;"
        "All Files (*.*)"
    )

    def __init__(
        self,
        *,
        material: NewAssetMaterial,
        slot_type: NewAssetSlotType,
        builder: NewAssetBuilder,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.material = material
        self.slot_type = slot_type
        self.builder = builder

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)

        label = QLabel(slot_type.display_name)
        label.setMinimumWidth(105)

        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("No texture selected")

        self.browse_button = QPushButton("Browse")
        self.reload_button = QPushButton("Reload")
        self.clear_button = QToolButton()
        self.clear_button.setText("×")

        self.browse_button.setToolTip(
            f"Assign a source texture to the {slot_type.display_name} slot."
        )
        self.reload_button.setToolTip(
            "Reload this slot from its source file on disk."
        )
        self.clear_button.setToolTip(
            "Clear this slot without deleting the source file."
        )

        row.addWidget(label)
        row.addWidget(self.path_edit, 1)
        row.addWidget(self.browse_button)
        row.addWidget(self.reload_button)
        row.addWidget(self.clear_button)
        root.addLayout(row)

        self.browse_button.clicked.connect(self._browse)
        self.reload_button.clicked.connect(self._reload)
        self.clear_button.clicked.connect(self._clear)
        self.refresh()

    def refresh(self) -> None:
        slot = self.material.slot(self.slot_type)
        self.path_edit.setText(str(slot.source_path or ""))
        self.path_edit.setToolTip(
            slot.error or str(slot.source_path or "")
        )
        self.reload_button.setEnabled(slot.source_path is not None)
        self.clear_button.setEnabled(slot.source_path is not None)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            f"Select {self.slot_type.display_name}",
            PathSettings.session_working_dialog_path(),
            self.FILE_FILTER,
        )
        if not path:
            return

        PathSettings.set_session_working_directory(
            Path(path).parent
        )

        try:
            self.builder.assign_path(
                self.material,
                self.slot_type,
                Path(path),
            )
        except NewAssetSlotLoadError as error:
            QMessageBox.warning(
                self,
                "New Asset Texture",
                str(error),
            )

        self.refresh()
        self.changed.emit()

    def _reload(self) -> None:
        try:
            self.builder.reload_slot(
                self.material,
                self.slot_type,
            )
        except NewAssetSlotLoadError as error:
            QMessageBox.warning(
                self,
                "Reload Texture",
                str(error),
            )

        self.refresh()
        self.changed.emit()

    def _clear(self) -> None:
        self.builder.clear_slot(
            self.material,
            self.slot_type,
        )
        self.refresh()
        self.changed.emit()


class NewAssetCard(QFrame):
    previewRequested = Signal(object)
    deleteRequested = Signal(object)
    exportAvailabilityChanged = Signal(object, bool)
    projectChanged = Signal()

    def __init__(
        self,
        *,
        material: NewAssetMaterial,
        builder: NewAssetBuilder,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.material = material
        self.builder = builder
        self.export_enabled = True

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        root = QVBoxLayout(self)

        header = QHBoxLayout()
        self.name_edit = QLineEdit(
            self._normalize_name(material.name)
        )
        self.material.name = self.name_edit.text()

        self.type_combo = DownwardComboBox()
        for asset_type in NewAssetType:
            self.type_combo.addItem(
                asset_type.display_name,
                asset_type,
            )
        self.type_combo.setCurrentIndex(
            self.type_combo.findData(material.asset_type)
        )

        self.delete_button = QPushButton("Delete")
        self.delete_button.setToolTip(
            "Remove this NEW ASSETS material from the project. "
            "Source files remain on disk."
        )
        self.type_combo.setToolTip(
            "Change the asset texture type and rebuild the required input slots."
        )

        header.addWidget(self.name_edit, 1)
        header.addWidget(self.type_combo)
        header.addWidget(self.delete_button)
        root.addLayout(header)

        self.slots_container = QWidget()
        self.slots_layout = QVBoxLayout(self.slots_container)
        self.slots_layout.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.slots_container)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        self.opengl_normal_check = QCheckBox(
            "OpenGL normal map"
        )
        self.opengl_normal_check.setToolTip(
            "Enable when the input RGB normal map uses the OpenGL "
            "convention. NEW ASSETS exports DirectX Y in the final _n TGA."
        )
        self.opengl_normal_check.setChecked(
            bool(material.normal_map_opengl)
        )
        self.opengl_normal_check.setVisible(
            material.asset_type is NewAssetType.NORMAL
        )
        root.addWidget(self.opengl_normal_check)

        self.export_check = QCheckBox("Available to export")
        self.export_check.setChecked(True)
        self.export_check.setToolTip(
            "Include this card when using Export Selected."
        )
        root.addWidget(self.export_check)

        self.name_edit.textChanged.connect(self._name_changed)
        self.type_combo.currentIndexChanged.connect(self._type_changed)
        self.delete_button.clicked.connect(
            lambda: self.deleteRequested.emit(self.material)
        )
        self.opengl_normal_check.toggled.connect(
            self._opengl_normal_toggled
        )
        self.export_check.toggled.connect(self._export_toggled)

        self._rebuild_rows()
        self._refresh_status()
        self._apply_export_state()

    def _name_changed(self, text: str) -> None:
        normalized = self._normalize_name(text)
        if normalized:
            self.material.name = normalized
            self.projectChanged.emit()

    def _type_changed(self) -> None:
        selected_type = self.type_combo.currentData()
        if selected_type == self.material.asset_type:
            return

        if self.material.has_any_source:
            answer = QMessageBox.question(
                self,
                "Change Asset Type",
                "Changing the type may remove assignments not used by "
                "the new asset type.",
            )
            if answer != QMessageBox.StandardButton.Yes:
                self.type_combo.blockSignals(True)
                self.type_combo.setCurrentIndex(
                    self.type_combo.findData(
                        self.material.asset_type
                    )
                )
                self.type_combo.blockSignals(False)
                return

        self.material.set_type(selected_type)
        self.opengl_normal_check.blockSignals(True)
        self.opengl_normal_check.setChecked(
            bool(self.material.normal_map_opengl)
        )
        self.opengl_normal_check.blockSignals(False)
        self.opengl_normal_check.setVisible(
            self.material.asset_type is NewAssetType.NORMAL
        )
        self._rebuild_rows()
        self.builder.build(self.material)
        self._refresh_status()
        self.previewRequested.emit(self.material)
        self.projectChanged.emit()

    def _rebuild_rows(self) -> None:
        while self.slots_layout.count():
            item = self.slots_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for slot_type in self.material.slots:
            row = NewAssetSlotRow(
                material=self.material,
                slot_type=slot_type,
                builder=self.builder,
            )
            row.changed.connect(self._slot_changed)
            self.slots_layout.addWidget(row)

    def _slot_changed(self) -> None:
        self._refresh_status()
        self.previewRequested.emit(self.material)
        self.projectChanged.emit()

    def _opengl_normal_toggled(self, enabled: bool) -> None:
        self.material.normal_map_opengl = bool(enabled)
        self.material.is_dirty = True
        self.builder.build(self.material)
        self._refresh_status()
        self.previewRequested.emit(self.material)
        self.projectChanged.emit()

    def mousePressEvent(self, event) -> None:
        child = self.childAt(event.position().toPoint())
        interactive = (
            QPushButton,
            QToolButton,
            QLineEdit,
            QComboBox,
            QCheckBox,
        )

        if not isinstance(child, interactive):
            self.builder.build(self.material)
            self._refresh_status()
            self.previewRequested.emit(self.material)

        super().mousePressEvent(event)

    def _export_toggled(self, enabled: bool) -> None:
        self.export_enabled = bool(enabled)
        self._apply_export_state()
        self.exportAvailabilityChanged.emit(
            self.material,
            self.export_enabled,
        )
        self.projectChanged.emit()

    def _apply_export_state(self) -> None:
        enabled = self.export_enabled
        self.name_edit.setEnabled(enabled)
        self.type_combo.setEnabled(enabled)
        self.slots_container.setEnabled(enabled)
        self.status_label.setEnabled(enabled)
        self.opengl_normal_check.setEnabled(enabled)

        self.setProperty("exportInactive", not enabled)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    @staticmethod
    def _normalize_name(text: str) -> str:
        value = re.sub(r"\s+", "_", str(text).strip())
        value = re.sub(r"_+", "_", value)
        return value or "Asset"

    def _refresh_status(self) -> None:
        if self.material.build_error:
            text = f"Not ready: {self.material.build_error}"
        elif self.material.build_warnings:
            text = (
                "Ready with warning: "
                + " ".join(self.material.build_warnings)
            )
        elif self.material.preview_image is not None:
            text = "Ready — AssetViewer TGA source built."
        else:
            text = "Assign textures to build the new asset source."
        self.status_label.setText(text)
