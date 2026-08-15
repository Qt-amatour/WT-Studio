from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QWidget

from app.workers.operation_worker import OperationWorker
from ui.widgets.message_box import QMessageBox
from ui.widgets.operation_progress_dialog import (
    OperationProgressDialog,
)


class OperationRunner(QObject):
    completed = Signal(object)
    cancelled = Signal()
    failed = Signal(str)

    def __init__(
        self,
        *,
        parent: QWidget,
    ) -> None:
        super().__init__(parent)

        self.parent_widget = parent
        self.thread: QThread | None = None
        self.worker: OperationWorker | None = None
        self.dialog: OperationProgressDialog | None = None

    @property
    def is_running(self) -> bool:
        return (
            self.thread is not None
            and self.thread.isRunning()
        )

    def start(
        self,
        *,
        title: str,
        operation: Callable,
        cancellable: bool = True,
    ) -> bool:
        if self.is_running:
            return False

        self.thread = QThread(
            self
        )
        self.worker = OperationWorker(
            operation
        )
        self.worker.moveToThread(
            self.thread
        )

        self.dialog = OperationProgressDialog(
            title=title,
            cancellable=cancellable,
            parent=self.parent_widget,
        )

        self.thread.started.connect(
            self.worker.run
        )
        self.worker.progressChanged.connect(
            self.dialog.set_progress
        )
        self.dialog.cancel_button.clicked.connect(
            self._request_cancel
        )

        self.worker.finished.connect(
            self._finish_success
        )
        self.worker.failed.connect(
            self._finish_failure
        )
        self.worker.cancelled.connect(
            self._finish_cancelled
        )

        self.worker.finished.connect(
            self.thread.quit
        )
        self.worker.failed.connect(
            self.thread.quit
        )
        self.worker.cancelled.connect(
            self.thread.quit
        )

        self.thread.finished.connect(
            self._cleanup
        )

        self.thread.start()
        self.dialog.show()

        return True

    def _request_cancel(self) -> None:
        if self.worker is None:
            return

        self.worker.request_cancel()

        if self.dialog is not None:
            self.dialog.mark_finishing()

    def _finish_success(
        self,
        result: Any,
    ) -> None:
        if self.dialog is not None:
            self.dialog.accept()

        self.completed.emit(result)

    def _finish_failure(
        self,
        message: str,
    ) -> None:
        if self.dialog is not None:
            self.dialog.accept()

        self.failed.emit(message)

        QMessageBox.critical(
            self.parent_widget,
            "Operation Failed",
            message,
        )

    def _finish_cancelled(self) -> None:
        if self.dialog is not None:
            self.dialog.accept()

        self.cancelled.emit()

    def _cleanup(self) -> None:
        if self.worker is not None:
            self.worker.deleteLater()

        if self.thread is not None:
            self.thread.deleteLater()

        self.worker = None
        self.thread = None
        self.dialog = None
