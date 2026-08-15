from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QMouseEvent, QMoveEvent, QResizeEvent, QShowEvent
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenuBar,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from ui.icons import brand_logo_icon, window_control_icon


class FramelessMainWindow(QMainWindow):
    """QMainWindow with stable custom chrome and normal-window geometry."""

    RESIZE_MARGIN = 7
    SCREEN_MARGIN = 24
    TOP_SNAP_THRESHOLD = 10
    TITLE_DRAG_POLL_MS = 35

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)

        # Qt/Windows can occasionally lose the normal geometry of a frameless
        # window while it is minimized. Keep an application-owned copy instead
        # of relying only on QWindow::normalGeometry().
        self._preferred_normal_size: QSize | None = None
        self._last_normal_geometry = QRect()
        self._pre_minimize_geometry = QRect()
        self._minimized_from_maximized = False
        self._initial_geometry_applied = False
        self._geometry_restore_in_progress = False

        # Native startSystemMove() does not provide Aero Snap for this
        # frameless QMainWindow, so watch only the end of a title-bar drag.
        self._title_drag_active = False
        self._title_drag_top_candidate = False

    def set_preferred_normal_size(
        self,
        width: int,
        height: int,
    ) -> None:
        self._preferred_normal_size = QSize(
            max(1, int(width)),
            max(1, int(height)),
        )

    def _available_geometry(self) -> QRect:
        screen = self.screen()
        if screen is None:
            return QRect()
        return screen.availableGeometry()

    def _fit_normal_geometry(self, geometry: QRect) -> QRect:
        available = self._available_geometry()
        if not available.isValid():
            return QRect(geometry)

        margin = self.SCREEN_MARGIN
        max_width = max(640, available.width() - (2 * margin))
        max_height = max(480, available.height() - (2 * margin))

        width = min(max(640, geometry.width()), max_width)
        height = min(max(480, geometry.height()), max_height)

        result = QRect(geometry)
        result.setSize(QSize(width, height))

        # Keep an already useful position. If the geometry no longer fits the
        # current monitor, center it in the available work area.
        if (
            result.left() < available.left()
            or result.top() < available.top()
            or result.right() > available.right()
            or result.bottom() > available.bottom()
        ):
            result.moveCenter(available.center())

        return result

    def _capture_normal_geometry(self) -> None:
        if self._geometry_restore_in_progress:
            return

        state = self.windowState()
        if state != Qt.WindowState.WindowNoState:
            return

        geometry = self.geometry()
        if geometry.isValid() and geometry.width() > 0 and geometry.height() > 0:
            self._last_normal_geometry = QRect(geometry)

    def _apply_initial_normal_geometry(self) -> None:
        if self._initial_geometry_applied:
            return
        if self.isMaximized() or self.isMinimized() or self.isFullScreen():
            return

        geometry = QRect(self.geometry())
        if self._preferred_normal_size is not None:
            geometry.setSize(self._preferred_normal_size)

        available = self._available_geometry()
        geometry = self._fit_normal_geometry(geometry)

        # On first show, prefer a predictable centered normal window. This also
        # prevents a 1600x900 request from opening partly outside smaller
        # displays or high-DPI work areas.
        if available.isValid():
            geometry.moveCenter(available.center())

        self._geometry_restore_in_progress = True
        try:
            self.setGeometry(geometry)
        finally:
            self._geometry_restore_in_progress = False

        self._last_normal_geometry = QRect(geometry)
        self._initial_geometry_applied = True

    def _restore_saved_normal_geometry(
        self,
        geometry: QRect | None = None,
    ) -> None:
        if self.isMaximized() or self.isMinimized() or self.isFullScreen():
            return

        candidate = QRect(geometry or self._last_normal_geometry)
        if not candidate.isValid():
            return

        candidate = self._fit_normal_geometry(candidate)

        self._geometry_restore_in_progress = True
        try:
            self.setGeometry(candidate)
        finally:
            self._geometry_restore_in_progress = False

        self._last_normal_geometry = QRect(candidate)

    def _restore_pre_minimize_geometry(
        self,
        geometry: QRect,
    ) -> None:
        """Restore the exact normal position saved before minimization."""
        if self.isMaximized() or self.isMinimized() or self.isFullScreen():
            return

        candidate = QRect(geometry)
        if not candidate.isValid():
            candidate = QRect(self._last_normal_geometry)
        if not candidate.isValid():
            return

        # While a window is minimized Qt can report a different current screen.
        # Resolve the monitor from the saved rectangle itself so restoring a
        # window never recenters it just because the minimized HWND temporarily
        # belongs to another screen.
        saved_screen = QApplication.screenAt(candidate.center())

        if saved_screen is None:
            # The saved monitor may have been disconnected. Only in that case
            # fall back to the normal safety fitting logic.
            candidate = self._fit_normal_geometry(candidate)
        else:
            available = saved_screen.availableGeometry()

            # Keep the position exactly when it is still valid. Clamp only if
            # a display/work-area change would otherwise make the title bar
            # unreachable.
            if candidate.width() > available.width():
                candidate.setWidth(available.width())
            if candidate.height() > available.height():
                candidate.setHeight(available.height())

            min_left = available.left()
            max_left = available.right() - candidate.width() + 1
            min_top = available.top()
            max_top = available.bottom() - candidate.height() + 1

            candidate.moveLeft(
                min(
                    max(candidate.left(), min_left),
                    max_left,
                )
            )
            candidate.moveTop(
                min(
                    max(candidate.top(), min_top),
                    max_top,
                )
            )

        self._geometry_restore_in_progress = True
        try:
            self.setGeometry(candidate)
        finally:
            self._geometry_restore_in_progress = False

        self._last_normal_geometry = QRect(candidate)
        self._pre_minimize_geometry = QRect(candidate)

    def restore_for_title_drag(
        self,
        global_position: QPoint,
        *,
        horizontal_ratio: float,
        title_press_y: int,
    ) -> bool:
        """Restore a maximized window beneath the drag cursor."""
        if not self.isMaximized():
            return False

        candidate = QRect(self._last_normal_geometry)
        if not candidate.isValid():
            candidate = QRect(self.geometry())
            if self._preferred_normal_size is not None:
                candidate.setSize(self._preferred_normal_size)

        candidate = self._fit_normal_geometry(candidate)
        if not candidate.isValid():
            return False

        ratio = min(
            0.95,
            max(0.05, float(horizontal_ratio)),
        )
        press_y = max(
            0,
            min(int(title_press_y), 33),
        )

        target_left = int(
            round(
                global_position.x()
                - (candidate.width() * ratio)
            )
        )
        target_top = int(
            global_position.y() - press_y
        )

        available = self._available_geometry()
        if available.isValid():
            max_left = (
                available.right()
                - candidate.width()
                + 1
            )
            max_top = (
                available.bottom()
                - candidate.height()
                + 1
            )
            target_left = min(
                max(target_left, available.left()),
                max_left,
            )
            target_top = min(
                max(target_top, available.top()),
                max_top,
            )

        candidate.moveTopLeft(
            QPoint(target_left, target_top)
        )

        self.showNormal()

        self._geometry_restore_in_progress = True
        try:
            self.setGeometry(candidate)
        finally:
            self._geometry_restore_in_progress = False

        self._last_normal_geometry = QRect(candidate)
        return True

    def begin_title_drag_snap_watch(self) -> None:
        if self.isMaximized() or self.isMinimized() or self.isFullScreen():
            return

        self._title_drag_active = True
        self._update_title_drag_snap_candidate()
        QTimer.singleShot(
            self.TITLE_DRAG_POLL_MS,
            self._poll_title_drag_release,
        )

    def cancel_title_drag_snap_watch(self) -> None:
        self._title_drag_active = False
        self._title_drag_top_candidate = False

    def _update_title_drag_snap_candidate(self) -> None:
        if (
            not self._title_drag_active
            or self.isMaximized()
            or self.isMinimized()
            or self.isFullScreen()
        ):
            self._title_drag_top_candidate = False
            return

        screen = self.screen()
        if screen is None:
            self._title_drag_top_candidate = False
            return

        available = screen.availableGeometry()
        top_distance = abs(
            self.frameGeometry().top() - available.top()
        )

        self._title_drag_top_candidate = (
            top_distance <= self.TOP_SNAP_THRESHOLD
        )

    def _poll_title_drag_release(self) -> None:
        if not self._title_drag_active:
            return

        self._update_title_drag_snap_candidate()

        if QApplication.mouseButtons() & Qt.MouseButton.LeftButton:
            QTimer.singleShot(
                self.TITLE_DRAG_POLL_MS,
                self._poll_title_drag_release,
            )
            return

        should_maximize = (
            self._title_drag_top_candidate
            and not self.isMaximized()
            and not self.isMinimized()
            and not self.isFullScreen()
        )

        self._title_drag_active = False
        self._title_drag_top_candidate = False

        if should_maximize:
            # Capture the final normal geometry first. This remains the geometry
            # used when the maximized window is later dragged back down.
            self._capture_normal_geometry()
            self.showMaximized()

    def minimize_safely(self) -> None:
        self._minimized_from_maximized = self.isMaximized()

        if not self._minimized_from_maximized:
            self._capture_normal_geometry()
            self._pre_minimize_geometry = QRect(
                self._last_normal_geometry
            )

        self.showMinimized()

    def toggle_maximized_safely(self) -> None:
        if self.isMaximized():
            restore_geometry = QRect(self._last_normal_geometry)
            self.showNormal()
            QTimer.singleShot(
                0,
                lambda geometry=restore_geometry:
                self._restore_saved_normal_geometry(geometry),
            )
            return

        self._capture_normal_geometry()
        self.showMaximized()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if not self._initial_geometry_applied:
            QTimer.singleShot(0, self._apply_initial_normal_geometry)

    def moveEvent(self, event: QMoveEvent) -> None:
        super().moveEvent(event)
        self._capture_normal_geometry()
        self._update_title_drag_snap_candidate()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._capture_normal_geometry()

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.WindowStateChange:
            old_state = event.oldState()
            new_state = self.windowState()

            was_minimized = bool(
                old_state & Qt.WindowState.WindowMinimized
            )
            is_minimized = bool(
                new_state & Qt.WindowState.WindowMinimized
            )

            if is_minimized and not was_minimized:
                self._minimized_from_maximized = bool(
                    old_state & Qt.WindowState.WindowMaximized
                )
                if not self._minimized_from_maximized:
                    self._capture_normal_geometry()
                    self._pre_minimize_geometry = QRect(
                        self._last_normal_geometry
                    )

            elif was_minimized and not is_minimized:
                if self._minimized_from_maximized:
                    # Preserve the standard Windows behaviour: a window that
                    # was maximized before minimizing returns maximized.
                    if not self.isMaximized():
                        QTimer.singleShot(0, self.showMaximized)
                else:
                    restore_geometry = QRect(
                        self._pre_minimize_geometry
                        if self._pre_minimize_geometry.isValid()
                        else self._last_normal_geometry
                    )
                    QTimer.singleShot(
                        0,
                        lambda geometry=restore_geometry:
                        self._restore_pre_minimize_geometry(geometry),
                    )

        super().changeEvent(event)

    def nativeEvent(self, event_type, message):
        # Stage 3.2D.1.6: custom edge resizing is intentionally disabled.
        # QMainWindow creates native child windows for dock widgets; handling
        # WM_NCHITTEST at this level caused Windows to treat those children as
        # top-level windows. Moving, maximize/restore and normal Qt sizing
        # behaviour remain available.
        return super().nativeEvent(event_type, message)



