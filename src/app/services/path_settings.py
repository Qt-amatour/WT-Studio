from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings


class PathSettings:
    ORGANIZATION = "WTStudio"
    APPLICATION = "WTStudio"
    USER_SKINS_KEY = "paths/user_skins"

    # Session-only file-dialog state. These values are intentionally not
    # written to QSettings. Every fresh WT Studio process starts from the
    # configured UserSkins path (or the user's home directory as fallback).
    _session_working_directory: Path | None = None
    _session_output_directory: Path | None = None
    _session_output_explicit = False

    @classmethod
    def settings(cls) -> QSettings:
        return QSettings(
            cls.ORGANIZATION,
            cls.APPLICATION,
        )

    @classmethod
    def user_skins_path(cls) -> Path | None:
        raw = str(
            cls.settings().value(
                cls.USER_SKINS_KEY,
                "",
            )
            or ""
        ).strip()

        if not raw:
            return None

        path = Path(raw).expanduser()

        if not path.exists() or not path.is_dir():
            return None

        return path

    @classmethod
    def user_skins_dialog_path(cls) -> str:
        path = cls.user_skins_path()
        return str(path) if path is not None else ""

    @classmethod
    def set_user_skins_path(
        cls,
        path: str | Path,
    ) -> Path:
        resolved = Path(path).expanduser().resolve(
            strict=False
        )

        cls.settings().setValue(
            cls.USER_SKINS_KEY,
            str(resolved),
        )

        return resolved

    @classmethod
    def clear_user_skins_path(cls) -> None:
        settings = cls.settings()
        settings.remove(cls.USER_SKINS_KEY)
        settings.sync()

    @classmethod
    def _default_session_directory(cls) -> Path:
        return cls.user_skins_path() or Path.home()

    @classmethod
    def reset_session_paths(cls) -> None:
        """Reset clean-session dialogs to the configured UserSkins path."""
        base = cls._default_session_directory()
        cls._session_working_directory = base
        cls._session_output_directory = base
        cls._session_output_explicit = False

    @classmethod
    def _ensure_session_paths(cls) -> None:
        if cls._session_working_directory is None:
            cls.reset_session_paths()

    @classmethod
    def session_working_directory(cls) -> Path:
        cls._ensure_session_paths()
        return Path(cls._session_working_directory)

    @classmethod
    def session_working_dialog_path(cls) -> str:
        return str(cls.session_working_directory())

    @classmethod
    def session_output_directory(cls) -> Path:
        cls._ensure_session_paths()
        if cls._session_output_directory is None:
            cls._session_output_directory = cls.session_working_directory()
        return Path(cls._session_output_directory)

    @classmethod
    def session_output_dialog_path(cls) -> str:
        return str(cls.session_output_directory())

    @classmethod
    def set_session_working_directory(
        cls,
        path: str | Path,
    ) -> Path:
        directory = Path(path).expanduser().resolve(strict=False)
        cls._session_working_directory = directory

        # Until the user explicitly chooses an export destination, output
        # follows the current working directory for this session.
        if not cls._session_output_explicit:
            cls._session_output_directory = directory

        return directory

    @classmethod
    def set_session_output_directory(
        cls,
        path: str | Path,
    ) -> Path:
        directory = Path(path).expanduser().resolve(strict=False)
        cls._session_output_directory = directory
        cls._session_output_explicit = True
        return directory
