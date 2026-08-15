from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from ui.widgets.message_box import QMessageBox
from ui.widgets.downward_combo_box import DownwardComboBox

from app.models.material_collection import MaterialCollection
from app.models.material_types import MaterialType
from app.models.pbr_material import PBRMaterial
from app.services.material_builder import MaterialBuilder
from ui.widgets.material_card import MaterialCard


class MaterialsPanel(QWidget):
    materialPreviewRequested = Signal(object)
    exportMaterialsRequested = Signal(object)
    projectChanged = Signal()

    def __init__(
        self,
        *,
        collection: MaterialCollection,
        parent=None,
    ):
        super().__init__(parent)

        self.collection = collection
        self.builder = MaterialBuilder()
        self.cards = {}

        root = QVBoxLayout(self)

        header = QLabel("PBR MATERIALS")
        header.setObjectName("sectionHeader")
        root.addWidget(header)

        controls = QHBoxLayout()

        self.type_combo = DownwardComboBox()

        for material_type in MaterialType:
            self.type_combo.addItem(
                material_type.display_name,
                material_type,
            )

        self.new_button = QPushButton(
            "New Material"
        )
        self.export_button = QPushButton(
            "Export Materials"
        )

        self.type_combo.setToolTip(
            "Choose the material type used when creating a new material."
        )
        self.new_button.setToolTip(
            "Create a new material card using the selected material type."
        )
        self.export_button.setToolTip(
            'Export every material marked "Available to export".'
        )

        controls.addWidget(
            self.type_combo,
            1,
        )
        controls.addWidget(
            self.new_button
        )

        root.addLayout(
            controls
        )
        root.addWidget(
            self.export_button
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(
            True
        )

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(
            self.cards_container
        )
        self.cards_layout.addStretch()

        scroll.setWidget(
            self.cards_container
        )
        root.addWidget(
            scroll,
            1,
        )

        self.new_button.clicked.connect(
            self.create_material
        )
        self.export_button.clicked.connect(
            self._request_export
        )

        self.refresh_actions()

    def create_material(self):
        material = self.collection.create(
            self.type_combo.currentData()
        )
        material.name = "_".join(material.name.split())
        self._add_material_card(material, export_enabled=True)
        self.collection.select(material)
        self.materialPreviewRequested.emit(material)
        self.projectChanged.emit()
        self.refresh_actions()

    def _add_material_card(self, material, *, export_enabled=True):
        card = MaterialCard(material=material, builder=self.builder)
        card.previewRequested.connect(self._preview)
        card.deleteRequested.connect(self._delete)
        card.exportAvailabilityChanged.connect(
            self._export_availability_changed
        )
        card.projectChanged.connect(self.projectChanged.emit)

        card.export_check.blockSignals(True)
        card.export_check.setChecked(bool(export_enabled))
        card.export_enabled = bool(export_enabled)
        card.export_check.blockSignals(False)
        card._apply_export_state()

        self.cards_layout.insertWidget(
            max(0, self.cards_layout.count() - 1),
            card,
        )
        self.cards[material.material_id] = card
        return card

    def clear_project_materials(self):
        for card in list(self.cards.values()):
            card.setParent(None)
            card.deleteLater()
        self.cards.clear()

        clear_method = getattr(self.collection, "clear", None)
        if callable(clear_method):
            clear_method()
        else:
            for material in list(getattr(self.collection, "materials", [])):
                self.collection.remove(material)

        self.materialPreviewRequested.emit(None)
        self.refresh_actions()

    def project_records(self, *, project_path, path_encoder):
        result = []
        for material in self.collection.materials:
            card = self.cards.get(material.material_id)
            slots = {}
            for slot_type in material.slots:
                slot = material.slot(slot_type)
                slots[slot_type.name] = path_encoder(
                    slot.source_path,
                    project_path,
                )
            result.append({
                "name": material.name,
                "type": material.material_type.name,
                "export_enabled": (
                    True if card is None else card.export_enabled
                ),
                "normal_map_opengl": bool(
                    material.normal_map_opengl
                ),
                "slots": slots,
            })
        return result

    def restore_project_records(
        self,
        records,
        *,
        project_path,
        path_decoder,
    ):
        from app.models.material_types import MaterialType

        self.clear_project_materials()
        errors = []

        for index, record in enumerate(records or [], start=1):
            material_type = MaterialType.__members__.get(
                str(record.get("type", ""))
            )
            if material_type is None:
                errors.append(f"Material {index}: unknown type.")
                continue

            material = self.collection.create(material_type)
            material.name = str(record.get("name", material.name))
            material.normal_map_opengl = bool(
                record.get("normal_map_opengl", False)
            )

            for slot_type in material.slots:
                source = path_decoder(
                    (record.get("slots") or {}).get(slot_type.name),
                    project_path,
                )
                if source is None:
                    continue
                try:
                    self.builder.assign_path(material, slot_type, source)
                except Exception as error:
                    errors.append(
                        f"{material.name} / {slot_type.display_name}: {error}"
                    )

            self.builder.build(material)
            self._add_material_card(
                material,
                export_enabled=record.get("export_enabled", True),
            )

        self.refresh_actions()
        return errors

    def exportable_materials(self):
        materials = []

        for material in self.collection.materials:
            card = self.cards.get(material.material_id)
            if card is None or card.export_enabled:
                materials.append(material)

        return materials

    def refresh_actions(self) -> None:
        self.export_button.setEnabled(
            bool(self.exportable_materials())
        )

    def set_operation_running(
        self,
        running: bool,
    ) -> None:
        enabled = not running

        self.new_button.setEnabled(
            enabled
        )
        self.export_button.setEnabled(
            enabled
            and bool(self.exportable_materials())
        )
        self.type_combo.setEnabled(
            enabled
        )

        for card in self.cards.values():
            card.setEnabled(
                enabled
            )


    def _request_export(self) -> None:
        materials = self.exportable_materials()

        if not materials:
            QMessageBox.information(
                self,
                "Material Export",
                "No materials are marked Available to export.",
            )
            return

        self.exportMaterialsRequested.emit(materials)

    def _export_availability_changed(
        self,
        material,
        enabled,
    ) -> None:
        self.refresh_actions()

    def _preview(self, material):
        self.collection.select(
            material
        )
        self.materialPreviewRequested.emit(
            material
        )

    def _delete(
        self,
        material: PBRMaterial,
    ):
        if material.has_any_source:
            answer = QMessageBox.question(
                self,
                "Delete Material",
                "Delete this material? "
                "Source files will remain on disk.",
            )

            if (
                answer
                != QMessageBox.StandardButton.Yes
            ):
                return

        self.collection.remove(
            material
        )

        card = self.cards.pop(
            material.material_id,
            None,
        )

        if card:
            card.setParent(
                None
            )
            card.deleteLater()

        self.materialPreviewRequested.emit(
            None
        )

        self.refresh_actions()
        self.projectChanged.emit()
