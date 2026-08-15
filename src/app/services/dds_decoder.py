# ============================================================
# WT Studio
# Version : 0.1.0
#
# File:
# dds_decoder.py
#
# Description:
# Decodes block-compressed DDS textures into Pillow images.
#
# ============================================================

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from PIL import Image

from app.services.dds_loader import DDSInfo, DDSLoader


class DDSDecodeError(Exception):
    """Raised when a DDS texture cannot be decoded."""


class DDSDecoderDependencyError(DDSDecodeError):
    """Raised when the optional native decoder is not installed."""


class DDSDecoderUnsupportedFormatError(DDSDecodeError):
    """Raised when the DDS compression is not supported by this backend."""


class DDSDecoder:
    """
    Decodes the first image and highest-resolution mip level of a DDS.

    Pillow remains the preferred decoder in TextureLoader. This backend
    is used as a fallback for block-compressed formats, especially BC7.

    The native ``texture2ddecoder`` package returns BGRA bytes. They are
    converted into an independent Pillow RGBA image.
    """

    BLOCK_BYTES = {
        "BC1": 8,
        "BC2": 16,
        "BC3": 16,
        "BC4": 8,
        "BC5": 16,
        "BC6H": 16,
        "BC7": 16,
    }

    DECODER_FUNCTIONS = {
        "BC1": "decode_bc1",
        "BC3": "decode_bc3",
        "BC4": "decode_bc4",
        "BC5": "decode_bc5",
        "BC6H": "decode_bc6",
        "BC7": "decode_bc7",
    }

    def decode(
        self,
        path: str | Path,
        dds_info: DDSInfo | None = None,
    ) -> Image.Image:
        source_path = Path(path)

        info = (
            dds_info
            if dds_info is not None
            else DDSLoader().load(source_path)
        )

        self._validate_surface(info)

        format_name = self._canonical_format(
            info.compression
        )

        decoder_name = self.DECODER_FUNCTIONS.get(
            format_name
        )

        if decoder_name is None:
            raise DDSDecoderUnsupportedFormatError(
                "The native DDS decoder does not support "
                f"'{info.compression}'."
            )

        decoder_module = self._import_decoder()

        decoder_function = getattr(
            decoder_module,
            decoder_name,
            None,
        )

        if not callable(decoder_function):
            raise DDSDecoderDependencyError(
                "The installed texture2ddecoder package does not "
                f"provide {decoder_name}()."
            )

        payload = self._read_top_mip_payload(
            source_path,
            info,
            format_name,
        )

        try:
            decoded = decoder_function(
                payload,
                info.width,
                info.height,
            )
        except Exception as error:
            raise DDSDecodeError(
                f"Could not decode {source_path.name} "
                f"as {format_name}: {error}"
            ) from error

        expected_size = (
            info.width
            * info.height
            * 4
        )

        if len(decoded) != expected_size:
            raise DDSDecodeError(
                "The native decoder returned an unexpected amount "
                f"of data: expected {expected_size}, got {len(decoded)}."
            )

        try:
            return Image.frombytes(
                "RGBA",
                (info.width, info.height),
                decoded,
                "raw",
                "BGRA",
            )
        except Exception as error:
            raise DDSDecodeError(
                "Could not create a Pillow image from decoded DDS data."
            ) from error

    @staticmethod
    def _import_decoder() -> Any:
        try:
            import texture2ddecoder
        except ImportError as error:
            raise DDSDecoderDependencyError(
                "BC texture decoding requires the optional package "
                "'texture2ddecoder'. Install it with: "
                "python -m pip install texture2ddecoder"
            ) from error

        return texture2ddecoder

    @classmethod
    def _canonical_format(
        cls,
        compression: str,
    ) -> str:
        normalized = (
            str(compression)
            .strip()
            .upper()
        )

        if normalized.startswith("BC4 SNORM"):
            raise DDSDecoderUnsupportedFormatError(
                "BC4 SNORM is not decoded because the available "
                "backend exposes only the unsigned BC4 decoder."
            )

        if normalized.startswith("BC5 SNORM"):
            raise DDSDecoderUnsupportedFormatError(
                "BC5 SNORM is not decoded because the available "
                "backend exposes only the unsigned BC5 decoder."
            )

        for format_name in cls.BLOCK_BYTES:
            if normalized.startswith(format_name):
                return format_name

        raise DDSDecoderUnsupportedFormatError(
            f"Unsupported DDS compression: {compression}"
        )

    @classmethod
    def _read_top_mip_payload(
        cls,
        path: Path,
        info: DDSInfo,
        format_name: str,
    ) -> bytes:
        block_bytes = cls.BLOCK_BYTES[
            format_name
        ]

        block_width = max(
            1,
            (info.width + 3) // 4,
        )

        block_height = max(
            1,
            (info.height + 3) // 4,
        )

        payload_size = (
            block_width
            * block_height
            * block_bytes
        )

        try:
            with path.open("rb") as source_file:
                source_file.seek(
                    info.data_offset
                )

                payload = source_file.read(
                    payload_size
                )
        except OSError as error:
            raise DDSDecodeError(
                f"Could not read DDS payload: {path}"
            ) from error

        if len(payload) != payload_size:
            raise DDSDecodeError(
                "DDS top mip payload is incomplete: "
                f"expected {payload_size}, got {len(payload)} bytes."
            )

        return payload

    @staticmethod
    def _validate_surface(
        info: DDSInfo,
    ) -> None:
        if info.is_cubemap:
            raise DDSDecoderUnsupportedFormatError(
                "Cubemap preview decoding is not implemented yet."
            )

        if info.is_volume:
            raise DDSDecoderUnsupportedFormatError(
                "Volume texture preview decoding is not implemented yet."
            )

        if info.array_size != 1:
            raise DDSDecoderUnsupportedFormatError(
                "Texture-array preview decoding is not implemented yet."
            )
