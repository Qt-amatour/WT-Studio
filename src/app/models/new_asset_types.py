from __future__ import annotations

from enum import Enum


class NewAssetType(Enum):
    COLOR = "_c"
    NORMAL = "_n"
    AO = "_ao"

    @property
    def display_name(self) -> str:
        return {
            NewAssetType.COLOR: "Color (_c)",
            NewAssetType.NORMAL: "Packed Normal (_n)",
            NewAssetType.AO: "Ambient Occlusion (_ao)",
        }[self]


class NewAssetSlotType(Enum):
    ALBEDO = "albedo"
    ALPHA = "alpha"
    ROUGHNESS = "roughness"
    NORMAL = "normal"
    METALLIC = "metallic"
    AO = "ao"

    @property
    def display_name(self) -> str:
        return {
            NewAssetSlotType.ALBEDO: "Albedo",
            NewAssetSlotType.ALPHA: "Alpha / Mask",
            NewAssetSlotType.ROUGHNESS: "Roughness",
            NewAssetSlotType.NORMAL: "Normal",
            NewAssetSlotType.METALLIC: "Metallic",
            NewAssetSlotType.AO: "Ambient Occlusion",
        }[self]


SLOTS_BY_NEW_ASSET_TYPE = {
    NewAssetType.COLOR: (
        NewAssetSlotType.ALBEDO,
        NewAssetSlotType.ALPHA,
    ),
    NewAssetType.NORMAL: (
        NewAssetSlotType.ROUGHNESS,
        NewAssetSlotType.NORMAL,
        NewAssetSlotType.METALLIC,
    ),
    NewAssetType.AO: (NewAssetSlotType.AO,),
}
