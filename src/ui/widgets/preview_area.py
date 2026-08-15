from __future__ import annotations

from PIL import Image

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.texture_info_panel import TextureInfoPanel
from ui.widgets.texture_preview import TexturePreview


class PreviewArea(QWidget):
    def __init__(self):
        super().__init__()

        self.setObjectName("centralPreviewArea")

        self._current_texture = None
        self._source_image = None
        self._channel_mode = "composite"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.texture_preview = TexturePreview()
        self.texture_info = TextureInfoPanel()

        layout.addWidget(
            self.texture_preview,
            1,
        )

        self.zoom_bar = QWidget()
        self.zoom_bar.setObjectName("zoomBar")
        zoom_layout = QHBoxLayout(
            self.zoom_bar
        )
        zoom_layout.setContentsMargins(
            6,
            2,
            6,
            2,
        )
        zoom_layout.setSpacing(4)

        self.fit_button = QPushButton("Fit")
        self.zoom_50_button = QPushButton("50%")
        self.zoom_100_button = QPushButton("100%")
        self.zoom_200_button = QPushButton("200%")

        self.zoom_label = QLabel("100%")
        self.zoom_label.setObjectName("zoomValueLabel")
        self.zoom_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        # Keep the complete zoom control group visually centered.
        zoom_layout.addStretch(1)
        zoom_layout.addWidget(self.fit_button)
        zoom_layout.addWidget(self.zoom_50_button)
        zoom_layout.addWidget(self.zoom_100_button)
        zoom_layout.addWidget(self.zoom_200_button)
        zoom_layout.addWidget(self.zoom_label)
        zoom_layout.addStretch(1)

        layout.addWidget(self.zoom_bar)
        layout.addWidget(self.texture_info)

        self.fit_button.clicked.connect(
            self.texture_preview.fit_to_view
        )
        self.zoom_50_button.clicked.connect(
            lambda:
            self.texture_preview.set_zoom_percent(50.0)
        )
        self.zoom_100_button.clicked.connect(
            lambda:
            self.texture_preview.set_zoom_percent(100.0)
        )
        self.zoom_200_button.clicked.connect(
            lambda:
            self.texture_preview.set_zoom_percent(200.0)
        )

        self.texture_preview.zoomChanged.connect(
            self._update_zoom_label
        )
        self.texture_info.channelModeChanged.connect(
            self._set_channel_mode
        )

    def show_texture(self, texture):
        self._current_texture = texture
        self._source_image = getattr(
            texture,
            "image",
            None,
        )

        self.texture_info.set_channel_controls_enabled(
            True
        )
        self.texture_info.set_texture(
            texture
        )
        self._channel_mode = "composite"
        self._refresh_texture_preview()

    def show_material(self, material):
        self._current_texture = None
        self._source_image = None

        # Clear texture-only controls first. clear() emits the Composite
        # channel signal, so calling it after show_image() would erase the
        # material preview.
        self.texture_info.clear()
        self.texture_info.set_channel_controls_enabled(
            False
        )

        if material is None:
            self.texture_preview.clear_preview(
                "No material selected"
            )
        elif material.preview_image is None:
            self.texture_preview.clear_preview(
                material.build_error
                or "Assign material textures to build preview"
            )
        else:
            self.texture_preview.show_image(
                material.preview_image
            )

    def clear_preview(self):
        self._current_texture = None
        self._source_image = None
        self.texture_preview.clear_preview(
            "No texture selected"
        )
        self.texture_info.clear()
        self.texture_info.set_channel_controls_enabled(
            False
        )

    def _set_channel_mode(
        self,
        mode: str,
    ) -> None:
        if self._current_texture is None:
            return

        self._channel_mode = mode
        self._refresh_texture_preview()

    def _refresh_texture_preview(self) -> None:
        image = self._source_image

        if image is None:
            self.texture_preview.clear_preview(
                "Preview unavailable"
            )
            return

        preview = self._build_preview_image(
            image,
            self._channel_mode,
            force_opaque=(
                self._is_color_texture(
                    self._current_texture
                )
            ),
        )

        self.texture_preview.show_image(
            preview
        )

    @staticmethod
    def _build_preview_image(
        image: Image.Image,
        mode: str,
        *,
        force_opaque: bool,
    ) -> Image.Image:
        rgba = image.convert("RGBA")

        if mode in {
            "r",
            "g",
            "b",
            "alpha",
        }:
            channel_index = {
                "r": 0,
                "g": 1,
                "b": 2,
                "alpha": 3,
            }[mode]

            channel = rgba.getchannel(
                channel_index
            )

            # Grayscale RGB keeps the channel clearly visible and avoids
            # accidental transparency in the viewer.
            return Image.merge(
                "RGBA",
                (
                    channel,
                    channel,
                    channel,
                    Image.new(
                        "L",
                        rgba.size,
                        255,
                    ),
                ),
            )

        if force_opaque:
            red, green, blue, _ = rgba.split()

            return Image.merge(
                "RGBA",
                (
                    red,
                    green,
                    blue,
                    Image.new(
                        "L",
                        rgba.size,
                        255,
                    ),
                ),
            )

        return rgba.copy()

    @staticmethod
    def _is_color_texture(texture) -> bool:
        if texture is None:
            return False

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

        role_name = str(
            getattr(
                role,
                "name",
                role,
            )
        ).casefold()

        role_value = str(
            getattr(
                role,
                "value",
                "",
            )
        ).casefold()

        source_name = str(
            getattr(
                getattr(texture, "file", None),
                "name",
                getattr(texture, "name", ""),
            )
        ).casefold()

        return (
            "color" in role_name
            or role_name in {"c", "_c"}
            or "color" in role_value
            or source_name.endswith("_c")
            or source_name.endswith("_c.dds")
            or source_name.endswith("_c.tga")
            or source_name.endswith("_c.png")
        )

    def _update_zoom_label(
        self,
        value: float,
    ):
        self.zoom_label.setText(
            f"{value:.0f}%"
        )
