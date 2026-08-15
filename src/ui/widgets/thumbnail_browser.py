# ============================================================
# WT Studio
# Version : 0.1.0
#
# File:
# thumbnail_browser.py
#
# Description:
# Thumbnail-based browser for imported textures
#
# ============================================================

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from PIL import Image
from PIL.ImageQt import ImageQt

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QIcon,
    QImage,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMenu,
)

from app.models.texture_collection import (
    TextureCollection,
    TextureNotFoundError,
)
from app.models.texture_info import TextureInfo


class ThumbnailBrowser(QListWidget):
    """
    Displays imported textures as selectable thumbnail tiles.

    The widget supports:

    - single selection,
    - Ctrl multi-selection,
    - Shift range selection,
    - Ctrl+A selection,
    - double-click activation,
    - synchronization with TextureCollection,
    - thumbnails stored in TextureInfo,
    - fallback icons for textures without a preview,
    - filtering without removing textures from the project.

    ThumbnailBrowser is only a visual representation. The authoritative
    texture storage remains TextureCollection.
    """

    textureSelected = Signal(object)
    textureActivated = Signal(object)

    selectionChanged = Signal(list)
    textureTypeChanged = Signal(object)

    ICON_SIZE = QSize(128, 128)
    GRID_SIZE = QSize(166, 182)

    FALLBACK_PIXMAP_SIZE = QSize(128, 128)

    ITEM_TEXTURE_ROLE = (
        Qt.ItemDataRole.UserRole
    )

    ITEM_PATH_ROLE = (
        Qt.ItemDataRole.UserRole + 1
    )

    def __init__(
        self,
        collection: TextureCollection | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self._collection: TextureCollection | None = None

        self._items_by_path: dict[
            str,
            QListWidgetItem,
        ] = {}

        self._selection_sync_enabled = True
        self._filter_query = ""

        self._configure_widget()
        self._connect_signals()

        if collection is not None:
            self.set_collection(collection)

    # ========================================================
    # Setup
    # ========================================================

    def _configure_widget(self) -> None:
        """
        Configures the browser as an icon grid.
        """

        self.setViewMode(
            QListView.ViewMode.IconMode
        )

        self.setFlow(
            QListView.Flow.LeftToRight
        )

        self.setWrapping(True)

        self.setResizeMode(
            QListView.ResizeMode.Adjust
        )

        self.setMovement(
            QListView.Movement.Static
        )

        self.setLayoutMode(
            QListView.LayoutMode.Batched
        )

        self.setBatchSize(50)

        self.setIconSize(self.ICON_SIZE)
        self.setGridSize(self.GRID_SIZE)

        self.setSpacing(4)

        self.setWordWrap(True)
        self.setUniformItemSizes(True)

        self.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )

        self.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectItems
        )

        self.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        self.setDragEnabled(False)
        self.setAcceptDrops(False)
        self.setDropIndicatorShown(False)

        self.setAlternatingRowColors(False)

        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        self.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

        self.setObjectName("thumbnailBrowser")

    def _connect_signals(self) -> None:
        self.itemSelectionChanged.connect(
            self._on_item_selection_changed
        )

        self.itemClicked.connect(
            self._on_item_clicked
        )

        self.itemDoubleClicked.connect(
            self._on_item_double_clicked
        )

        self.customContextMenuRequested.connect(
            self._show_context_menu
        )

    # ========================================================
    # Collection
    # ========================================================

    @property
    def collection(
        self,
    ) -> TextureCollection | None:
        return self._collection

    def set_collection(
        self,
        collection: TextureCollection | None,
    ) -> None:
        """
        Replaces the displayed TextureCollection.

        Passing None disconnects the browser from project data and
        clears all displayed items.
        """

        if (
            collection is not None
            and not isinstance(
                collection,
                TextureCollection,
            )
        ):
            raise TypeError(
                "ThumbnailBrowser requires a "
                "TextureCollection or None."
            )

        self._collection = collection

        self.reload()

    def reload(self) -> None:
        """
        Rebuilds all browser items from the current collection.
        """

        previously_selected_paths = {
            self._texture_path_key(texture)
            for texture in self.selected_textures()
        }

        self._selection_sync_enabled = False

        try:
            super().clear()
            self._items_by_path.clear()

            if self._collection is None:
                return

            for texture in self._collection:
                self._create_item(texture)

            self._apply_filter()

            collection_selected_paths = {
                self._texture_path_key(texture)
                for texture
                in self._collection.selected()
            }

            paths_to_restore = (
                collection_selected_paths
                or previously_selected_paths
            )

            self._restore_selection(
                paths_to_restore
            )

        finally:
            self._selection_sync_enabled = True

        self._emit_selection_state()

    def refresh(self) -> None:
        """
        Alias for reload().
        """

        self.reload()

    # ========================================================
    # Adding and removing
    # ========================================================

    def add_texture(
        self,
        texture: TextureInfo,
    ) -> QListWidgetItem:
        """
        Adds or refreshes one texture tile.

        This method does not automatically add the texture to the
        collection. ProjectManager remains responsible for project data.
        """

        self._validate_texture(texture)

        key = self._texture_path_key(texture)

        existing_item = self._items_by_path.get(
            key
        )

        if existing_item is not None:
            self.update_texture(texture)

            return existing_item

        item = self._create_item(texture)

        self._apply_item_filter(item)

        return item

    def add_textures(
        self,
        textures: Iterable[TextureInfo],
    ) -> list[QListWidgetItem]:
        """
        Adds multiple texture tiles.
        """

        items: list[QListWidgetItem] = []

        self.setUpdatesEnabled(False)

        try:
            for texture in textures:
                items.append(
                    self.add_texture(texture)
                )

        finally:
            self.setUpdatesEnabled(True)

        self.viewport().update()

        return items

    def update_texture(
        self,
        texture: TextureInfo,
    ) -> bool:
        """
        Refreshes the tile corresponding to TextureInfo.

        Returns False when the texture is not displayed.
        """

        self._validate_texture(texture)

        key = self._texture_path_key(texture)

        item = self._items_by_path.get(key)

        if item is None:
            return False

        item.setData(
            self.ITEM_TEXTURE_ROLE,
            texture,
        )

        item.setText(
            self._build_item_text(texture)
        )

        item.setToolTip(
            self._build_tooltip(texture)
        )

        item.setIcon(
            self._build_texture_icon(texture)
        )

        self._apply_item_filter(item)

        return True

    def remove_texture(
        self,
        texture_or_path: TextureInfo | str | Path,
    ) -> bool:
        """
        Removes one displayed tile.

        This method does not remove the texture from TextureCollection.
        """

        key = self._resolve_path_key(
            texture_or_path
        )

        item = self._items_by_path.pop(
            key,
            None,
        )

        if item is None:
            return False

        row = self.row(item)

        if row >= 0:
            self.takeItem(row)

        return True

    def remove_textures(
        self,
        textures_or_paths: Iterable[
            TextureInfo | str | Path
        ],
    ) -> int:
        """
        Removes multiple tiles and returns the number removed.
        """

        removed_count = 0

        for texture_or_path in textures_or_paths:
            if self.remove_texture(
                texture_or_path
            ):
                removed_count += 1

        return removed_count

    def clear_browser(self) -> None:
        """
        Clears displayed items without changing TextureCollection.
        """

        self._selection_sync_enabled = False

        try:
            super().clear()
            self._items_by_path.clear()

        finally:
            self._selection_sync_enabled = True

        self._emit_selection_state()

    # ========================================================
    # Item creation
    # ========================================================

    def _create_item(
        self,
        texture: TextureInfo,
    ) -> QListWidgetItem:
        self._validate_texture(texture)

        key = self._texture_path_key(texture)

        item = QListWidgetItem()

        item.setData(
            self.ITEM_TEXTURE_ROLE,
            texture,
        )

        item.setData(
            self.ITEM_PATH_ROLE,
            key,
        )

        item.setText(
            self._build_item_text(texture)
        )

        item.setToolTip(
            self._build_tooltip(texture)
        )

        item.setIcon(
            self._build_texture_icon(texture)
        )

        item.setTextAlignment(
            Qt.AlignmentFlag.AlignHCenter
            | Qt.AlignmentFlag.AlignTop
        )

        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
        )

        item.setSizeHint(self.GRID_SIZE)

        self.addItem(item)

        self._items_by_path[key] = item

        return item

    @staticmethod
    def _build_item_text(
        texture: TextureInfo,
    ) -> str:
        """
        Creates compact tile text.
        """

        name = texture.file.name

        width = texture.image_info.width
        height = texture.image_info.height

        if width > 0 and height > 0:
            resolution = f"{width} × {height}"
        else:
            resolution = "Unknown resolution"

        effective_role = (
            texture.pbr.role_name.upper()
        )

        if texture.has_manual_type:
            role_line = (
                f"[MANUAL: {effective_role}]"
            )
        else:
            role_line = (
                f"[AUTO: {effective_role}]"
            )

        return (
            f"{name}\n"
            f"{resolution}\n"
            f"{role_line}"
        )

    @staticmethod
    def _build_tooltip(
        texture: TextureInfo,
    ) -> str:
        """
        Creates a more detailed tooltip.
        """

        lines = [
            texture.file.name,
            str(texture.file.path),
        ]

        width = texture.image_info.width
        height = texture.image_info.height

        if width > 0 and height > 0:
            lines.append(
                f"Resolution: {width} × {height}"
            )

        detected_role = (
            texture.pbr.detected_role_name
        )

        effective_role = (
            texture.pbr.role_name
        )

        lines.append(
            f"Detected type: {detected_role}"
        )

        if texture.has_manual_type:
            lines.append(
                "Type mode: Manual"
            )

            lines.append(
                f"Effective type: {effective_role}"
            )

        else:
            lines.append(
                "Type mode: Automatic"
            )

        compression = (
            texture.compression_info.compression
        )

        if compression:
            lines.append(
                f"Compression: {compression}"
            )

        mipmaps = (
            texture.compression_info.mipmaps
        )

        if mipmaps:
            lines.append(
                f"MipMaps: {mipmaps}"
            )

        if not texture.preview.preview_available:
            lines.append(
                "Preview: unavailable"
            )

            if texture.preview.preview_error:
                lines.append(
                    texture.preview.preview_error
                )

        return "\n".join(lines)

    # ========================================================
    # Thumbnail conversion
    # ========================================================

    def _build_texture_icon(
        self,
        texture: TextureInfo,
    ) -> QIcon:
        """
        Creates an icon from a Pillow thumbnail or a fallback tile.
        """

        thumbnail = (
            texture.preview.thumbnail
        )

        pixmap = self._thumbnail_to_pixmap(
            thumbnail
        )

        if pixmap is None or pixmap.isNull():
            pixmap = self._create_fallback_pixmap(
                texture
            )

        pixmap = self._fit_pixmap_to_icon_size(
            pixmap
        )

        return QIcon(pixmap)

    @staticmethod
    def _thumbnail_to_pixmap(
        thumbnail: Any,
    ) -> QPixmap | None:
        """
        Converts supported thumbnail objects into QPixmap.

        Currently accepts:

        - QPixmap,
        - QImage,
        - Pillow Image.
        """

        if thumbnail is None:
            return None

        if isinstance(thumbnail, QPixmap):
            return QPixmap(thumbnail)

        if isinstance(thumbnail, QImage):
            return QPixmap.fromImage(
                thumbnail
            )

        if isinstance(thumbnail, Image.Image):
            try:
                source_image = thumbnail

                if source_image.mode not in {
                    "1",
                    "L",
                    "LA",
                    "P",
                    "RGB",
                    "RGBA",
                }:
                    source_image = (
                        source_image.convert("RGBA")
                    )

                qt_image = ImageQt(
                    source_image
                )

                qimage = QImage(qt_image)

                return QPixmap.fromImage(qimage)

            except Exception:
                return None

        return None

    def _fit_pixmap_to_icon_size(
        self,
        pixmap: QPixmap,
    ) -> QPixmap:
        """
        Centers the thumbnail on a fixed transparent canvas.

        This keeps differently shaped textures aligned in the grid.
        """

        target_width = self.ICON_SIZE.width()
        target_height = self.ICON_SIZE.height()

        scaled = pixmap.scaled(
            target_width,
            target_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        canvas = QPixmap(
            target_width,
            target_height,
        )

        canvas.fill(
            Qt.GlobalColor.transparent
        )

        painter = QPainter(canvas)

        x = (
            target_width - scaled.width()
        ) // 2

        y = (
            target_height - scaled.height()
        ) // 2

        painter.drawPixmap(
            x,
            y,
            scaled,
        )

        painter.end()

        return canvas

    def _create_fallback_pixmap(
        self,
        texture: TextureInfo,
    ) -> QPixmap:
        """
        Creates a simple placeholder for missing previews.

        BC7 textures can therefore still be represented in the browser.
        """

        pixmap = QPixmap(
            self.FALLBACK_PIXMAP_SIZE
        )

        pixmap.fill(
            QColor(42, 42, 42)
        )

        painter = QPainter(pixmap)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        border_pen = QPen(
            QColor(90, 90, 90)
        )

        border_pen.setWidth(1)

        painter.setPen(border_pen)

        painter.drawRect(
            0,
            0,
            pixmap.width() - 1,
            pixmap.height() - 1,
        )

        extension = (
            texture.file.extension
            .replace(".", "")
            .upper()
        )

        if not extension:
            extension = "TEXTURE"

        painter.setPen(
            QColor(210, 210, 210)
        )

        font = painter.font()
        font.setBold(True)
        font.setPointSize(13)

        painter.setFont(font)

        painter.drawText(
            pixmap.rect().adjusted(
                8,
                8,
                -8,
                -28,
            ),
            Qt.AlignmentFlag.AlignCenter,
            extension,
        )

        painter.setPen(
            QColor(155, 155, 155)
        )

        small_font = painter.font()
        small_font.setBold(False)
        small_font.setPointSize(8)

        painter.setFont(small_font)

        fallback_text = (
            self._fallback_description(
                texture
            )
        )

        painter.drawText(
            pixmap.rect().adjusted(
                8,
                82,
                -8,
                -8,
            ),
            Qt.AlignmentFlag.AlignCenter
            | Qt.TextFlag.TextWordWrap,
            fallback_text,
        )

        painter.end()

        return pixmap

    @staticmethod
    def _fallback_description(
        texture: TextureInfo,
    ) -> str:
        compression = (
            texture.compression_info.compression
        )

        if compression:
            return compression

        return "No preview"

    # ========================================================
    # Selection
    # ========================================================

    def selected_textures(
        self,
    ) -> list[TextureInfo]:
        """
        Returns selected textures in visual item order.

        QListWidgetItem objects are not hashable, therefore selection is
        checked directly through item.isSelected().
        """

        textures: list[TextureInfo] = []

        for index in range(self.count()):
            item = self.item(index)

            if item is None:
                continue

            if not item.isSelected():
                continue

            texture = self.texture_from_item(
                item
            )

            if texture is not None:
                textures.append(texture)

        return textures

    def current_texture(
        self,
    ) -> TextureInfo | None:
        item = self.currentItem()

        if item is None:
            return None

        return self.texture_from_item(item)

    def select_texture(
        self,
        texture_or_path: TextureInfo | str | Path,
        *,
        clear_existing: bool = True,
        ensure_visible: bool = True,
    ) -> bool:
        """
        Selects a texture tile by TextureInfo or source path.
        """

        key = self._resolve_path_key(
            texture_or_path
        )

        item = self._items_by_path.get(key)

        if item is None:
            return False

        if clear_existing:
            self.clearSelection()

        item.setSelected(True)
        self.setCurrentItem(item)

        if ensure_visible:
            self.scrollToItem(
                item,
                QAbstractItemView.ScrollHint.EnsureVisible,
            )

        return True

    def select_textures(
        self,
        textures_or_paths: Iterable[
            TextureInfo | str | Path
        ],
        *,
        clear_existing: bool = True,
    ) -> int:
        """
        Selects multiple texture tiles.

        Returns the number of matching items selected.
        """

        if clear_existing:
            self.clearSelection()

        selected_count = 0

        for texture_or_path in textures_or_paths:
            key = self._resolve_path_key(
                texture_or_path
            )

            item = self._items_by_path.get(
                key
            )

            if item is None:
                continue

            item.setSelected(True)
            selected_count += 1

        return selected_count

    def select_all_textures(self) -> None:
        self.selectAll()

    def clear_texture_selection(self) -> None:
        self.clearSelection()

    def _on_item_selection_changed(
        self,
    ) -> None:
        if self._selection_sync_enabled:
            self._synchronize_collection_selection()

        self._emit_selection_state()

    def _on_item_clicked(
        self,
        item: QListWidgetItem,
    ) -> None:
        texture = self.texture_from_item(
            item
        )

        if texture is not None:
            self.textureSelected.emit(
                texture
            )

    def _on_item_double_clicked(
        self,
        item: QListWidgetItem,
    ) -> None:
        texture = self.texture_from_item(
            item
        )

        if texture is not None:
            self.textureActivated.emit(
                texture
            )

    def _synchronize_collection_selection(
        self,
    ) -> None:
        """
        Copies visual selection into TextureCollection.
        """

        if self._collection is None:
            return

        selected = self.selected_textures()

        self._collection.clear_selection()

        if not selected:
            return

        try:
            self._collection.select_many(
                selected,
                clear_existing=False,
            )

        except TextureNotFoundError:
            # The browser may temporarily contain a tile that has not
            # yet been inserted into the authoritative collection.
            pass

    def sync_selection_from_collection(
        self,
    ) -> None:
        """
        Updates visual selection using TextureCollection state.
        """

        if self._collection is None:
            self.clearSelection()
            return

        selected_paths = {
            self._texture_path_key(texture)
            for texture
            in self._collection.selected()
        }

        self._selection_sync_enabled = False

        try:
            self._restore_selection(
                selected_paths
            )

        finally:
            self._selection_sync_enabled = True

        self._emit_selection_state()

    def _restore_selection(
        self,
        selected_paths: set[str],
    ) -> None:
        self.clearSelection()

        first_item: QListWidgetItem | None = None

        for path_key in selected_paths:
            item = self._items_by_path.get(
                path_key
            )

            if item is None:
                continue

            item.setSelected(True)

            if first_item is None:
                first_item = item

        if first_item is not None:
            self.setCurrentItem(first_item)

    def _emit_selection_state(self) -> None:
        selected = self.selected_textures()

        self.selectionChanged.emit(
            selected
        )

    # ========================================================
    # Manual texture type
    # ========================================================

    def _show_context_menu(
        self,
        position,
    ) -> None:
        """
        Opens a context menu for assigning a texture role manually.

        When the clicked tile is already part of a multi-selection,
        the selected role is applied to every selected texture.
        Otherwise it is applied only to the clicked texture.
        """

        item = self.itemAt(position)

        if item is None:
            return

        texture = self.texture_from_item(
            item
        )

        if texture is None:
            return

        if not item.isSelected():
            self.clearSelection()
            item.setSelected(True)
            self.setCurrentItem(item)

        target_textures = (
            self.selected_textures()
        )

        if not target_textures:
            target_textures = [texture]

        # Keep the context menu as an independent top-level popup.
        # Parenting it to this widget (inside a dock) can make Qt try to use
        # workspaceDockWindow as a native transient parent, producing:
        # "must be a top level window".
        menu = QMenu()

        automatic_action = QAction(
            self._automatic_action_text(texture),
            menu,
        )

        automatic_action.setCheckable(True)
        automatic_action.setChecked(
            not texture.has_manual_type
        )

        automatic_action.triggered.connect(
            lambda checked=False: (
                self._clear_manual_types(
                    target_textures
                )
            )
        )

        menu.addAction(
            automatic_action
        )

        menu.addSeparator()

        for label, canonical_name in (
            ("Color / Albedo (_c)", "COLOR"),
            ("Normal / Packed (_n)", "NORMAL"),
            ("Ambient Occlusion (_ao)", "AO"),
            ("Ignore", "IGNORE"),
        ):
            role_value = self._resolve_role_value(
                texture=texture,
                canonical_name=canonical_name,
            )

            action = QAction(
                label,
                menu,
            )

            action.setCheckable(True)

            action.setChecked(
                texture.has_manual_type
                and self._roles_match(
                    texture.effective_type,
                    role_value,
                )
            )

            action.triggered.connect(
                lambda checked=False,
                value=role_value: (
                    self._set_manual_types(
                        target_textures,
                        value,
                    )
                )
            )

            menu.addAction(action)

        menu.exec(
            self.viewport().mapToGlobal(
                position
            )
        )

    @staticmethod
    def _automatic_action_text(
        texture: TextureInfo,
    ) -> str:
        detected_name = (
            texture.pbr.detected_role_name
            .upper()
        )

        return (
            f"Automatic ({detected_name})"
        )

    def _set_manual_types(
        self,
        textures: Iterable[TextureInfo],
        role_value: Any,
    ) -> None:
        """
        Applies one manual role to one or more textures.
        """

        changed_textures: list[TextureInfo] = []

        for texture in textures:
            texture.set_manual_type(
                role_value
            )

            self.update_texture(
                texture
            )

            changed_textures.append(
                texture
            )

        self._apply_filter()
        self.viewport().update()

        for texture in changed_textures:
            self.textureTypeChanged.emit(
                texture
            )

        self._emit_selection_state()

    def _clear_manual_types(
        self,
        textures: Iterable[TextureInfo],
    ) -> None:
        """
        Removes manual role overrides and restores automatic detection.
        """

        changed_textures: list[TextureInfo] = []

        for texture in textures:
            texture.clear_manual_type()

            self.update_texture(
                texture
            )

            changed_textures.append(
                texture
            )

        self._apply_filter()
        self.viewport().update()

        for texture in changed_textures:
            self.textureTypeChanged.emit(
                texture
            )

        self._emit_selection_state()

    @classmethod
    def _resolve_role_value(
        cls,
        *,
        texture: TextureInfo,
        canonical_name: str,
    ) -> Any:
        """
        Resolves a menu role to the enum class already used by the
        project's TextureDetector.

        This keeps manual roles compatible with the existing detector
        without importing or duplicating its enum. A readable string is
        used only when the current detector role is not an enum or the
        requested enum member does not exist.
        """

        detected_role = texture.detected_type

        enum_class = getattr(
            detected_role,
            "__class__",
            None,
        )

        members = getattr(
            enum_class,
            "__members__",
            None,
        )

        if members:
            aliases = {
                "COLOR": (
                    "COLOR",
                    "ALBEDO",
                    "BASE_COLOR",
                    "COLOUR",
                    "C",
                ),
                "NORMAL": (
                    "NORMAL",
                    "NORMAL_MAP",
                    "PACKED_NORMAL",
                    "N",
                ),
                "AO": (
                    "AO",
                    "AMBIENT_OCCLUSION",
                    "OCCLUSION",
                ),
                "IGNORE": (
                    "IGNORE",
                    "IGNORED",
                    "SKIP",
                    "DISABLED",
                ),
            }

            for member_name in aliases.get(
                canonical_name,
                (canonical_name,),
            ):
                member = members.get(
                    member_name
                )

                if member is not None:
                    return member

        return canonical_name

    @staticmethod
    def _normalized_role_name(
        role: Any,
    ) -> str:
        if role is None:
            return "UNKNOWN"

        enum_name = getattr(
            role,
            "name",
            None,
        )

        if enum_name:
            return str(enum_name).upper()

        return str(role).strip().upper()

    @classmethod
    def _roles_match(
        cls,
        left: Any,
        right: Any,
    ) -> bool:
        if left is right:
            return True

        return (
            cls._normalized_role_name(left)
            == cls._normalized_role_name(right)
        )

    # ========================================================
    # Filtering
    # ========================================================

    @property
    def filter_query(self) -> str:
        return self._filter_query

    def set_filter(
        self,
        query: str,
    ) -> None:
        """
        Shows only textures whose file name, path, type, extension or
        compression contains the query.

        Filtering does not remove items from TextureCollection.
        """

        self._filter_query = (
            str(query or "").strip().casefold()
        )

        self._apply_filter()

    def clear_filter(self) -> None:
        self.set_filter("")

    def visible_textures(
        self,
    ) -> list[TextureInfo]:
        textures: list[TextureInfo] = []

        for index in range(self.count()):
            item = self.item(index)

            if item.isHidden():
                continue

            texture = self.texture_from_item(
                item
            )

            if texture is not None:
                textures.append(texture)

        return textures

    def _apply_filter(self) -> None:
        for index in range(self.count()):
            self._apply_item_filter(
                self.item(index)
            )

    def _apply_item_filter(
        self,
        item: QListWidgetItem,
    ) -> None:
        if not self._filter_query:
            item.setHidden(False)
            return

        texture = self.texture_from_item(
            item
        )

        if texture is None:
            item.setHidden(True)
            return

        searchable_text = " ".join(
            [
                texture.file.name,
                str(texture.file.path),
                texture.file.extension,
                texture.pbr.role_name,
                texture.pbr.detected_role_name,
                texture.pbr.manual_role_name,
                texture.compression_info.compression,
                texture.pbr.source_suffix,
            ]
        ).casefold()

        item.setHidden(
            self._filter_query
            not in searchable_text
        )

    # ========================================================
    # Access helpers
    # ========================================================

    def texture_from_item(
        self,
        item: QListWidgetItem | None,
    ) -> TextureInfo | None:
        if item is None:
            return None

        texture = item.data(
            self.ITEM_TEXTURE_ROLE
        )

        if isinstance(texture, TextureInfo):
            return texture

        return None

    def item_for_texture(
        self,
        texture_or_path: TextureInfo | str | Path,
    ) -> QListWidgetItem | None:
        key = self._resolve_path_key(
            texture_or_path
        )

        return self._items_by_path.get(key)

    def contains_texture(
        self,
        texture_or_path: TextureInfo | str | Path,
    ) -> bool:
        return (
            self.item_for_texture(
                texture_or_path
            )
            is not None
        )

    # ========================================================
    # Keyboard behavior
    # ========================================================

    def keyPressEvent(self, event) -> None:
        """
        ExtendedSelection already supports Ctrl and Shift.

        Ctrl+A is handled explicitly so it remains predictable after
        future custom keyboard shortcuts are introduced.
        """

        if (
            event.key() == Qt.Key.Key_A
            and event.modifiers()
            & Qt.KeyboardModifier.ControlModifier
        ):
            self.select_all_textures()

            event.accept()
            return

        super().keyPressEvent(event)

    # ========================================================
    # Internal path helpers
    # ========================================================

    @staticmethod
    def _validate_texture(
        texture: TextureInfo,
    ) -> None:
        if not isinstance(texture, TextureInfo):
            raise TypeError(
                "ThumbnailBrowser accepts only "
                "TextureInfo objects."
            )

    @classmethod
    def _resolve_path_key(
        cls,
        texture_or_path: TextureInfo | str | Path,
    ) -> str:
        if isinstance(
            texture_or_path,
            TextureInfo,
        ):
            return cls._texture_path_key(
                texture_or_path
            )

        if isinstance(
            texture_or_path,
            (str, Path),
        ):
            return cls._path_key(
                texture_or_path
            )

        raise TypeError(
            "Expected TextureInfo, str or Path."
        )

    @classmethod
    def _texture_path_key(
        cls,
        texture: TextureInfo,
    ) -> str:
        return cls._path_key(
            texture.file.path
        )

    @staticmethod
    def _path_key(
        path: str | Path,
    ) -> str:
        path_object = Path(path).expanduser()

        try:
            normalized_path = (
                path_object.resolve(
                    strict=False
                )
            )

        except OSError:
            normalized_path = (
                path_object.absolute()
            )

        return str(
            normalized_path
        ).casefold()