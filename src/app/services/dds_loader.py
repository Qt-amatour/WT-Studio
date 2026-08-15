from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Final


class DDSError(Exception):
    """Base class for DDS parser errors."""


class DDSFileNotFoundError(DDSError):
    pass


class DDSInvalidFileError(DDSError):
    pass


class DDSHeaderError(DDSError):
    pass


class DDSUnsupportedFormatError(DDSError):
    pass


DDS_MAGIC: Final[bytes] = b"DDS "
DDS_MAGIC_SIZE: Final[int] = 4
DDS_HEADER_SIZE: Final[int] = 124
DDS_PIXEL_FORMAT_SIZE: Final[int] = 32
DDS_DX10_HEADER_SIZE: Final[int] = 20
DDS_LEGACY_FILE_HEADER_SIZE: Final[int] = 128
DDS_DX10_FILE_HEADER_SIZE: Final[int] = 148
DDS_DX10_FOURCC: Final[bytes] = b"DX10"

DDSD_CAPS: Final[int] = 0x00000001
DDSD_HEIGHT: Final[int] = 0x00000002
DDSD_WIDTH: Final[int] = 0x00000004
DDSD_PIXELFORMAT: Final[int] = 0x00001000
DDSD_MIPMAPCOUNT: Final[int] = 0x00020000

DDPF_ALPHAPIXELS: Final[int] = 0x00000001
DDPF_ALPHA: Final[int] = 0x00000002
DDPF_FOURCC: Final[int] = 0x00000004
DDPF_RGB: Final[int] = 0x00000040
DDPF_LUMINANCE: Final[int] = 0x00020000

DDSCAPS2_CUBEMAP: Final[int] = 0x00000200
DDSCAPS2_CUBEMAP_POSITIVEX: Final[int] = 0x00000400
DDSCAPS2_CUBEMAP_NEGATIVEX: Final[int] = 0x00000800
DDSCAPS2_CUBEMAP_POSITIVEY: Final[int] = 0x00001000
DDSCAPS2_CUBEMAP_NEGATIVEY: Final[int] = 0x00002000
DDSCAPS2_CUBEMAP_POSITIVEZ: Final[int] = 0x00004000
DDSCAPS2_CUBEMAP_NEGATIVEZ: Final[int] = 0x00008000
DDSCAPS2_VOLUME: Final[int] = 0x00200000

D3D10_RESOURCE_DIMENSION_UNKNOWN: Final[int] = 0
D3D10_RESOURCE_DIMENSION_BUFFER: Final[int] = 1
D3D10_RESOURCE_DIMENSION_TEXTURE1D: Final[int] = 2
D3D10_RESOURCE_DIMENSION_TEXTURE2D: Final[int] = 3
D3D10_RESOURCE_DIMENSION_TEXTURE3D: Final[int] = 4
DDS_RESOURCE_MISC_TEXTURECUBE: Final[int] = 0x4

DDS_ALPHA_MODE_UNKNOWN: Final[int] = 0
DDS_ALPHA_MODE_STRAIGHT: Final[int] = 1
DDS_ALPHA_MODE_PREMULTIPLIED: Final[int] = 2
DDS_ALPHA_MODE_OPAQUE: Final[int] = 3
DDS_ALPHA_MODE_CUSTOM: Final[int] = 4

FOURCC_FORMATS: Final[dict[bytes, str]] = {
    b"DXT1": "BC1",
    b"DXT2": "BC2 premultiplied alpha",
    b"DXT3": "BC2",
    b"DXT4": "BC3 premultiplied alpha",
    b"DXT5": "BC3",
    b"ATI1": "BC4",
    b"BC4U": "BC4",
    b"BC4S": "BC4 SNORM",
    b"ATI2": "BC5",
    b"BC5U": "BC5",
    b"BC5S": "BC5 SNORM",
    b"BC6H": "BC6H",
    b"BC7 ": "BC7",
}

