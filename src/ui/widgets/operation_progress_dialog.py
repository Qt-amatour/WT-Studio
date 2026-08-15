from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from ui.widgets.window_chrome import (
    FramelessDialog,
    WindowTitleBar,
)


class OperationProgressDialog(FramelessDialog):
    def __init__(
        self,
        *,
        title: str,
        cancellable: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("operationProgressDialog")

        self.setWindowTitle(title)
        self.setWindowModality(
            Qt.WindowModality.ApplicationModal
        )
        self.setMinimumWidth(460)

        self.setWindowFlag(
            Qt.WindowType.WindowContextHelpButtonHint,
            False,
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.title_bar = WindowTitleBar(
            self,
            dialog=True,
            show_logo=True,
            show_minimize=False,
            show_maximize=False,
            show_close=cancellable,
        )
        outer.addWidget(self.title_bar)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)
        outer.addLayout(layout)

        self.operation_label = QLabel(title)
        self.item_label = QLabel(
            "Preparing operation..."
        )

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.counter_label = QLabel(
            "0 of 0"
        )

        self._cancellable = bool(cancellable)

        self.cancel_button = QPushButton(
            "Cancel"
        )
        self.cancel_button.setEnabled(
            self._cancellable
        )
        self.cancel_button.setVisible(
            self._cancellable
        )

        layout.addWidget(
            self.operation_label
        )
        layout.addWidget(
            self.item_label
        )
        layout.addWidget(
            self.progress_bar
        )
        layout.addWidget(
            self.counter_label
        )
        layout.addWidget(
            self.cancel_button
        )


    # Compatibility with the QProgressDialog-style API used by
    # synchronous project loading in MainWindow.
    def setRange(
        self,
        minimum: int,
        maximum: int,
    ) -> None:
        self.progress_bar.setRange(
            minimum,
            maximum,
        )

        if minimum == 0 and maximum == 0:
            self.counter_label.setText("")
            return

        current = self.progress_bar.value()
        if current < minimum:
            current = minimum

        self.counter_label.setText(
            f"{current} of {maximum}"
        )

    def setValue(
        self,
        value: int,
    ) -> None:
        self.progress_bar.setValue(
            value
        )

        minimum = self.progress_bar.minimum()
        maximum = self.progress_bar.maximum()

        if minimum == 0 and maximum == 0:
            self.counter_label.setText("")
            return

        self.counter_label.setText(
            f"{value} of {maximum}"
        )

    def setLabelText(
        self,
        text: str,
    ) -> None:
        self.item_label.setText(
            text or "Working..."
        )

    def set_indeterminate(
        self,
        text: str = "Working...",
    ) -> None:
        self.progress_bar.setRange(0, 0)
        self.item_label.setText(text)
        self.counter_label.setText("")

    def set_progress(
        self,
        current: int,
        total: int,
        item_name: str,
    ) -> None:
        safe_total = max(1, total)
        percentage = int(
            current * 100 / safe_total
        )

        self.progress_bar.setValue(
            max(0, min(100, percentage))
        )
        self.counter_label.setText(
            f"{current} of {total}"
        )
        self.item_label.setText(
            item_name or "Working..."
        )

    def mark_finishing(self) -> None:
        self.cancel_button.setEnabled(
            False
        )
        self.item_label.setText(
            "Finishing operation..."
        )

    def finish_and_close(self) -> None:
        """Finish a completed synchronous operation safely."""
        self.cancel_button.setEnabled(False)

        # The dialog is shown with show(), not exec(). OperationRunner already
        # closes identical dialogs safely through accept(), so use the same
        # path here. Do not change modality while the native window is visible
        # and do not call hide() a second time.
        self.accept()

    def reject(self) -> None:
        # The operation controls closing. Clicking X behaves like Cancel only
        # for genuinely cancellable worker operations.
        if self._cancellable and self.cancel_button.isEnabled():
            self.cancel_button.click()
