# ============================================================
# WT Studio
# Version : 0.9.0
#
# File:
# application.py
#
# Description:
# Main application controller
# ============================================================

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor

from ui.icons import application_icon
from ui.main_window import MainWindow
from ui.theme import load_theme
from ui.widgets.help_about_window import HelpAboutWindow
from ui.widgets.welcome_window import WelcomeWindow


class WTApplication:
    def __init__(self, app) -> None:
        self.app = app

        load_theme(self.app)
        self.app.setWindowIcon(application_icon(32))

        self.window = MainWindow()
        self.welcome: WelcomeWindow | None = None
        self.help_about: HelpAboutWindow | None = None
        self._help_about_after_startup_action = False
        self._help_cursor_override_active = False

        self.window.quickStartRequested.connect(
            self.show_quick_start
        )
        self.window.helpAboutRequested.connect(
            self.show_help_about
        )
        self.window.startupActionFinished.connect(
            self._startup_action_finished
        )

    def run(self) -> None:
        self.show_quick_start(startup_mode=True)

    def show_quick_start(
        self,
        startup_mode: bool = False,
    ) -> None:
        if self.welcome is not None and self.welcome.isVisible():
            self.welcome.raise_()
            self.welcome.activateWindow()
            return

        parent = self.window if self.window.isVisible() else None
        welcome = WelcomeWindow(
            parent=parent,
            startup_mode=startup_mode,
        )
        self.welcome = welcome

        welcome.importRequested.connect(
            lambda startup=startup_mode:
            self._start_import_workflow(startup)
        )
        welcome.openProjectRequested.connect(
            lambda path, startup=startup_mode:
            self._open_project(path, startup)
        )
        welcome.continueRequested.connect(
            self._continue_from_startup
        )
        welcome.destroyed.connect(
            self._welcome_destroyed
        )

        welcome.show()
        welcome.raise_()
        welcome.activateWindow()

    def _welcome_destroyed(self, _object=None) -> None:
        self.welcome = None

    def _show_main_window(self) -> None:
        if not self.window.isVisible():
            self.window.show()

        self.window.raise_()
        self.window.activateWindow()

    def _continue_from_startup(self) -> None:
        self._show_main_window()
        QTimer.singleShot(
            0,
            lambda: self.show_help_about(automatic=True),
        )

    def _start_import_workflow(
        self,
        show_help_after: bool = False,
    ) -> None:
        self._help_about_after_startup_action = bool(show_help_after)
        self._show_main_window()
        QTimer.singleShot(0, self.window.import_files)

    def _open_project(
        self,
        path: str,
        show_help_after: bool = False,
    ) -> None:
        self._help_about_after_startup_action = bool(show_help_after)
        self._show_main_window()
        QTimer.singleShot(
            0,
            lambda project_path=path: self.window.open_project_path(project_path),
        )

    def _startup_action_finished(self) -> None:
        if not self._help_about_after_startup_action:
            return

        self._help_about_after_startup_action = False
        QTimer.singleShot(
            0,
            lambda: self.show_help_about(automatic=True),
        )

    def show_help_about(self, automatic: bool = False) -> None:
        if automatic and HelpAboutWindow.dont_show_automatically():
            return

        if self.help_about is not None and self.help_about.isVisible():
            self.help_about.raise_()
            self.help_about.activateWindow()
            return

        dialog = HelpAboutWindow(parent=self.window)
        self.help_about = dialog
        dialog.destroyed.connect(self._help_about_destroyed)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _help_about_destroyed(self, _object=None) -> None:
        self.help_about = None

        # On Windows, destroying a modal frameless native dialog can leave the
        # platform cursor shape from the dialog's non-client hit-test active
        # over the reactivated main window. The Help window exposed this as a
        # diagonal resize cursor even though no resize operation was active.
        #
        # Reset the cursor for one event-loop turn only. This deliberately
        # avoids changing the normal cursor policy of the main window and does
        # not touch any of the validated move/maximize/snap geometry code.
        QTimer.singleShot(
            0,
            self._reset_cursor_after_help_close,
        )

    def _reset_cursor_after_help_close(self) -> None:
        if not self.window.isVisible():
            return

        self.window.raise_()
        self.window.activateWindow()

        # Never disturb an intentional application-wide cursor override such
        # as a future WaitCursor used by a running operation.
        if self.app.overrideCursor() is not None:
            return

        self.window.setCursor(Qt.CursorShape.ArrowCursor)
        self.app.setOverrideCursor(
            QCursor(Qt.CursorShape.ArrowCursor)
        )
        self._help_cursor_override_active = True

        QTimer.singleShot(
            0,
            self._finish_help_cursor_reset,
        )

    def _finish_help_cursor_reset(self) -> None:
        if self._help_cursor_override_active:
            if self.app.overrideCursor() is not None:
                self.app.restoreOverrideCursor()
            self._help_cursor_override_active = False

        # Return cursor handling to the normal per-widget Qt policy after the
        # native dialog has fully disappeared and Windows has re-evaluated the
        # widget under the pointer.
        self.window.unsetCursor()
