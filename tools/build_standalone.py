from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = (
    "Aircraft",
    "Tanks",
    "Helicopters",
    "Ships",
    "Boats",
    "Others",
)


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    print("\n>", " ".join(command))
    subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        check=True,
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


def verify_build_host() -> None:
    if sys.platform != "win32":
        raise RuntimeError(
            "Windows standalone builds must be created on Windows."
        )

    if sys.maxsize <= 2**32:
        raise RuntimeError("Use 64-bit Python to build WT Studio.")

    if sys.version_info[:2] != (3, 13):
        raise RuntimeError(
            "WT Studio standalone build requires Python 3.13 x64. "
            f"Current interpreter: {platform.python_version()}"
        )


def copy_runtime_files(output_dir: Path) -> None:
    mappings = (
        (
            ROOT / "tools" / "texture_encoder" / "texconv.exe",
            output_dir / "tools" / "texture_encoder" / "texconv.exe",
        ),
        (
            ROOT / "tools" / "texture_encoder" / "LICENSE_DirectXTex.txt",
            output_dir / "tools" / "texture_encoder" / "LICENSE_DirectXTex.txt",
        ),
        (
            ROOT / "tools" / "texture_encoder" / "README.txt",
            output_dir / "tools" / "texture_encoder" / "README.txt",
        ),
        (
            ROOT / "THIRD_PARTY_NOTICES.txt",
            output_dir / "THIRD_PARTY_NOTICES.txt",
        ),
        (
            ROOT / "README.md",
            output_dir / "README.md",
        ),
        (
            ROOT / "CHANGELOG.md",
            output_dir / "CHANGELOG.md",
        ),
        (
            ROOT / "LICENSE",
            output_dir / "LICENSE",
        ),
    )

    for source, target in mappings:
        if not source.is_file():
            raise FileNotFoundError(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    library = output_dir / "Project Library"
    for category in CATEGORIES:
        (library / category).mkdir(parents=True, exist_ok=True)


def write_build_info(output_dir: Path, *, debug: bool) -> None:
    encoder = output_dir / "tools" / "texture_encoder" / "texconv.exe"
    info = {
        "product": "WT Studio",
        "version": "0.9.0",
        "build_type": "debug" if debug else "release",
        "platform": platform.platform(),
        "python": platform.python_version(),
        "packages": {
            "PyInstaller": package_version("PyInstaller"),
            "PySide6": package_version("PySide6"),
            "Pillow": package_version("Pillow"),
            "texture2ddecoder": package_version("texture2ddecoder"),
        },
        "texconv": {
            "path": "tools/texture_encoder/texconv.exe",
            "size": encoder.stat().st_size,
            "sha256": sha256(encoder),
        },
    }
    (output_dir / "BUILD_INFO.json").write_text(
        json.dumps(info, indent=2) + "\n",
        encoding="utf-8",
    )


def verify_release(output_dir: Path, executable_name: str) -> None:
    required = (
        output_dir / executable_name,
        output_dir / "_internal",
        output_dir / "tools" / "texture_encoder" / "texconv.exe",
        output_dir / "tools" / "texture_encoder" / "LICENSE_DirectXTex.txt",
        output_dir / "THIRD_PARTY_NOTICES.txt",
        output_dir / "README.md",
        output_dir / "CHANGELOG.md",
        output_dir / "LICENSE",
        output_dir / "BUILD_INFO.json",
    )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError("Missing release files:\n" + "\n".join(missing))

    source_encoder = ROOT / "tools" / "texture_encoder" / "texconv.exe"
    release_encoder = output_dir / "tools" / "texture_encoder" / "texconv.exe"
    if sha256(source_encoder) != sha256(release_encoder):
        raise RuntimeError("texconv.exe hash changed during the build.")

    report = output_dir / "RUNTIME_CHECK.json"
    executable = output_dir / executable_name
    run([str(executable), "--runtime-check", str(report)])

    payload = json.loads(report.read_text(encoding="utf-8"))
    if not payload.get("pass"):
        raise RuntimeError(
            "Frozen runtime check failed:\n"
            + json.dumps(payload, indent=2)
        )

    print("\nFrozen runtime check: PASS")


def create_zip(output_dir: Path, *, debug: bool) -> Path:
    release_dir = ROOT / "release"
    release_dir.mkdir(parents=True, exist_ok=True)
    suffix = "Debug" if debug else "Windows_x64"
    archive_path = release_dir / f"WT_Studio_0.9.0_{suffix}.zip"
    if archive_path.exists():
        archive_path.unlink()

    with zipfile.ZipFile(
        archive_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file():
                archive.write(
                    path,
                    Path(output_dir.name) / path.relative_to(output_dir),
                )

    print(f"\nRelease archive: {archive_path}")
    print(f"SHA-256: {sha256(archive_path)}")
    return archive_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--no-zip", action="store_true")
    args = parser.parse_args()

    verify_build_host()

    if not args.skip_tests:
        run([
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-v",
        ], env={**os.environ, "PYTHONPATH": str(ROOT / "src")})

    dist_dir = ROOT / "dist"
    work_dir = ROOT / "build" / "pyinstaller"
    for path in (dist_dir, work_dir):
        if path.exists():
            shutil.rmtree(path)

    env = dict(os.environ)
    env["WT_STUDIO_BUILD_DEBUG"] = "1" if args.debug else "0"

    run([
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(work_dir),
        str(ROOT / "build" / "WT_Studio.spec"),
    ], env=env)

    app_name = "WT Studio Debug" if args.debug else "WT Studio"
    executable_name = f"{app_name}.exe"
    output_dir = dist_dir / app_name

    copy_runtime_files(output_dir)
    write_build_info(output_dir, debug=args.debug)
    verify_release(output_dir, executable_name)

    if not args.no_zip:
        create_zip(output_dir, debug=args.debug)

    print("\nBUILD COMPLETE")
    print(f"Application folder: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
