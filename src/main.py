# ============================================================
# WT Studio
# Version : 0.9.1
#
# File:
# main.py
#
# Description:
# Application entry point
# ============================================================

from __future__ import annotations

import json
import multiprocessing
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.application import WTApplication


def _runtime_check(output_path: str | None) -> int:
    """Verify the files required by the portable frozen release."""
    from app.runtime_paths import (
        application_root,
        project_library_path,
        third_party_notices_path,
    )
    from app.services.texture_engine import TextureEngineResolver
    from ui.icons import icon_path

    root = application_root()
    resolver = TextureEngineResolver()
    engine = resolver.resolve()

    required_icons = (
        "wt_studio_logo.svg",
        "wt_studio_background_logo.svg",
        "warning.svg",
        "information.svg",
        "question.svg",
        "critical.svg",
        "success.svg",
        "chevron_right.svg",
        "chevron_down.svg",
    )

    checks = {
        "application_root": str(root),
        "frozen": bool(getattr(sys, "frozen", False)),
        "executable": str(Path(sys.executable).resolve()),
        "texture_engine": str(resolver.expected_executable),
        "texture_engine_found": engine is not None,
        "third_party_notices": str(third_party_notices_path()),
        "third_party_notices_found": third_party_notices_path().is_file(),
        "icons": {
            name: icon_path(name).is_file()
            for name in required_icons
        },
    }

    library = project_library_path()
    try:
        library.mkdir(parents=True, exist_ok=True)
        checks["project_library"] = str(library)
        checks["project_library_writable"] = library.is_dir()
    except OSError as error:
        checks["project_library"] = str(library)
        checks["project_library_writable"] = False
        checks["project_library_error"] = str(error)

    checks["pass"] = bool(
        checks["texture_engine_found"]
        and checks["third_party_notices_found"]
        and checks["project_library_writable"]
        and all(checks["icons"].values())
    )

    payload = json.dumps(
        checks,
        indent=2,
        ensure_ascii=False,
    ) + "\n"

    if output_path:
        target = Path(output_path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")

    return 0 if checks["pass"] else 1


def main() -> int:
    multiprocessing.freeze_support()

    if "--runtime-check" in sys.argv:
        index = sys.argv.index("--runtime-check")
        output = (
            sys.argv[index + 1]
            if index + 1 < len(sys.argv)
            else None
        )
        return _runtime_check(output)

    app = QApplication(sys.argv)
    application = WTApplication(app)
    application.run()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
