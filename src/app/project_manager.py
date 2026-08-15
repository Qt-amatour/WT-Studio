# ============================================================
# WT Studio
# Version : 0.1.0
#
# File:
# project_manager.py
#
# Description:
# Manages the current WT Studio project
#
# ============================================================

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from app.models.material_collection import MaterialCollection
from app.models.new_asset_collection import NewAssetCollection
from app.models.material_types import MaterialType
from app.models.pbr_material import PBRMaterial
from app.models.texture_collection import TextureCollection
from app.models.texture_info import TextureInfo
from app.services.texture_loader import (
    TextureLoadError,
    TextureLoader,
)


class ProjectManager:
    """
    Manages the current WT Studio project.

    ProjectManager is responsible for:

    - storing the project's imported textures,
    - importing files through TextureLoader,
    - preventing duplicate entries,
    - collecting import errors,
    - exposing project-level texture operations.

    The actual texture storage is handled by TextureCollection.
    """

    def __init__(self) -> None:
        self.textures = TextureCollection()
        self.materials = MaterialCollection()
        self.new_assets = NewAssetCollection()

        self.import_errors: list[
            tuple[Path, str]
        ] = []

        self.last_imported: list[
            TextureInfo
        ] = []

        self.last_skipped_duplicates: list[
            Path
        ] = []

    # ========================================================
    # Import
    # ========================================================

    def import_textures(
        self,
        files: Iterable[str | Path],
    ) -> list[TextureInfo]:
        """
        Imports multiple texture files.

        Successfully imported textures are added to the project's
        TextureCollection.

        Duplicate source paths are skipped.

        A failure in one file does not stop the remaining files from
        being imported.

        Returns only textures that were newly added to the project.
        """

        imported: list[TextureInfo] = []

        self.import_errors.clear()
        self.last_imported.clear()
        self.last_skipped_duplicates.clear()

        for file in files:
            source_path = Path(file)

            if source_path in self.textures:
                self.last_skipped_duplicates.append(
                    source_path
                )

                continue

            try:
                texture = TextureLoader.load(
                    source_path
                )

            except TextureLoadError as error:
                self.import_errors.append(
                    (
                        source_path,
                        str(error),
                    )
                )

                continue

            except Exception as error:
                self.import_errors.append(
                    (
                        source_path,
                        str(error),
                    )
                )

                continue

            was_added = self.textures.add_if_missing(
                texture
            )

            if not was_added:
                self.last_skipped_duplicates.append(
                    source_path
                )

                continue

            imported.append(texture)

        self.last_imported = list(imported)

        return imported

    def import_texture(
        self,
        file: str | Path,
    ) -> TextureInfo | None:
        """
        Imports one texture.

        Returns the newly added TextureInfo or None when the file was
        skipped or could not be imported.
        """

        imported = self.import_textures(
            [file]
        )

        if not imported:
            return None

        return imported[0]

    # ========================================================
    # Texture access
    # ========================================================

    def get_texture(
        self,
        path: str | Path,
    ) -> TextureInfo | None:
        """
        Returns a texture by source path.
        """

        return self.textures.get(path)

    def find_textures(
        self,
        query: str,
    ) -> list[TextureInfo]:
        """
        Searches imported textures by file name or path.
        """

        return self.textures.search(query)

    def selected_textures(
        self,
    ) -> list[TextureInfo]:
        """
        Returns selected textures in collection order.
        """

        return self.textures.selected()

    def all_textures(
        self,
    ) -> list[TextureInfo]:
        """
        Returns all project textures as a list copy.
        """

        return self.textures.to_list()

    # ========================================================
    # Selection
    # ========================================================

    def select_texture(
        self,
        texture_or_path: TextureInfo | str | Path,
        *,
        clear_existing: bool = True,
    ) -> None:
        """
        Selects one project texture.

        By default this behaves as single selection.
        """

        self.textures.select(
            texture_or_path,
            clear_existing=clear_existing,
        )

    def select_textures(
        self,
        textures_or_paths: Iterable[
            TextureInfo | str | Path
        ],
        *,
        clear_existing: bool = True,
    ) -> None:
        """
        Selects multiple project textures.
        """

        self.textures.select_many(
            textures_or_paths,
            clear_existing=clear_existing,
        )

    def select_all_textures(self) -> None:
        self.textures.select_all()

    def clear_texture_selection(self) -> None:
        self.textures.clear_selection()

    # ========================================================
    # Removing textures
    # ========================================================

    def remove_texture(
        self,
        texture_or_path: TextureInfo | str | Path,
    ) -> TextureInfo | None:
        """
        Removes one texture from the project.

        Returns None when the texture was not found.
        """

        return self.textures.remove(
            texture_or_path,
            missing_ok=True,
        )

    def remove_textures(
        self,
        textures_or_paths: Iterable[
            TextureInfo | str | Path
        ],
    ) -> list[TextureInfo]:
        """
        Removes multiple textures from the project.
        """

        return self.textures.remove_many(
            textures_or_paths,
            missing_ok=True,
        )

    def remove_selected_textures(
        self,
    ) -> list[TextureInfo]:
        """
        Removes all selected textures.
        """

        return self.textures.remove_selected()

    def clear_textures(self) -> None:
        """
        Removes every imported texture from the project.
        """

        self.textures.clear()

        self.last_imported.clear()
        self.last_skipped_duplicates.clear()
        self.import_errors.clear()

    # ========================================================
    # Filters used by future tools
    # ========================================================

    def pbr_exportable_textures(
        self,
    ) -> list[TextureInfo]:
        return self.textures.pbr_exportable()

    def material_buildable_textures(
        self,
    ) -> list[TextureInfo]:
        return self.textures.material_buildable()

    def textures_by_suffix(
        self,
        suffix: str,
    ) -> list[TextureInfo]:
        return self.textures.filter_by_suffix(
            suffix
        )


    # ========================================================
    # Materials
    # ========================================================

    def create_material(
        self,
        material_type: MaterialType,
        name: str = "",
    ) -> PBRMaterial:
        return self.materials.create(material_type, name)

    def remove_material(
        self,
        material_or_id: PBRMaterial | str,
    ) -> PBRMaterial | None:
        return self.materials.remove(material_or_id)

    def all_materials(self) -> list[PBRMaterial]:
        return list(self.materials.materials)

    # ========================================================
    # Project state
    # ========================================================

    @property
    def texture_count(self) -> int:
        return self.textures.count

    @property
    def selected_texture_count(self) -> int:
        return self.textures.selected_count

    @property
    def has_textures(self) -> bool:
        return bool(self.textures)

    @property
    def has_import_errors(self) -> bool:
        return bool(self.import_errors)

    @property
    def skipped_duplicate_count(self) -> int:
        return len(
            self.last_skipped_duplicates
        )

    def reset_project(self) -> None:
        """
        Resets the current project state.

        At this stage the project contains only imported textures.
        Later this method will also reset materials, BLK state and
        project paths.
        """

        self.clear_textures()