from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()

    root = args.folder.expanduser().resolve()
    executable = root / "WT Studio.exe"
    encoder = root / "tools" / "texture_encoder" / "texconv.exe"
    report = root / "RUNTIME_CHECK.json"

    required = (
        executable,
        root / "_internal",
        encoder,
        root / "THIRD_PARTY_NOTICES.txt",
        root / "README.md",
        root / "CHANGELOG.md",
        root / "LICENSE",
        root / "BUILD_INFO.json",
    )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("FAIL - missing files:")
        print("\n".join(missing))
        return 1

    subprocess.run(
        [str(executable), "--runtime-check", str(report)],
        cwd=root,
        check=True,
    )
    payload = json.loads(report.read_text(encoding="utf-8"))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"texconv SHA-256: {sha256(encoder)}")
    return 0 if payload.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