class FramelessDialog(QDialog):
    """Modal WT Studio dialog without the native white Windows title bar."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)



class WindowTitleBar(QWidget):
    """VS Code-like title row shared by the main window and dialogs."""

    def __init__(
        self,
        window: QWidget,
        *,
        include_menu: bool = False,
        dialog: bool = False,
        show_logo: bool = True,
        show_minimize: bool = True,
        show_maximize: bool = True,
        show_close: bool = True,
        movable: bool | None = None,
    ) -> None:
        super().__init__(window)

        self._window = window
        self._dialog = bool(dialog)

        # Existing dialogs remain fixed by default. Welcome / Quick Start
        # explicitly opts into the same native move operation as the main window.
        self._movable = (
            not self._dialog
            if movable is None
            else bool(movable)
        )

        self.setObjectName(
            "dialogTitleBar" if self._dialog else "mainTitleBar"
        )
        self.setFixedHeight(31 if self._dialog else 34)
        self.setMouseTracking(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(7, 0, 0, 0)
        layout.setSpacing(2)

        if show_logo:
            self.logo_label = QLabel()
            self.logo_label.setObjectName("windowLogo")
            self.logo_label.setPixmap(
                brand_logo_icon(18 if self._dialog else 20).pixmap(
                    18 if self._dialog else 20,
                    18 if self._dialog else 20,
                )
            )
            self.logo_label.setFixedSize(24, 24)
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.logo_label.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )
            layout.addWidget(self.logo_label)

        self.menu_bar: QMenuBar | None = None
        if include_menu:
            self.menu_bar = QMenuBar(self)
            self.menu_bar.setObjectName("titleMenuBar")
            self.menu_bar.setNativeMenuBar(False)
            self.menu_bar.setSizePolicy(
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Expanding,
            )
            layout.addWidget(self.menu_bar)

        layout.addStretch(1)

        self.title_label = QLabel(window.windowTitle())
        self.title_label.setObjectName("windowTitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        self.title_label.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )
        layout.addWidget(self.title_label)

        layout.addStretch(1)

        self.minimize_button = None
        self.maximize_button = None
        self.close_button = None

        if show_minimize:
            self.minimize_button = self._create_window_button(
                "windowMinimizeButton",
                "Minimize",
                window_control_icon("minimize"),
            )
            self.minimize_button.clicked.connect(self.minimize_window)
            layout.addWidget(self.minimize_button)

        if show_maximize:
            self.maximize_button = self._create_window_button(
                "windowMaximizeButton",
                "Maximize",
                window_control_icon("maximize"),
            )
            self.maximize_button.clicked.connect(self.toggle_maximized)
            layout.addWidget(self.maximize_button)

        if show_close:
            self.close_button = self._create_window_button(
                "windowCloseButton",
                "Close",
                window_control_icon("close"),
            )
            self.close_button.clicked.connect(window.close)
            layout.addWidget(self.close_button)

        window.windowTitleChanged.connect(self.title_label.setText)

        # Only the main window needs WindowStateChange tracking.
        # Dialog title bars have no maximize button, so installing an event
        # filter there adds risk without providing any behaviour.
        if self.maximize_button is not None:
            window.installEventFilter(self)

        self._maximized_drag_pending = False
        self._maximized_drag_start = QPoint()
        self._maximized_drag_ratio = 0.5
        self._maximized_drag_press_y = 0

        self._refresh_maximize_button()

    @staticmethod
    def _create_window_button(
        object_name: str,
        tooltip: str,
        icon,
    ) -> QToolButton:
        button = QToolButton()
        button.setObjectName(object_name)
        button.setToolTip(tooltip)
        button.setIcon(icon)
        button.setIconSize(QSize(16, 16))
        button.setAutoRaise(True)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return button

    def eventFilter(self, watched, event):
        # Qt can deliver a late event while the Python wrapper is being
        # constructed or destroyed. Never assume that _window still exists.
        window = getattr(self, "_window", None)

        if (
            window is not None
            and watched is window
            and event.type() == QEvent.Type.WindowStateChange
        ):
            self._refresh_maximize_button()
            QTimer.singleShot(0, self._refresh_maximize_button)

        return super().eventFilter(watched, event)

    def minimize_window(self) -> None:
        safe_minimize = getattr(
            self._window,
            "minimize_safely",
            None,
        )
        if callable(safe_minimize):
            safe_minimize()
        else:
            self._window.showMinimized()

    def toggle_maximized(self) -> None:
        safe_toggle = getattr(
            self._window,
            "toggle_maximized_safely",
            None,
        )
        if callable(safe_toggle):
            safe_toggle()
        elif self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()

        # WindowStateChange may be delivered before Windows finishes applying
        # the native state. Refresh once immediately and once on the next event
        # loop turn so the maximize/restore glyph cannot remain stale.
        self._refresh_maximize_button()
        QTimer.singleShot(0, self._refresh_maximize_button)

    def _refresh_maximize_button(self) -> None:
        if self.maximize_button is None:
            return

        maximized = self._window.isMaximized()
        self.maximize_button.setIcon(
            window_control_icon("restore" if maximized else "maximize")
        )
        self.maximize_button.setToolTip(
            "Restore" if maximized else "Maximize"
        )

    def _start_native_move(self) -> bool:
        window = getattr(self, "_window", None)
        if (
            window is None
            or not window.isWindow()
            or window.window() is not window
        ):
            return False

        handle = window.windowHandle()
        if (
            handle is None
            or int(handle.winId()) != int(window.winId())
        ):
            return False

        begin_snap_watch = getattr(
            window,
            "begin_title_drag_snap_watch",
            None,
        )
        cancel_snap_watch = getattr(
            window,
            "cancel_title_drag_snap_watch",
            None,
        )

        if callable(begin_snap_watch):
            begin_snap_watch()

        started = bool(handle.startSystemMove())

        if not started and callable(cancel_snap_watch):
            cancel_snap_watch()

        return started

    def mousePressEvent(self, event: QMouseEvent) -> None:
        window = getattr(self, "_window", None)

        if (
            self._movable
            and window is not None
            and window.isWindow()
            and window.window() is window
            and event.button() == Qt.MouseButton.LeftButton
            and not window.isMinimized()
            and not window.isFullScreen()
        ):
            if window.isMaximized():
                # A maximized frameless Qt window does not receive native
                # Windows restore-on-drag automatically. Delay the restore
                # until the pointer has actually moved by the platform drag
                # threshold so a simple click on the title bar does nothing.
                self._maximized_drag_pending = True
                self._maximized_drag_start = (
                    event.globalPosition().toPoint()
                )

                width = max(1, window.width())
                local_x = (
                    self._maximized_drag_start.x()
                    - window.frameGeometry().left()
                )
                self._maximized_drag_ratio = min(
                    0.95,
                    max(0.05, local_x / width),
                )
                self._maximized_drag_press_y = int(
                    round(event.position().y())
                )

                event.accept()
                return

            if self._start_native_move():
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        window = getattr(self, "_window", None)

        if (
            self._maximized_drag_pending
            and window is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            current = event.globalPosition().toPoint()
            delta = current - self._maximized_drag_start

            if (
                abs(delta.x()) + abs(delta.y())
                >= QApplication.startDragDistance()
            ):
                self._maximized_drag_pending = False

                restore_for_drag = getattr(
                    window,
                    "restore_for_title_drag",
                    None,
                )
                restored = False
                if callable(restore_for_drag):
                    restored = bool(
                        restore_for_drag(
                            current,
                            horizontal_ratio=(
                                self._maximized_drag_ratio
                            ),
                            title_press_y=(
                                self._maximized_drag_press_y
                            ),
                        )
                    )

                if restored:
                    self._refresh_maximize_button()
                    QTimer.singleShot(
                        0,
                        self._refresh_maximize_button,
                    )

                    if self._start_native_move():
                        event.accept()
                        return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._maximized_drag_pending = False

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self._maximized_drag_pending = False

        if (
            not self._dialog
            and event.button() == Qt.MouseButton.LeftButton
            and self.maximize_button is not None
        ):
            self.toggle_maximized()
            event.accept()
            return

        super().mouseDoubleClickEvent(event)
