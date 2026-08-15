from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

from ui.theme.palette import Palette
from ui.theme.stylesheet import build_stylesheet


class ThemeManager:
    @staticmethod
    def _ui_font_family() -> str:
        families = set(QFontDatabase.families())

        for candidate in (
            "Segoe UI Variable Text",
            "Segoe UI",
        ):
            if candidate in families:
                return candidate

        app = QApplication.instance()
        return app.font().family() if app is not None else "Sans Serif"

    @staticmethod
    def apply(
        application: QApplication | None = None,
    ) -> None:
        app = application or QApplication.instance()

        if app is None:
            return

        app.setStyle("Fusion")

        font_family = ThemeManager._ui_font_family()
        ui_font = QFont(font_family)
        ui_font.setPointSizeF(9.0)
        app.setFont(ui_font)

        palette = QPalette()
        palette.setColor(
            QPalette.ColorRole.Window,
            QColor(Palette.WINDOW),
        )
        palette.setColor(
            QPalette.ColorRole.WindowText,
            QColor(Palette.TEXT),
        )
        palette.setColor(
            QPalette.ColorRole.Base,
            QColor(Palette.PANEL),
        )
        palette.setColor(
            QPalette.ColorRole.AlternateBase,
            QColor(Palette.PANEL_ALT),
        )
        palette.setColor(
            QPalette.ColorRole.Text,
            QColor(Palette.TEXT),
        )
        palette.setColor(
            QPalette.ColorRole.Button,
            QColor(Palette.CONTROL),
        )
        palette.setColor(
            QPalette.ColorRole.ButtonText,
            QColor(Palette.TEXT),
        )
        palette.setColor(
            QPalette.ColorRole.Highlight,
            QColor(Palette.SELECTION),
        )
        palette.setColor(
            QPalette.ColorRole.HighlightedText,
            QColor(Palette.TEXT_BRIGHT),
        )
        palette.setColor(
            QPalette.ColorRole.PlaceholderText,
            QColor(Palette.TEXT_MUTED),
        )

        app.setPalette(palette)
        app.setStyleSheet(build_stylesheet(font_family))
