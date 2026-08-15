from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.services.texture_engine import TextureEngineResolver


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    resolver = TextureEngineResolver(project_root=ROOT)
    info = resolver.resolve()

    print("WT Studio Texture Engine Diagnostic")
    print("=" * 40)
    print(f"WT Studio root: {ROOT}")
    print(f"Required bundled encoder: {resolver.expected_executable}")
    print("Runtime policy: bundled DirectXTex only")
    print("External NVTT fallback: DISABLED")
    print("BC7 game export: DISABLED")
    print(
        "WT Studio 1.0 export formats: "
        "TGA, DDS ARGB 8.8.8.8, BC1, BC3"
    )
    print()

    if info is None:
        print("Status: NOT FOUND")
        print("Compressed DDS export is unavailable.")
        print(
            "Restore texconv.exe to the required bundled location "
            "shown above."
        )
        return 1

    print("Status: FOUND")
    print(f"Engine: {info.display_name}")
    print(f"Source: {info.source_name}")
    print(f"Path: {info.executable}")
    print("Bundled/self-contained: YES")
    print(
        "Version: "
        + TextureEngineResolver.probe_version(info)
    )
    print(f"File size: {info.executable.stat().st_size} bytes")
    print(f"SHA-256: {sha256(info.executable)}")
    print()
    print("Self-contained runtime check: PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
