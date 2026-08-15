# ============================================================
# WT Studio
# Version : 0.1.0
#
# File:
# texture_info.py
#
# Description:
# Central texture data model used by WT Studio
#
# ============================================================

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


# ============================================================
# File information
# ============================================================

@dataclass(slots=True)
class FileInfo:
    """
    Information about the source file stored on disk.
    """

    path: Path
    name: str
    extension: str
    size_bytes: int = 0
    modified_time: datetime | None = None

    @classmethod
    def from_path(cls, path: str | Path) -> FileInfo:
        """
        Creates FileInfo from a filesystem path.

        The method does not require the file metadata to be readable.
        When stat() fails, size and modification time remain unavailable.
        """

        resolved_path = Path(path)

        size_bytes = 0
        modified_time = None

        try:
            stat_result = resolved_path.stat()

            size_bytes = stat_result.st_size
            modified_time = datetime.fromtimestamp(
                stat_result.st_mtime
            )

        except OSError:
            pass

        return cls(
            path=resolved_path,
            name=resolved_path.name,
            extension=resolved_path.suffix.lower(),
            size_bytes=size_bytes,
            modified_time=modified_time,
        )


# ============================================================
# Image information
# ============================================================

@dataclass(slots=True)
class ImageInfo:
    """
    General image properties independent of the source format.
    """

    width: int = 0
    height: int = 0

    channels: int = 0
    channel_names: tuple[str, ...] = field(
        default_factory=tuple
    )

    mode: str = ""
    color_space: str = ""

    has_alpha: bool | None = None

    @property
    def resolution(self) -> tuple[int, int]:
        return self.width, self.height

    @property
    def resolution_text(self) -> str:
        if self.width <= 0 or self.height <= 0:
            return "-"

        return f"{self.width} × {self.height}"


# ============================================================
# Compression and resource information
# ============================================================

@dataclass(slots=True)
class CompressionInfo:
    """
    Compression and GPU-resource properties.

    Most fields are especially useful for DDS files, but the structure
    is format-independent so that other loaders can use it too.
    """

    compression: str = ""
    mipmaps: int = 1

    resource_type: str = "Texture 2D"

    dxgi_format: int | str | None = None
    dxgi_format_name: str = ""

    array_size: int = 1

    is_cubemap: bool = False
    is_volume: bool = False

    alpha_mode: str = ""

    @property
    def has_dxgi_format(self) -> bool:
        return self.dxgi_format is not None


# ============================================================
# Preview information
# ============================================================

@dataclass
class PreviewInfo:
    """
    Runtime preview data used by the graphical interface.

    These values are intentionally separated from file and image
    metadata. Loaders can create TextureInfo even when no preview
    decoder is available.
    """

    image: Any | None = None
    thumbnail: Any | None = None

    preview_available: bool = False
    thumbnail_available: bool = False

    preview_error: str = ""

    def clear(self) -> None:
        self.image = None
        self.thumbnail = None

        self.preview_available = False
        self.thumbnail_available = False

        self.preview_error = ""


# ============================================================
# PBR information
# ============================================================

@dataclass(slots=True)
class PBRInfo:
    """
    Information used by the PBR Converter and Material Builder.

    texture_role:
        Role detected automatically by TextureDetector.

    manual_texture_role:
        Optional role selected manually by the user.

    effective_texture_role:
        Manual role when an override exists, otherwise the detected role.

    The role values may currently be enums or strings, depending on
    TextureDetector and the user-interface implementation.
    """

    # Existing field retained for compatibility with current loaders.
    # It represents the automatically detected role.
    texture_role: Any = None

    # None means that automatic detection remains active.
    manual_texture_role: Any = None

    channel_layout: str = "Unknown"

    can_export_as_pbr: bool = False
    can_build_material: bool = False

    source_suffix: str = ""

    @property
    def detected_texture_role(self) -> Any:
        """
        Explicit alias for the automatically detected role.
        """

        return self.texture_role

    @detected_texture_role.setter
    def detected_texture_role(self, value: Any) -> None:
        self.texture_role = value

    @property
    def effective_texture_role(self) -> Any:
        """
        Returns the role that should currently be used by the program.
        """

        if self.manual_texture_role is not None:
            return self.manual_texture_role

        return self.texture_role

    @property
    def has_manual_override(self) -> bool:
        return self.manual_texture_role is not None

    def set_manual_texture_role(
        self,
        texture_role: Any,
    ) -> None:
        """
        Sets a manual role override.

        Passing None is equivalent to clearing the override.
        """

        self.manual_texture_role = texture_role

    def clear_manual_texture_role(self) -> None:
        """
        Restores automatic role detection.
        """

        self.manual_texture_role = None

    @staticmethod
    def _role_name(role: Any) -> str:
        if role is None:
            return "Unknown"

        enum_name = getattr(
            role,
            "name",
            None,
        )

        if enum_name:
            return str(enum_name)

        return str(role)

    @property
    def role_name(self) -> str:
        """
        Display name of the effective role.
        """

        return self._role_name(
            self.effective_texture_role
        )

    @property
    def detected_role_name(self) -> str:
        return self._role_name(
            self.detected_texture_role
        )

    @property
    def manual_role_name(self) -> str:
        if not self.has_manual_override:
            return "Automatic"

        return self._role_name(
            self.manual_texture_role
        )


