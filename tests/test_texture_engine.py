from __future__ import annotations

from _bootstrap import SRC_ROOT  # noqa: F401

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.texture_engine import (
    TextureEngineKind,
    TextureEngineResolver,
    TextureEngineSource,
)


class TextureEngineResolverTests(unittest.TestCase):
    def test_resolves_only_bundled_texconv(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            texconv = (
                root
                / "tools"
                / "texture_encoder"
                / "texconv.exe"
            )
            texconv.parent.mkdir(parents=True)
            texconv.write_bytes(b"fake encoder")

            resolver = TextureEngineResolver(project_root=root)
            info = resolver.resolve()

            self.assertIsNotNone(info)
            assert info is not None
            self.assertEqual(
                info.kind,
                TextureEngineKind.DIRECTXTEX,
            )
            self.assertEqual(
                info.source,
                TextureEngineSource.BUNDLED,
            )
            self.assertTrue(info.is_bundled)
            self.assertEqual(info.executable, texconv.resolve())

    def test_does_not_use_environment_or_system_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            external = root / "external" / "texconv.exe"
            external.parent.mkdir(parents=True)
            external.write_bytes(b"external encoder")

            program_files = root / "Program Files"
            nvtt = (
                program_files
                / "NVIDIA Corporation"
                / "NVIDIA Texture Tools"
                / "nvtt_export.exe"
            )
            nvtt.parent.mkdir(parents=True)
            nvtt.write_bytes(b"external nvtt")

            with patch.dict(
                os.environ,
                {
                    "WT_STUDIO_TEXTURE_ENCODER": str(external),
                    "WT_STUDIO_NVTT": str(nvtt),
                    "ProgramFiles": str(program_files),
                    "ProgramW6432": str(program_files),
                    "PATH": str(external.parent),
                },
                clear=False,
            ):
                resolver = TextureEngineResolver(project_root=root)
                self.assertIsNone(resolver.resolve())

    def test_rejects_texconv_in_wrong_local_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wrong = root / "tools" / "texconv.exe"
            wrong.parent.mkdir(parents=True)
            wrong.write_bytes(b"wrong location")

            resolver = TextureEngineResolver(project_root=root)

            self.assertEqual(
                resolver.expected_executable,
                (
                    root
                    / "tools"
                    / "texture_encoder"
                    / "texconv.exe"
                ).resolve(),
            )
            self.assertIsNone(resolver.resolve())


if __name__ == "__main__":
    unittest.main()
