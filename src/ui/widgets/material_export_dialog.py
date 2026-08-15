from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)
from ui.widgets.downward_combo_box import DownwardComboBox
from ui.widgets.window_chrome import (
    FramelessDialog,
    WindowTitleBar,
)

from app.services.material_exporter import (
    MaterialExportFormat,
    MaterialExportOptions,
    MipmapMode,
)


class MaterialExportDialog(FramelessDialog):
    def __init__(
        self,
        *,
        initial_directory: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("materialExportDialog")
        self.setWindowTitle("Export All Materials")
        self.resize(620, 320)
        self.setMinimumWidth(520)

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

        self.format_combo = DownwardComboBox()

        visible_formats = (
            MaterialExportFormat.TGA,
            MaterialExportFormat.DDS_ARGB_8888,
            MaterialExportFormat.DDS_BC1,
            MaterialExportFormat.DDS_BC3,
        )

        for export_format in visible_formats:
            self.format_combo.addItem(
                export_format.display_name,
                export_format,
            )

        self.mipmap_combo = DownwardComboBox()
        for mipmap_mode in MipmapMode:
            self.mipmap_combo.addItem(
                mipmap_mode.display_name,
                mipmap_mode,
            )

        directory_row = QHBoxLayout()
        self.directory_edit = QLineEdit(initial_directory)
        self.directory_edit.setPlaceholderText("Select output folder")

        browse_button = QPushButton("Browse")

        directory_row.addWidget(self.directory_edit, 1)
        directory_row.addWidget(browse_button)

        self.mipmap_note = QLabel(
            "4096 × 4096 DDS: 13 levels in total, ending at 1 × 1."
        )
        self.mipmap_note.setWordWrap(True)

        self.bc_note = QLabel(
            "BC1 and BC3 are lossy block-compressed DDS formats."
        )
        self.bc_note.setWordWrap(True)

        self.overwrite_check = QCheckBox("Overwrite existing files")
        self.overwrite_check.setChecked(True)

        self.verify_check = QCheckBox(
            "Verify lossless pixel data after export (TGA / ARGB)"
        )
        self.verify_check.setChecked(True)

        form.addRow("Format:", self.format_combo)
        form.addRow("Mipmaps:", self.mipmap_combo)
        form.addRow("", self.mipmap_note)
        form.addRow("", self.bc_note)
        form.addRow("Output folder:", directory_row)
        form.addRow("", self.overwrite_check)
        form.addRow("", self.verify_check)

        self.validation_note = QLabel(
            "DDS header, format, mip chain and payload size are always "
            "validated before the final file replaces any existing export."
        )
        self.validation_note.setWordWrap(True)
        form.addRow("", self.validation_note)

        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.setObjectName("materialExportButtonBox")
        buttons.setCenterButtons(True)

        export_button = buttons.button(
            QDialogButtonBox.StandardButton.Ok
        )
        cancel_button = buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        )

        export_button.setText("Export")

        for button in (export_button, cancel_button):
            button.setObjectName("dialogActionButton")
            button.setMinimumWidth(160)
            button.setMinimumHeight(30)
            button.setAutoDefault(False)
            button.setDefault(False)

        root.addWidget(buttons)

        browse_button.clicked.connect(self._browse)
        self.format_combo.currentIndexChanged.connect(
            self._format_changed
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        self._format_changed()

    def options(self) -> MaterialExportOptions:
        return MaterialExportOptions(
            output_directory=Path(self.directory_edit.text()),
            export_format=self.format_combo.currentData(),
            mipmap_mode=self.mipmap_combo.currentData(),
            overwrite=self.overwrite_check.isChecked(),
            verify_pixels=self.verify_check.isChecked(),
        )

    def _format_changed(self) -> None:
        export_format = self.format_combo.currentData()

        is_dds = (
            export_format is not None
            and export_format.is_dds
        )

        is_bc = (
            export_format is not None
            and export_format.is_compressed
        )

        self.mipmap_combo.setEnabled(is_dds)
        self.mipmap_note.setEnabled(is_dds)
        self.bc_note.setVisible(is_bc)
        self.verify_check.setEnabled(not is_bc)

        if not is_dds:
            index = self.mipmap_combo.findData(
                MipmapMode.DO_NOT_GENERATE
            )
            if index >= 0:
                self.mipmap_combo.setCurrentIndex(index)

    def _browse(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Select Material Export Folder",
            self.directory_edit.text(),
            QFileDialog.Option.ShowDirsOnly,
        )

        if selected:
            self.directory_edit.setText(selected)

    def _accept(self) -> None:
        if not self.directory_edit.text().strip():
            self.directory_edit.setFocus()
            return

        self.accept()
