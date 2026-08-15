from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from app.models.new_asset_texture_slot import NewAssetTextureSlot
from app.models.new_asset_types import (
    NewAssetSlotType,
    NewAssetType,
    SLOTS_BY_NEW_ASSET_TYPE,
)


@dataclass
class NewAssetMaterial:
    asset_id: str
    name: str
    asset_type: NewAssetType
    slots: dict[NewAssetSlotType, NewAssetTextureSlot] = field(
        default_factory=dict
    )
    preview_image: Any | None = None
    build_error: str = ""
    build_warnings: list[str] = field(default_factory=list)
    normal_map_opengl: bool = False
    is_dirty: bool = True

    @classmethod
    def create(
        cls,
        asset_type: NewAssetType,
        name: str = "",
    ) -> "NewAssetMaterial":
        asset_id = uuid4().hex
        material = cls(
            asset_id=asset_id,
            name=name or f"Asset {asset_id[:6]}",
            asset_type=asset_type,
        )
        material.rebuild_slots()
        return material

    def rebuild_slots(self) -> None:
        previous = self.slots
        self.slots = {
            slot_type: previous.get(
                slot_type,
                NewAssetTextureSlot(slot_type),
            )
            for slot_type in SLOTS_BY_NEW_ASSET_TYPE[self.asset_type]
        }
        self.preview_image = None
        self.build_error = ""
        self.build_warnings.clear()
        self.is_dirty = True

    def set_type(self, asset_type: NewAssetType) -> None:
        if asset_type != self.asset_type:
            self.asset_type = asset_type
            self.rebuild_slots()

    def slot(
        self,
        slot_type: NewAssetSlotType,
    ) -> NewAssetTextureSlot:
        return self.slots[slot_type]

    @property
    def has_any_source(self) -> bool:
        return any(
            slot.source_path is not None
            for slot in self.slots.values()
        )
