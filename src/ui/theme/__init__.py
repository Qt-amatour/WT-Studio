from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ui.theme.manager import ThemeManager
from ui.theme.stylesheet import build_stylesheet


def load_theme(
    application: QApplication | None = None,
) -> str:
    """
    Load and optionally apply the global WT Studio theme.

    Existing startup code calls:

        load_theme(self.app)

    so the function accepts a QApplication instance and applies
    the centralized theme immediately.

    When called without an application, it still returns the QSS
    string for backward compatibility with older code.
    """
    stylesheet = build_stylesheet()

    if application is not None:
        ThemeManager.apply(application)

    return stylesheet


__all__ = [
    "ThemeManager",
    "load_theme",
]
