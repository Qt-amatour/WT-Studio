from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from PIL import Image, ImageChops

from app.models.new_asset_material import NewAssetMaterial
from app.models.new_asset_types import NewAssetType
from app.services.new_asset_builder import NewAssetBuilder


class NewAssetExportError(Exception):
    pass


@dataclass(slots=True)
class NewAssetExportItemResult:
    asset_id: str
    asset_name: str
    output_path: Path | None = None
    error: str = ""
    verified: bool = False

    @property
    def succeeded(self) -> bool:
        return self.output_path is not None and not self.error


@dataclass(slots=True)
class NewAssetBatchExportResult:
    items: list[NewAssetExportItemResult] = field(default_factory=list)

    @property
    def exported_paths(self) -> list[Path]:
        return [
            item.output_path
            for item in self.items
            if item.output_path is not None
        ]

    @property
    def errors(self) -> list[NewAssetExportItemResult]:
        return [item for item in self.items if item.error]

    @property
    def exported_count(self) -> int:
        return len(self.exported_paths)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def verified_count(self) -> int:
        return sum(1 for item in self.items if item.verified)


ProgressCallback = Callable[[int, int, str], None]
CancelCallback = Callable[[], bool]


class NewAssetExporter:
    """Lossless, uncompressed TGA exporter for AssetViewer source assets."""

    def __init__(
        self,
        builder: NewAssetBuilder | None = None,
    ) -> None:
        self.builder = builder or NewAssetBuilder()

    def export_many(
        self,
        materials: list[NewAssetMaterial],
        output_directory: str | Path,
        *,
        progress_callback: ProgressCallback | None = None,
        cancel_callback: CancelCallback | None = None,
    ) -> NewAssetBatchExportResult:
        target = Path(output_directory).expanduser()
        target.mkdir(parents=True, exist_ok=True)

        result = NewAssetBatchExportResult()
        total = len(materials)

        for index, material in enumerate(materials, start=1):
            if cancel_callback and cancel_callback():
                break

            if progress_callback:
                progress_callback(
                    index - 1,
                    total,
                    material.name,
                )

            item = NewAssetExportItemResult(
                asset_id=material.asset_id,
                asset_name=material.name,
            )

            try:
                item.output_path = self.export_material(
                    material,
                    target,
                )
                item.verified = True
            except Exception as error:
                item.error = str(error)

            result.items.append(item)

            if progress_callback:
                progress_callback(
                    index,
                    total,
                    material.name,
                )

        return result

    def export_material(
        self,
        material: NewAssetMaterial,
        output_directory: str | Path,
    ) -> Path:
        image = material.preview_image
        if image is None or material.is_dirty:
            image = self.builder.build(material)

        if image is None:
            raise NewAssetExportError(
                material.build_error
                or "New asset material is not ready for export."
            )

        target_dir = Path(output_directory).expanduser()
        target_dir.mkdir(parents=True, exist_ok=True)

        output_path = target_dir / self.build_filename(material)
        staged = output_path.with_suffix(output_path.suffix + ".tmp")

        try:
            self._write_tga(material, image, staged)
            self._verify_tga(material, image, staged)
            staged.replace(output_path)
        except Exception:
            staged.unlink(missing_ok=True)
            raise

        return output_path

    @classmethod
    def build_filename(cls, material: NewAssetMaterial) -> str:
        base = cls.normalize_base_name(material.name)
        return f"{base}{material.asset_type.value}.tga"

    @staticmethod
    def normalize_base_name(value: str) -> str:
        cleaned = re.sub(r"\s+", "_", str(value).strip())
        cleaned = re.sub(r"_+", "_", cleaned)
        cleaned = re.sub(
            r"(?:_c|_n|_ao)(?:\.tga)?$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = cleaned.strip(" ._")
        return cleaned or "asset"

    @staticmethod
    def _write_tga(
        material: NewAssetMaterial,
        image: Image.Image,
        output_path: Path,
    ) -> None:
        if material.asset_type is NewAssetType.AO:
            prepared = image.convert("L")
        else:
            prepared = image.convert("RGBA")

        # Pillow writes uncompressed TGA unless RLE compression is explicitly
        # requested. We deliberately do not request compression here.
        prepared.save(output_path, format="TGA")

    @staticmethod
    def _verify_tga(
        material: NewAssetMaterial,
        source_image: Image.Image,
        output_path: Path,
    ) -> None:
        expected = (
            source_image.convert("L")
            if material.asset_type is NewAssetType.AO
            else source_image.convert("RGBA")
        )

        with Image.open(output_path) as reopened:
            reopened.load()
            actual = reopened.convert(expected.mode)

        if actual.size != expected.size:
            raise NewAssetExportError(
                "TGA verification failed: resolution changed."
            )

        if ImageChops.difference(expected, actual).getbbox() is not None:
            raise NewAssetExportError(
                "TGA verification failed: pixel values changed."
            )
