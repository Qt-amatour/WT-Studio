from __future__ import annotations

from _bootstrap import SRC_ROOT  # noqa: F401

import io
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from app.models.new_asset_material import NewAssetMaterial
from app.models.new_asset_types import NewAssetSlotType, NewAssetType
from app.services.new_asset_builder import NewAssetBuilder
from app.services.new_asset_exporter import NewAssetExporter


class NewAssetBuilderTests(unittest.TestCase):
    def setUp(self):
        self.builder = NewAssetBuilder()

    @staticmethod
    def _assign_image(material, slot_type, image):
        material.slot(slot_type).image = image.copy()

    def test_color_uses_albedo_rgb_and_opaque_default_alpha(self):
        material = NewAssetMaterial.create(NewAssetType.COLOR, "test")
        albedo = Image.new("RGB", (2, 1))
        albedo.putdata([(10, 20, 30), (40, 50, 60)])
        self._assign_image(material, NewAssetSlotType.ALBEDO, albedo)

        result = self.builder.build(material)
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(
            list(result.getdata()),
            [(10, 20, 30, 255), (40, 50, 60, 255)],
        )

    def test_color_uses_optional_alpha(self):
        material = NewAssetMaterial.create(NewAssetType.COLOR, "test")
        self._assign_image(
            material,
            NewAssetSlotType.ALBEDO,
            Image.new("RGB", (1, 1), (1, 2, 3)),
        )
        self._assign_image(
            material,
            NewAssetSlotType.ALPHA,
            Image.new("L", (1, 1), 77),
        )

        result = self.builder.build(material)
        self.assertEqual(result.getpixel((0, 0)), (1, 2, 3, 77))

    def test_normal_packing_directx(self):
        material = NewAssetMaterial.create(NewAssetType.NORMAL, "test")
        self._assign_image(
            material,
            NewAssetSlotType.NORMAL,
            Image.new("RGB", (1, 1), (11, 22, 200)),
        )
        self._assign_image(
            material,
            NewAssetSlotType.ROUGHNESS,
            Image.new("L", (1, 1), 90),
        )
        self._assign_image(
            material,
            NewAssetSlotType.METALLIC,
            Image.new("L", (1, 1), 44),
        )

        result = self.builder.build(material)
        self.assertEqual(
            result.getpixel((0, 0)),
            (11, 22, 44, 165),
        )

    def test_normal_packing_opengl_flips_y_only(self):
        material = NewAssetMaterial.create(NewAssetType.NORMAL, "test")
        material.normal_map_opengl = True
        self._assign_image(
            material,
            NewAssetSlotType.NORMAL,
            Image.new("RGB", (1, 1), (11, 22, 200)),
        )
        self._assign_image(
            material,
            NewAssetSlotType.ROUGHNESS,
            Image.new("L", (1, 1), 90),
        )
        self._assign_image(
            material,
            NewAssetSlotType.METALLIC,
            Image.new("L", (1, 1), 44),
        )

        result = self.builder.build(material)
        self.assertEqual(
            result.getpixel((0, 0)),
            (11, 233, 44, 165),
        )

    def test_ao_stays_single_channel(self):
        material = NewAssetMaterial.create(NewAssetType.AO, "test")
        self._assign_image(
            material,
            NewAssetSlotType.AO,
            Image.new("L", (1, 1), 123),
        )
        result = self.builder.build(material)
        self.assertEqual(result.mode, "L")
        self.assertEqual(result.getpixel((0, 0)), 123)


class NewAssetExporterTests(unittest.TestCase):
    def setUp(self):
        self.builder = NewAssetBuilder()
        self.exporter = NewAssetExporter(self.builder)

    @staticmethod
    def _set_source(material, slot_type, image):
        material.slot(slot_type).image = image.copy()

    def test_filename_replaces_spaces_and_appends_suffix(self):
        material = NewAssetMaterial.create(
            NewAssetType.NORMAL,
            "Main Hull",
        )
        self.assertEqual(
            self.exporter.build_filename(material),
            "Main_Hull_n.tga",
        )

    def test_existing_suffix_is_not_duplicated(self):
        material = NewAssetMaterial.create(
            NewAssetType.COLOR,
            "main_hull_c",
        )
        self.assertEqual(
            self.exporter.build_filename(material),
            "main_hull_c.tga",
        )

    def test_color_tga_is_uncompressed_32_bit_and_lossless(self):
        material = NewAssetMaterial.create(NewAssetType.COLOR, "color")
        self._set_source(
            material,
            NewAssetSlotType.ALBEDO,
            Image.new("RGB", (2, 2), (10, 20, 30)),
        )
        self.builder.build(material)

        with tempfile.TemporaryDirectory() as temp:
            path = self.exporter.export_material(material, temp)
            header = path.read_bytes()[:18]
            self.assertEqual(header[2], 2)   # uncompressed true-color
            self.assertEqual(header[16], 32) # 32 bits/pixel
            payload = path.read_bytes()
            with Image.open(io.BytesIO(payload)) as image:
                image.load()
                self.assertEqual(
                    image.convert("RGBA").getpixel((0, 0)),
                    (10, 20, 30, 255),
                )

    def test_ao_tga_is_uncompressed_8_bit_grayscale_and_lossless(self):
        material = NewAssetMaterial.create(NewAssetType.AO, "ao")
        self._set_source(
            material,
            NewAssetSlotType.AO,
            Image.new("L", (2, 2), 91),
        )
        self.builder.build(material)

        with tempfile.TemporaryDirectory() as temp:
            path = self.exporter.export_material(material, temp)
            header = path.read_bytes()[:18]
            self.assertEqual(header[2], 3)  # uncompressed grayscale
            self.assertEqual(header[16], 8) # 8 bits/pixel
            payload = path.read_bytes()
            with Image.open(io.BytesIO(payload)) as image:
                image.load()
                self.assertEqual(image.convert("L").getpixel((0, 0)), 91)


if __name__ == "__main__":
    unittest.main()
