from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import Image, ImageChops

from app.models.new_asset_material import NewAssetMaterial
from app.models.new_asset_types import NewAssetSlotType, NewAssetType


class NewAssetBuildError(Exception):
    pass


class NewAssetSlotLoadError(NewAssetBuildError):
    pass


class NewAssetBuilder:
    """Build AssetViewer-ready source textures without touching DDS workflow."""

    SUPPORTED_EXTENSIONS = {
        ".dds", ".tga", ".png", ".jpg", ".jpeg",
        ".bmp", ".tif", ".tiff", ".webp",
    }

    def assign_path(
        self,
        material: NewAssetMaterial,
        slot_type: NewAssetSlotType,
        path: str | Path,
    ) -> None:
        material.slot(slot_type).source_path = Path(path)
        self.reload_slot(material, slot_type)

    def reload_slot(
        self,
        material: NewAssetMaterial,
        slot_type: NewAssetSlotType,
    ) -> None:
        slot = material.slot(slot_type)
        if slot.source_path is None:
            raise NewAssetSlotLoadError(
                f"No file assigned to {slot_type.display_name}."
            )

        path = slot.source_path
        if not path.exists() or not path.is_file():
            slot.image = None
            slot.error = f"File does not exist: {path}"
            raise NewAssetSlotLoadError(slot.error)

        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            slot.image = None
            slot.error = f"Unsupported format: {path.suffix}"
            raise NewAssetSlotLoadError(slot.error)

        try:
            with Image.open(path) as source:
                source.load()
                slot.image = source.copy()
        except Exception as error:
            slot.image = None
            slot.error = str(error)
            raise NewAssetSlotLoadError(
                f"Could not load '{path.name}': {error}"
            ) from error

        stat_result = path.stat()
        slot.loaded_at = datetime.now()
        slot.file_modified_at = stat_result.st_mtime
        slot.error = ""
        material.is_dirty = True
        self.build(material)

    def clear_slot(
        self,
        material: NewAssetMaterial,
        slot_type: NewAssetSlotType,
    ) -> None:
        material.slot(slot_type).clear()
        material.is_dirty = True
        self.build(material)

    def build(self, material: NewAssetMaterial):
        material.build_error = ""
        material.build_warnings.clear()

        try:
            if material.asset_type is NewAssetType.COLOR:
                result = self._build_color(material)
            elif material.asset_type is NewAssetType.NORMAL:
                result = self._build_normal(material)
            elif material.asset_type is NewAssetType.AO:
                result = self._build_ao(material)
            else:
                raise NewAssetBuildError(
                    f"Unsupported new asset type: {material.asset_type}"
                )
        except NewAssetBuildError as error:
            material.preview_image = None
            material.build_error = str(error)
            material.is_dirty = True
            return None

        material.preview_image = result
        material.is_dirty = False
        return result

    def _build_color(self, material: NewAssetMaterial) -> Image.Image:
        albedo = self._required_image(
            material,
            NewAssetSlotType.ALBEDO,
        ).convert("RGB")

        alpha_slot = material.slot(NewAssetSlotType.ALPHA)
        if alpha_slot.image is None:
            material.build_warnings.append(
                "Alpha / Mask is empty; export uses opaque alpha (255)."
            )
            alpha = Image.new("L", albedo.size, 255)
        else:
            alpha = self._match_size(
                alpha_slot.image,
                albedo.size,
                NewAssetSlotType.ALPHA,
            ).convert("L")

        red, green, blue = albedo.split()
        return Image.merge(
            "RGBA",
            (red, green, blue, alpha),
        )

    def _build_normal(self, material: NewAssetMaterial) -> Image.Image:
        normal = self._required_image(
            material,
            NewAssetSlotType.NORMAL,
        ).convert("RGB")
        size = normal.size

        roughness = self._match_size(
            self._required_image(
                material,
                NewAssetSlotType.ROUGHNESS,
            ),
            size,
            NewAssetSlotType.ROUGHNESS,
        ).convert("L")

        metallic = self._match_size(
            self._required_image(
                material,
                NewAssetSlotType.METALLIC,
            ),
            size,
            NewAssetSlotType.METALLIC,
        ).convert("L")

        normal_x, normal_y, _ = normal.split()

        if material.normal_map_opengl:
            normal_y = ImageChops.invert(normal_y)

        # AssetViewer source _n profile confirmed from working TGA samples:
        #   R = Normal X
        #   G = Normal Y (DirectX convention)
        #   B = Metallic
        #   A = inverted Roughness
        return Image.merge(
            "RGBA",
            (
                normal_x,
                normal_y,
                metallic,
                ImageChops.invert(roughness),
            ),
        )

    def _build_ao(self, material: NewAssetMaterial) -> Image.Image:
        # Keep AO truly single-channel. The NewAssetExporter writes this as
        # an uncompressed 8-bit grayscale TGA with no redundant RGB copies.
        return self._required_image(
            material,
            NewAssetSlotType.AO,
        ).convert("L")

    @staticmethod
    def _required_image(
        material: NewAssetMaterial,
        slot_type: NewAssetSlotType,
    ) -> Image.Image:
        image = material.slot(slot_type).image
        if image is None:
            raise NewAssetBuildError(
                f"Missing required slot: {slot_type.display_name}"
            )
        return image

    @staticmethod
    def _match_size(
        image: Image.Image,
        expected_size: tuple[int, int],
        slot_type: NewAssetSlotType,
    ) -> Image.Image:
        if image.size != expected_size:
            raise NewAssetBuildError(
                f"{slot_type.display_name} has resolution "
                f"{image.width} × {image.height}; expected "
                f"{expected_size[0]} × {expected_size[1]}."
            )
        return image
