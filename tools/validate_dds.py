from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.services.dds_validator import (
    DDSValidationError,
    DDSValidator,
)


def main(arguments: list[str]) -> int:
    paths = [Path(value.strip('"')) for value in arguments]

    if not paths:
        entered = input("DDS path: ").strip().strip('"')
        if not entered:
            print("No file selected.")
            return 1
        paths = [Path(entered)]

    failed = False

    for index, path in enumerate(paths):
        if index:
            print()
            print("-" * 60)

        print("WT Studio DDS Diagnostic")
        print("=" * 40)

        try:
            report = DDSValidator.inspect(path)
        except DDSValidationError as error:
            failed = True
            print(f"File: {path}")
            print(f"Validation: FAIL")
            print(f"Reason: {error}")
            continue

        print(report.to_text())

        if report.format.value == "DDS BC7":
            print()
            print(
                "Note: BC7 is supported as an input/reference format only. "
                "WT Studio 1.0 does not export BC7 for War Thunder."
            )

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
