from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QToolButton,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from ui.widgets.message_box import QMessageBox
from ui.widgets.downward_combo_box import DownwardComboBox

from ui.icons import panel_chevron_icon, vertical_chevron_icon

from app.services.path_settings import PathSettings
from app.services.blk_editor import (
    BLKDocument,
    BLKEditor,
    BLKEditorError,
    BLKEntryType,
    BLKTextureEntry,
    requires_replace_texture_rule,
)


@dataclass(slots=True)
class BLKMaterialChoice:
    display_name: str
    target_stem: str


class BLKEntryCard(QFrame):
    removeRequested = Signal(object)
    moveUpRequested = Signal(object)
    moveDownRequested = Signal(object)
    changed = Signal()

    def __init__(
        self,
        *,
        entry: BLKTextureEntry,
        material_choices: list[BLKMaterialChoice],
        is_camo_card: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.entry = entry
        self.is_camo_card = is_camo_card
        self.material_choices = list(material_choices)

        # Until the user explicitly selects a project material, preserve
        # the original "to:" value from the loaded BLK.
        self._original_to_value = entry.to_value
        self._material_was_selected = False

        self.setFrameShape(
            QFrame.Shape.StyledPanel
        )

        root = QVBoxLayout(self)

        header = QHBoxLayout()

        self.type_combo = None

        if not is_camo_card:
            self.type_combo = DownwardComboBox()
            self.type_combo.setObjectName("blkRuleTypeCombo")
            self.type_combo.addItem(
                "Replace",
                BLKEntryType.REPLACE,
            )
            self.type_combo.addItem(
                "Set",
                BLKEntryType.SET,
            )
            self.type_combo.setCurrentIndex(
                self.type_combo.findData(
                    entry.entry_type
                )
            )

        self.move_up_button = None
        self.move_down_button = None

        if not is_camo_card:
            self.move_up_button = QToolButton()
            self.move_up_button.setObjectName(
                "blkMoveRuleUpButton"
            )
            self.move_up_button.setIcon(
                vertical_chevron_icon("up", 14)
            )
            self.move_up_button.setIconSize(QSize(14, 14))
            self.move_up_button.setAutoRaise(True)
            self.move_up_button.setFocusPolicy(
                Qt.FocusPolicy.NoFocus
            )
            self.move_up_button.setToolTip(
                "Move this texture rule one position up."
            )

            self.move_down_button = QToolButton()
            self.move_down_button.setObjectName(
                "blkMoveRuleDownButton"
            )
            self.move_down_button.setIcon(
                vertical_chevron_icon("down", 14)
            )
            self.move_down_button.setIconSize(QSize(14, 14))
            self.move_down_button.setAutoRaise(True)
            self.move_down_button.setFocusPolicy(
                Qt.FocusPolicy.NoFocus
            )
            self.move_down_button.setToolTip(
                "Move this texture rule one position down."
            )

            header.addWidget(self.move_up_button)
            header.addWidget(self.move_down_button)

        header.addStretch(1)

        self.rule_title_label = QLabel(
            "Camo texture"
            if is_camo_card
            else "Texture rule"
        )
        header.addWidget(self.rule_title_label)

        self.remove_button = QPushButton(
            "Remove"
        )
        self.remove_button.setToolTip(
            "Remove this rule from the BLK editor."
        )

        if self.type_combo is not None:
            self.type_combo.setToolTip(
                "Choose whether this texture rule uses REPLACE or SET."
            )
            header.addWidget(
                self.type_combo
            )

        header.addWidget(
            self.remove_button
        )

        root.addLayout(header)

        # from: -----------------------------------------------------
        from_row = QHBoxLayout()
        from_row.addWidget(
            QLabel("from:")
        )

        self.from_edit = QLineEdit(
            entry.from_value
        )
        self.from_edit.setPlaceholderText(
            (
                "Camo texture name"
                if is_camo_card
                else "Texture name, e.g. vehicle_body_n"
            )
        )
        self.from_edit.setToolTip(
            "Original BLK texture name to match. "
            "_n and _ao texture names automatically force REPLACE."
            if not is_camo_card
            else "Original camo texture name to match."
        )

        from_row.addWidget(
            self.from_edit,
            1,
        )
        root.addLayout(from_row)

        # to: material + extension ---------------------------------
        to_row = QHBoxLayout()
        to_row.addWidget(
            QLabel("to:")
        )

        self.to_combo = DownwardComboBox()
        self.to_combo.setEditable(False)
        self.to_combo.setToolTip(
            "Choose a WT Studio material for the new target. "
            "Leave the original entry unassigned to keep it unchanged."
        )

        self.extension_combo = DownwardComboBox()
        self.extension_combo.addItem(
            ".dds",
            ".dds",
        )
        self.extension_combo.addItem(
            ".tga",
            ".tga",
        )

        self._set_material_choices(
            self.material_choices,
            current_target=entry.to_value,
        )

        to_row.addWidget(
            self.to_combo,
            1,
        )
        to_row.addWidget(
            self.extension_combo
        )

        root.addLayout(to_row)

        if self.type_combo is not None:
            self.type_combo.currentIndexChanged.connect(
                self._sync_entry
            )
        self.from_edit.textChanged.connect(
            self._from_value_changed
        )
        self.from_edit.editingFinished.connect(
            self._ensure_from_wildcard
        )

        self.to_combo.currentIndexChanged.connect(
            self._material_selected
        )
        self.extension_combo.currentIndexChanged.connect(
            self._extension_changed
        )

        self.remove_button.clicked.connect(
            lambda: self.removeRequested.emit(self)
        )

        if self.move_up_button is not None:
            self.move_up_button.clicked.connect(
                lambda: self.moveUpRequested.emit(self)
            )
        if self.move_down_button is not None:
            self.move_down_button.clicked.connect(
                lambda: self.moveDownRequested.emit(self)
            )

        self._apply_entry_type_policy()

    def set_move_availability(
        self,
        *,
        can_move_up: bool,
        can_move_down: bool,
    ) -> None:
        if self.move_up_button is None or self.move_down_button is None:
            return

        self.move_up_button.setEnabled(can_move_up)
        self.move_down_button.setEnabled(can_move_down)
        self.move_up_button.setIcon(
            vertical_chevron_icon(
                "up",
                14,
                disabled=not can_move_up,
            )
        )
        self.move_down_button.setIcon(
            vertical_chevron_icon(
                "down",
                14,
                disabled=not can_move_down,
            )
        )

    # ------------------------------------------------------------
    # Material targets
    # ------------------------------------------------------------

    def _set_material_choices(
        self,
        choices: list[BLKMaterialChoice],
        *,
        current_target: str,
    ) -> None:
        self.material_choices = list(choices)

        extension = self._extension_from_target(
            current_target
        )

        self.extension_combo.blockSignals(True)
        extension_index = (
            self.extension_combo.findData(
                extension
            )
        )
        self.extension_combo.setCurrentIndex(
            extension_index
            if extension_index >= 0
            else 0
        )
        self.extension_combo.blockSignals(False)

        current_stem = self._stem_from_target(
            current_target
        )

        self.to_combo.blockSignals(True)
        self.to_combo.clear()

        # A placeholder means the existing BLK value can remain untouched
        # if it does not correspond to any project material.
        self.to_combo.addItem(
            "Select material...",
            None,
        )

        matching_index = -1

        for choice in self.material_choices:
            self.to_combo.addItem(
                choice.display_name,
                choice.target_stem,
            )

            if (
                choice.target_stem.casefold()
                == current_stem.casefold()
            ):
                matching_index = (
                    self.to_combo.count() - 1
                )

        if matching_index >= 0:
            self.to_combo.setCurrentIndex(
                matching_index
            )
            self._material_was_selected = True
        else:
            self.to_combo.setCurrentIndex(0)
            self._material_was_selected = False

        self.to_combo.blockSignals(False)

    def set_material_choices(
        self,
        choices: list[BLKMaterialChoice],
    ) -> None:
        # Preserve the current generated target if a material has already
        # been selected. Otherwise preserve the original loaded "to:".
        current_target = (
            self.entry.to_value
            if self._material_was_selected
            else self._original_to_value
        )

        self._set_material_choices(
            choices,
            current_target=current_target,
        )

        if self._material_was_selected:
            self._sync_target_from_material()

    def _material_selected(
        self,
        index: int,
    ) -> None:
        target_stem = self.to_combo.itemData(
            index
        )

        if target_stem is None:
            self._material_was_selected = False
            self.entry.to_value = (
                self._original_to_value
            )
            self.changed.emit()
            return

        self._material_was_selected = True
        self._sync_target_from_material()

    def _extension_changed(
        self,
        index: int,
    ) -> None:
        # Extension only changes the BLK target once a project material
        # is explicitly selected.
        if self._material_was_selected:
            self._sync_target_from_material()

    def _sync_target_from_material(
        self,
    ) -> None:
        target_stem = self.to_combo.currentData()

        if not target_stem:
            return

        extension = (
            self.extension_combo.currentData()
            or ".dds"
        )

        self.entry.to_value = (
            f"{target_stem}{extension}"
        )
        self.changed.emit()

    # ------------------------------------------------------------
    # from:
    # ------------------------------------------------------------

    def _apply_entry_type_policy(self) -> None:
        if self.is_camo_card or self.type_combo is None:
            return

        force_replace = requires_replace_texture_rule(
            self.from_edit.text()
        )

        if force_replace:
            replace_index = self.type_combo.findData(
                BLKEntryType.REPLACE
            )
            self.type_combo.blockSignals(True)
            if replace_index >= 0:
                self.type_combo.setCurrentIndex(replace_index)
            self.type_combo.blockSignals(False)
            self.type_combo.setEnabled(False)
            self.type_combo.setToolTip(
                "_n and _ao texture rules always use REPLACE in WT Studio."
            )
            self.entry.entry_type = BLKEntryType.REPLACE
        else:
            self.type_combo.setEnabled(True)
            self.type_combo.setToolTip(
                "Choose whether this texture rule uses REPLACE or SET."
            )

    def _from_value_changed(self) -> None:
        self._apply_entry_type_policy()
        self._sync_entry()

    def _ensure_from_wildcard(self) -> None:
        value = self.from_edit.text().strip()

        if not value:
            return

        # One wildcard at the end only. The user can paste a value with
        # "*" already present and WT Studio will not duplicate it.
        value = value.rstrip("*").rstrip()
        value += "*"

        if self.from_edit.text() != value:
            self.from_edit.setText(
                value
            )
        else:
            self._sync_entry()

    # ------------------------------------------------------------
    # Entry sync
    # ------------------------------------------------------------

    def _sync_entry(self) -> None:
        if self.is_camo_card:
            self.entry.entry_type = (
                BLKEntryType.REPLACE
            )
            self.entry.is_camo = True
            self.entry.has_param = False
        else:
            if requires_replace_texture_rule(
                self.from_edit.text()
            ):
                self.entry.entry_type = BLKEntryType.REPLACE
            else:
                selected = self.type_combo.currentData()

                if selected is not None:
                    self.entry.entry_type = selected

            self.entry.is_camo = False
            self.entry.has_param = True

        self.entry.from_value = (
            self.from_edit.text().strip()
        )

        # Do not read text from the material combo here. "to:" must be the
        # actual exported filename, not the visible material label.
        if self._material_was_selected:
            target_stem = self.to_combo.currentData()

            if target_stem:
                extension = (
                    self.extension_combo.currentData()
                    or ".dds"
                )
                self.entry.to_value = (
                    f"{target_stem}{extension}"
                )

        self.changed.emit()

    @staticmethod
    def _extension_from_target(
        value: str,
    ) -> str:
        suffix = Path(value).suffix.casefold()

        if suffix in {
            ".dds",
            ".tga",
        }:
            return suffix

        return ".dds"

    @staticmethod
    def _stem_from_target(
        value: str,
    ) -> str:
        suffix = Path(value).suffix.casefold()

        if suffix in {
            ".dds",
            ".tga",
        }:
            return value[:-len(suffix)]

        return value


class BLKPanel(QWidget):
    """
    Structured editor for an existing War Thunder BLK.

    WT Studio never creates the BLK itself.
    """

    def __init__(
        self,
        *,
        material_collection=None,
        texture_collection=None,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.material_collection = (
            material_collection
        )
        self.texture_collection = (
            texture_collection
        )
        self.editor = BLKEditor()

        self.document: BLKDocument | None = None
        self.cards: list[BLKEntryCard] = []
        self.is_dirty = False
        self._saved_state = ()

        root = QVBoxLayout(self)

        header = QLabel("BLK EDITOR")
        header.setObjectName("sectionHeader")
        root.addWidget(header)

        file_row = QHBoxLayout()

        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText(
            "Open an existing .blk file"
        )

        self.open_button = QPushButton(
            "Open BLK"
        )
        self.open_button.setToolTip(
            "Open the existing War Thunder .blk file that will be edited "
            "in place."
        )
        file_row.addWidget(
            self.path_edit,
            1,
        )
        file_row.addWidget(
            self.open_button
        )

        root.addLayout(file_row)

        action_row = QHBoxLayout()

        self.save_button = QPushButton("Save")
        self.close_button = QPushButton("Close")

        self.save_button.setToolTip(
            "Save the current BLK changes back to the opened file."
        )
        self.close_button.setToolTip(
            "Close the currently opened BLK file."
        )

        self.save_button.setEnabled(False)
        self.close_button.setEnabled(False)

        action_row.addWidget(self.save_button)
        action_row.addWidget(self.close_button)

        root.addLayout(action_row)

        self.name_label = QLabel(
            'name:t="user" — protected'
        )
        self.name_label.setEnabled(False)
        root.addWidget(
            self.name_label
        )

        add_row = QHBoxLayout()

        self.add_rule_button = QPushButton(
            "Add Texture Rule"
        )
        self.add_camo_button = QPushButton(
            "Add Camo Rule"
        )

        self.add_rule_button.setToolTip(
            "Add a new texture rule with a from/to mapping."
        )
        self.add_camo_button.setToolTip(
            "Add a camo_skin_tex rule to the current BLK."
        )

        self.add_rule_button.setEnabled(False)
        self.add_camo_button.setEnabled(False)

        add_row.addWidget(
            self.add_rule_button
        )
        add_row.addWidget(
            self.add_camo_button
        )

        root.addLayout(add_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(
            self.cards_container
        )
        self.cards_layout.addStretch(1)

        scroll.setWidget(
            self.cards_container
        )
        root.addWidget(
            scroll,
            1,
        )

        self.reference_toggle = QToolButton()
        self.reference_toggle.setText("Original BLK Texture Names")
        self.reference_toggle.setCheckable(True)
        self.reference_toggle.setChecked(False)
        self.reference_toggle.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.reference_toggle.setArrowType(
            Qt.ArrowType.NoArrow
        )
        self.reference_toggle.setIcon(
            panel_chevron_icon(False)
        )
        self.reference_toggle.setIconSize(
            QSize(12, 12)
        )
        self.reference_toggle.setEnabled(False)
        self.reference_toggle.setToolTip(
            "Show texture names detected in the original BLK. "
            "Names in the list can be clicked to copy them."
        )
        root.addWidget(self.reference_toggle)

        self.reference_panel = QFrame()
        self.reference_panel.setFrameShape(
            QFrame.Shape.StyledPanel
        )
        self.reference_panel.setVisible(False)

        reference_layout = QVBoxLayout(self.reference_panel)

        reference_title = QLabel(
            "Original texture names recognised in the original BLK"
        )
        reference_title.setWordWrap(True)
        reference_layout.addWidget(reference_title)

        reference_help = QLabel(
            "Click a name to copy it to the clipboard."
        )
        reference_help.setWordWrap(True)
        reference_help.setEnabled(False)
        reference_layout.addWidget(reference_help)

        self.original_names_list = QListWidget()
        self.original_names_list.setMaximumHeight(220)
        reference_layout.addWidget(self.original_names_list)

        root.addWidget(self.reference_panel)

        self.imported_toggle = QToolButton()
        self.imported_toggle.setText(
            "Original Imported Texture Names"
        )
        self.imported_toggle.setCheckable(True)
        self.imported_toggle.setChecked(False)
        self.imported_toggle.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.imported_toggle.setArrowType(
            Qt.ArrowType.NoArrow
        )
        self.imported_toggle.setIcon(
            panel_chevron_icon(False)
        )
        self.imported_toggle.setIconSize(
            QSize(12, 12)
        )
        self.imported_toggle.setToolTip(
            "Show original names of imported textures for quick copying."
        )
        root.addWidget(self.imported_toggle)

        self.imported_panel = QFrame()
        self.imported_panel.setFrameShape(
            QFrame.Shape.StyledPanel
        )
        self.imported_panel.setVisible(False)

        imported_layout = QVBoxLayout(
            self.imported_panel
        )

        imported_title = QLabel(
            "Original imported texture names"
        )
        imported_title.setWordWrap(True)
        imported_layout.addWidget(
            imported_title
        )

        imported_help = QLabel(
            "Click a name to copy it to the clipboard."
        )
        imported_help.setWordWrap(True)
        imported_help.setEnabled(False)
        imported_layout.addWidget(
            imported_help
        )

        self.imported_names_list = QListWidget()
        self.imported_names_list.setMaximumHeight(220)
        imported_layout.addWidget(
            self.imported_names_list
        )

        root.addWidget(self.imported_panel)

        self.status_label = QLabel(
            "No BLK loaded."
        )
        self.status_label.setWordWrap(True)
        root.addWidget(
            self.status_label
        )

        self.open_button.clicked.connect(
            self.open_blk
        )
        self.save_button.clicked.connect(
            self.save_blk
        )
        self.close_button.clicked.connect(
            self.close_blk
        )
        self.reference_toggle.toggled.connect(
            self._toggle_reference_panel
        )
        self.original_names_list.itemClicked.connect(
            self._copy_original_name
        )
        self.imported_toggle.toggled.connect(
            self._toggle_imported_panel
        )
        self.imported_names_list.itemClicked.connect(
            self._copy_imported_name
        )
        self.add_rule_button.clicked.connect(
            self.add_regular_rule
        )
        self.add_camo_button.clicked.connect(
            self.add_camo_rule
        )

    @property
    def current_blk_path(self):
        return None if self.document is None else self.document.path

    def open_project_blk(self, path):
        document = self.editor.load(path)
        self.document = document
        self.path_edit.setText(str(document.path))
        self.name_label.setText(
            f'name:t="{document.name_value}" — protected'
        )
        self._set_original_names([
            entry.from_value
            for entry in document.entries
            if entry.from_value
        ])
        self.refresh_imported_names()
        self._rebuild_cards()
        self._refresh_save_button()
        self.close_button.setEnabled(True)
        self.reference_toggle.setEnabled(True)
        self.add_rule_button.setEnabled(True)
        self._refresh_camo_button()
        self.is_dirty = False
        self.status_label.setText(
            f"Loaded {len(document.entries)} texture rule(s). "
            "The original BLK will be edited in place."
        )

    def close_project_blk(self):
        if self.document is not None:
            self._close_blk_session()

    # --------------------------------------------------------
    # File operations
    # --------------------------------------------------------

    def open_blk(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Existing War Thunder BLK",
            PathSettings.session_working_dialog_path(),
            "War Thunder BLK (*.blk);;All Files (*.*)",
        )

        if not path:
            return

        try:
            document = self.editor.load(path)
        except BLKEditorError as error:
            QMessageBox.warning(
                self,
                "BLK Editor",
                str(error),
            )
            return

        PathSettings.set_session_working_directory(
            Path(document.path).parent
        )

        self.document = document
        self.path_edit.setText(
            str(document.path)
        )

        self.name_label.setText(
            f'name:t="{document.name_value}" — protected'
        )

        original_names = [
            entry.from_value
            for entry in document.entries
            if entry.from_value
        ]
        self._set_original_names(
            original_names
        )
        self.refresh_imported_names()

        self._rebuild_cards()

        self._refresh_save_button()
        self.close_button.setEnabled(True)
        self.reference_toggle.setEnabled(True)
        self.add_rule_button.setEnabled(True)
        self._refresh_camo_button()

        self._saved_state = self._current_state()
        self.is_dirty = False

        self.status_label.setText(
            f"Loaded {len(document.entries)} texture rule(s). "
            "The original BLK will be edited in place."
        )


    def save_blk(self) -> None:
        if self.document is None:
            return

        if not self.cards:
            self._refresh_save_button()
            self.status_label.setText(
                "Cannot save BLK: at least one texture rule is required."
            )
            QMessageBox.warning(
                self,
                "BLK Save",
                (
                    "The BLK cannot be saved without any texture rules.\n\n"
                    "Add at least one Texture Rule or Camo Rule before saving."
                ),
            )
            return

        # Ensure wildcard also applies if the user types and immediately
        # presses Save without moving focus first.
        for card in self.cards:
            card._ensure_from_wildcard()

        self._sync_document_entries()

        try:
            self.editor.save_in_place(
                self.document
            )
        except BLKEditorError as error:
            QMessageBox.warning(
                self,
                "BLK Save",
                str(error),
            )
            return
        except OSError as error:
            QMessageBox.warning(
                self,
                "BLK Save",
                f"Could not write the original BLK:\n{error}",
            )
            return

        self._saved_state = self._current_state()
        self.is_dirty = False

        self.status_label.setText(
            "BLK saved in place."
        )

        QMessageBox.information(
            self,
            "BLK Saved",
            "BLK saved successfully.",
            QMessageBox.StandardButton.Ok,
        )


    def close_blk(self) -> None:
        if self.document is None:
            return

        self._refresh_dirty_state()

        if self.is_dirty:
            answer = QMessageBox.question(
                self,
                "Unsaved BLK Changes",
                (
                    "The current BLK has unsaved changes.\n\n"
                    "Do you want to close without saving?"
                ),
                (
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                ),
                QMessageBox.StandardButton.No,
            )

            if answer != QMessageBox.StandardButton.Yes:
                return

        self._close_blk_session()

    def _close_blk_session(self) -> None:
        self.document = None
        self.is_dirty = False
        self._saved_state = ()

        for card in self.cards:
            card.setParent(None)
            card.deleteLater()

        self.cards.clear()
        self.path_edit.clear()
        self.name_label.setText(
            'name:t="user" — protected'
        )

        self.save_button.setEnabled(False)
        self.close_button.setEnabled(False)
        self.reference_toggle.setEnabled(False)
        self.reference_toggle.setIcon(
            panel_chevron_icon(False, disabled=True)
        )
        self.add_rule_button.setEnabled(False)
        self.add_camo_button.setEnabled(False)

        self.reference_toggle.setChecked(False)
        self.reference_panel.setVisible(False)
        self.original_names_list.clear()

        self.imported_toggle.setChecked(False)
        self.imported_panel.setVisible(False)
        self.imported_names_list.clear()

        self.status_label.setText(
            "BLK editing closed."
        )

    def _toggle_reference_panel(
        self,
        expanded: bool,
    ) -> None:
        self.reference_panel.setVisible(expanded)
        self.reference_toggle.setIcon(
            panel_chevron_icon(
                expanded,
                disabled=not self.reference_toggle.isEnabled(),
            )
        )

    def _set_original_names(
        self,
        names: list[str],
    ) -> None:
        self.original_names_list.clear()

        if names:
            self.original_names_list.addItems(names)
        else:
            self.original_names_list.addItem(
                "No texture names were recognised."
            )

    def _copy_original_name(
        self,
        item,
    ) -> None:
        value = item.text().strip()

        if (
            not value
            or value == "No texture names were recognised."
        ):
            return

        QGuiApplication.clipboard().setText(value)

        self.status_label.setText(
            f"Copied texture name: {value}"
        )


    def _toggle_imported_panel(
        self,
        expanded: bool,
    ) -> None:
        self.imported_panel.setVisible(
            expanded
        )
        self.imported_toggle.setIcon(
            panel_chevron_icon(expanded)
        )

    def refresh_imported_names(
        self,
    ) -> None:
        self.imported_names_list.clear()

        names: list[str] = []

        collection = self.texture_collection

        if collection is not None:
            try:
                textures = list(collection)
            except TypeError:
                textures = []

            for texture in textures:
                path = getattr(
                    texture,
                    "path",
                    "",
                )

                name = Path(
                    str(path)
                ).stem

                if not name:
                    name = str(
                        getattr(
                            texture,
                            "name",
                            "",
                        )
                    )

                if (
                    name
                    and name not in names
                ):
                    names.append(name)

        if names:
            self.imported_names_list.addItems(
                names
            )
        else:
            self.imported_names_list.addItem(
                "No imported texture names are available."
            )

    def _copy_imported_name(
        self,
        item,
    ) -> None:
        value = item.text().strip()

        if (
            not value
            or value
            == "No imported texture names are available."
        ):
            return

        QGuiApplication.clipboard().setText(
            value
        )

        self.status_label.setText(
            f"Copied imported texture name: {value}"
        )

    # --------------------------------------------------------
    # Cards
    # --------------------------------------------------------

    def add_regular_rule(self) -> None:
        if self.document is None:
            return

        entry = BLKTextureEntry(
            entry_type=BLKEntryType.REPLACE,
            has_param=True,
            is_camo=False,
        )

        self.document.entries.append(
            entry
        )
        self._add_card(
            entry,
            is_camo=False,
        )
        self._refresh_save_button()
        self._refresh_dirty_state()

    def add_camo_rule(self) -> None:
        if (
            self.document is None
            or self._has_camo_card()
        ):
            return

        entry = BLKTextureEntry(
            entry_type=BLKEntryType.REPLACE,
            from_value="",
            has_param=False,
            is_camo=True,
        )

        self.document.entries.insert(
            0,
            entry,
        )
        card = self._create_card(
            entry,
            is_camo=True,
        )

        self.cards.insert(
            0,
            card,
        )
        self.cards_layout.insertWidget(
            0,
            card,
        )

        self._refresh_camo_button()
        self._refresh_save_button()
        self._refresh_move_buttons()
        self._refresh_dirty_state()

    def _rebuild_cards(self) -> None:
        for card in self.cards:
            card.setParent(None)
            card.deleteLater()

        self.cards.clear()

        if self.document is None:
            return

        camo = [
            entry
            for entry in self.document.entries
            if entry.is_camo
        ]

        regular = [
            entry
            for entry in self.document.entries
            if not entry.is_camo
        ]

        for entry in camo[:1]:
            self._add_card(
                entry,
                is_camo=True,
            )

        for entry in regular:
            self._add_card(
                entry,
                is_camo=False,
            )

        self._refresh_camo_button()
        self._refresh_save_button()
        self._refresh_move_buttons()

    def _add_card(
        self,
        entry: BLKTextureEntry,
        *,
        is_camo: bool,
    ) -> None:
        card = self._create_card(
            entry,
            is_camo=is_camo,
        )

        self.cards.append(card)

        self.cards_layout.insertWidget(
            max(
                0,
                self.cards_layout.count() - 1,
            ),
            card,
        )
        self._refresh_move_buttons()

    def _create_card(
        self,
        entry: BLKTextureEntry,
        *,
        is_camo: bool,
    ) -> BLKEntryCard:
        card = BLKEntryCard(
            entry=entry,
            material_choices=(
                self._material_choices()
            ),
            is_camo_card=is_camo,
        )

        card.removeRequested.connect(
            self._remove_card
        )
        card.moveUpRequested.connect(
            self._move_card_up
        )
        card.moveDownRequested.connect(
            self._move_card_down
        )
        card.changed.connect(
            self._card_changed
        )

        return card

    def _remove_card(
        self,
        card: BLKEntryCard,
    ) -> None:
        if card not in self.cards:
            return

        self.cards.remove(card)

        card.setParent(None)
        card.deleteLater()

        self._sync_document_entries()
        self._refresh_camo_button()
        self._refresh_save_button()
        self._refresh_move_buttons()
        self._refresh_dirty_state()

    def _move_card_up(
        self,
        card: BLKEntryCard,
    ) -> None:
        self._move_regular_card(card, -1)

    def _move_card_down(
        self,
        card: BLKEntryCard,
    ) -> None:
        self._move_regular_card(card, 1)

    def _move_regular_card(
        self,
        card: BLKEntryCard,
        direction: int,
    ) -> None:
        if card not in self.cards or card.is_camo_card:
            return

        regular_cards = [
            current
            for current in self.cards
            if not current.is_camo_card
        ]

        try:
            regular_index = regular_cards.index(card)
        except ValueError:
            return

        target_regular_index = regular_index + direction
        if not (0 <= target_regular_index < len(regular_cards)):
            return

        target_card = regular_cards[target_regular_index]
        card_index = self.cards.index(card)
        target_index = self.cards.index(target_card)

        self.cards[card_index], self.cards[target_index] = (
            self.cards[target_index],
            self.cards[card_index],
        )

        self.cards_layout.removeWidget(card)
        self.cards_layout.insertWidget(
            target_index,
            card,
        )

        self._sync_document_entries()
        self._refresh_move_buttons()
        self._refresh_dirty_state()

    def _card_changed(self) -> None:
        self._sync_document_entries()
        self._refresh_dirty_state()

    def _sync_document_entries(self) -> None:
        if self.document is None:
            return

        entries = [
            card.entry
            for card in self.cards
        ]

        camo = [
            entry
            for entry in entries
            if entry.is_camo
        ]

        regular = [
            entry
            for entry in entries
            if not entry.is_camo
        ]

        self.document.entries = (
            camo[:1]
            + regular
        )

    def refresh_materials(self) -> None:
        choices = self._material_choices()

        for card in self.cards:
            card.set_material_choices(
                choices
            )

    def has_unsaved_changes(self) -> bool:
        if self.document is None:
            self.is_dirty = False
            return False

        self._sync_document_entries()

        try:
            prospective_text = (
                self.editor._rebuild_document(
                    self.document
                )
            )
        except Exception:
            # Fall back to semantic comparison only if reconstruction
            # itself cannot be evaluated.
            self._refresh_dirty_state()
            return self.is_dirty

        self.is_dirty = (
            prospective_text
            != self.document.original_text
        )

        return self.is_dirty

    def _refresh_dirty_state(self) -> None:
        if self.document is None:
            self.is_dirty = False
            return

        self.is_dirty = (
            self._current_state()
            != self._saved_state
        )

    def _current_state(self):
        state = []

        for card in self.cards:
            entry = card.entry

            state.append(
                (
                    str(
                        getattr(
                            entry.entry_type,
                            "value",
                            entry.entry_type,
                        )
                    ),
                    entry.from_value.strip(),
                    entry.to_value.strip(),
                    bool(entry.is_camo),
                    bool(entry.has_param),
                )
            )

        return tuple(state)

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    def _has_camo_card(self) -> bool:
        return any(
            card.is_camo_card
            for card in self.cards
        )

    def _refresh_camo_button(self) -> None:
        self.add_camo_button.setEnabled(
            self.document is not None
            and not self._has_camo_card()
        )

    def _refresh_move_buttons(self) -> None:
        regular_cards = [
            card
            for card in self.cards
            if not card.is_camo_card
        ]

        last_index = len(regular_cards) - 1

        for index, card in enumerate(regular_cards):
            card.set_move_availability(
                can_move_up=index > 0,
                can_move_down=index < last_index,
            )

    def _refresh_save_button(self) -> None:
        can_save = (
            self.document is not None
            and bool(self.cards)
        )
        self.save_button.setEnabled(can_save)

        if self.document is None:
            self.save_button.setToolTip(
                "Save the current BLK changes back to the opened file."
            )
        elif not self.cards:
            self.save_button.setToolTip(
                "Add at least one Texture Rule or Camo Rule before saving."
            )
        else:
            self.save_button.setToolTip(
                "Save the current BLK changes back to the opened file."
            )

    def _material_choices(
        self,
    ) -> list[BLKMaterialChoice]:
        collection = self.material_collection

        if collection is None:
            return []

        try:
            materials = collection.materials
        except AttributeError:
            try:
                materials = list(collection)
            except TypeError:
                return []

        choices: list[BLKMaterialChoice] = []

        for material in materials:
            raw_name = str(
                getattr(
                    material,
                    "name",
                    "",
                )
            ).strip()

            if not raw_name:
                continue

            # Match MaterialExporter filename sanitisation.
            clean_name = re.sub(
                r'[<>:"/\\|?*\x00-\x1f]+',
                "_",
                raw_name,
            ).strip(" ._")

            if not clean_name:
                material_id = str(
                    getattr(
                        material,
                        "material_id",
                        "",
                    )
                )
                clean_name = (
                    f"material_{material_id[:6]}"
                )

            suffix = self._material_suffix(
                material
            )

            target_stem = clean_name

            if (
                suffix
                and not target_stem.casefold().endswith(
                    suffix
                )
            ):
                target_stem += suffix

            display_name = raw_name

            choice = BLKMaterialChoice(
                display_name=display_name,
                target_stem=target_stem,
            )

            if not any(
                existing.target_stem.casefold()
                == choice.target_stem.casefold()
                for existing in choices
            ):
                choices.append(choice)

        return choices

    @staticmethod
    def _material_suffix(
        material,
    ) -> str:
        material_type = getattr(
            material,
            "material_type",
            None,
        )

        type_name = str(
            getattr(
                material_type,
                "name",
                material_type,
            )
        ).upper()

        if type_name.endswith("COLOR"):
            return "_c"

        if type_name.endswith("NORMAL"):
            return "_n"

        if type_name.endswith("AO"):
            return "_ao"

        return ""
