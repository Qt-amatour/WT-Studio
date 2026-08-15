from __future__ import annotations
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageChops
from app.models.material_types import MaterialSlotType, MaterialType
from app.models.pbr_material import PBRMaterial

class MaterialBuildError(Exception):
    pass

class MaterialSlotLoadError(MaterialBuildError):
    pass

class MaterialBuilder:
    SUPPORTED_EXTENSIONS = {
        ".dds", ".tga", ".png", ".jpg", ".jpeg",
        ".bmp", ".tif", ".tiff", ".webp",
    }

    def assign_path(self, material: PBRMaterial, slot_type: MaterialSlotType, path: str | Path) -> None:
        material.slot(slot_type).source_path = Path(path)
        self.reload_slot(material, slot_type)

    def reload_slot(self, material: PBRMaterial, slot_type: MaterialSlotType) -> None:
        slot = material.slot(slot_type)
        if slot.source_path is None:
            raise MaterialSlotLoadError(f"No file assigned to {slot_type.display_name}.")
        path = slot.source_path
        if not path.exists() or not path.is_file():
            slot.image = None
            slot.error = f"File does not exist: {path}"
            raise MaterialSlotLoadError(slot.error)
        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            slot.image = None
            slot.error = f"Unsupported format: {path.suffix}"
            raise MaterialSlotLoadError(slot.error)
        try:
            with Image.open(path) as source:
                source.load()
                slot.image = source.copy()
        except Exception as error:
            slot.image = None
            slot.error = str(error)
            raise MaterialSlotLoadError(f"Could not load '{path.name}': {error}") from error
        stat_result = path.stat()
        slot.loaded_at = datetime.now()
        slot.file_modified_at = stat_result.st_mtime
        slot.error = ""
        material.is_dirty = True
        self.build(material)

    def clear_slot(self, material: PBRMaterial, slot_type: MaterialSlotType) -> None:
        material.slot(slot_type).clear()
        material.is_dirty = True
        self.build(material)

    def build(self, material: PBRMaterial):
        material.build_error = ""
        material.build_warnings.clear()
        try:
            if material.material_type == MaterialType.COLOR:
                result = self._build_color(material)
            elif material.material_type == MaterialType.NORMAL:
                result = self._build_normal(material)
            elif material.material_type == MaterialType.AO:
                result = self._build_ao(material)
            else:
                raise MaterialBuildError(f"Unsupported material type: {material.material_type}")
        except MaterialBuildError as error:
            material.preview_image = None
            material.build_error = str(error)
            material.is_dirty = True
            return None
        material.preview_image = result
        material.is_dirty = False
        return result

    def _build_color(self, material: PBRMaterial) -> Image.Image:
        albedo = self._required_image(material, MaterialSlotType.ALBEDO).convert("RGB")
        mask_slot = material.slot(MaterialSlotType.MASK)
        if mask_slot.image is None:
            material.build_warnings.append("Mask is empty; preview uses opaque alpha.")
            alpha = Image.new("L", albedo.size, 255)
        else:
            mask = self._match_size(mask_slot.image, albedo.size, MaterialSlotType.MASK)
            alpha = mask.convert("L")
        r, g, b = albedo.split()
        return Image.merge("RGBA", (r, g, b, alpha))

    def _build_normal(self, material: PBRMaterial) -> Image.Image:
        normal = self._required_image(material, MaterialSlotType.NORMAL).convert("RGB")
        size = normal.size
        roughness = self._match_size(
            self._required_image(material, MaterialSlotType.ROUGHNESS),
            size,
            MaterialSlotType.ROUGHNESS,
        ).convert("L")
        metallic = self._match_size(
            self._required_image(material, MaterialSlotType.METALLIC),
            size,
            MaterialSlotType.METALLIC,
        ).convert("L")
        normal_x, normal_y, _ = normal.split()

        if material.normal_map_opengl:
            # WT Studio's packed game output keeps the existing DirectX
            # convention. OpenGL RGB normal maps differ by the sign of Y,
            # represented by the green channel, so convert that source Y
            # component before packing it into the WT _n green channel.
            normal_y = ImageChops.invert(normal_y)

        # PBRConverter reconstructs:
        #   normal R = WT Alpha (X)
        #   normal G = WT Green (Y)
        #
        # Repacking therefore restores:
        #   WT Green = normal G (Y)
        #   WT Alpha = normal R (X)
        return Image.merge(
            "RGBA",
            (
                ImageChops.invert(roughness),
                normal_y,
                metallic,
                normal_x,
            ),
        )

    def _build_ao(self, material: PBRMaterial) -> Image.Image:
        channel = self._required_image(material, MaterialSlotType.AO).convert("L")
        return Image.merge("RGB", (channel, channel, channel))

    @staticmethod
    def _required_image(material: PBRMaterial, slot_type: MaterialSlotType) -> Image.Image:
        image = material.slot(slot_type).image
        if image is None:
            raise MaterialBuildError(f"Missing required slot: {slot_type.display_name}")
        return image

    @staticmethod
    def _match_size(image: Image.Image, expected_size: tuple[int, int], slot_type: MaterialSlotType) -> Image.Image:
        if image.size != expected_size:
            raise MaterialBuildError(
                f"{slot_type.display_name} has resolution {image.width} × {image.height}; "
                f"expected {expected_size[0]} × {expected_size[1]}."
            )
        return image
