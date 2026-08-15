from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    """Return True when WT Studio runs from a frozen executable."""
    return bool(getattr(sys, "frozen", False))


def application_root() -> Path:
    """Return the writable portable application directory.

    Source mode:
        .../WT Studio

    Frozen onedir mode:
        directory containing WT Studio.exe
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent

    # .../WT Studio/src/app/runtime_paths.py
    return Path(__file__).resolve().parents[2]


def bundled_root() -> Path:
    """Return the directory containing bundled Python/data resources."""
    if is_frozen():
        internal = getattr(sys, "_MEIPASS", None)
        if internal:
            return Path(internal).resolve()

    return application_root()


def project_library_path() -> Path:
    """Return the writable portable Project Library directory."""
    return application_root() / "Project Library"


def third_party_notices_path() -> Path:
    return application_root() / "THIRD_PARTY_NOTICES.txt"
