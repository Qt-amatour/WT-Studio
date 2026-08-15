from __future__ import annotations

from collections.abc import Iterator

from app.models.new_asset_material import NewAssetMaterial
from app.models.new_asset_types import NewAssetType


class NewAssetCollection:
    def __init__(self) -> None:
        self._materials: list[NewAssetMaterial] = []
        self._by_id: dict[str, NewAssetMaterial] = {}
        self.selected_asset_id: str | None = None

    def __iter__(self) -> Iterator[NewAssetMaterial]:
        return iter(self._materials)

    def __len__(self) -> int:
        return len(self._materials)

    @property
    def materials(self) -> tuple[NewAssetMaterial, ...]:
        return tuple(self._materials)

    def create(
        self,
        asset_type: NewAssetType,
        name: str = "",
    ) -> NewAssetMaterial:
        material = NewAssetMaterial.create(asset_type, name)
        self._materials.append(material)
        self._by_id[material.asset_id] = material
        return material

    def remove(
        self,
        material_or_id: NewAssetMaterial | str,
    ) -> NewAssetMaterial | None:
        asset_id = (
            material_or_id.asset_id
            if isinstance(material_or_id, NewAssetMaterial)
            else str(material_or_id)
        )
        material = self._by_id.pop(asset_id, None)
        if material is None:
            return None
        self._materials.remove(material)
        if self.selected_asset_id == asset_id:
            self.selected_asset_id = None
        return material

    def select(
        self,
        material_or_id: NewAssetMaterial | str | None,
    ) -> None:
        if material_or_id is None:
            self.selected_asset_id = None
            return
        asset_id = (
            material_or_id.asset_id
            if isinstance(material_or_id, NewAssetMaterial)
            else str(material_or_id)
        )
        if asset_id not in self._by_id:
            raise KeyError(f"Unknown new asset material: {asset_id}")
        self.selected_asset_id = asset_id

    @property
    def selected(self) -> NewAssetMaterial | None:
        if self.selected_asset_id is None:
            return None
        return self._by_id.get(self.selected_asset_id)

    def clear(self) -> None:
        self._materials.clear()
        self._by_id.clear()
        self.selected_asset_id = None
