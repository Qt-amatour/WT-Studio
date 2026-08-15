from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QListWidget,
    QListWidgetItem,
)


class ImportList(QListWidget):
    textureSelected = Signal(object)
    removeTexturesRequested = Signal(object)

    ITEM_TEXTURE_ROLE = Qt.ItemDataRole.UserRole

    def __init__(self):
        super().__init__()

        self.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )

        self.itemClicked.connect(
            self._on_item_clicked
        )

    def add_texture(self, texture):
        item = QListWidgetItem(
            self._item_text(texture)
        )
        item.setData(
            self.ITEM_TEXTURE_ROLE,
            texture,
        )
        item.setToolTip(
            str(getattr(texture, "path", ""))
        )
        self.addItem(item)

    def add_textures(
        self,
        textures: Iterable,
    ) -> None:
        for texture in textures:
            self.add_texture(texture)

    def selected_textures(self) -> list:
        return [
            item.data(self.ITEM_TEXTURE_ROLE)
            for item in self.selectedItems()
            if item.data(self.ITEM_TEXTURE_ROLE) is not None
        ]

    def remove_texture(
        self,
        texture_or_path,
    ) -> bool:
        target = self._path_key(texture_or_path)

        for row in range(self.count() - 1, -1, -1):
            item = self.item(row)
            texture = item.data(
                self.ITEM_TEXTURE_ROLE
            )

            if self._path_key(texture) == target:
                self.takeItem(row)
                return True

        return False

    def remove_textures(
        self,
        textures_or_paths: Iterable,
    ) -> int:
        return sum(
            1
            for value in textures_or_paths
            if self.remove_texture(value)
        )

    def keyPressEvent(
        self,
        event: QKeyEvent,
    ) -> None:
        if event.key() == Qt.Key.Key_Delete:
            textures = self.selected_textures()

            if textures:
                self.removeTexturesRequested.emit(
                    textures
                )
                event.accept()
                return

        super().keyPressEvent(event)

    def _on_item_clicked(
        self,
        item: QListWidgetItem,
    ) -> None:
        texture = item.data(
            self.ITEM_TEXTURE_ROLE
        )

        if texture is not None:
            self.textureSelected.emit(texture)

    @staticmethod
    def _item_text(texture) -> str:
        name = str(
            getattr(
                texture,
                "name",
                getattr(
                    getattr(texture, "file", None),
                    "name",
                    "Texture",
                ),
            )
        )

        texture_type = getattr(
            texture,
            "texture_type",
            None,
        )

        type_name = getattr(
            texture_type,
            "name",
            "",
        )

        return (
            f"{name}   [{type_name}]"
            if type_name
            else name
        )

    @staticmethod
    def _path_key(value) -> str:
        path = getattr(value, "path", value)

        try:
            return str(
                Path(path).expanduser().resolve()
            ).casefold()
        except Exception:
            return str(path).casefold()
