from __future__ import annotations

from _bootstrap import SRC_ROOT  # noqa: F401

import struct
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from app.services.dds_validator import (
    DDSFormat,
    DDSHeaderKind,
    DDSValidationError,
    DDSValidator,
)
from app.services.material_exporter import (
    MaterialExportFormat,
    MaterialExporter,
)


class DDSValidatorTests(unittest.TestCase):
    def test_validates_bc1_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "test_bc1.dds"
            MaterialExporter._assemble_bc_dds(
                output_path=path,
                export_format=MaterialExportFormat.DDS_BC1,
                width=8,
                height=8,
                payloads=[
                    b"\x00" * 32,
                    b"\x00" * 8,
                ],
            )

            report = DDSValidator.validate_export(
                path,
                expected_format=DDSFormat.BC1,
                expected_width=8,
                expected_height=8,
                expected_mipmap_count=2,
            )

            self.assertEqual(report.actual_payload_size, 40)
            self.assertEqual(
                report.header_kind,
                DDSHeaderKind.LEGACY,
            )

    def test_validates_bc3_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "test_bc3.dds"
            MaterialExporter._assemble_bc_dds(
                output_path=path,
                export_format=MaterialExportFormat.DDS_BC3,
                width=8,
                height=8,
                payloads=[
                    b"\x00" * 64,
                    b"\x00" * 16,
                ],
            )

            report = DDSValidator.validate_export(
                path,
                expected_format=DDSFormat.BC3,
                expected_width=8,
                expected_height=8,
                expected_mipmap_count=2,
            )

            self.assertEqual(report.actual_payload_size, 80)
            self.assertTrue(report.has_alpha)

    def test_validates_argb_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "test_argb.dds"
            levels = [
                Image.new("RGBA", (4, 4), (10, 20, 30, 40)),
                Image.new("RGBA", (2, 2), (50, 60, 70, 80)),
            ]
            MaterialExporter._write_dds_argb_8888_levels(
                levels,
                path,
            )

            report = DDSValidator.validate_export(
                path,
                expected_format=DDSFormat.ARGB_8888,
                expected_width=4,
                expected_height=4,
                expected_mipmap_count=2,
            )

            self.assertEqual(report.actual_payload_size, 80)
            self.assertTrue(report.has_alpha)

    def test_accepts_war_thunder_reference_bc7(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "reference_bc7.dds"
            payloads = [
                b"\x00" * 64,
                b"\x00" * 16,
            ]
            fourcc = struct.unpack("<I", b"BC7 ")[0]
            flags = (
                0x00000001
                | 0x00000002
                | 0x00000004
                | 0x00001000
                | 0x00020000
            )
            values = [
                124,
                flags,
                8,
                8,
                0,
                0,
                2,
                *([0] * 11),
                32,
                0x00000004,
                fourcc,
                0,
                0,
                0,
                0,
                0,
                0x00001000,
                0,
                0,
                0,
                0,
            ]
            path.write_bytes(
                b"DDS "
                + struct.pack("<31I", *values)
                + b"".join(payloads)
            )

            report = DDSValidator.inspect(path)

            self.assertEqual(report.format, DDSFormat.BC7)
            self.assertEqual(report.mipmap_count, 2)

    def test_rejects_truncated_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "broken.dds"
            MaterialExporter._assemble_bc_dds(
                output_path=path,
                export_format=MaterialExportFormat.DDS_BC1,
                width=8,
                height=8,
                payloads=[b"\x00" * 32],
            )
            path.write_bytes(path.read_bytes()[:-1])

            with self.assertRaises(DDSValidationError):
                DDSValidator.inspect(path)

    def test_atomic_export_preserves_existing_file_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "existing.dds"
            destination.write_bytes(b"known-good")

            with self.assertRaises(RuntimeError):
                with MaterialExporter._atomic_output_path(
                    destination
                ) as staged:
                    staged.write_bytes(b"partial")
                    raise RuntimeError("simulated failure")

            self.assertEqual(destination.read_bytes(), b"known-good")

    def test_wt_bc7_export_uses_reference_legacy_header(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "test_bc7.dds"
            MaterialExporter._assemble_bc_dds(
                output_path=path,
                export_format=(
                    MaterialExportFormat.DDS_BC7_EXPERIMENTAL
                ),
                width=8,
                height=8,
                payloads=[
                    b"\x11" * 64,
                    b"\x22" * 16,
                ],
            )

            raw = path.read_bytes()
            header = struct.unpack("<31I", raw[4:128])

            self.assertEqual(header[1], 0x00021007)
            self.assertEqual(header[4], 0)
            self.assertEqual(header[6], 2)
            self.assertEqual(struct.pack("<I", header[20]), b"BC7 ")
            self.assertEqual(header[26], 0x00001000)

            report = DDSValidator.validate_export(
                path,
                expected_format=DDSFormat.BC7,
                expected_width=8,
                expected_height=8,
                expected_mipmap_count=2,
            )
            self.assertEqual(report.actual_payload_size, 80)
            self.assertEqual(
                report.header_kind,
                DDSHeaderKind.LEGACY,
            )

    def test_bc7_mechanism_is_retained_but_not_user_selectable(self) -> None:
        self.assertIn(
            "DDS_BC7_EXPERIMENTAL",
            MaterialExportFormat.__members__,
        )
        self.assertFalse(
            MaterialExportFormat.DDS_BC7_EXPERIMENTAL.is_user_selectable
        )
        self.assertTrue(
            MaterialExportFormat.DDS_BC3.is_user_selectable
        )
        self.assertEqual(
            MaterialExporter._bc_level_size(
                MaterialExportFormat.DDS_BC7_EXPERIMENTAL,
                8,
                8,
            ),
            64,
        )


if __name__ == "__main__":
    unittest.main()
