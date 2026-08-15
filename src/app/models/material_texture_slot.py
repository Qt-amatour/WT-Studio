from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from app.models.material_types import MaterialSlotType

@dataclass
class MaterialTextureSlot:
    slot_type: MaterialSlotType
    source_path: Path | None = None
    image: Any | None = None
    loaded_at: datetime | None = None
    file_modified_at: float | None = None
    error: str = ""

    @property
    def has_source(self) -> bool:
        return self.source_path is not None

    @property
    def is_loaded(self) -> bool:
        return self.image is not None and not self.error

    def clear(self) -> None:
        self.source_path = None
        self.image = None
        self.loaded_at = None
        self.file_modified_at = None
        self.error = ""
