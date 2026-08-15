from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QCloseEvent, QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QMessageBox as QtMessageBox,
)

from ui.icons import message_icon
from ui.widgets.window_chrome import (
    FramelessDialog,
    WindowTitleBar,
)


class QMessageBox(FramelessDialog):
    """WT Studio message dialog with predictable, compact geometry.

    The public surface intentionally mirrors the subset of Qt's QMessageBox
    used by WT Studio.  It keeps the familiar StandardButton/Icon enums while
    avoiding the native QMessageBox layout constraints that caused extreme
    word wrapping and QWindowsWindow::setGeometry warnings on Windows.
    """

    Icon = QtMessageBox.Icon
    StandardButton = QtMessageBox.StandardButton
    ButtonRole = QtMessageBox.ButtonRole

    _BUTTON_ORDER = (
        StandardButton.Ok,
        StandardButton.Save,
        StandardButton.SaveAll,
        StandardButton.Open,
        StandardButton.Yes,
        StandardButton.YesToAll,
        StandardButton.No,
        StandardButton.NoToAll,
        StandardButton.Abort,
        StandardButton.Retry,
        StandardButton.Ignore,
        StandardButton.Close,
        StandardButton.Cancel,
        StandardButton.Discard,
        StandardButton.Apply,
        StandardButton.Reset,
        StandardButton.RestoreDefaults,
        StandardButton.Help,
    )

    _BUTTON_TEXT = {
        StandardButton.Ok: "OK",
        StandardButton.Save: "Save",
        StandardButton.SaveAll: "Save All",
        StandardButton.Open: "Open",
        StandardButton.Yes: "Yes",
        StandardButton.YesToAll: "Yes to All",
        StandardButton.No: "No",
        StandardButton.NoToAll: "No to All",
        StandardButton.Abort: "Abort",
        StandardButton.Retry: "Retry",
        StandardButton.Ignore: "Ignore",
        StandardButton.Close: "Close",
        StandardButton.Cancel: "Cancel",
        StandardButton.Discard: "Discard",
        StandardButton.Apply: "Apply",
        StandardButton.Reset: "Reset",
        StandardButton.RestoreDefaults: "Restore Defaults",
        StandardButton.Help: "Help",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setObjectName("wtMessageBox")
        self.setModal(True)
        self.setSizeGripEnabled(False)
        self.setMinimumWidth(540)
        self.setMaximumWidth(700)

        self._icon = self.Icon.NoIcon
        self._standard_buttons = self.StandardButton.Ok
        self._default_button = self.StandardButton.NoButton
        self._clicked_standard_button = self.StandardButton.NoButton
        self._button_widgets: dict[QtMessageBox.StandardButton, QPushButton] = {}
        self._details_text = ""
        self._collapsed_height: int | None = None

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

        body = QWidget()
        body.setObjectName("messageBoxBody")
        root = QVBoxLayout(body)
        root.setContentsMargins(18, 14, 18, 16)
        root.setSpacing(10)
        outer.addWidget(body)

        # A vertical composition gives the message its full width and keeps
        # the icon from visually pulling the text to one side.
        self.icon_label = QLabel()
        self.icon_label.setObjectName("messageBoxIcon")
        self.icon_label.setFixedSize(68, 68)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setVisible(False)
        root.addWidget(
            self.icon_label,
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )

        self.text_label = QLabel()
        self.text_label.setObjectName("messageBoxText")
        self.text_label.setWordWrap(True)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.text_label.setMinimumWidth(460)
        self.text_label.setMaximumWidth(620)
        root.addWidget(self.text_label)

        self.informative_label = QLabel()
        self.informative_label.setObjectName("messageBoxInformativeText")
        self.informative_label.setWordWrap(True)
        self.informative_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.informative_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.informative_label.setMinimumWidth(460)
        self.informative_label.setMaximumWidth(620)
        self.informative_label.setVisible(False)
        root.addWidget(self.informative_label)

        self.details_frame = QFrame()
        self.details_frame.setObjectName("messageBoxDetailsFrame")
        self.details_frame.setVisible(False)
        details_layout = QVBoxLayout(self.details_frame)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(0)

        self.details_view = QPlainTextEdit()
        self.details_view.setObjectName("messageBoxDetails")
        self.details_view.setReadOnly(True)
        self.details_view.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )
        self.details_view.setMinimumHeight(110)
        self.details_view.setMaximumHeight(180)
        details_layout.addWidget(self.details_view)
        root.addWidget(self.details_frame)

        self.button_row = QHBoxLayout()
        self.button_row.setContentsMargins(0, 0, 0, 0)
        self.button_row.setSpacing(10)
        root.addLayout(self.button_row)

        self.details_button = QPushButton("Show Details...")
        self.details_button.setObjectName("messageBoxDetailsButton")
        self.details_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.details_button.setAutoDefault(False)
        self.details_button.setDefault(False)
        self.details_button.setVisible(False)
        self.details_button.clicked.connect(self._toggle_details)

        self._rebuild_buttons()

    def setIcon(self, icon: QtMessageBox.Icon) -> None:
        self._icon = icon
        icon_name = self._icon_name(icon)

        if icon_name is None:
            self.icon_label.clear()
            self.icon_label.setVisible(False)
            return

        self.icon_label.setPixmap(
            message_icon(icon_name, 62).pixmap(62, 62)
        )
        self.icon_label.setVisible(True)

    def setText(self, text: str) -> None:
        self.text_label.setText(str(text or ""))

    def text(self) -> str:
        return self.text_label.text()

    def setInformativeText(self, text: str) -> None:
        value = str(text or "")
        self.informative_label.setText(value)
        self.informative_label.setVisible(bool(value))

    def informativeText(self) -> str:
        return self.informative_label.text()

    def setDetailedText(self, text: str) -> None:
        self._details_text = str(text or "")
        self.details_view.setPlainText(self._details_text)
        has_details = bool(self._details_text)
        self.details_button.setVisible(has_details)

        if not has_details:
            self.details_frame.setVisible(False)
            self.details_button.setText("Show Details...")

        self._rebuild_buttons()

    def detailedText(self) -> str:
        return self._details_text

    def setStandardButtons(
        self,
        buttons: QtMessageBox.StandardButton,
    ) -> None:
        self._standard_buttons = buttons or self.StandardButton.Ok
        self._rebuild_buttons()

    def standardButtons(self) -> QtMessageBox.StandardButton:
        return self._standard_buttons

    def setDefaultButton(
        self,
        button: QtMessageBox.StandardButton,
    ) -> None:
        self._default_button = button
        self._apply_default_button()

    def defaultButton(self) -> QPushButton | None:
        return self._button_widgets.get(self._default_button)

    def clickedButton(self) -> QPushButton | None:
        return self._button_widgets.get(self._clicked_standard_button)

    def standardButton(
        self,
        button: QPushButton | None,
    ) -> QtMessageBox.StandardButton:
        for standard_button, widget in self._button_widgets.items():
            if widget is button:
                return standard_button
        return self.StandardButton.NoButton

    def exec(self) -> QtMessageBox.StandardButton:
        self._prepare_for_show()
        super().exec()
        return self._clicked_standard_button

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        ):
            focused = QApplication.focusWidget()

            if isinstance(focused, QPushButton):
                if focused is self.details_button:
                    focused.click()
                    event.accept()
                    return

                for button in self._button_widgets.values():
                    if focused is button:
                        focused.click()
                        event.accept()
                        return

            target = self._default_button
            if target not in self._button_widgets:
                target = next(
                    iter(self._button_widgets),
                    self.StandardButton.NoButton,
                )

            if target != self.StandardButton.NoButton:
                self._standard_button_clicked(target)
                event.accept()
                return

        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            event.accept()
            return

        super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._clicked_standard_button == self.StandardButton.NoButton:
            self._clicked_standard_button = self._escape_standard_button()
        super().closeEvent(event)

    def reject(self) -> None:
        if self._clicked_standard_button == self.StandardButton.NoButton:
            self._clicked_standard_button = self._escape_standard_button()
        super().reject()

    def _prepare_for_show(self) -> None:
        self._rebuild_buttons()
        self._apply_default_button()

        # Release any fixed height left by a previous details toggle before
        # calculating the compact geometry for this execution.
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)

        self.details_frame.setVisible(False)
        self.details_button.setText("Show Details...")
        self.layout().invalidate()
        self.layout().activate()
        self.adjustSize()

        target_width = max(540, min(700, self.sizeHint().width()))
        self.resize(target_width, self.sizeHint().height())
        self.layout().activate()

        self._collapsed_height = self.sizeHint().height()

        # QDialog can retain the expanded native minimum size on Windows.
        # A fixed height is deliberate here: it guarantees that hiding the
        # details panel restores the exact compact geometry.
        self.setFixedHeight(self._collapsed_height)

    def _rebuild_buttons(self) -> None:
        while self.button_row.count():
            item = self.button_row.takeAt(0)
            widget = item.widget()
            if widget is not None and widget is not self.details_button:
                widget.setParent(None)
                widget.deleteLater()

        self._button_widgets.clear()

        for standard_button in self._buttons_from_flags(
            self._standard_buttons
        ):
            button = QPushButton(
                self._BUTTON_TEXT.get(
                    standard_button,
                    str(standard_button),
                )
            )
            button.setObjectName("messageBoxStandardButton")
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            button.setAutoDefault(False)
            button.setDefault(False)
            button.clicked.connect(
                lambda checked=False, value=standard_button:
                self._standard_button_clicked(value)
            )
            self._button_widgets[standard_button] = button
            self.button_row.addWidget(button, 1)

        if self._details_text:
            self.button_row.addWidget(self.details_button, 1)

        self._apply_default_button()

    def _apply_default_button(self) -> None:
        # Keep the default action logically, but do not expose a permanent
        # native/default focus frame. Enter is handled in keyPressEvent.
        for button in self._button_widgets.values():
            button.setAutoDefault(False)
            button.setDefault(False)

    def _standard_button_clicked(
        self,
        standard_button: QtMessageBox.StandardButton,
    ) -> None:
        self._clicked_standard_button = standard_button
        self.done(0)

    @Slot()
    def _toggle_details(self) -> None:
        expanded = not self.details_frame.isVisible()

        if expanded:
            self._collapsed_height = self.height()

            # Release the compact fixed height, show the details panel and
            # calculate one exact expanded height.
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            self.details_frame.setVisible(True)
            self.details_button.setText("Hide Details...")
            self.layout().invalidate()
            self.layout().activate()
            self.adjustSize()

            expanded_height = self.sizeHint().height()
            self.setFixedHeight(expanded_height)
            return

        self.details_frame.setVisible(False)
        self.details_button.setText("Show Details...")
        self.layout().invalidate()
        self.layout().activate()

        collapsed_height = (
            self._collapsed_height
            if self._collapsed_height is not None
            else self.sizeHint().height()
        )
        self.setFixedHeight(collapsed_height)

    def _escape_standard_button(self) -> QtMessageBox.StandardButton:
        for candidate in (
            self.StandardButton.Cancel,
            self.StandardButton.No,
            self.StandardButton.Close,
            self.StandardButton.Ok,
        ):
            if self._has_button(candidate):
                return candidate
        return self.StandardButton.NoButton

    def _buttons_from_flags(
        self,
        flags: QtMessageBox.StandardButton,
    ) -> Iterable[QtMessageBox.StandardButton]:
        buttons = [
            button
            for button in self._BUTTON_ORDER
            if self._flag_contains(flags, button)
        ]
        return buttons or [self.StandardButton.Ok]

    def _has_button(
        self,
        button: QtMessageBox.StandardButton,
    ) -> bool:
        return self._flag_contains(self._standard_buttons, button)

    @staticmethod
    def _flag_contains(flags, button) -> bool:
        try:
            return bool(flags & button)
        except TypeError:
            return bool(int(flags) & int(button))

    @staticmethod
    def _icon_name(icon: QtMessageBox.Icon) -> str | None:
        return {
            QtMessageBox.Icon.Information: "information",
            QtMessageBox.Icon.Warning: "warning",
            QtMessageBox.Icon.Critical: "critical",
            QtMessageBox.Icon.Question: "question",
        }.get(icon)

    @classmethod
    def _show_static(
        cls,
        parent: QWidget | None,
        title: str,
        text: str,
        icon: QtMessageBox.Icon,
        buttons: QtMessageBox.StandardButton,
        default_button: QtMessageBox.StandardButton,
    ) -> QtMessageBox.StandardButton:
        box = cls(parent)
        box.setWindowTitle(title)
        box.setIcon(icon)
        box.setText(text)
        box.setStandardButtons(buttons)
        box.setDefaultButton(default_button)
        return box.exec()

    @classmethod
    def information(
        cls,
        parent: QWidget | None,
        title: str,
        text: str,
        buttons: QtMessageBox.StandardButton = StandardButton.Ok,
        defaultButton: QtMessageBox.StandardButton = StandardButton.NoButton,
    ) -> QtMessageBox.StandardButton:
        return cls._show_static(
            parent,
            title,
            text,
            cls.Icon.Information,
            buttons,
            defaultButton,
        )

    @classmethod
    def warning(
        cls,
        parent: QWidget | None,
        title: str,
        text: str,
        buttons: QtMessageBox.StandardButton = StandardButton.Ok,
        defaultButton: QtMessageBox.StandardButton = StandardButton.NoButton,
    ) -> QtMessageBox.StandardButton:
        return cls._show_static(
            parent,
            title,
            text,
            cls.Icon.Warning,
            buttons,
            defaultButton,
        )

    @classmethod
    def critical(
        cls,
        parent: QWidget | None,
        title: str,
        text: str,
        buttons: QtMessageBox.StandardButton = StandardButton.Ok,
        defaultButton: QtMessageBox.StandardButton = StandardButton.NoButton,
    ) -> QtMessageBox.StandardButton:
        return cls._show_static(
            parent,
            title,
            text,
            cls.Icon.Critical,
            buttons,
            defaultButton,
        )

    @classmethod
    def question(
        cls,
        parent: QWidget | None,
        title: str,
        text: str,
        buttons: QtMessageBox.StandardButton = (
            StandardButton.Yes | StandardButton.No
        ),
        defaultButton: QtMessageBox.StandardButton = StandardButton.No,
    ) -> QtMessageBox.StandardButton:
        return cls._show_static(
            parent,
            title,
            text,
            cls.Icon.Question,
            buttons,
            defaultButton,
        )
