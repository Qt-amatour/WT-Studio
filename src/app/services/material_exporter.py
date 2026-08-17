from __future__ import annotations

import math
import os
import re
import struct
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable

from PIL import Image, ImageChops

from app.models.material_types import MaterialType
from app.models.pbr_material import PBRMaterial
from app.services.dds_validator import (
    DDSFormat,
    DDSValidationError,
    DDSValidator,
)
from app.services.material_builder import MaterialBuilder
from app.services.texture_engine import (
    TextureEngineInfo,
    TextureEngineResolver,
)


class MaterialExportError(Exception):
    pass


class MaterialExportFormat(Enum):
    TGA = "tga"
    DDS_ARGB_8888 = "dds_argb_8888"
    DDS_BC1 = "dds_bc1"
    DDS_BC3 = "dds_bc3"
    DDS_BC7_EXPERIMENTAL = "dds_bc7_experimental"

    @property
    def display_name(self) -> str:
        return {
            MaterialExportFormat.TGA:
                "TGA",
            MaterialExportFormat.DDS_ARGB_8888:
                "DDS 8.8.8.8 ARGB — 32 bpp",
            MaterialExportFormat.DDS_BC1:
                "DDS BC1 — DXT1 — dedicated for _ao",
            MaterialExportFormat.DDS_BC3:
                "DDS BC3 — DXT5",
            MaterialExportFormat.DDS_BC7_EXPERIMENTAL:
                "DDS BC7 — EXPERIMENTAL — War Thunder _n",
        }[self]

    @property
    def extension(self) -> str:
        return {
            MaterialExportFormat.TGA: ".tga",
            MaterialExportFormat.DDS_ARGB_8888: ".dds",
            MaterialExportFormat.DDS_BC1: ".dds",
            MaterialExportFormat.DDS_BC3: ".dds",
            MaterialExportFormat.DDS_BC7_EXPERIMENTAL: ".dds",
        }[self]

    @property
    def is_user_selectable(self) -> bool:
        # BC7 support is retained internally for future compatibility tests,
        # but current War Thunder UserSkins testing did not resolve the file.
        return self is not MaterialExportFormat.DDS_BC7_EXPERIMENTAL

    @property
    def is_dds(self) -> bool:
        return self is not MaterialExportFormat.TGA

    @property
    def is_compressed(self) -> bool:
        return self in {
            MaterialExportFormat.DDS_BC1,
            MaterialExportFormat.DDS_BC3,
            MaterialExportFormat.DDS_BC7_EXPERIMENTAL,
        }



class MipmapMode(Enum):
    GENERATE = "generate"
    DO_NOT_GENERATE = "do_not_generate"

    @property
    def display_name(self) -> str:
        return {
            MipmapMode.GENERATE:
                "Generate — maximum 13 levels",
            MipmapMode.DO_NOT_GENERATE:
                "Do not generate",
        }[self]


@dataclass(slots=True)
class MaterialExportOptions:
    output_directory: Path
    export_format: MaterialExportFormat
    mipmap_mode: MipmapMode = MipmapMode.GENERATE
    overwrite: bool = True
    verify_pixels: bool = True


@dataclass(slots=True)
class MaterialExportItemResult:
    material_id: str
    material_name: str
    output_path: Path | None = None
    error: str = ""
    verified: bool = False
    mipmap_count: int = 1

    @property
    def succeeded(self) -> bool:
        return self.output_path is not None and not self.error


@dataclass(slots=True)
class MaterialBatchExportResult:
    items: list[MaterialExportItemResult] = field(default_factory=list)

    @property
    def exported_paths(self) -> list[Path]:
        return [
            item.output_path
            for item in self.items
            if item.output_path is not None
        ]

    @property
    def errors(self) -> list[MaterialExportItemResult]:
        return [item for item in self.items if item.error]

    @property
    def exported_count(self) -> int:
        return len(self.exported_paths)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def verified_count(self) -> int:
        return sum(1 for item in self.items if item.verified)


