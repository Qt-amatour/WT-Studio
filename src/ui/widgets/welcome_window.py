from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QCloseEvent, QShowEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.version import APP_FULL_NAME
from ui.icons import brand_logo_icon
from ui.widgets.project_browser import ProjectBrowser
from ui.widgets.window_chrome import FramelessDialog, WindowTitleBar


class WelcomeWindow(FramelessDialog):
    """Large WT Studio startup screen with two primary workflow choices."""

    importRequested = Signal()
    openProjectRequested = Signal(str)
    continueRequested = Signal()

    WINDOW_WIDTH = 920
    WINDOW_HEIGHT = 620

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        startup_mode: bool = True,
    ) -> None:
        super().__init__(parent)

        self._startup_mode = bool(startup_mode)
        self._completed = False

        self.setObjectName("welcomeWindow")
        self.setWindowTitle(f"{APP_FULL_NAME} — Quick Start")
        self.setModal(True)
        self.setFixedSize(
            self.WINDOW_WIDTH,
            self.WINDOW_HEIGHT,
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_DeleteOnClose,
            True,
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.title_bar = WindowTitleBar(
            self,
            dialog=True,
            movable=True,
            show_logo=True,
            show_minimize=False,
            show_maximize=False,
            show_close=True,
        )
        outer.addWidget(self.title_bar)

        self.body = QWidget()
        self.body.setObjectName("welcomeBody")
        outer.addWidget(self.body, 1)

        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(52, 34, 52, 38)
        body_layout.setSpacing(0)

        self.pages = QStackedWidget()
        self.pages.setObjectName("welcomePages")
        body_layout.addWidget(self.pages)

        self.home_page = self._build_home_page()
        self.projects_page = self._build_projects_page()

        self.pages.addWidget(self.home_page)
        self.pages.addWidget(self.projects_page)
        self.pages.setCurrentWidget(self.home_page)

    def _build_home_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("welcomeHomePage")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addStretch(1)

        logo = QLabel()
        logo.setObjectName("welcomeLogo")
        logo.setFixedSize(176, 176)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setPixmap(
            brand_logo_icon(152).pixmap(152, 152)
        )
        layout.addWidget(
            logo,
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )

        title = QLabel("WT STUDIO")
        title.setObjectName("welcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        version = QLabel(APP_FULL_NAME)
        version.setObjectName("welcomeVersion")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        subtitle = QLabel(
            "Start a new PBR texture workflow or continue from your Project Library."
        )
        subtitle.setObjectName("welcomeSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        layout.addSpacing(34)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(24)
        actions.addStretch(1)

        import_column = self._action_column(
            button_text="Import Texture",
            description="Start an unsaved Untitled PBR workflow.",
        )
        self.import_button = import_column.property("actionButton")
        actions.addWidget(import_column)

        open_column = self._action_column(
            button_text="Open Project",
            description="Choose a saved .wts project from the library.",
        )
        self.open_projects_button = open_column.property("actionButton")
        actions.addWidget(open_column)

        actions.addStretch(1)
        layout.addLayout(actions)

        layout.addSpacing(30)

        hint = QLabel(
            "Closing Quick Start continues with an empty Untitled session."
        )
        hint.setObjectName("welcomeHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        layout.addStretch(1)

        self.import_button.clicked.connect(
            self._request_import
        )
        self.open_projects_button.clicked.connect(
            self._show_projects
        )

        return page

    @staticmethod
    def _action_column(
        *,
        button_text: str,
        description: str,
    ) -> QFrame:
        frame = QFrame()
        frame.setObjectName("welcomeActionColumn")
        frame.setFixedWidth(272)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        button = QPushButton(button_text)
        button.setObjectName("welcomePrimaryButton")
        button.setFixedWidth(272)
        button.setMinimumHeight(52)
        button.setMaximumHeight(52)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setAutoDefault(False)
        button.setDefault(False)
        layout.addWidget(button)

        label = QLabel(description)
        label.setObjectName("welcomeActionDescription")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        label.setFixedWidth(272)
        layout.addWidget(label)

        frame.setProperty("actionButton", button)
        return frame

    def _build_projects_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("welcomeProjectsPage")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 8, 18, 4)
        layout.setSpacing(14)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(12)

        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("welcomeSecondaryButton")
        self.back_button.setFixedSize(104, 34)
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        header.addWidget(self.back_button)
        header.addStretch(1)
        layout.addLayout(header)

        title = QLabel("Open Project")
        title.setObjectName("welcomeProjectsTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel(
            "Choose a saved WT Studio project. Double-click a project to open it immediately."
        )
        subtitle.setObjectName("welcomeProjectsSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        layout.addSpacing(4)

        browser_frame = QFrame()
        browser_frame.setObjectName("welcomeProjectBrowserFrame")
        browser_layout = QVBoxLayout(browser_frame)
        browser_layout.setContentsMargins(1, 1, 1, 1)
        browser_layout.setSpacing(0)

        self.project_browser = ProjectBrowser()
        self.project_browser.setObjectName("welcomeProjectBrowser")
        self.project_browser.setContextMenuPolicy(
            Qt.ContextMenuPolicy.NoContextMenu
        )
        self.project_browser.setMinimumHeight(330)
        self.project_browser.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        browser_layout.addWidget(self.project_browser)
        layout.addWidget(browser_frame, 1)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 4, 0, 0)
        footer.setSpacing(12)
        footer.addStretch(1)

        self.open_selected_button = QPushButton("Open Selected")
        self.open_selected_button.setObjectName("welcomePrimaryButton")
        self.open_selected_button.setFixedSize(190, 42)
        self.open_selected_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.open_selected_button.setEnabled(False)
        footer.addWidget(self.open_selected_button)
        layout.addLayout(footer)

        self.back_button.clicked.connect(
            self._show_home
        )
        self.open_selected_button.clicked.connect(
            self._open_selected_project
        )
        self.project_browser.itemSelectionChanged.connect(
            self._update_open_button
        )
        self.project_browser.projectOpenRequested.connect(
            self._open_project_path
        )

        return page

    def _show_projects(self) -> None:
        self.project_browser.refresh()
        self.project_browser.clearSelection()
        self._update_open_button()
        self.pages.setCurrentWidget(self.projects_page)

    def _show_home(self) -> None:
        self.pages.setCurrentWidget(self.home_page)

    def _update_open_button(self) -> None:
        self.open_selected_button.setEnabled(
            self.project_browser.selected_project_path() is not None
        )

    def _request_import(self) -> None:
        self._completed = True
        self.importRequested.emit()
        self.close()

    def _open_selected_project(self) -> None:
        path = self.project_browser.selected_project_path()
        if path is None:
            return
        self._open_project_path(str(path))

    def _open_project_path(self, path: str) -> None:
        project_path = Path(path)
        if not project_path.is_file():
            self.project_browser.refresh()
            self._update_open_button()
            return

        self._completed = True
        self.openProjectRequested.emit(str(project_path))
        self.close()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)

        parent = self.parentWidget()
        if parent is not None and parent.isVisible():
            center = parent.frameGeometry().center()
        else:
            screen = self.screen()
            if screen is None:
                return
            center = screen.availableGeometry().center()

        geometry = self.frameGeometry()
        geometry.moveCenter(center)
        self.move(geometry.topLeft())

    def _continue_startup_if_needed(self) -> None:
        if self._startup_mode and not self._completed:
            self._completed = True
            self.continueRequested.emit()

    def reject(self) -> None:
        # QDialog maps Escape to reject(). On the project-selection page,
        # Escape behaves like Back. On the home page it follows the same
        # startup behavior as the title-bar X instead of quitting the app.
        if self.pages.currentWidget() is self.projects_page:
            self._show_home()
            return

        self._continue_startup_if_needed()
        super().reject()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._continue_startup_if_needed()
        event.accept()
