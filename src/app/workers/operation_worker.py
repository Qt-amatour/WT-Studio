from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot


class OperationContext:
    def __init__(
        self,
        progress_callback: Callable[
            [int, int, str],
            None,
        ],
        cancel_callback: Callable[
            [],
            bool,
        ],
    ) -> None:
        self.progress = progress_callback
        self.is_cancelled = cancel_callback


class OperationWorker(QObject):
    progressChanged = Signal(
        int,
        int,
        str,
    )
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(
        self,
        operation: Callable[
            [OperationContext],
            Any,
        ],
    ) -> None:
        super().__init__()
        self.operation = operation
        self._cancel_requested = False

    @Slot()
    def run(self) -> None:
        context = OperationContext(
            progress_callback=(
                self.progressChanged.emit
            ),
            cancel_callback=(
                lambda: self._cancel_requested
            ),
        )

        try:
            result = self.operation(context)
        except Exception as error:
            self.failed.emit(str(error))
            return

        if self._cancel_requested:
            self.cancelled.emit()
            return

        self.finished.emit(result)

    @Slot()
    def request_cancel(self) -> None:
        self._cancel_requested = True