DXGI_FORMATS: Final[dict[int, str]] = {
    0: "UNKNOWN", 2: "RGBA32_FLOAT", 10: "RGBA16_FLOAT",
    11: "RGBA16_UNORM", 16: "RG32_FLOAT", 24: "RGB10A2_UNORM",
    26: "R11G11B10_FLOAT", 28: "RGBA8", 29: "RGBA8 sRGB",
    34: "RG16_FLOAT", 35: "RG16_UNORM", 40: "D32_FLOAT",
    41: "R32_FLOAT", 45: "D24_UNORM_S8_UINT", 49: "RG8",
    54: "R16_FLOAT", 55: "D16_UNORM", 56: "R16_UNORM",
    61: "R8", 65: "A8", 67: "RGB9E5_SHAREDEXP",
    71: "BC1", 72: "BC1 sRGB", 74: "BC2", 75: "BC2 sRGB",
    77: "BC3", 78: "BC3 sRGB", 80: "BC4", 81: "BC4 SNORM",
    83: "BC5", 84: "BC5 SNORM", 85: "B5G6R5",
    86: "B5G5R5A1", 87: "BGRA8", 88: "BGRX8",
    91: "BGRA8 sRGB", 93: "BGRX8 sRGB", 95: "BC6H UF16",
    96: "BC6H SF16", 98: "BC7", 99: "BC7 sRGB",
    115: "B4G4R4A4",
}

DXGI_BITS_PER_PIXEL: Final[dict[int, int]] = {
    2: 128, 10: 64, 11: 64, 16: 64, 24: 32, 26: 32,
    28: 32, 29: 32, 34: 32, 35: 32, 40: 32, 41: 32,
    45: 32, 49: 16, 54: 16, 55: 16, 56: 16, 61: 8,
    65: 8, 67: 32, 85: 16, 86: 16, 87: 32, 88: 32,
    91: 32, 93: 32, 115: 16,
}

BLOCK_BYTES: Final[dict[str, int]] = {
    "BC1": 8, "BC4": 8, "BC2": 16, "BC3": 16,
    "BC5": 16, "BC6H": 16, "BC7": 16,
}


@dataclass(frozen=True, slots=True)
class DDSPixelFormat:
    size: int
    flags: int
    fourcc: bytes
    rgb_bit_count: int
    red_mask: int
    green_mask: int
    blue_mask: int
    alpha_mask: int

    @property
    def has_fourcc(self) -> bool:
        return bool(self.flags & DDPF_FOURCC)

    @property
    def has_rgb(self) -> bool:
        return bool(self.flags & DDPF_RGB)

    @property
    def has_alpha_pixels(self) -> bool:
        return bool(self.flags & DDPF_ALPHAPIXELS)


@dataclass(frozen=True, slots=True)
class DDSDX10Header:
    dxgi_format: int
    resource_dimension: int
    misc_flag: int
    array_size: int
    misc_flags2: int

    @property
    def is_cubemap(self) -> bool:
        return bool(self.misc_flag & DDS_RESOURCE_MISC_TEXTURECUBE)

    @property
    def alpha_mode(self) -> int:
        return self.misc_flags2 & 0x7

    @property
    def alpha_mode_name(self) -> str:
        return {
            0: "Unknown", 1: "Straight", 2: "Premultiplied",
            3: "Opaque", 4: "Custom",
        }.get(self.alpha_mode, f"Unknown ({self.alpha_mode})")

    @property
    def resource_dimension_name(self) -> str:
        return {
            0: "Unknown", 1: "Buffer", 2: "Texture 1D",
            3: "Texture 2D", 4: "Texture 3D",
        }.get(self.resource_dimension, f"Unknown ({self.resource_dimension})")


@dataclass(frozen=True, slots=True)
class DDSInfo:
    path: Path
    width: int
    height: int
    mipmap_count: int
    compression: str
    depth: int
    pitch_or_linear_size: int
    header_flags: int
    caps: int
    caps2: int
    caps3: int
    caps4: int
    pixel_format: DDSPixelFormat
    dx10_header: DDSDX10Header | None
    dxgi_format: int | None
    is_dx10: bool
    has_alpha: bool
    data_offset: int
    file_size: int

    @property
    def payload_size(self) -> int:
        return max(0, self.file_size - self.data_offset)

    @property
    def array_size(self) -> int:
        return self.dx10_header.array_size if self.dx10_header else 1

    @property
    def is_cubemap(self) -> bool:
        if self.dx10_header:
            return self.dx10_header.is_cubemap
        return bool(self.caps2 & DDSCAPS2_CUBEMAP)

    @property
    def is_volume(self) -> bool:
        if self.dx10_header:
            return self.dx10_header.resource_dimension == D3D10_RESOURCE_DIMENSION_TEXTURE3D
        return bool(self.caps2 & DDSCAPS2_VOLUME)

    @property
    def resource_type(self) -> str:
        if self.dx10_header:
            base = self.dx10_header.resource_dimension_name
            if self.is_cubemap:
                return f"{base} Cubemap"
            if self.array_size > 1:
                return f"{base} Array"
            return base
        if self.is_cubemap:
            return "Texture 2D Cubemap"
        if self.is_volume:
            return "Texture 3D"
        return "Texture 2D"

    @property
    def alpha_mode(self) -> str:
        return self.dx10_header.alpha_mode_name if self.dx10_header else "Legacy"

    @property
    def dimensions_text(self) -> str:
        if self.is_volume:
            return f"{self.width} × {self.height} × {max(1, self.depth)}"
        return f"{self.width} × {self.height}"


