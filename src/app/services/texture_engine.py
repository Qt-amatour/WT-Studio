from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from app.runtime_paths import application_root


class TextureEngineKind(Enum):
    DIRECTXTEX = "directxtex"


class TextureEngineSource(Enum):
    BUNDLED = "bundled"


@dataclass(frozen=True, slots=True)
class TextureEngineInfo:
    kind: TextureEngineKind
    executable: Path
    source: TextureEngineSource
    project_root: Path

    @property
    def is_bundled(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return "DirectXTex texconv"

    @property
    def source_name(self) -> str:
        return "bundled with WT Studio"


class TextureEngineResolver:
    """
    Resolves the texture compressor used by WT Studio.

    Runtime policy for Stage 3.2B.2 and later:
    - only the DirectXTex texconv executable bundled with WT Studio is used;
    - external NVIDIA Texture Tools installations are never searched;
    - PATH and encoder override variables cannot silently change the backend.

    This guarantees that every user receives the same, version-controlled
    conversion engine with the application.
    """

    BUNDLED_RELATIVE_PATH = (
        Path("tools") / "texture_encoder" / "texconv.exe"
    )

    def __init__(
        self,
        *,
        project_root: Path | None = None,
    ) -> None:
        self.project_root = (
            Path(project_root).expanduser().resolve()
            if project_root is not None
            else self._default_project_root()
        )

    @staticmethod
    def _default_project_root() -> Path:
        configured = os.environ.get("WT_STUDIO_ROOT")
        if configured:
            return Path(configured).expanduser().resolve()

        return application_root()

    @property
    def expected_executable(self) -> Path:
        return (
            self.project_root / self.BUNDLED_RELATIVE_PATH
        ).resolve()

    @staticmethod
    def _existing_file(path: Path) -> Path | None:
        try:
            resolved = path.expanduser().resolve()
            if not resolved.is_file() or resolved.stat().st_size <= 0:
                return None
            return resolved
        except OSError:
            return None

    def resolve(self) -> TextureEngineInfo | None:
        executable = self._existing_file(self.expected_executable)
        if executable is None:
            return None

        try:
            executable.relative_to(self.project_root)
        except ValueError:
            return None

        if executable.name.casefold() != "texconv.exe":
            return None

        return TextureEngineInfo(
            kind=TextureEngineKind.DIRECTXTEX,
            executable=executable,
            source=TextureEngineSource.BUNDLED,
            project_root=self.project_root,
        )

    @staticmethod
    def probe_version(
        info: TextureEngineInfo,
        *,
        timeout_seconds: int = 10,
    ) -> str:
        command = [str(info.executable), "--version"]

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
                timeout=timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return f"version unavailable ({error})"

        output = (
            completed.stdout.strip()
            or completed.stderr.strip()
        )
        if not output:
            return (
                "version unavailable "
                f"(exit code {completed.returncode})"
            )

        return output.splitlines()[0].strip()
