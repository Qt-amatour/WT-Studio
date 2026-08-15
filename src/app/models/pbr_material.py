from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4
from app.models.material_texture_slot import MaterialTextureSlot
from app.models.material_types import MaterialSlotType, MaterialType, SLOTS_BY_MATERIAL_TYPE

@dataclass
class PBRMaterial:
    material_id: str
    name: str
    material_type: MaterialType
    slots: dict[MaterialSlotType, MaterialTextureSlot] = field(default_factory=dict)
    preview_image: Any | None = None
    build_error: str = ""
    build_warnings: list[str] = field(default_factory=list)
    normal_map_opengl: bool = False
    is_dirty: bool = True

    @classmethod
    def create(cls, material_type: MaterialType, name: str = "") -> "PBRMaterial":
        material_id = uuid4().hex
        material = cls(
            material_id=material_id,
            name=name or f"Material {material_id[:6]}",
            material_type=material_type,
        )
        material.rebuild_slots()
        return material

    def rebuild_slots(self) -> None:
        previous = self.slots
        self.slots = {
            slot_type: previous.get(slot_type, MaterialTextureSlot(slot_type))
            for slot_type in SLOTS_BY_MATERIAL_TYPE[self.material_type]
        }
        self.preview_image = None
        self.build_error = ""
        self.build_warnings.clear()
        self.is_dirty = True

    def set_type(self, material_type: MaterialType) -> None:
        if material_type != self.material_type:
            self.material_type = material_type
            self.rebuild_slots()

    def slot(self, slot_type: MaterialSlotType) -> MaterialTextureSlot:
        return self.slots[slot_type]

    @property
    def has_any_source(self) -> bool:
        return any(slot.source_path is not None for slot in self.slots.values())