ProgressCallback = Callable[[int, int, str], None]
CancelCallback = Callable[[], bool]


class MaterialExporter:
    """
    Final material exporter.

    Important invariant:
    WT Studio creates the mip chain itself. Each RGBA channel is resized
    independently, because War Thunder uses Alpha as texture data/masks,
    not necessarily transparency.

    BC1/BC3/BC7 compression is delegated exclusively to the bundled
    DirectXTex texconv executable. External encoders are never used.

    The compressor receives one mip level at a time. This prevents the
    external encoder from regenerating or changing WT Studio's mip chain.
    """

    DDS_MAGIC = b"DDS "
    DDS_HEADER_SIZE = 124
    DDS_PIXEL_FORMAT_SIZE = 32
    MAX_MIPMAP_LEVELS = 13

    def __init__(
        self,
        builder: MaterialBuilder | None = None,
        engine_resolver: TextureEngineResolver | None = None,
    ) -> None:
        self.builder = builder or MaterialBuilder()
        self.engine_resolver = (
            engine_resolver or TextureEngineResolver()
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def export_many(
        self,
        materials: list[PBRMaterial],
        options: MaterialExportOptions,
        *,
        progress_callback: ProgressCallback | None = None,
        cancel_callback: CancelCallback | None = None,
    ) -> MaterialBatchExportResult:
        output_directory = Path(options.output_directory).expanduser()
        output_directory.mkdir(parents=True, exist_ok=True)

        result = MaterialBatchExportResult()
        total = len(materials)

        for index, material in enumerate(materials, start=1):
            if cancel_callback and cancel_callback():
                break

            if progress_callback:
                progress_callback(
                    (index - 1) * 1000,
                    total * 1000,
                    material.name,
                )

            item = MaterialExportItemResult(
                material_id=material.material_id,
                material_name=material.name,
            )

            try:
                def item_progress(
                    mip_current: int,
                    mip_total: int,
                    label: str,
                ) -> None:
                    if not progress_callback:
                        return

                    fraction = (
                        0.0
                        if mip_total <= 0
                        else mip_current / mip_total
                    )

                    global_current = (
                        (index - 1)
                        + fraction
                    )

                    progress_callback(
                        int(global_current * 1000),
                        total * 1000,
                        (
                            f"{material.name} — "
                            f"{label} "
                            f"({mip_current}/{mip_total})"
                        ),
                    )

                output_path, verified, mipmap_count = self.export_material(
                    material,
                    options,
                    cancel_callback=cancel_callback,
                    item_progress_callback=item_progress,
                )
                item.output_path = output_path
                item.verified = verified
                item.mipmap_count = mipmap_count
            except Exception as error:
                item.error = str(error)

            result.items.append(item)

            if progress_callback:
                progress_callback(
                    index * 1000,
                    total * 1000,
                    material.name,
                )

        return result

    def export_material(
        self,
        material: PBRMaterial,
        options: MaterialExportOptions,
        *,
        cancel_callback: CancelCallback | None = None,
        item_progress_callback: ProgressCallback | None = None,
    ) -> tuple[Path, bool, int]:
        image = material.preview_image

        if image is None or material.is_dirty:
            image = self.builder.build(material)

        if image is None:
            raise MaterialExportError(
                material.build_error
                or "Material is not ready for export."
            )

        if (
            options.export_format
            is MaterialExportFormat.DDS_BC7_EXPERIMENTAL
            and material.material_type is not MaterialType.NORMAL
        ):
            raise MaterialExportError(
                "Experimental BC7 export is currently enabled only for "
                "Normal (_n) materials."
            )

        output_path = Path(options.output_directory) / self._build_filename(
            material,
            options.export_format,
        )

        if output_path.exists() and not options.overwrite:
            raise MaterialExportError(
                f"File already exists: {output_path}"
            )

        if options.export_format is MaterialExportFormat.TGA:
            with self._atomic_output_path(output_path) as staged_path:
                self._write_tga(image, staged_path)
                if options.verify_pixels:
                    self._verify_tga(image, staged_path)
            return output_path, True, 1

        generate_mipmaps = (
            options.mipmap_mode is MipmapMode.GENERATE
        )

        levels = self._build_mip_chain(
            image,
            generate_mipmaps=generate_mipmaps,
        )

        if options.export_format is MaterialExportFormat.DDS_ARGB_8888:
            with self._atomic_output_path(output_path) as staged_path:
                payloads = self._write_dds_argb_8888_levels(
                    levels,
                    staged_path,
                )
                self._validate_dds_export(
                    staged_path,
                    export_format=options.export_format,
                    expected_width=image.width,
                    expected_height=image.height,
                    expected_mip_count=len(levels),
                )
                if options.verify_pixels:
                    self._verify_uncompressed_dds(
                        staged_path,
                        expected_payloads=payloads,
                        expected_base_image=image,
                    )
            return output_path, True, len(levels)

        if options.export_format.is_compressed:
            engine = self.find_texture_engine()

            if engine is None:
                expected = self.engine_resolver.expected_executable
                raise MaterialExportError(
                    "The bundled DirectXTex encoder is missing.\n\n"
                    "WT Studio does not use system-wide NVIDIA tools or "
                    "programs found in PATH.\n\n"
                    "Expected file:\n"
                    f"{expected}"
                )

            with self._atomic_output_path(output_path) as staged_path:
                self._write_compressed_dds_directxtex(
                    levels=levels,
                    output_path=staged_path,
                    export_format=options.export_format,
                    texconv_path=engine.executable,
                    cancel_callback=cancel_callback,
                    progress_callback=item_progress_callback,
                )
                self._validate_dds_export(
                    staged_path,
                    export_format=options.export_format,
                    expected_width=image.width,
                    expected_height=image.height,
                    expected_mip_count=len(levels),
                )

            return output_path, True, len(levels)

        raise MaterialExportError(
            f"Unsupported export format: {options.export_format}"
        )

    # ------------------------------------------------------------------
    # Texture engine discovery
    # ------------------------------------------------------------------

    def find_texture_engine(self) -> TextureEngineInfo | None:
        return self.engine_resolver.resolve()

    @staticmethod
    def find_nvtt_exporter() -> Path | None:
        """
        Backwards-compatible helper retained for old diagnostic commands.

        Stage 3.2B.2 deliberately disables all NVTT discovery.
        """
        return None

    # ------------------------------------------------------------------
    # Mip generation
    # ------------------------------------------------------------------

    @classmethod
    def _build_mip_chain(
        cls,
        image: Image.Image,
        *,
        generate_mipmaps: bool,
    ) -> list[Image.Image]:
        base = image.convert("RGBA")
        levels = [base.copy()]

        if not generate_mipmaps:
            return levels

        target_count = min(
            cls.MAX_MIPMAP_LEVELS,
            int(math.floor(math.log2(max(base.size)))) + 1,
        )

        current = base

        while len(levels) < target_count:
            next_size = (
                max(1, current.width // 2),
                max(1, current.height // 2),
            )

            if next_size == current.size:
                break

            # War Thunder packed textures use RGBA as four data channels.
            # Never let Alpha influence RGB during mip generation.
            red, green, blue, alpha = current.split()

            current = Image.merge(
                "RGBA",
                (
                    red.resize(next_size, Image.Resampling.BOX),
                    green.resize(next_size, Image.Resampling.BOX),
                    blue.resize(next_size, Image.Resampling.BOX),
                    alpha.resize(next_size, Image.Resampling.BOX),
                ),
            )
            levels.append(current)

            if current.size == (1, 1):
                break

        return levels

    # ------------------------------------------------------------------
    # TGA
    # ------------------------------------------------------------------

    @staticmethod
    def _write_tga(image: Image.Image, output_path: Path) -> None:
        prepared = (
            image.convert("RGBA")
            if "A" in image.getbands()
            else image.convert("RGB")
        )
        prepared.save(output_path, format="TGA")

    @staticmethod
    def _verify_tga(source_image: Image.Image, output_path: Path) -> bool:
        expected = (
            source_image.convert("RGBA")
            if "A" in source_image.getbands()
            else source_image.convert("RGB")
        )

        with Image.open(output_path) as reopened:
            reopened.load()
            actual = reopened.convert(expected.mode)

        if actual.size != expected.size:
            raise MaterialExportError(
                "TGA verification failed: resolution changed."
            )

        if ImageChops.difference(expected, actual).getbbox() is not None:
            raise MaterialExportError(
                "TGA verification failed: pixel values changed."
            )

        return True

    # ------------------------------------------------------------------
    # DDS ARGB 8.8.8.8
    # ------------------------------------------------------------------

    @classmethod
    def _write_dds_argb_8888_levels(
        cls,
        levels: list[Image.Image],
        output_path: Path,
    ) -> list[bytes]:
        base = levels[0]
        width, height = base.size
        mipmap_count = len(levels)

        header_flags = (
            0x00000001  # DDSD_CAPS
            | 0x00000002  # DDSD_HEIGHT
            | 0x00000004  # DDSD_WIDTH
            | 0x00000008  # DDSD_PITCH
            | 0x00001000  # DDSD_PIXELFORMAT
        )

        if mipmap_count > 1:
            header_flags |= 0x00020000  # DDSD_MIPMAPCOUNT

        pixel_format_flags = (
            0x00000001  # DDPF_ALPHAPIXELS
            | 0x00000040  # DDPF_RGB
        )

        caps = 0x00001000  # DDSCAPS_TEXTURE

        if mipmap_count > 1:
            caps |= (
                0x00000008  # DDSCAPS_COMPLEX
                | 0x00400000  # DDSCAPS_MIPMAP
            )

        values = [
            cls.DDS_HEADER_SIZE,
            header_flags,
            height,
            width,
            width * 4,
            0,
            mipmap_count if mipmap_count > 1 else 0,
            *([0] * 11),
            cls.DDS_PIXEL_FORMAT_SIZE,
            pixel_format_flags,
            0,
            32,
            0x00FF0000,
            0x0000FF00,
            0x000000FF,
            0xFF000000,
            caps,
            0,
            0,
            0,
            0,
        ]

        header = struct.pack("<31I", *values)

        payloads = [
            level.convert("RGBA").tobytes("raw", "BGRA")
            for level in levels
        ]

        with output_path.open("wb") as target:
            target.write(cls.DDS_MAGIC)
            target.write(header)
            for payload in payloads:
                target.write(payload)

        return payloads

    @classmethod
    def _verify_uncompressed_dds(
        cls,
        output_path: Path,
        *,
        expected_payloads: list[bytes],
        expected_base_image: Image.Image,
    ) -> bool:
        raw = output_path.read_bytes()

        if raw[:4] != cls.DDS_MAGIC or len(raw) < 128:
            raise MaterialExportError(
                "DDS verification failed: invalid DDS."
            )

        values = struct.unpack("<31I", raw[4:128])

        width = values[3]
        height = values[2]
        header_mipmap_count = values[6]
        actual_count = header_mipmap_count if header_mipmap_count > 0 else 1

        if (width, height) != expected_base_image.size:
            raise MaterialExportError(
                "DDS verification failed: base resolution changed."
            )

        if actual_count != len(expected_payloads):
            raise MaterialExportError(
                "DDS verification failed: mipmap count changed."
            )

        actual_payload = raw[128:]
        expected_payload = b"".join(expected_payloads)

        if actual_payload != expected_payload:
            raise MaterialExportError(
                "DDS verification failed: mip payload changed."
            )

        return True

    # ------------------------------------------------------------------
    # DirectXTex texconv
    # ------------------------------------------------------------------

    @classmethod
    def _write_compressed_dds_directxtex(
        cls,
        *,
        levels: list[Image.Image],
        output_path: Path,
        export_format: MaterialExportFormat,
        texconv_path: Path,
        cancel_callback: CancelCallback | None,
        progress_callback: ProgressCallback | None,
    ) -> None:
        if export_format not in {
            MaterialExportFormat.DDS_BC1,
            MaterialExportFormat.DDS_BC3,
            MaterialExportFormat.DDS_BC7_EXPERIMENTAL,
        }:
            raise MaterialExportError(
                "DirectXTex received a non-BC export format."
            )

        with tempfile.TemporaryDirectory(
            prefix="wt_studio_texconv_",
            ignore_cleanup_errors=True,
        ) as temp_dir_string:
            temp_dir = Path(temp_dir_string)
            source_dir = temp_dir / "source"
            encoded_dir = temp_dir / "encoded"
            source_dir.mkdir()
            encoded_dir.mkdir()

            compressed_payloads: list[bytes] = []
            total_mips = len(levels)

            for mip_index, level in enumerate(levels):
                if cancel_callback and cancel_callback():
                    raise MaterialExportError("Export cancelled.")

                if progress_callback:
                    progress_callback(
                        mip_index,
                        total_mips,
                        "Compressing mip",
                    )

                source_path = (
                    source_dir / f"mip_{mip_index:02d}.tga"
                )
                encoded_path = (
                    encoded_dir / f"mip_{mip_index:02d}.dds"
                )

                # TGA is an exact RGBA source. Alpha is texture data in
                # War Thunder, therefore texconv is called with -sepalpha.
                level.convert("RGBA").save(
                    source_path,
                    format="TGA",
                )

                cls._run_texconv_single_mip(
                    texconv_path=texconv_path,
                    source_path=source_path,
                    output_directory=encoded_dir,
                    export_format=export_format,
                )

                if not encoded_path.is_file():
                    raise MaterialExportError(
                        "DirectXTex did not create the expected DDS file:\n"
                        f"{encoded_path}"
                    )

                payload, width, height = cls._extract_single_bc_payload(
                    encoded_path,
                    export_format=export_format,
                )

                if (width, height) != level.size:
                    raise MaterialExportError(
                        "DirectXTex returned a different mip resolution: "
                        f"expected {level.width}x{level.height}, "
                        f"got {width}x{height}."
                    )

                expected_size = cls._bc_level_size(
                    export_format,
                    level.width,
                    level.height,
                )
                if len(payload) != expected_size:
                    raise MaterialExportError(
                        "DirectXTex returned an unexpected compressed "
                        f"mip size: expected {expected_size} bytes, "
                        f"got {len(payload)}."
                    )

                compressed_payloads.append(payload)

                if progress_callback:
                    progress_callback(
                        mip_index + 1,
                        total_mips,
                        "Compressed mip",
                    )

            cls._assemble_bc_dds(
                output_path=output_path,
                export_format=export_format,
                width=levels[0].width,
                height=levels[0].height,
                payloads=compressed_payloads,
            )

    @classmethod
    def _run_texconv_single_mip(
        cls,
        *,
        texconv_path: Path,
        source_path: Path,
        output_directory: Path,
        export_format: MaterialExportFormat,
    ) -> None:
        dxgi_format = {
            MaterialExportFormat.DDS_BC1: "BC1_UNORM",
            MaterialExportFormat.DDS_BC3: "BC3_UNORM",
            MaterialExportFormat.DDS_BC7_EXPERIMENTAL: "BC7_UNORM",
        }.get(export_format)

        if dxgi_format is None:
            raise MaterialExportError(
                "DirectXTex received an unsupported BC format."
            )

        command = [
            str(texconv_path),
            "-nologo",
            "-y",
            "-m",
            "1",
            "-ft",
            "dds",
            "-f",
            dxgi_format,
            "-sepalpha",
            "--ignore-srgb",
        ]

        command.extend([
            "-o",
            str(output_directory),
            str(source_path),
        ])

        try:
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=getattr(
                    subprocess,
                    "CREATE_NO_WINDOW",
                    0,
                ),
                check=False,
                timeout=600,
            )
        except subprocess.TimeoutExpired as error:
            raise MaterialExportError(
                "DirectXTex timed out after 600 seconds."
            ) from error
        except OSError as error:
            raise MaterialExportError(
                "Could not start the bundled DirectXTex encoder:\n"
                f"{error}"
            ) from error

        if completed.returncode == 0:
            return

        details = (
            completed.stderr.strip()
            or completed.stdout.strip()
            or f"texconv exited with code {completed.returncode}."
        )
        raise MaterialExportError(
            "DirectXTex compression failed.\n\n"
            f"{details}"
        )

    # ------------------------------------------------------------------
    # Compressed DDS payload extraction / assembly
    # ------------------------------------------------------------------

    @classmethod
    def _extract_single_bc_payload(
        cls,
        path: Path,
        *,
        export_format: MaterialExportFormat,
    ) -> tuple[bytes, int, int]:
        expected_format = cls._dds_validator_format(export_format)

        try:
            report = DDSValidator.inspect(path)
        except DDSValidationError as error:
            raise MaterialExportError(
                "DirectXTex output is not a valid DDS file.\n\n"
                f"{error}"
            ) from error

        if report.format is not expected_format:
            raise MaterialExportError(
                "DirectXTex returned an unexpected DDS format: "
                f"expected {expected_format.value}, "
                f"got {report.format.value}."
            )

        if report.mipmap_count != 1:
            raise MaterialExportError(
                "DirectXTex returned more than one mip level even though "
                "WT Studio requested exactly one."
            )

        raw = path.read_bytes()
        payload = raw[report.data_offset:]

        return payload, report.width, report.height

    @classmethod
    def _assemble_bc_dds(
        cls,
        *,
        output_path: Path,
        export_format: MaterialExportFormat,
        width: int,
        height: int,
        payloads: list[bytes],
    ) -> None:
        if export_format not in {
            MaterialExportFormat.DDS_BC1,
            MaterialExportFormat.DDS_BC3,
            MaterialExportFormat.DDS_BC7_EXPERIMENTAL,
        }:
            raise MaterialExportError(
                "Unsupported compressed DDS export format."
            )

        if not payloads:
            raise MaterialExportError(
                "Cannot assemble a compressed DDS without mip payloads."
            )

        mipmap_count = len(payloads)
        is_wt_bc7 = (
            export_format
            is MaterialExportFormat.DDS_BC7_EXPERIMENTAL
        )

        if is_wt_bc7:
            # AssetViewer / War Thunder reference BC7 DDS files use a
            # 128-byte legacy container with FourCC "BC7 ". They keep
            # DDSD_MIPMAPCOUNT set even for one mip, leave linear size
            # at zero, and keep caps at DDSCAPS_TEXTURE only. The BC7
            # payload itself is standard 16-byte-per-block BC7 data.
            flags = 0x00021007
            caps = 0x00001000
            linear_size = 0
            header_mipmap_count = mipmap_count
            fourcc_bytes = b"BC7 "
        else:
            flags = (
                0x00000001  # DDSD_CAPS
                | 0x00000002  # DDSD_HEIGHT
                | 0x00000004  # DDSD_WIDTH
                | 0x00001000  # DDSD_PIXELFORMAT
                | 0x00080000  # DDSD_LINEARSIZE
            )
            if mipmap_count > 1:
                flags |= 0x00020000  # DDSD_MIPMAPCOUNT

            caps = 0x00001000  # DDSCAPS_TEXTURE
            if mipmap_count > 1:
                caps |= (
                    0x00000008  # DDSCAPS_COMPLEX
                    | 0x00400000  # DDSCAPS_MIPMAP
                )

            linear_size = len(payloads[0])
            header_mipmap_count = (
                mipmap_count if mipmap_count > 1 else 0
            )
            fourcc_bytes = (
                b"DXT1"
                if export_format is MaterialExportFormat.DDS_BC1
                else b"DXT5"
            )

        fourcc = struct.unpack("<I", fourcc_bytes)[0]

        values = [
            cls.DDS_HEADER_SIZE,
            flags,
            height,
            width,
            linear_size,
            0,
            header_mipmap_count,
            *([0] * 11),
            cls.DDS_PIXEL_FORMAT_SIZE,
            0x00000004,  # DDPF_FOURCC
            fourcc,
            0,
            0,
            0,
            0,
            0,
            caps,
            0,
            0,
            0,
            0,
        ]

        with output_path.open("wb") as target:
            target.write(cls.DDS_MAGIC)
            target.write(struct.pack("<31I", *values))
            for payload in payloads:
                target.write(payload)

    @classmethod
    def _validate_dds_export(
        cls,
        output_path: Path,
        *,
        export_format: MaterialExportFormat,
        expected_width: int,
        expected_height: int,
        expected_mip_count: int,
    ) -> None:
        expected_format = cls._dds_validator_format(export_format)

        try:
            DDSValidator.validate_export(
                output_path,
                expected_format=expected_format,
                expected_width=expected_width,
                expected_height=expected_height,
                expected_mipmap_count=expected_mip_count,
            )
        except DDSValidationError as error:
            raise MaterialExportError(str(error)) from error

    @staticmethod
    def _dds_validator_format(
        export_format: MaterialExportFormat,
    ) -> DDSFormat:
        mapping = {
            MaterialExportFormat.DDS_ARGB_8888:
                DDSFormat.ARGB_8888,
            MaterialExportFormat.DDS_BC1:
                DDSFormat.BC1,
            MaterialExportFormat.DDS_BC3:
                DDSFormat.BC3,
            MaterialExportFormat.DDS_BC7_EXPERIMENTAL:
                DDSFormat.BC7,
        }
        try:
            return mapping[export_format]
        except KeyError as error:
            raise MaterialExportError(
                f"No DDS validator mapping for {export_format}."
            ) from error

    @staticmethod
    @contextmanager
    def _atomic_output_path(output_path: Path):
        """
        Write and validate a temporary sibling file first, then replace the
        destination atomically. A failed encoder or validator never leaves a
        partial final texture and never destroys a previously valid export.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{output_path.stem}_",
            suffix=f"{output_path.suffix}.wtstudio_tmp",
            dir=output_path.parent,
        )
        os.close(descriptor)
        temporary_path = Path(temporary_name)

        try:
            yield temporary_path
            if not temporary_path.is_file():
                raise MaterialExportError(
                    "Export did not create the expected temporary file."
                )
            os.replace(temporary_path, output_path)
        except Exception:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    @staticmethod
    def _bc_level_size(
        export_format: MaterialExportFormat,
        width: int,
        height: int,
    ) -> int:
        blocks_wide = max(1, (width + 3) // 4)
        blocks_high = max(1, (height + 3) // 4)

        if export_format is MaterialExportFormat.DDS_BC1:
            bytes_per_block = 8
        elif export_format in {
            MaterialExportFormat.DDS_BC3,
            MaterialExportFormat.DDS_BC7_EXPERIMENTAL,
        }:
            bytes_per_block = 16
        else:
            raise MaterialExportError(
                "Block size requested for a non-exportable BC format."
            )

        return blocks_wide * blocks_high * bytes_per_block

    # ------------------------------------------------------------------
    # Filename
    # ------------------------------------------------------------------

    @staticmethod
    def _build_filename(
        material: PBRMaterial,
        export_format: MaterialExportFormat,
    ) -> str:
        clean_name = re.sub(
            r'[<>:"/\\|?*\x00-\x1f]+',
            "_",
            material.name.strip(),
        ).strip(" ._")

        if not clean_name:
            clean_name = f"material_{material.material_id[:6]}"

        suffix = {
            MaterialType.COLOR: "_c",
            MaterialType.NORMAL: "_n",
            MaterialType.AO: "_ao",
        }[material.material_type]

        if not clean_name.casefold().endswith(suffix):
            clean_name += suffix

        return clean_name + export_format.extension
