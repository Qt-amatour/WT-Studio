from __future__ import annotations
import json
from pathlib import Path
from typing import Any

class ProjectFileError(Exception):
    pass

class ProjectFileService:
    FORMAT = "WT Studio Project"
    VERSION = 1
    EXTENSION = ".wts"

    @classmethod
    def ensure_extension(cls, path):
        result = Path(path)
        if result.suffix.casefold() != cls.EXTENSION:
            result = result.with_suffix(cls.EXTENSION)
        return result

    @classmethod
    def save(cls, path, payload):
        target = cls.ensure_extension(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(target.suffix + ".tmp")
        document = {
            "format": cls.FORMAT,
            "version": cls.VERSION,
            **payload,
        }
        try:
            temp.write_text(
                json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            temp.replace(target)
        except OSError as error:
            temp.unlink(missing_ok=True)
            raise ProjectFileError(f"Could not save project:\n{error}") from error
        return target

    @classmethod
    def load(cls, path):
        target = Path(path)
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ProjectFileError(f"Could not read project:\n{error}") from error
        if not isinstance(data, dict) or data.get("format") != cls.FORMAT:
            raise ProjectFileError("The selected file is not a WT Studio project.")
        if data.get("version") != cls.VERSION:
            raise ProjectFileError(
                f"Unsupported WT Studio project version: {data.get('version')}"
            )
        return data

    @classmethod
    def encode_path(cls, value, project_path):
        if value is None or not str(value).strip():
            return None
        source = Path(value).expanduser().resolve(strict=False)
        root = Path(project_path).expanduser().parent.resolve(strict=False)
        try:
            relative = source.relative_to(root)
        except ValueError:
            return {"kind": "absolute", "value": str(source)}
        return {"kind": "relative", "value": relative.as_posix()}

    @classmethod
    def decode_path(cls, record: Any, project_path):
        if record is None:
            return None
        if isinstance(record, str):
            return Path(record)
        if not isinstance(record, dict):
            return None
        value = str(record.get("value", "")).strip()
        if not value:
            return None
        if record.get("kind") == "relative":
            return Path(project_path).parent / value
        return Path(value)
