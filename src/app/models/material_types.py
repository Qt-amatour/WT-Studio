from __future__ import annotations
from enum import Enum

class MaterialType(Enum):
    COLOR = "_c"
    NORMAL = "_n"
    AO = "_ao"

    @property
    def display_name(self) -> str:
        return {
            MaterialType.COLOR: "Color (_c)",
            MaterialType.NORMAL: "Packed Normal (_n)",
            MaterialType.AO: "Ambient Occlusion (_ao)",
        }[self]

class MaterialSlotType(Enum):
    ALBEDO = "albedo"
    MASK = "mask"
    ROUGHNESS = "roughness"
    NORMAL = "normal"
    METALLIC = "metallic"
    AO = "ao"

    @property
    def display_name(self) -> str:
        return {
            MaterialSlotType.ALBEDO: "Albedo",
            MaterialSlotType.MASK: "Mask",
            MaterialSlotType.ROUGHNESS: "Roughness",
            MaterialSlotType.NORMAL: "Normal",
            MaterialSlotType.METALLIC: "Metallic",
            MaterialSlotType.AO: "Ambient Occlusion",
        }[self]

SLOTS_BY_MATERIAL_TYPE = {
    MaterialType.COLOR: (MaterialSlotType.ALBEDO, MaterialSlotType.MASK),
    MaterialType.NORMAL: (
        MaterialSlotType.ROUGHNESS,
        MaterialSlotType.NORMAL,
        MaterialSlotType.METALLIC,
    ),
    MaterialType.AO: (MaterialSlotType.AO,),
}
