from __future__ import annotations
from collections.abc import Iterator
from app.models.material_types import MaterialType
from app.models.pbr_material import PBRMaterial

class MaterialCollection:
    def __init__(self) -> None:
        self._materials: list[PBRMaterial] = []
        self._by_id: dict[str, PBRMaterial] = {}
        self.selected_material_id: str | None = None

    def __iter__(self) -> Iterator[PBRMaterial]:
        return iter(self._materials)

    def __len__(self) -> int:
        return len(self._materials)

    @property
    def materials(self) -> tuple[PBRMaterial, ...]:
        return tuple(self._materials)

    def create(self, material_type: MaterialType, name: str = "") -> PBRMaterial:
        material = PBRMaterial.create(material_type, name)
        self._materials.append(material)
        self._by_id[material.material_id] = material
        return material

    def remove(self, material_or_id: PBRMaterial | str) -> PBRMaterial | None:
        material_id = (
            material_or_id.material_id
            if isinstance(material_or_id, PBRMaterial)
            else str(material_or_id)
        )
        material = self._by_id.pop(material_id, None)
        if material is None:
            return None
        self._materials.remove(material)
        if self.selected_material_id == material_id:
            self.selected_material_id = None
        return material

    def select(self, material_or_id: PBRMaterial | str | None) -> None:
        if material_or_id is None:
            self.selected_material_id = None
            return
        material_id = (
            material_or_id.material_id
            if isinstance(material_or_id, PBRMaterial)
            else str(material_or_id)
        )
        if material_id not in self._by_id:
            raise KeyError(f"Unknown material: {material_id}")
        self.selected_material_id = material_id

    @property
    def selected(self) -> PBRMaterial | None:
        if self.selected_material_id is None:
            return None
        return self._by_id.get(self.selected_material_id)

    def clear(self) -> None:
        self._materials.clear()
        self._by_id.clear()
        self.selected_material_id = None
