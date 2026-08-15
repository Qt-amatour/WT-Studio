from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class DDSValidationError(ValueError):
    pass


class DDSFormat(Enum):
    ARGB_8888 = "DDS 8.8.8.8 ARGB"
    BC1 = "DDS BC1 / DXT1"
    BC3 = "DDS BC3 / DXT5"
    BC7 = "DDS BC7"


class DDSHeaderKind(Enum):
    LEGACY = "legacy DDS"
    DX10 = "DDS with DX10 extension"


@dataclass(frozen=True, slots=True)
class DDSValidationReport:
    path: Path
    format: DDSFormat
    width: int
    height: int
    mipmap_count: int
    header_kind: DDSHeaderKind
    data_offset: int
    expected_payload_size: int
    actual_payload_size: int
    file_size: int
    has_alpha: bool
    fourcc: bytes
    dxgi_format: int | None = None

    @property
    def dimensions(self) -> str:
        return f"{self.width} x {self.height}"

    @property
    def is_complete(self) -> bool:
        return self.expected_payload_size == self.actual_payload_size

    def to_text(self) -> str:
        lines = [
            f"File: {self.path}",
            f"Format: {self.format.value}",
            f"Dimensions: {self.dimensions}",
            f"Mipmaps: {self.mipmap_count}",
            f"Header: {self.header_kind.value}",
            f"Alpha: {'YES' if self.has_alpha else 'NO'}",
            f"Expected payload: {self.expected_payload_size} bytes",
            f"Actual payload: {self.actual_payload_size} bytes",
            f"File size: {self.file_size} bytes",
            f"Validation: {'PASS' if self.is_complete else 'FAIL'}",
        ]
        if self.dxgi_format is not None:
            lines.insert(5, f"DXGI format: {self.dxgi_format}")
        return "\n".join(lines)


