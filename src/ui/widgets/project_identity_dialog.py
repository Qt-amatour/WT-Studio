from __future__ import annotations

from PySide6.QtWidgets import (
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)
from ui.widgets.downward_combo_box import DownwardComboBox
from ui.widgets.window_chrome import (
    FramelessDialog,
    WindowTitleBar,
)


class ProjectIdentityDialog(FramelessDialog):
    """
    Collects project name and category in one modal dialog.

    The Save button remains disabled until both fields contain
    a valid selection.
    """

    def __init__(
        self,
        *,
        title: str,
        categories,
        initial_name: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("projectIdentityDialog")

        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(420)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.title_bar = WindowTitleBar(
            self,
            dialog=True,
            show_logo=True,
            show_minimize=False,
            show_maximize=False,
            show_close=True,
        )
        outer.addWidget(self.title_bar)

        body = QVBoxLayout()
        body.setContentsMargins(12, 10, 12, 12)
        body.setSpacing(8)
        outer.addLayout(body)

        root = body
        form = QFormLayout()

        self.name_edit = QLineEdit(initial_name)
        self.name_edit.setPlaceholderText(
            "Enter project name"
        )

        self.category_combo = DownwardComboBox()
        self.category_combo.addItem(
            "Select category...",
            None,
        )

        for category in categories:
            self.category_combo.addItem(
                str(category),
                str(category),
            )

        form.addRow(
            "Project name:",
            self.name_edit,
        )
        form.addRow(
            "Category:",
            self.category_combo,
        )

        root.addLayout(form)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.setObjectName("projectIdentityButtonBox")
        self.buttons.setCenterButtons(True)

        self.save_button = self.buttons.button(
            QDialogButtonBox.StandardButton.Save
        )
        self.cancel_button = self.buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        )

        for button in (
            self.save_button,
            self.cancel_button,
        ):
            button.setObjectName("dialogActionButton")
            button.setMinimumWidth(160)
            button.setMinimumHeight(30)
            button.setAutoDefault(False)
            button.setDefault(False)

        self.save_button.setEnabled(False)

        root.addWidget(self.buttons)

        self.name_edit.textChanged.connect(
            self._refresh_save_state
        )
        self.category_combo.currentIndexChanged.connect(
            self._refresh_save_state
        )

        self.buttons.accepted.connect(
            self.accept
        )
        self.buttons.rejected.connect(
            self.reject
        )

        self._refresh_save_state()

    def project_name(self) -> str:
        return self.name_edit.text().strip()

    def category(self) -> str | None:
        return self.category_combo.currentData()

    def _refresh_save_state(self) -> None:
        self.save_button.setEnabled(
            bool(self.project_name())
            and bool(self.category())
        )