class DDSLoader:
    _HEADER_STRUCT: Final[struct.Struct] = struct.Struct("<31I")
    _DX10_HEADER_STRUCT: Final[struct.Struct] = struct.Struct("<5I")

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path is not None else None

    def load(self, path: str | Path | None = None) -> DDSInfo:
        selected = Path(path) if path is not None else self._path
        validated = self._validate_path(selected)
        file_size = validated.stat().st_size

        with validated.open("rb") as file:
            if self._read_exact(file, 4, "sygnatura DDS") != DDS_MAGIC:
                raise DDSInvalidFileError(f"Plik {validated.name} nie jest plikiem DDS.")

            values = self._unpack_header(self._read_exact(file, 124, "nagłówek DDS"))
            header_size, flags, height, width = values[0:4]
            pitch_or_linear_size, depth, raw_mips = values[4:7]
            pixel_format = self._read_pixel_format(values)
            caps, caps2, caps3, caps4 = values[26:30]

            self._validate_header_sizes(header_size, pixel_format.size)
            self._validate_required_flags(flags, validated)
            self._validate_dimensions(width, height, validated)
            mipmap_count = max(1, raw_mips) if flags & DDSD_MIPMAPCOUNT else 1

            is_dx10 = pixel_format.has_fourcc and pixel_format.fourcc == DDS_DX10_FOURCC
            dx10_header = None
            dxgi_format = None

            if is_dx10:
                dx10_header = self._read_dx10_header(
                    self._read_exact(file, 20, "nagłówek DDS DX10")
                )
                self._validate_dx10_header(dx10_header, validated)
                dxgi_format = dx10_header.dxgi_format
                compression = DXGI_FORMATS.get(dxgi_format, f"DXGI {dxgi_format}")
                data_offset = DDS_DX10_FILE_HEADER_SIZE
            else:
                compression = self._detect_legacy_format(pixel_format)
                data_offset = DDS_LEGACY_FILE_HEADER_SIZE

        info = DDSInfo(
            path=validated, width=width, height=height,
            mipmap_count=mipmap_count, compression=compression,
            depth=depth, pitch_or_linear_size=pitch_or_linear_size,
            header_flags=flags, caps=caps, caps2=caps2,
            caps3=caps3, caps4=caps4, pixel_format=pixel_format,
            dx10_header=dx10_header, dxgi_format=dxgi_format,
            is_dx10=is_dx10,
            has_alpha=self._detect_alpha(pixel_format, compression, dx10_header),
            data_offset=data_offset, file_size=file_size,
        )
        self._validate_info(info)
        self._validate_texture_layout(info)
        return info

    def read_header(self, path: str | Path | None = None) -> DDSInfo:
        return self.load(path)

    def parse(self, path: str | Path | None = None) -> DDSInfo:
        return self.load(path)

    @staticmethod
    def _validate_path(path: Path | None) -> Path:
        if path is None:
            raise DDSFileNotFoundError("Nie podano ścieżki do pliku DDS.")
        path = path.expanduser()
        if not path.exists():
            raise DDSFileNotFoundError(f"Plik DDS nie istnieje: {path}")
        if not path.is_file():
            raise DDSInvalidFileError(f"Ścieżka nie wskazuje na plik: {path}")
        if path.suffix.lower() != ".dds":
            raise DDSInvalidFileError(f"Plik nie ma rozszerzenia .dds: {path.name}")
        if path.stat().st_size < DDS_LEGACY_FILE_HEADER_SIZE:
            raise DDSHeaderError(f"Plik {path.name} jest zbyt mały na nagłówek DDS.")
        return path

    @staticmethod
    def _read_exact(file: BinaryIO, size: int, description: str) -> bytes:
        data = file.read(size)
        if len(data) != size:
            raise DDSHeaderError(
                f"Nie udało się odczytać: {description}. "
                f"Oczekiwano {size} bajtów, odczytano {len(data)}."
            )
        return data

    def _unpack_header(self, raw: bytes) -> tuple[int, ...]:
        try:
            return self._HEADER_STRUCT.unpack(raw)
        except struct.error as error:
            raise DDSHeaderError("Nie udało się rozpakować nagłówka DDS.") from error

    @staticmethod
    def _read_pixel_format(values: tuple[int, ...]) -> DDSPixelFormat:
        return DDSPixelFormat(
            size=values[18], flags=values[19],
            fourcc=struct.pack("<I", values[20]),
            rgb_bit_count=values[21], red_mask=values[22],
            green_mask=values[23], blue_mask=values[24],
            alpha_mask=values[25],
        )

    def _read_dx10_header(self, raw: bytes) -> DDSDX10Header:
        try:
            values = self._DX10_HEADER_STRUCT.unpack(raw)
        except struct.error as error:
            raise DDSHeaderError("Nie udało się rozpakować nagłówka DX10.") from error
        return DDSDX10Header(*values)

    @staticmethod
    def _validate_header_sizes(header_size: int, pf_size: int) -> None:
        if header_size != DDS_HEADER_SIZE:
            raise DDSHeaderError(f"Nieprawidłowe DDS_HEADER.dwSize: {header_size}.")
        if pf_size != DDS_PIXEL_FORMAT_SIZE:
            raise DDSHeaderError(f"Nieprawidłowe DDS_PIXELFORMAT.dwSize: {pf_size}.")

    @staticmethod
    def _validate_required_flags(flags: int, path: Path) -> None:
        required = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT
        missing = required & ~flags
        if missing:
            raise DDSHeaderError(
                f"Plik {path.name} nie ma wymaganych flag. Maska: 0x{missing:08X}."
            )

    @staticmethod
    def _validate_dimensions(width: int, height: int, path: Path) -> None:
        if width <= 0 or height <= 0:
            raise DDSHeaderError(
                f"Plik {path.name} ma nieprawidłowe wymiary: {width} × {height}."
            )

    @staticmethod
    def _validate_dx10_header(header: DDSDX10Header, path: Path) -> None:
        valid = {
            D3D10_RESOURCE_DIMENSION_TEXTURE1D,
            D3D10_RESOURCE_DIMENSION_TEXTURE2D,
            D3D10_RESOURCE_DIMENSION_TEXTURE3D,
        }
        if header.resource_dimension not in valid:
            if header.resource_dimension == D3D10_RESOURCE_DIMENSION_BUFFER:
                raise DDSUnsupportedFormatError(
                    f"Plik {path.name} opisuje bufor DX10, a nie teksturę."
                )
            raise DDSHeaderError(
                f"Plik {path.name} ma nieprawidłowy typ zasobu DX10: "
                f"{header.resource_dimension}."
            )
        if header.array_size <= 0:
            raise DDSHeaderError(f"Plik {path.name} ma nieprawidłowe arraySize.")
        if header.resource_dimension == D3D10_RESOURCE_DIMENSION_TEXTURE3D and header.array_size != 1:
            raise DDSHeaderError("Tekstura 3D nie może być tablicą tekstur.")
        if header.is_cubemap and header.resource_dimension != D3D10_RESOURCE_DIMENSION_TEXTURE2D:
            raise DDSHeaderError("Cubemap musi być teksturą 2D.")

    @staticmethod
    def _validate_info(info: DDSInfo) -> None:
        if info.file_size <= info.data_offset:
            raise DDSHeaderError(f"Plik {info.path.name} nie zawiera danych tekstury.")

    def _validate_texture_layout(self, info: DDSInfo) -> None:
        expected = self._minimum_payload_size(info)
        if expected is not None and info.payload_size < expected:
            raise DDSHeaderError(
                f"Plik {info.path.name} ma za mało danych tekstury. "
                f"Minimum: {expected}, dostępne: {info.payload_size} bajtów."
            )

    def _minimum_payload_size(self, info: DDSInfo) -> int | None:
        block_bytes = next(
            (size for prefix, size in BLOCK_BYTES.items()
             if info.compression.startswith(prefix)),
            None,
        )
        bits = (
            DXGI_BITS_PER_PIXEL.get(info.dxgi_format)
            if info.dxgi_format is not None
            else info.pixel_format.rgb_bit_count
            if not info.pixel_format.has_fourcc
            else None
        )
        if block_bytes is None and not bits:
            return None

        width, height = info.width, info.height
        depth = max(1, info.depth) if info.is_volume else 1
        total = 0
        for _ in range(info.mipmap_count):
            if block_bytes is not None:
                level = max(1, (width + 3) // 4) * max(1, (height + 3) // 4) * block_bytes * depth
            else:
                level = ((width * bits + 7) // 8) * height * depth
            total += level
            width = max(1, width // 2)
            height = max(1, height // 2)
            if info.is_volume:
                depth = max(1, depth // 2)

        return total * self._surface_multiplier(info)

    @staticmethod
    def _surface_multiplier(info: DDSInfo) -> int:
        if info.dx10_header:
            return info.array_size * (6 if info.is_cubemap else 1)
        if not info.is_cubemap:
            return 1
        flags = (
            DDSCAPS2_CUBEMAP_POSITIVEX, DDSCAPS2_CUBEMAP_NEGATIVEX,
            DDSCAPS2_CUBEMAP_POSITIVEY, DDSCAPS2_CUBEMAP_NEGATIVEY,
            DDSCAPS2_CUBEMAP_POSITIVEZ, DDSCAPS2_CUBEMAP_NEGATIVEZ,
        )
        return sum(bool(info.caps2 & flag) for flag in flags) or 6

    def _detect_legacy_format(self, pf: DDSPixelFormat) -> str:
        if pf.has_fourcc:
            return FOURCC_FORMATS.get(pf.fourcc, f"FourCC {self._format_fourcc(pf.fourcc)}")
        if pf.has_rgb:
            return self._detect_rgb_format(pf)
        if pf.flags & DDPF_LUMINANCE:
            if pf.rgb_bit_count == 8:
                return "L8"
            if pf.rgb_bit_count == 16 and pf.alpha_mask:
                return "L8A8"
            return f"Luminance {pf.rgb_bit_count}-bit"
        if pf.flags & DDPF_ALPHA:
            return "A8" if pf.rgb_bit_count == 8 else f"Alpha {pf.rgb_bit_count}-bit"
        return "Unknown"

    @staticmethod
    def _detect_rgb_format(pf: DDSPixelFormat) -> str:
        key = (pf.rgb_bit_count, pf.red_mask, pf.green_mask, pf.blue_mask, pf.alpha_mask)
        formats = {
            (32, 0x000000FF, 0x0000FF00, 0x00FF0000, 0xFF000000): "RGBA8",
            (32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000): "BGRA8",
            (32, 0x000000FF, 0x0000FF00, 0x00FF0000, 0): "RGBX8",
            (32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0): "BGRX8",
            (16, 0xF800, 0x07E0, 0x001F, 0): "B5G6R5",
            (16, 0x7C00, 0x03E0, 0x001F, 0x8000): "B5G5R5A1",
            (16, 0x0F00, 0x00F0, 0x000F, 0xF000): "B4G4R4A4",
        }
        if key in formats:
            return formats[key]
        if pf.rgb_bit_count == 24:
            return "RGB8"
        suffix = " with Alpha" if pf.has_alpha_pixels or pf.alpha_mask else ""
        return f"RGB {pf.rgb_bit_count}-bit{suffix}"

    @staticmethod
    def _detect_alpha(
        pf: DDSPixelFormat,
        compression: str,
        dx10: DDSDX10Header | None,
    ) -> bool:
        if dx10:
            if dx10.alpha_mode == DDS_ALPHA_MODE_OPAQUE:
                return False
            if dx10.alpha_mode in {
                DDS_ALPHA_MODE_STRAIGHT,
                DDS_ALPHA_MODE_PREMULTIPLIED,
                DDS_ALPHA_MODE_CUSTOM,
            }:
                return True
        if pf.has_alpha_pixels or pf.flags & DDPF_ALPHA or pf.alpha_mask:
            return True
        return compression.startswith((
            "BC2", "BC3", "BC7", "RGBA", "BGRA", "B5G5R5A1",
            "B4G4R4A4", "A8", "L8A8", "RGB10A2",
        ))

    @staticmethod
    def _format_fourcc(fourcc: bytes) -> str:
        if all(32 <= value <= 126 for value in fourcc):
            return repr(fourcc.decode("ascii", errors="replace"))
        return "[" + " ".join(f"{value:02X}" for value in fourcc) + "]"
