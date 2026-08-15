# ============================================================
# WT Studio
# Version : 0.1.0
#
# File:
# texture_loader.py
#
# Description:
# Format-independent texture importer
#
# ============================================================

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from PIL import Image, UnidentifiedImageError

from app.models.texture_info import TextureInfo
from app.services.dds_decoder import (
    DDSDecodeError,
    DDSDecoder,
)
from app.services.dds_loader import DDSLoader
from app.services.texture_detector import TextureDetector


class TextureLoadError(Exception):
    """
    Raised when a source file cannot be imported.
    """


class UnsupportedTextureFormatError(TextureLoadError):
    """
    Raised when no loader is registered for a file extension.
    """


class TextureLoader:
    """
    Main texture importer used by WT Studio.

    TextureLoader is responsible for:

    - validating the source path,
    - detecting the texture role,
    - selecting a format loader,
    - reading technical metadata,
    - preparing a preview when Pillow supports the format,
    - returning a unified TextureInfo object.

    DDS metadata is always read with DDSLoader. A Pillow preview is
    optional, so unsupported DDS compression such as BC7 can still be
    imported and displayed in the technical information panel.
    """

    THUMBNAIL_SIZE = (128, 128)

    PILLOW_EXTENSIONS = {
        ".tga",
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
        ".tif",
        ".tiff",
        ".webp",
    }

    SUPPORTED_EXTENSIONS = {
        ".dds",
        *PILLOW_EXTENSIONS,
    }

    def __init__(
        self,
        thumbnail_size: tuple[int, int] | None = None,
    ) -> None:
        self.thumbnail_size = (
            thumbnail_size
            if thumbnail_size is not None
            else self.THUMBNAIL_SIZE
        )

        self._loaders: dict[
            str,
            Callable[[Path, TextureInfo], None],
        ] = {}

        self._register_default_loaders()

    # ========================================================
    # Public API
    # ========================================================

    @classmethod
    def load(
        cls,
        path: str | Path,
    ) -> TextureInfo:
        """
        Compatibility entry point used by the current ProjectManager.

        Existing code can continue calling:

            TextureLoader.load(path)

        Internally, an instance of TextureLoader performs the import.
        """

        return cls().load_texture(path)

    def load_texture(
        self,
        path: str | Path,
    ) -> TextureInfo:
        """
        Loads one texture and returns TextureInfo.

        Import errors related only to preview decoding do not prevent
        the texture from being imported. Structural errors, such as a
        missing file or unsupported extension, raise TextureLoadError.
        """

        source_path = self._validate_path(path)

        extension = source_path.suffix.lower()

        loader = self._loaders.get(extension)

        if loader is None:
            raise UnsupportedTextureFormatError(
                "Unsupported texture format: "
                f"{extension or '(no extension)'}"
            )

        texture_role = (
            TextureDetector.detect_texture_type(
                source_path
            )
        )

        texture = TextureInfo.create(
            path=source_path,
            texture_role=texture_role,
        )

        try:
            loader(source_path, texture)

        except TextureLoadError:
            raise

        except Exception as error:
            texture.import_error = str(error)

            raise TextureLoadError(
                f"Could not import texture "
                f"'{source_path.name}': {error}"
            ) from error

        self._configure_pbr_metadata(texture)

        return texture

    def register_loader(
        self,
        extension: str,
        loader: Callable[
            [Path, TextureInfo],
            None,
        ],
    ) -> None:
        """
        Registers or replaces a format loader.

        This is the extension point for future loaders such as PSDLoader
        or EXRLoader.
        """

        normalized_extension = (
            self._normalize_extension(extension)
        )

        if not callable(loader):
            raise TypeError(
                "Texture loader must be callable."
            )

        self._loaders[normalized_extension] = loader

    def supports(
        self,
        path_or_extension: str | Path,
    ) -> bool:
        """
        Returns True when a loader is registered for the extension.
        """

        text = str(path_or_extension)

        if text.startswith(".") and "/" not in text:
            extension = self._normalize_extension(
                text
            )
        else:
            extension = Path(text).suffix.lower()

        return extension in self._loaders

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        return tuple(sorted(self._loaders.keys()))

    # ========================================================
    # Loader registration
    # ========================================================

    def _register_default_loaders(self) -> None:
        self.register_loader(
            ".dds",
            self._load_dds,
        )

        for extension in self.PILLOW_EXTENSIONS:
            self.register_loader(
                extension,
                self._load_pillow_texture,
            )

    # ========================================================
    # DDS loader
    # ========================================================

    def _load_dds(
        self,
        path: Path,
        texture: TextureInfo,
    ) -> None:
        """
        Loads DDS metadata and attempts to create a preview.

        Metadata loading is mandatory. Preview loading is optional.
        """

        dds_info = self._read_dds_info(path)

        texture.dds_info = dds_info

        self._apply_dds_metadata(
            texture,
            dds_info,
        )

        pillow_error = self._try_load_pillow_preview(
            path,
            texture,
        )

        if texture.preview.preview_available:
            return

        self._try_load_native_dds_preview(
            path=path,
            texture=texture,
            dds_info=dds_info,
            pillow_error=pillow_error,
        )

    def _read_dds_info(
        self,
        path: Path,
    ) -> Any:
        """
        Reads DDS metadata while supporting both the new DDSLoader API
        and the previous read_header() entry point.

        Preferred API:

            DDSLoader().load(path)

        Compatibility API:

            DDSLoader().read_header(path)
        """

        dds_loader = DDSLoader()

        load_method = getattr(
            dds_loader,
            "load",
            None,
        )

        if callable(load_method):
            return load_method(path)

        read_header_method = getattr(
            dds_loader,
            "read_header",
            None,
        )

        if callable(read_header_method):
            return read_header_method(path)

        raise TextureLoadError(
            "DDSLoader has no supported loading method."
        )

    def _apply_dds_metadata(
        self,
        texture: TextureInfo,
        dds_info: Any,
    ) -> None:
        """
        Copies normalized DDS metadata into TextureInfo.
        """

        texture.image_info.width = (
            self._safe_int(
                self._get_first_attribute(
                    dds_info,
                    "width",
                ),
                fallback=0,
            )
        )

        texture.image_info.height = (
            self._safe_int(
                self._get_first_attribute(
                    dds_info,
                    "height",
                ),
                fallback=0,
            )
        )

        texture.compression_info.compression = (
            self._safe_text(
                self._get_first_attribute(
                    dds_info,
                    "compression",
                    "format_name",
                    "pixel_format_name",
                )
            )
        )

        texture.compression_info.mipmaps = max(
            1,
            self._safe_int(
                self._get_first_attribute(
                    dds_info,
                    "mipmap_count",
                    "mipmaps",
                ),
                fallback=1,
            ),
        )

        texture.compression_info.resource_type = (
            self._safe_text(
                self._get_first_attribute(
                    dds_info,
                    "resource_type",
                )
            )
            or "Texture 2D"
        )

        texture.compression_info.dxgi_format = (
            self._get_first_attribute(
                dds_info,
                "dxgi_format",
            )
        )

        texture.compression_info.dxgi_format_name = (
            self._safe_text(
                self._get_first_attribute(
                    dds_info,
                    "dxgi_format_name",
                    "dxgi_name",
                )
            )
        )

        texture.compression_info.array_size = max(
            1,
            self._safe_int(
                self._get_first_attribute(
                    dds_info,
                    "array_size",
                ),
                fallback=1,
            ),
        )

        texture.compression_info.is_cubemap = bool(
            self._get_first_attribute(
                dds_info,
                "is_cubemap",
            )
            or False
        )

        texture.compression_info.is_volume = bool(
            self._get_first_attribute(
                dds_info,
                "is_volume",
            )
            or False
        )

        texture.compression_info.alpha_mode = (
            self._safe_text(
                self._get_first_attribute(
                    dds_info,
                    "alpha_mode",
                )
            )
        )

        dds_alpha = self._get_first_attribute(
            dds_info,
            "has_alpha",
            "contains_alpha",
        )

        if isinstance(dds_alpha, bool):
            texture.image_info.has_alpha = dds_alpha

    # ========================================================
    # Pillow loader
    # ========================================================

    def _load_pillow_texture(
        self,
        path: Path,
        texture: TextureInfo,
    ) -> None:
        """
        Loads a standard image supported by Pillow.
        """

        try:
            with Image.open(path) as source_image:
                source_image.load()

                self._apply_pillow_metadata(
                    texture,
                    source_image,
                )

                self._store_preview(
                    texture,
                    source_image,
                )

        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
        ) as error:
            raise TextureLoadError(
                f"Pillow could not decode "
                f"'{path.name}': {error}"
            ) from error

    def _try_load_pillow_preview(
        self,
        path: Path,
        texture: TextureInfo,
    ) -> str:
        """
        Attempts Pillow decoding first.

        Returns an empty string on success or a readable error message
        when the fallback DDS decoder should be attempted.
        """

        try:
            with Image.open(path) as source_image:
                source_image.load()

                self._apply_pillow_metadata(
                    texture,
                    source_image,
                    preserve_dimensions=True,
                )

                self._store_preview(
                    texture,
                    source_image,
                )

            return ""

        except Exception as error:
            texture.preview.clear()

            error_message = str(error)

            texture.preview.preview_error = (
                error_message
            )

            return error_message

    def _try_load_native_dds_preview(
        self,
        *,
        path: Path,
        texture: TextureInfo,
        dds_info: Any,
        pillow_error: str,
    ) -> None:
        """
        Uses DDSDecoder after Pillow fails.

        This path provides BC1/BC3/BC4/BC5/BC6H/BC7 decoding through
        texture2ddecoder. Import still succeeds when no decoder can
        produce an image; the detailed reason is stored in preview_error.
        """

        try:
            decoded_image = DDSDecoder().decode(
                path,
                dds_info,
            )

            self._apply_pillow_metadata(
                texture,
                decoded_image,
                preserve_dimensions=True,
            )

            self._store_preview(
                texture,
                decoded_image,
            )

        except DDSDecodeError as error:
            texture.preview.clear()

            native_error = str(error)

            if pillow_error:
                texture.preview.preview_error = (
                    "Pillow: "
                    f"{pillow_error}\n"
                    "DDS decoder: "
                    f"{native_error}"
                )
            else:
                texture.preview.preview_error = (
                    native_error
                )

    def _apply_pillow_metadata(
        self,
        texture: TextureInfo,
        image: Image.Image,
        preserve_dimensions: bool = False,
    ) -> None:
        """
        Copies generic image properties from Pillow.
        """

        if (
            not preserve_dimensions
            or texture.image_info.width <= 0
        ):
            texture.image_info.width = image.width

        if (
            not preserve_dimensions
            or texture.image_info.height <= 0
        ):
            texture.image_info.height = image.height

        bands = tuple(image.getbands())

        texture.image_info.channel_names = bands
        texture.image_info.channels = len(bands)

        texture.image_info.mode = image.mode

        texture.image_info.has_alpha = (
            "A" in bands
            or image.mode in {
                "LA",
                "PA",
                "RGBA",
                "RGBa",
            }
        )

        if not texture.compression_info.compression:
            texture.compression_info.compression = (
                self._detect_pillow_compression(
                    image,
                    texture.file.extension,
                )
            )

    def _store_preview(
        self,
        texture: TextureInfo,
        source_image: Image.Image,
    ) -> None:
        """
        Stores independent image and thumbnail copies.

        The source image may be closed safely after this method returns.
        """

        preview_image = source_image.copy()

        thumbnail = source_image.copy()

        thumbnail.thumbnail(
            self.thumbnail_size,
            self._thumbnail_resampling_filter(),
        )

        texture.preview.image = preview_image
        texture.preview.thumbnail = thumbnail

        texture.preview.preview_available = True
        texture.preview.thumbnail_available = True

        texture.preview.preview_error = ""

    # ========================================================
    # PBR metadata
    # ========================================================

    def _configure_pbr_metadata(
        self,
        texture: TextureInfo,
    ) -> None:
        """
        Prepares initial information for the future PBR Converter.

        This does not perform conversion. It only identifies known
        War Thunder suffixes and records their channel layouts.
        """

        filename_stem = texture.file.path.stem.lower()

        if filename_stem.endswith("_n"):
            texture.pbr.source_suffix = "_n"

            texture.pbr.channel_layout = (
                "R=Smoothness(Inverted), "
                "G=Normal X, "
                "B=Metallic, "
                "A=Normal Y"
            )

            texture.pbr.can_export_as_pbr = True
            texture.pbr.can_build_material = True

            return

        if filename_stem.endswith("_c"):
            texture.pbr.source_suffix = "_c"

            if texture.image_info.has_alpha:
                texture.pbr.channel_layout = (
                    "RGB=Albedo, A=Color Mask"
                )
            else:
                texture.pbr.channel_layout = (
                    "RGB=Albedo"
                )

            texture.pbr.can_export_as_pbr = True
            texture.pbr.can_build_material = True

            return

        if filename_stem.endswith("_ao"):
            texture.pbr.source_suffix = "_ao"

            texture.pbr.channel_layout = (
                "Ambient Occlusion"
            )

            texture.pbr.can_export_as_pbr = True
            texture.pbr.can_build_material = True

            return

        texture.pbr.source_suffix = (
            texture.file.extension
        )

        texture.pbr.channel_layout = "Unknown"

        texture.pbr.can_export_as_pbr = False
        texture.pbr.can_build_material = False

    # ========================================================
    # Validation
    # ========================================================

    @staticmethod
    def _validate_path(
        path: str | Path,
    ) -> Path:
        if path is None:
            raise TextureLoadError(
                "Texture path cannot be None."
            )

        source_path = Path(path)

        if not source_path.exists():
            raise TextureLoadError(
                f"Texture file does not exist: "
                f"{source_path}"
            )

        if not source_path.is_file():
            raise TextureLoadError(
                f"Texture path is not a file: "
                f"{source_path}"
            )

        if not source_path.suffix:
            raise UnsupportedTextureFormatError(
                "Texture file has no extension."
            )

        return source_path

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

    # ========================================================
    # Metadata helpers
    # ========================================================

    @staticmethod
    def _get_first_attribute(
        source: Any,
        *attribute_names: str,
    ) -> Any:
        if source is None:
            return None

        for attribute_name in attribute_names:
            value = getattr(
                source,
                attribute_name,
                None,
            )

            if value is not None:
                return value

        return None

    @staticmethod
    def _safe_int(
        value: Any,
        fallback: int = 0,
    ) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _safe_text(value: Any) -> str:
        if value is None:
            return ""

        enum_name = getattr(
            value,
            "name",
            None,
        )

        if enum_name:
            return str(enum_name)

        return str(value)

    @staticmethod
    def _detect_pillow_compression(
        image: Image.Image,
        extension: str,
    ) -> str:
        """
        Returns a readable compression description for standard images.
        """

        compression = image.info.get(
            "compression"
        )

        if compression:
            return str(compression)

        if extension == ".tga":
            return "Uncompressed"

        if extension in {
            ".png",
            ".bmp",
        }:
            return "Lossless"

        if extension in {
            ".jpg",
            ".jpeg",
        }:
            return "JPEG"

        if extension in {
            ".tif",
            ".tiff",
        }:
            return "TIFF"

        if extension == ".webp":
            return "WebP"

        return "Uncompressed"

    @staticmethod
    def _thumbnail_resampling_filter() -> Any:
        """
        Returns a high-quality resampling filter while remaining
        compatible with different Pillow versions.
        """

        resampling = getattr(
            Image,
            "Resampling",
            None,
        )

        if resampling is not None:
            return resampling.LANCZOS

        return Image.LANCZOS