class DDSValidator:
    DDS_MAGIC = b"DDS "
    DDS_HEADER_BYTES = 128
    DDS_DX10_HEADER_BYTES = 20

    # DDS_PIXELFORMAT flags.
    DDPF_ALPHAPIXELS = 0x00000001
    DDPF_FOURCC = 0x00000004
    DDPF_RGB = 0x00000040

    # DDS caps.
    DDSCAPS_COMPLEX = 0x00000008
    DDSCAPS_TEXTURE = 0x00001000
    DDSCAPS_MIPMAP = 0x00400000

    # Common DXGI values used by DirectXTex.
    DXGI_FORMAT_R8G8B8A8_UNORM = 28
    DXGI_FORMAT_R8G8B8A8_UNORM_SRGB = 29
    DXGI_FORMAT_BC1_UNORM = 71
    DXGI_FORMAT_BC1_UNORM_SRGB = 72
    DXGI_FORMAT_BC3_UNORM = 77
    DXGI_FORMAT_BC3_UNORM_SRGB = 78
    DXGI_FORMAT_BC7_UNORM = 98
    DXGI_FORMAT_BC7_UNORM_SRGB = 99

    @classmethod
    def inspect(cls, path: Path | str) -> DDSValidationReport:
        source = Path(path)
        try:
            raw = source.read_bytes()
        except OSError as error:
            raise DDSValidationError(
                f"Could not read DDS file: {source}\n{error}"
            ) from error

        if len(raw) < cls.DDS_HEADER_BYTES:
            raise DDSValidationError(
                "DDS validation failed: file is smaller than the "
                "mandatory 128-byte header."
            )

        if raw[:4] != cls.DDS_MAGIC:
            raise DDSValidationError(
                "DDS validation failed: missing 'DDS ' magic."
            )

        try:
            header = struct.unpack("<31I", raw[4:128])
        except struct.error as error:
            raise DDSValidationError(
                "DDS validation failed: malformed header."
            ) from error

        header_size = header[0]
        flags = header[1]
        height = header[2]
        width = header[3]
        pitch_or_linear_size = header[4]
        header_mipmap_count = header[6]

        pixel_format_size = header[18]
        pixel_format_flags = header[19]
        fourcc = struct.pack("<I", header[20])
        rgb_bit_count = header[21]
        red_mask = header[22]
        green_mask = header[23]
        blue_mask = header[24]
        alpha_mask = header[25]
        caps = header[26]

        if header_size != 124:
            raise DDSValidationError(
                "DDS validation failed: header size must be 124 bytes, "
                f"got {header_size}."
            )

        if pixel_format_size != 32:
            raise DDSValidationError(
                "DDS validation failed: pixel-format header size must be "
                f"32 bytes, got {pixel_format_size}."
            )

        if width <= 0 or height <= 0:
            raise DDSValidationError(
                "DDS validation failed: invalid texture dimensions."
            )

        mipmap_count = (
            header_mipmap_count
            if header_mipmap_count > 0
            else 1
        )

        data_offset = cls.DDS_HEADER_BYTES
        header_kind = DDSHeaderKind.LEGACY
        dxgi_format: int | None = None

        if fourcc == b"DX10":
            if len(raw) < (
                cls.DDS_HEADER_BYTES
                + cls.DDS_DX10_HEADER_BYTES
            ):
                raise DDSValidationError(
                    "DDS validation failed: truncated DX10 extension."
                )

            dxgi_format, _, _, _, _ = struct.unpack(
                "<5I",
                raw[
                    cls.DDS_HEADER_BYTES:
                    cls.DDS_HEADER_BYTES
                    + cls.DDS_DX10_HEADER_BYTES
                ],
            )
            data_offset += cls.DDS_DX10_HEADER_BYTES
            header_kind = DDSHeaderKind.DX10

        detected_format, has_alpha = cls._detect_format(
            pixel_format_flags=pixel_format_flags,
            fourcc=fourcc,
            rgb_bit_count=rgb_bit_count,
            red_mask=red_mask,
            green_mask=green_mask,
            blue_mask=blue_mask,
            alpha_mask=alpha_mask,
            dxgi_format=dxgi_format,
        )

        cls._validate_mipmap_caps(
            format=detected_format,
            fourcc=fourcc,
            mipmap_count=mipmap_count,
            caps=caps,
        )

        expected_payload_size = cls.expected_payload_size(
            detected_format,
            width,
            height,
            mipmap_count,
        )
        actual_payload_size = len(raw) - data_offset

        if actual_payload_size != expected_payload_size:
            raise DDSValidationError(
                "DDS validation failed: payload size mismatch. "
                f"Expected {expected_payload_size} bytes, "
                f"got {actual_payload_size}."
            )

        cls._validate_pitch_or_linear_size(
            format=detected_format,
            width=width,
            height=height,
            value=pitch_or_linear_size,
        )

        return DDSValidationReport(
            path=source.resolve(),
            format=detected_format,
            width=width,
            height=height,
            mipmap_count=mipmap_count,
            header_kind=header_kind,
            data_offset=data_offset,
            expected_payload_size=expected_payload_size,
            actual_payload_size=actual_payload_size,
            file_size=len(raw),
            has_alpha=has_alpha,
            fourcc=fourcc,
            dxgi_format=dxgi_format,
        )

    @classmethod
    def validate_export(
        cls,
        path: Path | str,
        *,
        expected_format: DDSFormat,
        expected_width: int,
        expected_height: int,
        expected_mipmap_count: int,
    ) -> DDSValidationReport:
        report = cls.inspect(path)

        if report.format is not expected_format:
            raise DDSValidationError(
                "DDS validation failed: format mismatch. "
                f"Expected {expected_format.value}, "
                f"got {report.format.value}."
            )

        if (
            report.width,
            report.height,
        ) != (
            expected_width,
            expected_height,
        ):
            raise DDSValidationError(
                "DDS validation failed: resolution mismatch. "
                f"Expected {expected_width} x {expected_height}, "
                f"got {report.width} x {report.height}."
            )

        if report.mipmap_count != expected_mipmap_count:
            raise DDSValidationError(
                "DDS validation failed: mipmap-count mismatch. "
                f"Expected {expected_mipmap_count}, "
                f"got {report.mipmap_count}."
            )

        # WT Studio 1.0 exports legacy DDS containers for these formats.
        if report.header_kind is not DDSHeaderKind.LEGACY:
            raise DDSValidationError(
                "DDS validation failed: WT Studio game exports must use "
                "the legacy DDS header."
            )

        return report

    @classmethod
    def expected_payload_size(
        cls,
        format: DDSFormat,
        width: int,
        height: int,
        mipmap_count: int,
    ) -> int:
        if width <= 0 or height <= 0 or mipmap_count <= 0:
            raise DDSValidationError(
                "Cannot calculate DDS payload for invalid dimensions "
                "or mipmap count."
            )

        total = 0
        level_width = width
        level_height = height

        for _ in range(mipmap_count):
            if format is DDSFormat.ARGB_8888:
                total += level_width * level_height * 4
            else:
                bytes_per_block = (
                    8 if format is DDSFormat.BC1 else 16
                )
                blocks_wide = max(1, (level_width + 3) // 4)
                blocks_high = max(1, (level_height + 3) // 4)
                total += (
                    blocks_wide
                    * blocks_high
                    * bytes_per_block
                )

            level_width = max(1, level_width // 2)
            level_height = max(1, level_height // 2)

        return total

    @classmethod
    def _detect_format(
        cls,
        *,
        pixel_format_flags: int,
        fourcc: bytes,
        rgb_bit_count: int,
        red_mask: int,
        green_mask: int,
        blue_mask: int,
        alpha_mask: int,
        dxgi_format: int | None,
    ) -> tuple[DDSFormat, bool]:
        if fourcc == b"DX10":
            if dxgi_format in {
                cls.DXGI_FORMAT_BC1_UNORM,
                cls.DXGI_FORMAT_BC1_UNORM_SRGB,
            }:
                return DDSFormat.BC1, False

            if dxgi_format in {
                cls.DXGI_FORMAT_BC3_UNORM,
                cls.DXGI_FORMAT_BC3_UNORM_SRGB,
            }:
                return DDSFormat.BC3, True

            if dxgi_format in {
                cls.DXGI_FORMAT_BC7_UNORM,
                cls.DXGI_FORMAT_BC7_UNORM_SRGB,
            }:
                return DDSFormat.BC7, True

            if dxgi_format in {
                cls.DXGI_FORMAT_R8G8B8A8_UNORM,
                cls.DXGI_FORMAT_R8G8B8A8_UNORM_SRGB,
            }:
                return DDSFormat.ARGB_8888, True

            raise DDSValidationError(
                "DDS validation failed: unsupported DXGI format "
                f"{dxgi_format}."
            )

        if fourcc == b"DXT1":
            return DDSFormat.BC1, False

        if fourcc == b"DXT5":
            return DDSFormat.BC3, True

        if fourcc == b"BC7 ":
            # War Thunder / Dagor reference texture container.
            return DDSFormat.BC7, True

        expected_masks = (
            0x00FF0000,
            0x0000FF00,
            0x000000FF,
            0xFF000000,
        )
        actual_masks = (
            red_mask,
            green_mask,
            blue_mask,
            alpha_mask,
        )

        if (
            pixel_format_flags & cls.DDPF_RGB
            and pixel_format_flags & cls.DDPF_ALPHAPIXELS
            and not pixel_format_flags & cls.DDPF_FOURCC
            and rgb_bit_count == 32
            and actual_masks == expected_masks
        ):
            return DDSFormat.ARGB_8888, True

        printable_fourcc = fourcc.decode(
            "ascii",
            errors="replace",
        )
        raise DDSValidationError(
            "DDS validation failed: unsupported pixel format "
            f"(FourCC={printable_fourcc!r}, "
            f"RGB bits={rgb_bit_count})."
        )

    @classmethod
    def _validate_mipmap_caps(
        cls,
        *,
        format: DDSFormat,
        fourcc: bytes,
        mipmap_count: int,
        caps: int,
    ) -> None:
        if not caps & cls.DDSCAPS_TEXTURE:
            raise DDSValidationError(
                "DDS validation failed: DDSCAPS_TEXTURE is missing."
            )

        if mipmap_count > 1:
            # War Thunder / Dagor reference BC7 containers use only
            # DDSCAPS_TEXTURE even when a full mip chain is present.
            if format is DDSFormat.BC7 and fourcc == b"BC7 ":
                return

            required = cls.DDSCAPS_COMPLEX | cls.DDSCAPS_MIPMAP
            if caps & required != required:
                raise DDSValidationError(
                    "DDS validation failed: mipmapped texture is missing "
                    "DDSCAPS_COMPLEX or DDSCAPS_MIPMAP."
                )

    @classmethod
    def _validate_pitch_or_linear_size(
        cls,
        *,
        format: DDSFormat,
        width: int,
        height: int,
        value: int,
    ) -> None:
        if format is DDSFormat.ARGB_8888:
            expected = width * 4
            if value != expected:
                raise DDSValidationError(
                    "DDS validation failed: invalid ARGB pitch. "
                    f"Expected {expected}, got {value}."
                )
            return

        if format is DDSFormat.BC7 and value == 0:
            # War Thunder reference BC7 files may leave this field empty.
            return

        bytes_per_block = 8 if format is DDSFormat.BC1 else 16
        expected = (
            max(1, (width + 3) // 4)
            * max(1, (height + 3) // 4)
            * bytes_per_block
        )
        if value != expected:
            raise DDSValidationError(
                "DDS validation failed: invalid linear size. "
                f"Expected {expected}, got {value}."
            )
