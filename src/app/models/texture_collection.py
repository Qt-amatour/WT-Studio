# ============================================================
# WT Studio
# Version : 0.1.0
#
# File:
# texture_collection.py
#
# Description:
# Central collection for imported textures
#
# ============================================================

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from app.models.texture_info import TextureInfo


class TextureCollectionError(Exception):
    """
    Base exception for texture collection operations.
    """


class DuplicateTextureError(TextureCollectionError):
    """
    Raised when a texture with the same source path already exists.
    """


class TextureNotFoundError(TextureCollectionError):
    """
    Raised when a requested texture cannot be found.
    """


class TextureCollection:
    """
    Stores and manages textures imported into the current project.

    The collection is independent from the user interface. Widgets
    should display its contents, but they should not become the primary
    storage location for imported textures.

    The collection provides:

    - adding and removing textures,
    - duplicate protection,
    - lookup by source path or file name,
    - selection state,
    - filtering by extension, suffix and texture role,
    - sorting,
    - iteration and indexed access.

    Selection is stored using normalized file paths rather than GUI
    item references. This allows the same selection to be shared later
    by ImportList, ThumbnailBrowser and export tools.
    """

    def __init__(
        self,
        textures: Iterable[TextureInfo] | None = None,
    ) -> None:
        self._textures: list[TextureInfo] = []

        self._textures_by_path: dict[
            str,
            TextureInfo,
        ] = {}

        self._selected_paths: set[str] = set()

        if textures is not None:
            self.extend(textures)

    # ========================================================
    # Python collection protocol
    # ========================================================

    def __len__(self) -> int:
        return len(self._textures)

    def __iter__(self) -> Iterator[TextureInfo]:
        return iter(self._textures)

    def __getitem__(
        self,
        index: int | slice,
    ) -> TextureInfo | list[TextureInfo]:
        return self._textures[index]

    def __contains__(
        self,
        texture_or_path: object,
    ) -> bool:
        if isinstance(texture_or_path, TextureInfo):
            key = self._path_key(
                texture_or_path.file.path
            )

            return key in self._textures_by_path

        if isinstance(texture_or_path, (str, Path)):
            key = self._path_key(texture_or_path)

            return key in self._textures_by_path

        return False

    def __bool__(self) -> bool:
        return bool(self._textures)

    # ========================================================
    # General information
    # ========================================================

    @property
    def count(self) -> int:
        return len(self._textures)

    @property
    def is_empty(self) -> bool:
        return not self._textures

    @property
    def textures(self) -> tuple[TextureInfo, ...]:
        """
        Returns a read-only view of the collection contents.

        A tuple prevents external code from accidentally modifying
        the internal list without using add(), remove() or clear().
        """

        return tuple(self._textures)

    @property
    def selected_count(self) -> int:
        return len(self._selected_paths)

    @property
    def has_selection(self) -> bool:
        return bool(self._selected_paths)

    # ========================================================
    # Adding textures
    # ========================================================

    def add(
        self,
        texture: TextureInfo,
        *,
        replace: bool = False,
    ) -> bool:
        """
        Adds one texture to the collection.

        Returns True when a new texture was added.

        When a texture with the same normalized source path already
        exists:

        - replace=False raises DuplicateTextureError,
        - replace=True replaces the existing TextureInfo object and
          returns False because the number of items did not increase.
        """

        self._validate_texture(texture)

        key = self._path_key(texture.file.path)

        existing = self._textures_by_path.get(key)

        if existing is not None:
            if not replace:
                raise DuplicateTextureError(
                    "Texture is already present in the "
                    f"collection: {texture.file.path}"
                )

            index = self._textures.index(existing)

            self._textures[index] = texture
            self._textures_by_path[key] = texture

            return False

        self._textures.append(texture)
        self._textures_by_path[key] = texture

        return True

    def add_if_missing(
        self,
        texture: TextureInfo,
    ) -> bool:
        """
        Adds a texture only when its path is not already present.

        Returns True if added and False if skipped.
        """

        self._validate_texture(texture)

        key = self._path_key(texture.file.path)

        if key in self._textures_by_path:
            return False

        self._textures.append(texture)
        self._textures_by_path[key] = texture

        return True

    def extend(
        self,
        textures: Iterable[TextureInfo],
        *,
        skip_duplicates: bool = True,
        replace: bool = False,
    ) -> list[TextureInfo]:
        """
        Adds many textures and returns the textures that were newly
        inserted.

        By default duplicate paths are skipped. This is convenient for
        importing multiple files from QFileDialog without interrupting
        the entire import because one file was already loaded.

        replace=True updates existing entries. Replaced entries are not
        included in the returned list because they are not newly added.
        """

        added: list[TextureInfo] = []

        for texture in textures:
            try:
                was_added = self.add(
                    texture,
                    replace=replace,
                )

            except DuplicateTextureError:
                if skip_duplicates:
                    continue

                raise

            if was_added:
                added.append(texture)

        return added

    # ========================================================
    # Removing textures
    # ========================================================

    def remove(
        self,
        texture_or_path: TextureInfo | str | Path,
        *,
        missing_ok: bool = False,
    ) -> TextureInfo | None:
        """
        Removes one texture by object or source path.

        Returns the removed TextureInfo.

        With missing_ok=True, None is returned when the texture cannot
        be found.
        """

        key = self._resolve_key(texture_or_path)

        texture = self._textures_by_path.get(key)

        if texture is None:
            if missing_ok:
                return None

            raise TextureNotFoundError(
                "Texture was not found in the collection."
            )

        self._textures.remove(texture)
        del self._textures_by_path[key]

        self._selected_paths.discard(key)

        return texture

    def remove_many(
        self,
        textures_or_paths: Iterable[
            TextureInfo | str | Path
        ],
        *,
        missing_ok: bool = True,
    ) -> list[TextureInfo]:
        """
        Removes multiple textures and returns successfully removed
        entries.
        """

        removed: list[TextureInfo] = []

        for texture_or_path in textures_or_paths:
            texture = self.remove(
                texture_or_path,
                missing_ok=missing_ok,
            )

            if texture is not None:
                removed.append(texture)

        return removed

    def remove_selected(self) -> list[TextureInfo]:
        """
        Removes all currently selected textures.
        """

        selected_paths = tuple(self._selected_paths)

        return self.remove_many(
            selected_paths,
            missing_ok=True,
        )

    def clear(self) -> None:
        """
        Removes all textures and clears the selection.
        """

        self._textures.clear()
        self._textures_by_path.clear()
        self._selected_paths.clear()

    # ========================================================
    # Lookup
    # ========================================================

    def get(
        self,
        path: str | Path,
        default: Any = None,
    ) -> TextureInfo | Any:
        """
        Returns a texture by normalized source path.
        """

        key = self._path_key(path)

        return self._textures_by_path.get(
            key,
            default,
        )

    def require(
        self,
        path: str | Path,
    ) -> TextureInfo:
        """
        Returns a texture by path or raises TextureNotFoundError.
        """

        texture = self.get(path)

        if texture is None:
            raise TextureNotFoundError(
                f"Texture was not found: {path}"
            )

        return texture

    def find_by_name(
        self,
        name: str,
        *,
        case_sensitive: bool = False,
    ) -> list[TextureInfo]:
        """
        Finds all textures with an exact file name match.

        More than one result is possible because textures from different
        folders may have the same file name.
        """

        if case_sensitive:
            return [
                texture
                for texture in self._textures
                if texture.file.name == name
            ]

        normalized_name = name.casefold()

        return [
            texture
            for texture in self._textures
            if texture.file.name.casefold()
            == normalized_name
        ]

    def search(
        self,
        query: str,
        *,
        case_sensitive: bool = False,
    ) -> list[TextureInfo]:
        """
        Performs a simple text search over file names and source paths.
        """

        if not query:
            return list(self._textures)

        if case_sensitive:
            return [
                texture
                for texture in self._textures
                if query in texture.file.name
                or query in str(texture.file.path)
            ]

        normalized_query = query.casefold()

        return [
            texture
            for texture in self._textures
            if normalized_query
            in texture.file.name.casefold()
            or normalized_query
            in str(texture.file.path).casefold()
        ]

    # ========================================================
    # Selection
    # ========================================================

    def select(
        self,
        texture_or_path: TextureInfo | str | Path,
        *,
        clear_existing: bool = False,
    ) -> None:
        """
        Selects one texture.

        clear_existing=True provides single-selection behavior.
        """

        key = self._resolve_existing_key(
            texture_or_path
        )

        if clear_existing:
            self._selected_paths.clear()

        self._selected_paths.add(key)

    def select_many(
        self,
        textures_or_paths: Iterable[
            TextureInfo | str | Path
        ],
        *,
        clear_existing: bool = False,
    ) -> None:
        """
        Selects multiple textures.
        """

        keys = [
            self._resolve_existing_key(item)
            for item in textures_or_paths
        ]

        if clear_existing:
            self._selected_paths.clear()

        self._selected_paths.update(keys)

    def deselect(
        self,
        texture_or_path: TextureInfo | str | Path,
    ) -> None:
        key = self._resolve_key(texture_or_path)

        self._selected_paths.discard(key)

    def toggle_selection(
        self,
        texture_or_path: TextureInfo | str | Path,
    ) -> bool:
        """
        Toggles selection and returns the new state.
        """

        key = self._resolve_existing_key(
            texture_or_path
        )

        if key in self._selected_paths:
            self._selected_paths.remove(key)

            return False

        self._selected_paths.add(key)

        return True

    def select_all(self) -> None:
        self._selected_paths = set(
            self._textures_by_path.keys()
        )

    def clear_selection(self) -> None:
        self._selected_paths.clear()

    def is_selected(
        self,
        texture_or_path: TextureInfo | str | Path,
    ) -> bool:
        key = self._resolve_key(texture_or_path)

        return key in self._selected_paths

    def selected(self) -> list[TextureInfo]:
        """
        Returns selected textures in collection order.

        This is more predictable for export than iterating over a set.
        """

        return [
            texture
            for texture in self._textures
            if self._path_key(texture.file.path)
            in self._selected_paths
        ]

    # ========================================================
    # Filtering
    # ========================================================

    def filter_by_extension(
        self,
        extension: str,
    ) -> list[TextureInfo]:
        normalized_extension = (
            self._normalize_extension(extension)
        )

        return [
            texture
            for texture in self._textures
            if texture.file.extension
            == normalized_extension
        ]

    def filter_by_suffix(
        self,
        suffix: str,
    ) -> list[TextureInfo]:
        """
        Filters by a War Thunder file suffix such as:

            _c
            _n
            _ao

        It first checks PBRInfo.source_suffix and falls back to the file
        stem so it remains useful for older TextureInfo objects.
        """

        normalized_suffix = (
            self._normalize_texture_suffix(suffix)
        )

        matching: list[TextureInfo] = []

        for texture in self._textures:
            source_suffix = str(
                texture.pbr.source_suffix or ""
            ).casefold()

            if source_suffix == normalized_suffix:
                matching.append(texture)
                continue

            stem = texture.file.path.stem.casefold()

            if stem.endswith(normalized_suffix):
                matching.append(texture)

        return matching

    def filter_by_role(
        self,
        role: Any,
    ) -> list[TextureInfo]:
        """
        Filters by the value stored in texture.pbr.texture_role.
        """

        return [
            texture
            for texture in self._textures
            if texture.pbr.texture_role == role
        ]

    def pbr_exportable(self) -> list[TextureInfo]:
        return [
            texture
            for texture in self._textures
            if texture.pbr.can_export_as_pbr
        ]

    def material_buildable(self) -> list[TextureInfo]:
        return [
            texture
            for texture in self._textures
            if texture.pbr.can_build_material
        ]

    def with_preview(self) -> list[TextureInfo]:
        return [
            texture
            for texture in self._textures
            if texture.preview.preview_available
        ]

    def without_preview(self) -> list[TextureInfo]:
        return [
            texture
            for texture in self._textures
            if not texture.preview.preview_available
        ]

    # ========================================================
    # Sorting
    # ========================================================

    def sort_by_name(
        self,
        *,
        reverse: bool = False,
    ) -> None:
        self._textures.sort(
            key=lambda texture: (
                texture.file.name.casefold()
            ),
            reverse=reverse,
        )

    def sort_by_extension(
        self,
        *,
        reverse: bool = False,
    ) -> None:
        self._textures.sort(
            key=lambda texture: (
                texture.file.extension.casefold(),
                texture.file.name.casefold(),
            ),
            reverse=reverse,
        )

    def sort_by_size(
        self,
        *,
        reverse: bool = False,
    ) -> None:
        self._textures.sort(
            key=lambda texture: (
                texture.file.size_bytes
            ),
            reverse=reverse,
        )

    def sort_by_resolution(
        self,
        *,
        reverse: bool = False,
    ) -> None:
        self._textures.sort(
            key=lambda texture: (
                texture.image_info.width
                * texture.image_info.height,
                texture.file.name.casefold(),
            ),
            reverse=reverse,
        )

    def sort_by_import_order(self) -> None:
        """
        This method currently does nothing.

        The normal internal order is already the import order. It is
        included as an explicit API placeholder because restoring import
        order after custom sorting will later require a persistent import
        index in TextureInfo or ProjectManager.
        """

        return None

    # ========================================================
    # Conversion helpers
    # ========================================================

    def to_list(self) -> list[TextureInfo]:
        """
        Returns a shallow copy of the internal texture list.
        """

        return list(self._textures)

    def paths(self) -> list[Path]:
        return [
            texture.file.path
            for texture in self._textures
        ]

    def selected_paths(self) -> list[Path]:
        return [
            texture.file.path
            for texture in self.selected()
        ]

    # ========================================================
    # Internal helpers
    # ========================================================

    @staticmethod
    def _validate_texture(
        texture: TextureInfo,
    ) -> None:
        if not isinstance(texture, TextureInfo):
            raise TypeError(
                "TextureCollection accepts only "
                "TextureInfo objects."
            )

        if texture.file is None:
            raise ValueError(
                "TextureInfo.file cannot be None."
            )

        if not texture.file.path:
            raise ValueError(
                "TextureInfo.file.path cannot be empty."
            )

    @classmethod
    def _resolve_key(
        cls,
        texture_or_path: TextureInfo | str | Path,
    ) -> str:
        if isinstance(texture_or_path, TextureInfo):
            return cls._path_key(
                texture_or_path.file.path
            )

        if isinstance(texture_or_path, (str, Path)):
            return cls._path_key(texture_or_path)

        raise TypeError(
            "Expected TextureInfo, str or Path."
        )

    def _resolve_existing_key(
        self,
        texture_or_path: TextureInfo | str | Path,
    ) -> str:
        key = self._resolve_key(texture_or_path)

        if key not in self._textures_by_path:
            raise TextureNotFoundError(
                "Texture cannot be selected because it "
                "is not present in the collection."
            )

        return key

    @staticmethod
    def _path_key(path: str | Path) -> str:
        """
        Produces a normalized key suitable for Windows paths.

        resolve(strict=False) normalizes relative segments without
        requiring the file to exist. casefold() prevents duplicates that
        differ only in letter casing on Windows.
        """

        path_object = Path(path).expanduser()

        try:
            normalized = path_object.resolve(
                strict=False
            )

        except OSError:
            normalized = path_object.absolute()

        return str(normalized).casefold()

    @staticmethod
    def _normalize_extension(
        extension: str,
    ) -> str:
        normalized = str(extension).strip().lower()

        if not normalized:
            raise ValueError(
                "Extension cannot be empty."
            )

        if not normalized.startswith("."):
            normalized = f".{normalized}"

        return normalized

    @staticmethod
    def _normalize_texture_suffix(
        suffix: str,
    ) -> str:
        normalized = str(suffix).strip().casefold()

        if not normalized:
            raise ValueError(
                "Texture suffix cannot be empty."
            )

        if not normalized.startswith("_"):
            normalized = f"_{normalized}"

        return normalized