# ============================================================
# Central texture model
# ============================================================

@dataclass
class TextureInfo:
    """
    Central texture object used by WT Studio.

    New code should use the structured properties:

        texture.file.name
        texture.image_info.width
        texture.compression_info.mipmaps
        texture.preview.thumbnail
        texture.pbr.detected_texture_role
        texture.pbr.manual_texture_role
        texture.pbr.effective_texture_role
        texture.dds_info

    Compatibility properties are provided at the bottom of this class
    so that the current UI can continue using:

        texture.name
        texture.width
        texture.image
        texture.compression
        texture.mipmaps
        texture.texture_type
    """

    file: FileInfo

    image_info: ImageInfo = field(
        default_factory=ImageInfo
    )

    compression_info: CompressionInfo = field(
        default_factory=CompressionInfo
    )

    preview: PreviewInfo = field(
        default_factory=PreviewInfo
    )

    pbr: PBRInfo = field(
        default_factory=PBRInfo
    )

    dds_info: Any | None = None

    import_error: str = ""

    # ========================================================
    # Construction helpers
    # ========================================================

    @classmethod
    def create(
        cls,
        path: str | Path,
        texture_role: Any = None,
    ) -> TextureInfo:
        """
        Creates an empty texture model for the selected source path.

        texture_role is stored as the automatically detected role.
        """

        file_info = FileInfo.from_path(path)

        return cls(
            file=file_info,
            pbr=PBRInfo(
                texture_role=texture_role,
                source_suffix=file_info.extension,
            ),
        )

    # ========================================================
    # General properties
    # ========================================================

    @property
    def is_dds(self) -> bool:
        return self.file.extension == ".dds"

    @property
    def has_preview(self) -> bool:
        return self.preview.preview_available

    @property
    def dimensions_text(self) -> str:
        return self.image_info.resolution_text

    @property
    def file_size(self) -> int:
        return self.file.size_bytes

    @property
    def size_bytes(self) -> int:
        return self.file.size_bytes

    # ========================================================
    # Texture-role API
    # ========================================================

    @property
    def detected_type(self) -> Any:
        """
        Role detected automatically from the source texture.
        """

        return self.pbr.detected_texture_role

    @detected_type.setter
    def detected_type(self, value: Any) -> None:
        self.pbr.detected_texture_role = value

    @property
    def manual_type(self) -> Any:
        """
        Optional role selected manually by the user.
        """

        return self.pbr.manual_texture_role

    @manual_type.setter
    def manual_type(self, value: Any) -> None:
        self.pbr.manual_texture_role = value

    @property
    def effective_type(self) -> Any:
        """
        Role that should be used by converter and interface code.
        """

        return self.pbr.effective_texture_role

    @property
    def has_manual_type(self) -> bool:
        return self.pbr.has_manual_override

    def set_manual_type(
        self,
        texture_role: Any,
    ) -> None:
        """
        Overrides the automatically detected role.
        """

        self.pbr.set_manual_texture_role(
            texture_role
        )

    def clear_manual_type(self) -> None:
        """
        Removes the manual override and returns to automatic detection.
        """

        self.pbr.clear_manual_texture_role()

    # ========================================================
    # DDS aliases
    # ========================================================

    @property
    def dds(self) -> Any | None:
        """
        Alias retained for widgets that search for texture.dds.
        """

        return self.dds_info

    @dds.setter
    def dds(self, value: Any | None) -> None:
        self.dds_info = value

    # ========================================================
    # Compatibility API
    #
    # These properties preserve the interface used by the current
    # widgets and ProjectManager.
    # ========================================================

    @property
    def name(self) -> str:
        return self.file.name

    @name.setter
    def name(self, value: str) -> None:
        self.file.name = str(value)

    @property
    def path(self) -> str:
        return str(self.file.path)

    @path.setter
    def path(self, value: str | Path) -> None:
        self.file.path = Path(value)

    @property
    def extension(self) -> str:
        return self.file.extension

    @extension.setter
    def extension(self, value: str) -> None:
        extension = str(value).strip().lower()

        if extension and not extension.startswith("."):
            extension = f".{extension}"

        self.file.extension = extension

    @property
    def texture_type(self) -> Any:
        """
        Backward-compatible detected-role property.

        Existing loaders can continue assigning texture.texture_type.
        New converter and UI code should read texture.effective_type.
        """

        return self.detected_type

    @texture_type.setter
    def texture_type(self, value: Any) -> None:
        self.detected_type = value

    @property
    def width(self) -> int:
        return self.image_info.width

    @width.setter
    def width(self, value: int) -> None:
        self.image_info.width = self._safe_positive_int(
            value,
            fallback=0,
        )

    @property
    def height(self) -> int:
        return self.image_info.height

    @height.setter
    def height(self, value: int) -> None:
        self.image_info.height = self._safe_positive_int(
            value,
            fallback=0,
        )

    @property
    def channels(self) -> int:
        return self.image_info.channels

    @channels.setter
    def channels(self, value: int) -> None:
        self.image_info.channels = self._safe_positive_int(
            value,
            fallback=0,
        )

    @property
    def has_alpha(self) -> bool | None:
        return self.image_info.has_alpha

    @has_alpha.setter
    def has_alpha(
        self,
        value: bool | None,
    ) -> None:
        self.image_info.has_alpha = value

    @property
    def color_space(self) -> str:
        return self.image_info.color_space

    @color_space.setter
    def color_space(self, value: str) -> None:
        self.image_info.color_space = str(value or "")

    @property
    def compression(self) -> str:
        return self.compression_info.compression

    @compression.setter
    def compression(self, value: str) -> None:
        self.compression_info.compression = str(
            value or ""
        )

    @property
    def mipmaps(self) -> int:
        return self.compression_info.mipmaps

    @mipmaps.setter
    def mipmaps(self, value: int) -> None:
        self.compression_info.mipmaps = (
            self._safe_positive_int(
                value,
                fallback=1,
            )
        )

    @property
    def resource_type(self) -> str:
        return self.compression_info.resource_type

    @resource_type.setter
    def resource_type(self, value: str) -> None:
        self.compression_info.resource_type = str(
            value or ""
        )

    @property
    def dxgi_format(self) -> int | str | None:
        return self.compression_info.dxgi_format

    @dxgi_format.setter
    def dxgi_format(
        self,
        value: int | str | None,
    ) -> None:
        self.compression_info.dxgi_format = value

    @property
    def dxgi_format_name(self) -> str:
        return self.compression_info.dxgi_format_name

    @dxgi_format_name.setter
    def dxgi_format_name(self, value: str) -> None:
        self.compression_info.dxgi_format_name = str(
            value or ""
        )

    @property
    def image(self) -> Any | None:
        return self.preview.image

    @image.setter
    def image(self, value: Any | None) -> None:
        self.preview.image = value
        self.preview.preview_available = value is not None

    @property
    def thumbnail(self) -> Any | None:
        return self.preview.thumbnail

    @thumbnail.setter
    def thumbnail(self, value: Any | None) -> None:
        self.preview.thumbnail = value
        self.preview.thumbnail_available = (
            value is not None
        )

    @property
    def preview_available(self) -> bool:
        return self.preview.preview_available

    @preview_available.setter
    def preview_available(self, value: bool) -> None:
        self.preview.preview_available = bool(value)

    # ========================================================
    # Internal helpers
    # ========================================================

    @staticmethod
    def _safe_positive_int(
        value: Any,
        fallback: int,
    ) -> int:
        try:
            result = int(value)
        except (TypeError, ValueError):
            return fallback

        if result < 0:
            return fallback

        return result
