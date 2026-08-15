from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, Signal, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.models.new_asset_collection import NewAssetCollection
from app.models.new_asset_material import NewAssetMaterial
from app.models.new_asset_types import NewAssetType
from app.services.new_asset_builder import NewAssetBuilder
from ui.icons import icon_path
from ui.theme.palette import Palette
from ui.widgets.downward_combo_box import DownwardComboBox
from ui.widgets.message_box import QMessageBox
from ui.widgets.new_asset_card import NewAssetCard


class NewAssetsPanel(QWidget):
    assetPreviewRequested = Signal(object)
    exportRequested = Signal(object, str)
    projectChanged = Signal()

    def __init__(
        self,
        *,
        collection: NewAssetCollection,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.collection = collection
        self.builder = NewAssetBuilder()
        self.cards: dict[str, NewAssetCard] = {}
        self._export_directory = ""

        root = QVBoxLayout(self)

        header = QLabel("NEW ASSETS")
        header.setObjectName("sectionHeader")
        root.addWidget(header)

        controls = QHBoxLayout()
        self.type_combo = DownwardComboBox()
        for asset_type in NewAssetType:
            self.type_combo.addItem(
                asset_type.display_name,
                asset_type,
            )

        self.new_button = QPushButton("New Asset")
        self.type_combo.setToolTip(
            "Choose the asset texture type used when creating a new card."
        )
        self.new_button.setToolTip(
            "Create a new NEW ASSETS card using the selected texture type."
        )
        controls.addWidget(self.type_combo, 1)
        controls.addWidget(self.new_button)
        root.addLayout(controls)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)

        self.empty_state = self._build_empty_state()
        self.cards_layout.addWidget(self.empty_state, 1)
        self.cards_layout.addStretch(0)

        scroll.setWidget(self.cards_container)
        root.addWidget(scroll, 1)

        export_header = QLabel("EXPORT DIRECTORY")
        export_header.setObjectName("sectionHeader")
        root.addWidget(export_header)

        export_row = QHBoxLayout()
        self.export_path_edit = QLineEdit()
        self.export_path_edit.setReadOnly(True)
        self.export_path_edit.setPlaceholderText(
            "No New Assets export directory selected"
        )
        self.browse_export_button = QPushButton("Browse")
        self.browse_export_button.setToolTip(
            "Choose the dedicated NEW ASSETS export directory. "
            "A clean session starts with no directory selected."
        )
        export_row.addWidget(self.export_path_edit, 1)
        export_row.addWidget(self.browse_export_button)
        root.addLayout(export_row)

        export_buttons = QHBoxLayout()
        export_buttons.addStretch(1)
        self.export_selected_button = QPushButton("Export Selected")
        self.export_all_button = QPushButton("Export All")
        self.export_selected_button.setToolTip(
            'Export only NEW ASSETS cards marked "Available to export" as TGA.'
        )
        self.export_all_button.setToolTip(
            'Export every NEW ASSETS card as TGA, ignoring the '
            '"Available to export" checkbox.'
        )
        export_buttons.addWidget(self.export_selected_button)
        export_buttons.addWidget(self.export_all_button)
        root.addLayout(export_buttons)

        self.new_button.clicked.connect(self.create_asset)
        self.browse_export_button.clicked.connect(
            self._browse_export_directory
        )
        self.export_selected_button.clicked.connect(
            self._request_export_selected
        )
        self.export_all_button.clicked.connect(
            self._request_export_all
        )

        self.refresh_actions()
        self._refresh_empty_state()

    def _build_empty_state(self) -> QWidget:
        state = QWidget()
        state.setObjectName("newAssetsEmptyState")

        layout = QVBoxLayout(state)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)
        layout.addStretch(1)

        message = QLabel(
            "This tab is intended for creating textures for new/modded "
            "content.\nFiles created here are not intended for UserSkins "
            "— especially NORMAL textures, which are not compatible."
        )
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)
        message.setStyleSheet(
            f"color: {Palette.ACCENT}; "
            "font-size: 10pt; font-weight: 600;"
        )
        layout.addWidget(message)

        illustration = QLabel()
        illustration.setAlignment(Qt.AlignmentFlag.AlignCenter)
        illustration.setPixmap(
            self._render_svg_contained(
                "help_snail.svg",
                width=150,
                height=190,
            )
        )
        illustration.setFixedSize(150, 190)
        layout.addWidget(
            illustration,
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )

        layout.addStretch(1)
        return state

    @staticmethod
    def _render_svg_contained(
        filename: str,
        *,
        width: int,
        height: int,
    ) -> QPixmap:
        renderer = QSvgRenderer(str(icon_path(filename)))

        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)

        if not renderer.isValid():
            return pixmap

        source_box = renderer.viewBoxF()
        if (
            source_box.width() <= 0.0
            or source_box.height() <= 0.0
        ):
            return pixmap

        scale = min(
            width / source_box.width(),
            height / source_box.height(),
        )
        render_width = source_box.width() * scale
        render_height = source_box.height() * scale

        target = QRectF(
            (width - render_width) / 2.0,
            (height - render_height) / 2.0,
            render_width,
            render_height,
        )

        painter = QPainter(pixmap)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )
        renderer.render(painter, target)
        painter.end()

        return pixmap

    def _refresh_empty_state(self) -> None:
        self.empty_state.setVisible(not bool(self.cards))

    @property
    def export_directory(self) -> str:
        return self._export_directory

    def set_export_directory(
        self,
        value: str | Path | None,
        *,
        mark_dirty: bool = False,
    ) -> None:
        if value is None or not str(value).strip():
            normalized = ""
        else:
            normalized = str(
                Path(value).expanduser().resolve(strict=False)
            )

        changed = normalized != self._export_directory
        self._export_directory = normalized
        self.export_path_edit.setText(normalized)
        self.export_path_edit.setToolTip(normalized)
        self.refresh_actions()

        if changed and mark_dirty:
            self.projectChanged.emit()

    def _browse_export_directory(self) -> None:
        initial = self._export_directory or str(Path.home())
        path = QFileDialog.getExistingDirectory(
            self,
            "Select New Assets Export Directory",
            initial,
            QFileDialog.Option.ShowDirsOnly,
        )
        if not path:
            return
        self.set_export_directory(path, mark_dirty=True)

    def create_asset(self) -> None:
        material = self.collection.create(
            self.type_combo.currentData()
        )
        material.name = "_".join(material.name.split())
        self._add_asset_card(material, export_enabled=True)
        self.collection.select(material)
        self.assetPreviewRequested.emit(material)
        self.projectChanged.emit()
        self.refresh_actions()

    def _add_asset_card(
        self,
        material: NewAssetMaterial,
        *,
        export_enabled: bool = True,
    ) -> NewAssetCard:
        card = NewAssetCard(
            material=material,
            builder=self.builder,
        )
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
        self.cards[material.asset_id] = card
        self._refresh_empty_state()
        return card

    def clear_project_assets(
        self,
        *,
        reset_export_directory: bool = True,
    ) -> None:
        for card in list(self.cards.values()):
            card.setParent(None)
            card.deleteLater()
        self.cards.clear()
        self.collection.clear()
        self.assetPreviewRequested.emit(None)

        if reset_export_directory:
            self.set_export_directory("", mark_dirty=False)

        self._refresh_empty_state()
        self.refresh_actions()

    def project_record(
        self,
        *,
        project_path,
        path_encoder,
    ) -> dict:
        materials = []

        for material in self.collection.materials:
            card = self.cards.get(material.asset_id)
            slots = {}
            for slot_type in material.slots:
                slot = material.slot(slot_type)
                slots[slot_type.name] = path_encoder(
                    slot.source_path,
                    project_path,
                )

            materials.append({
                "name": material.name,
                "type": material.asset_type.name,
                "export_enabled": (
                    True if card is None else card.export_enabled
                ),
                "normal_map_opengl": bool(
                    material.normal_map_opengl
                ),
                "slots": slots,
            })

        export_record = path_encoder(
            self._export_directory or None,
            project_path,
        )

        return {
            "export_directory": export_record,
            "materials": materials,
        }

    def restore_project_record(
        self,
        record,
        *,
        project_path,
        path_decoder,
    ) -> list[str]:
        self.clear_project_assets(reset_export_directory=True)
        errors: list[str] = []
        record = record or {}

        export_directory = path_decoder(
            record.get("export_directory"),
            project_path,
        )
        self.set_export_directory(
            export_directory,
            mark_dirty=False,
        )

        for index, item in enumerate(
            record.get("materials", []) or [],
            start=1,
        ):
            asset_type = NewAssetType.__members__.get(
                str(item.get("type", ""))
            )
            if asset_type is None:
                errors.append(
                    f"New Asset {index}: unknown type."
                )
                continue

            material = self.collection.create(asset_type)
            material.name = str(item.get("name", material.name))
            material.normal_map_opengl = bool(
                item.get("normal_map_opengl", False)
            )

            for slot_type in material.slots:
                source = path_decoder(
                    (item.get("slots") or {}).get(slot_type.name),
                    project_path,
                )
                if source is None:
                    continue
                try:
                    self.builder.assign_path(
                        material,
                        slot_type,
                        source,
                    )
                except Exception as error:
                    errors.append(
                        f"New Asset {material.name} / "
                        f"{slot_type.display_name}: {error}"
                    )

            self.builder.build(material)
            self._add_asset_card(
                material,
                export_enabled=item.get(
                    "export_enabled",
                    True,
                ),
            )

        self.refresh_actions()
        return errors

    def selected_for_export(self) -> list[NewAssetMaterial]:
        result = []
        for material in self.collection.materials:
            card = self.cards.get(material.asset_id)
            if card is None or card.export_enabled:
                result.append(material)
        return result

    def all_for_export(self) -> list[NewAssetMaterial]:
        return list(self.collection.materials)

    def refresh_actions(self) -> None:
        has_directory = bool(self._export_directory)
        self.export_selected_button.setEnabled(
            has_directory and bool(self.selected_for_export())
        )
        self.export_all_button.setEnabled(
            has_directory and bool(self.all_for_export())
        )

    def set_operation_running(self, running: bool) -> None:
        enabled = not running
        self.new_button.setEnabled(enabled)
        self.type_combo.setEnabled(enabled)
        self.browse_export_button.setEnabled(enabled)

        self.export_selected_button.setEnabled(
            enabled
            and bool(self._export_directory)
            and bool(self.selected_for_export())
        )
        self.export_all_button.setEnabled(
            enabled
            and bool(self._export_directory)
            and bool(self.all_for_export())
        )

        for card in self.cards.values():
            card.setEnabled(enabled)

    def _request_export_selected(self) -> None:
        self._request_export(self.selected_for_export())

    def _request_export_all(self) -> None:
        self._request_export(self.all_for_export())

    def _request_export(
        self,
        materials: list[NewAssetMaterial],
    ) -> None:
        if not self._export_directory:
            QMessageBox.information(
                self,
                "New Assets Export",
                "Select a New Assets export directory first.",
            )
            return

        if not materials:
            QMessageBox.information(
                self,
                "New Assets Export",
                "There are no New Assets materials to export.",
            )
            return

        self.exportRequested.emit(
            materials,
            self._export_directory,
        )

    def _export_availability_changed(
        self,
        material,
        enabled,
    ) -> None:
        self.refresh_actions()

    def _preview(self, material: NewAssetMaterial) -> None:
        self.collection.select(material)
        self.assetPreviewRequested.emit(material)

    def _delete(self, material: NewAssetMaterial) -> None:
        if material.has_any_source:
            answer = QMessageBox.question(
                self,
                "Delete New Asset",
                "Delete this new asset material? Source files will remain "
                "on disk.",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        self.collection.remove(material)
        card = self.cards.pop(material.asset_id, None)
        if card:
            card.setParent(None)
            card.deleteLater()

        self.assetPreviewRequested.emit(None)
        self._refresh_empty_state()
        self.refresh_actions()
        self.projectChanged.emit()
