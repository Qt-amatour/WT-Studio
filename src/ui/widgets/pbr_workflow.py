from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.thumbnail_browser import ThumbnailBrowser


class PBRWorkflow(QWidget):
    textureSelected = Signal(object)
    textureActivated = Signal(object)

    importRequested = Signal()
    removeTexturesRequested = Signal(object)
    exportSelectedRequested = Signal(object)
    exportAllRequested = Signal(object)
    workspaceChanged = Signal()

    def __init__(
        self,
        *,
        collection,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.collection = collection

        root = QVBoxLayout(self)

        self.import_button = QPushButton(
            "Import Source Textures"
        )
        self.import_button.setObjectName("importSourceButton")
        self.import_button.setToolTip(
            "Import original DDS/TGA textures exported from AssetViewer "
            "or created in a UserSkins folder. Use this as the first step "
            "of a new workflow; WT Studio does not scan War Thunder or "
            "AssetViewer automatically."
        )
        root.addWidget(self.import_button)

        search_row = QHBoxLayout()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(
            "Search imported textures..."
        )

        self.select_all_button = QPushButton(
            "Select All"
        )
        self.clear_selection_button = QPushButton(
            "Clear Selection"
        )

        self.select_all_button.setToolTip(
            "Select all currently visible imported textures."
        )
        self.clear_selection_button.setToolTip(
            "Clear the current texture selection."
        )

        search_row.addWidget(
            self.search_edit,
            1,
        )
        search_row.addWidget(
            self.select_all_button
        )
        search_row.addWidget(
            self.clear_selection_button
        )
        root.addLayout(search_row)

        self.browser = ThumbnailBrowser(
            collection=collection
        )
        root.addWidget(
            self.browser,
            1,
        )

        self.create_export_folder_check = QCheckBox(
            'Create "PBR Textures" export folder'
        )
        self.create_export_folder_check.setChecked(
            True
        )
        self.create_export_folder_check.setToolTip(
            'Create a "PBR Textures" subfolder inside the selected '
            "export directory."
        )
        root.addWidget(
            self.create_export_folder_check
        )

        self.export_opengl_normal_check = QCheckBox(
            "Export normal map as OpenGL"
        )
        self.export_opengl_normal_check.setChecked(
            False
        )
        self.export_opengl_normal_check.setToolTip(
            "Leave disabled for DirectX normal maps. "
            "Enable when the exported PBR normal map will be "
            "edited in an OpenGL normal-map workflow."
        )
        root.addWidget(
            self.export_opengl_normal_check
        )

        action_row = QHBoxLayout()

        self.remove_button = QPushButton(
            "Remove Selected"
        )
        self.export_selected_button = QPushButton(
            "Export Selected"
        )
        self.export_all_button = QPushButton(
            "Export All"
        )

        self.remove_button.setToolTip(
            "Remove selected textures from the project. "
            "Source files remain on disk."
        )
        self.export_selected_button.setToolTip(
            "Split the selected source textures into editable PBR PNG maps."
        )
        self.export_all_button.setToolTip(
            "Split all imported source textures into editable PBR PNG maps."
        )

        action_row.addWidget(
            self.remove_button
        )
        action_row.addStretch(1)
        action_row.addWidget(
            self.export_selected_button
        )
        action_row.addWidget(
            self.export_all_button
        )

        root.addLayout(action_row)

        self.import_button.clicked.connect(
            self.importRequested.emit
        )
        self.search_edit.textChanged.connect(
            self.browser.set_filter
        )
        self.select_all_button.clicked.connect(
            self.browser.selectAll
        )
        self.clear_selection_button.clicked.connect(
            self.browser.clearSelection
        )
        self.create_export_folder_check.toggled.connect(
            self._workspace_option_changed
        )
        self.export_opengl_normal_check.toggled.connect(
            self._workspace_option_changed
        )

        self.remove_button.clicked.connect(
            self._request_remove
        )
        self.export_selected_button.clicked.connect(
            self._request_export_selected
        )
        self.export_all_button.clicked.connect(
            self._request_export_all
        )

        self.browser.textureSelected.connect(
            self.textureSelected.emit
        )
        self.browser.textureActivated.connect(
            self.textureActivated.emit
        )
        self.browser.selectionChanged.connect(
            self._selection_changed
        )

        self._selection_changed(
            self.browser.selected_textures()
        )
        self._refresh_actions()

    def _workspace_option_changed(
        self,
        _checked: bool,
    ) -> None:
        # QCheckBox.toggled emits one bool argument, while workspaceChanged
        # is intentionally a zero-argument application signal.
        self.workspaceChanged.emit()

    @property
    def create_export_folder(self) -> bool:
        return (
            self.create_export_folder_check
            .isChecked()
        )

    @property
    def export_normal_map_as_opengl(self) -> bool:
        return self.export_opengl_normal_check.isChecked()

    def add_texture(self, texture) -> None:
        self.browser.add_texture(texture)
        self._refresh_actions()

    def add_textures(
        self,
        textures: Iterable,
    ) -> None:
        self.browser.add_textures(textures)
        self._refresh_actions()

    def remove_textures(
        self,
        textures: Iterable,
    ) -> int:
        removed = self.browser.remove_textures(
            textures
        )
        self._refresh_actions()
        return removed

    def reload(self) -> None:
        self.browser.reload()
        self._refresh_actions()

    def selected_textures(self) -> list:
        return self.browser.selected_textures()

    def all_textures(self) -> list:
        return list(self.collection)

    def set_operation_running(
        self,
        running: bool,
    ) -> None:
        enabled = not running

        for widget in (
            self.import_button,
            self.search_edit,
            self.select_all_button,
            self.clear_selection_button,
            self.browser,
            self.create_export_folder_check,
            self.export_opengl_normal_check,
            self.remove_button,
            self.export_selected_button,
            self.export_all_button,
        ):
            widget.setEnabled(enabled)

        if enabled:
            self._refresh_actions()

    def _request_remove(self) -> None:
        textures = self.selected_textures()

        if textures:
            self.removeTexturesRequested.emit(
                textures
            )

    def _request_export_selected(self) -> None:
        self.exportSelectedRequested.emit(
            self.selected_textures()
        )

    def _request_export_all(self) -> None:
        self.exportAllRequested.emit(
            self.all_textures()
        )

    def _selection_changed(
        self,
        textures: list,
    ) -> None:
        self.remove_button.setEnabled(
            bool(textures)
        )
        self.export_selected_button.setEnabled(
            bool(textures)
        )

    def _refresh_actions(self) -> None:
        has_textures = bool(
            list(self.collection)
        )

        selected = self.selected_textures()

        self.remove_button.setEnabled(
            bool(selected)
        )
        self.export_selected_button.setEnabled(
            bool(selected)
        )
        self.export_all_button.setEnabled(
            has_textures
        )
        self.select_all_button.setEnabled(
            has_textures
        )
        self.clear_selection_button.setEnabled(
            has_textures
        )
