from __future__ import annotations

from _bootstrap import SRC_ROOT  # noqa: F401

import io
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from app.models.material_types import MaterialSlotType, MaterialType
from app.models.pbr_material import PBRMaterial
from app.services.material_builder import MaterialBuilder
from app.services.pbr_converter import (
    GeneratedPBRMap,
    PBRConversionResult,
    PBRConverter,
    PBRMapType,
    WarThunderTextureType,
)


class NormalMapConventionTests(unittest.TestCase):
    def test_opengl_material_inverts_y_before_wt_packing(self):
        material = PBRMaterial.create(MaterialType.NORMAL)
        material.slot(MaterialSlotType.ROUGHNESS).image = Image.new(
            "L", (1, 1), 10
        )
        material.slot(MaterialSlotType.NORMAL).image = Image.new(
            "RGB", (1, 1), (128, 64, 255)
        )
        material.slot(MaterialSlotType.METALLIC).image = Image.new(
            "L", (1, 1), 20
        )

        builder = MaterialBuilder()

        directx = builder.build(material)
        self.assertEqual(directx.getpixel((0, 0)), (245, 64, 20, 128))

        material.normal_map_opengl = True
        opengl_source = builder.build(material)
        self.assertEqual(
            opengl_source.getpixel((0, 0)),
            (245, 191, 20, 128),
        )

    def test_pbr_opengl_export_inverts_only_green_channel(self):
        converter = PBRConverter()
        normal = Image.new("RGB", (1, 1), (20, 64, 240))
        generated = GeneratedPBRMap(
            map_type=PBRMapType.NORMAL,
            image=normal,
            suggested_filename="test_normal.png",
            source_path=Path("test_n.dds"),
        )
        result = PBRConversionResult(
            source_texture=None,
            source_path=Path("test_n.dds"),
            source_type=WarThunderTextureType.NORMAL,
            maps=[generated],
        )

        with tempfile.TemporaryDirectory() as directory:
            converter.export_result(
                result,
                directory,
                normal_map_opengl=True,
            )
            payload = (Path(directory) / "test_normal.png").read_bytes()
            with Image.open(io.BytesIO(payload)) as image:
                self.assertEqual(
                    image.convert("RGB").getpixel((0, 0)),
                    (20, 191, 240),
                )


if __name__ == "__main__":
    unittest.main()
