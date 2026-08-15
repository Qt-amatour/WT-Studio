from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ui.icons import panel_chevron_icon


class TextureInfoPanel(QWidget):
    channelModeChanged = Signal(str)

    CHANNELS = (
        ("Composite", "composite"),
        ("R", "r"),
        ("G", "g"),
        ("B", "b"),
        ("Alpha", "alpha"),
    )

    def __init__(self):
        super().__init__()

        self.setObjectName("textureInfoPanel")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.toggle = QToolButton()
        self.toggle.setObjectName("textureInfoToggle")
        self.toggle.setText(
            "TEXTURE INFORMATION"
        )
        self.toggle.setCheckable(True)
        self.toggle.setChecked(False)
        self.toggle.setArrowType(
            Qt.ArrowType.NoArrow
        )
        self.toggle.setIcon(
            panel_chevron_icon(False)
        )
        self.toggle.setIconSize(
            QSize(12, 12)
        )
        self.toggle.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        root.addWidget(self.toggle)

        self.content = QFrame()
        self.content.setFrameShape(
            QFrame.Shape.StyledPanel
        )
        self.content.setVisible(False)

        content_layout = QVBoxLayout(
            self.content
        )

        form = QFormLayout()

        self.value_labels: dict[str, QLabel] = {}

        fields = (
            ("texture", "Texture"),
            ("type", "Type"),
            ("resolution", "Resolution"),
            ("compression", "Compression"),
            ("mipmaps", "MipMaps"),
            ("alpha", "Alpha"),
            ("resource", "Resource"),
            ("file_size", "File Size"),
        )

        for key, title in fields:
            label = QLabel("-")
            label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            self.value_labels[key] = label
            form.addRow(
                f"{title}:",
                label,
            )

        content_layout.addLayout(form)

        channel_title = QLabel(
            "CHANNEL PREVIEW"
        )
        channel_title.setObjectName("sectionHeader")
        content_layout.addWidget(
            channel_title
        )

        channel_row = QHBoxLayout()
        self.channel_buttons: dict[
            str,
            QPushButton,
        ] = {}

        for title, mode in self.CHANNELS:
            button = QPushButton(title)
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked=False, value=mode:
                self.set_channel_mode(value)
            )
            self.channel_buttons[mode] = button
            channel_row.addWidget(button)

        content_layout.addLayout(
            channel_row
        )

        self.channel_buttons[
            "composite"
        ].setChecked(True)

        root.addWidget(self.content)

        self.toggle.toggled.connect(
            self._set_expanded
        )

    def set_texture(self, texture) -> None:
        self.value_labels["texture"].setText(
            self._texture_name(texture)
        )
        self.value_labels["type"].setText(
            self._texture_type(texture)
        )
        self.value_labels["resolution"].setText(
            self._resolution(texture)
        )
        self.value_labels["compression"].setText(
            self._compression(texture)
        )
        self.value_labels["mipmaps"].setText(
            self._mipmaps(texture)
        )
        self.value_labels["alpha"].setText(
            self._alpha(texture)
        )
        self.value_labels["resource"].setText(
            str(getattr(texture, "path", "-"))
        )
        self.value_labels["file_size"].setText(
            self._file_size(texture)
        )

        self.set_channel_mode(
            "composite"
        )

    def clear(self) -> None:
        for label in self.value_labels.values():
            label.setText("-")

        self.set_channel_mode(
            "composite"
        )

    def set_channel_controls_enabled(
        self,
        enabled: bool,
    ) -> None:
        for button in self.channel_buttons.values():
            button.setEnabled(enabled)

    def set_channel_mode(
        self,
        mode: str,
    ) -> None:
        if mode not in self.channel_buttons:
            mode = "composite"

        for key, button in self.channel_buttons.items():
            button.blockSignals(True)
            button.setChecked(
                key == mode
            )
            button.blockSignals(False)

        self.channelModeChanged.emit(mode)

    def _set_expanded(
        self,
        expanded: bool,
    ) -> None:
        self.content.setVisible(expanded)
        self.toggle.setIcon(
            panel_chevron_icon(expanded)
        )

    @staticmethod
    def _texture_name(texture) -> str:
        file_info = getattr(
            texture,
            "file",
            None,
        )
        return str(
            getattr(
                file_info,
                "name",
                getattr(texture, "name", "-"),
            )
        )

    @staticmethod
    def _texture_type(texture) -> str:
        role = getattr(
            getattr(texture, "pbr", None),
            "effective_texture_role",
            None,
        )

        if role is None:
            role = getattr(
                texture,
                "texture_type",
                None,
            )

        return str(
            getattr(
                role,
                "display_name",
                getattr(role, "name", role or "-"),
            )
        )

    @staticmethod
    def _resolution(texture) -> str:
        info = getattr(
            texture,
            "image_info",
            None,
        )

        width = int(
            getattr(info, "width", 0) or 0
        )
        height = int(
            getattr(info, "height", 0) or 0
        )

        return (
            f"{width} × {height}"
            if width and height
            else "-"
        )

    @staticmethod
    def _compression(texture) -> str:
        dds = getattr(
            texture,
            "dds",
            None,
        )

        for attribute in (
            "compression",
            "compression_name",
            "format_name",
            "fourcc",
        ):
            value = getattr(
                dds,
                attribute,
                None,
            )

            if value:
                return str(value)

        return "-"

    @staticmethod
    def _mipmaps(texture) -> str:
        image_info = getattr(
            texture,
            "image_info",
            None,
        )
        dds = getattr(
            texture,
            "dds",
            None,
        )

        value = (
            getattr(
                image_info,
                "mipmap_count",
                None,
            )
            or getattr(
                dds,
                "mipmap_count",
                None,
            )
        )

        return str(value or "-")

    @staticmethod
    def _alpha(texture) -> str:
        info = getattr(
            texture,
            "image_info",
            None,
        )

        has_alpha = getattr(
            info,
            "has_alpha",
            None,
        )

        if has_alpha is None:
            image = getattr(
                texture,
                "image",
                None,
            )
            has_alpha = (
                image is not None
                and "A" in image.getbands()
            )

        return "Yes" if has_alpha else "No"

    @staticmethod
    def _file_size(texture) -> str:
        file_info = getattr(
            texture,
            "file",
            None,
        )

        size = (
            getattr(
                file_info,
                "size_bytes",
                None,
            )
            or getattr(
                file_info,
                "file_size",
                None,
            )
        )

        if not size:
            return "-"

        size = int(size)

        if size >= 1024 * 1024:
            return f"{size / (1024 * 1024):.2f} MB"

        if size >= 1024:
            return f"{size / 1024:.1f} KB"

        return f"{size} B"
