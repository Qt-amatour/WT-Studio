from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QMenu,
)

from app.runtime_paths import project_library_path


class ProjectBrowser(QTreeWidget):
    projectOpenRequested = Signal(str)
    projectDeleteRequested = Signal(str)

    CATEGORIES = (
        "Aircraft",
        "Tanks",
        "Helicopters",
        "Ships",
        "Boats",
        "Others",
    )

    PATH_ROLE = Qt.ItemDataRole.UserRole

    def __init__(
        self,
        *,
        library_path: str | Path | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.setHeaderHidden(True)

        if library_path is None:
            library_path = project_library_path()

        self.library_path = Path(
            library_path
        )
        self.library_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.itemDoubleClicked.connect(
            self._item_double_clicked
        )

        self.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.customContextMenuRequested.connect(
            self._show_context_menu
        )

        self.refresh()

    def refresh(self) -> None:
        self.clear()

        for category in self.CATEGORIES:
            category_path = (
                self.library_path / category
            )
            category_path.mkdir(
                parents=True,
                exist_ok=True,
            )

            category_item = QTreeWidgetItem(
                [category]
            )
            category_item.setData(
                0,
                self.PATH_ROLE,
                None,
            )
            self.addTopLevelItem(
                category_item
            )

            projects = sorted(
                category_path.glob("*.wts"),
                key=lambda path: path.stem.casefold(),
            )

            for project_path in projects:
                project_item = QTreeWidgetItem(
                    [project_path.stem]
                )
                project_item.setToolTip(
                    0,
                    str(project_path),
                )
                project_item.setData(
                    0,
                    self.PATH_ROLE,
                    str(project_path),
                )
                category_item.addChild(
                    project_item
                )

        self.expandAll()

    def selected_project_path(
        self,
    ) -> Path | None:
        item = self.currentItem()

        if item is None:
            return None

        value = item.data(
            0,
            self.PATH_ROLE,
        )

        if not value:
            return None

        return Path(value)

    def category_path(
        self,
        category: str,
    ) -> Path:
        if category not in self.CATEGORIES:
            raise ValueError(
                f"Unknown project category: {category}"
            )

        path = self.library_path / category
        path.mkdir(
            parents=True,
            exist_ok=True,
        )
        return path

    def _show_context_menu(
        self,
        position: QPoint,
    ) -> None:
        item = self.itemAt(position)

        if item is None:
            return

        value = item.data(
            0,
            self.PATH_ROLE,
        )

        # Category headers do not have a project path.
        if not value:
            return

        # Parentless popup avoids native dock-window transient-parent
        # warnings while exec() keeps the local menu alive synchronously.
        menu = QMenu()

        delete_action = menu.addAction(
            "Delete Project"
        )

        selected = menu.exec(
            self.viewport().mapToGlobal(
                position
            )
        )

        if selected is delete_action:
            self.projectDeleteRequested.emit(
                str(value)
            )

    def _item_double_clicked(
        self,
        item: QTreeWidgetItem,
        column: int,
    ) -> None:
        value = item.data(
            0,
            self.PATH_ROLE,
        )

        if value:
            self.projectOpenRequested.emit(
                str(value)
            )
