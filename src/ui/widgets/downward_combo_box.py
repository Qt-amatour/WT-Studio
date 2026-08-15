from __future__ import annotations

from PySide6.QtCore import QPoint, QTimer
from PySide6.QtWidgets import QComboBox


class DownwardComboBox(QComboBox):
    """Combo box whose popup is anchored directly below the field."""

    def showPopup(self) -> None:
        super().showPopup()
        QTimer.singleShot(0, self._place_popup_below)

    def _place_popup_below(self) -> None:
        popup = self.view().window()
        if popup is None:
            return

        popup.resize(
            max(self.width(), popup.width()),
            popup.height(),
        )
        popup.move(
            self.mapToGlobal(
                QPoint(0, self.height())
            )
        )
