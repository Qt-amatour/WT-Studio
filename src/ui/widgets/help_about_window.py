from __future__ import annotations

from PySide6.QtCore import QRectF, QSettings, Qt
from PySide6.QtGui import (
    QCloseEvent,
    QPainter,
    QPixmap,
    QShowEvent,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui.icons import icon_path
from ui.widgets.window_chrome import FramelessDialog, WindowTitleBar


ABOUT_TEXT = """
WT Studio is an independent desktop toolkit for preparing War Thunder
user-skin textures. It reads source DDS and TGA files, separates packed
texture data into an editable PBR workflow, assembles finished textures for
game use, and edits the skin's original BLK configuration in place.

Imported files are not moved or duplicated. WT Studio reads them from their
existing locations and creates new files only when you explicitly export a
texture or save a change.
""".strip()

PBR_WORKFLOW_TEXT = """
Use this tab to import DDS or TGA source textures created by the in-game
user-skin workflow or exported from Asset Viewer. Keeping the original texture
name helps WT Studio identify the correct workflow automatically.

Recognized filename suffixes are <b>_c</b>, <b>_n</b>, and <b>_ao</b>. When a
filename has no recognized suffix, right-click the imported texture and assign
its type manually.

<b>[COLOR]</b> identifies a color/albedo texture, including alpha when the
source contains it. <b>[NORMAL]</b> identifies the packed normal/PBR texture
used for roughness or smoothness, normal data, and metallic information.
<b>[AO]</b> identifies an ambient-occlusion texture.

Leave <b>Export normal map as OpenGL</b> disabled for the standard DirectX
workflow. Enable it when the exported RGB normal map will be edited in an
OpenGL normal-map workflow such as an OpenGL-configured Substance project.
""".strip()

DDS_MATERIALS_TEXT = """
Use this tab to build final DDS or TGA materials from your edited PBR maps.
The material name becomes the base name of the exported file. WT Studio adds
the correct <b>_c</b>, <b>_n</b>, or <b>_ao</b> suffix for the selected
material type and replaces spaces in the name with underscores.

Keep imported PBR files in a stable location. WT Studio stores their paths, so
the <b>Reload</b> action can read updated versions of the same files while you
continue working in an external editor.

For packed <b>_n</b> materials, enable <b>OpenGL normal map</b> when the
selected RGB normal source uses the OpenGL convention. WT Studio converts its
Y component while packing the final game texture. Leave it disabled for
DirectX normal-map sources.
""".strip()

NEW_ASSETS_TEXT = """
Use this tab to build lossless TGA source textures for new/modded assets that
will be processed through Asset Viewer. NEW ASSETS is separate from the normal
UserSkins DDS MATERIALS workflow and has its own export directory.

The available material types are <b>Color (_c)</b>, <b>Packed Normal (_n)</b>,
and <b>Ambient Occlusion (_ao)</b>. WT Studio automatically adds the selected
suffix and the <b>.tga</b> extension, and replaces spaces in the material name
with underscores.

For <b>_c</b>, Albedo supplies RGB and Alpha / Mask is optional; when no alpha
source is assigned, the exported alpha value is 255. Enable <b>OpenGL normal
map</b> only when the input RGB normal map uses the OpenGL Y convention.
<b>_ao</b> is exported as a lossless single-channel 8-bit grayscale TGA.

The NEW ASSETS export directory is intentionally independent from the normal
WT Studio Working and Output paths. A clean session starts with this field
empty. When a project is saved as <b>.wts</b>, the selected directory and NEW
ASSETS material setup are stored with that project and restored when it opens.
""".strip()


BLK_EDITOR_TEXT = """
Use this tab to edit the original <b>.blk</b> file located in the user-skin
folder. Each rule can use <b>SET</b> or <b>REPLACE</b>, and can target a DDS or
TGA output. Rules whose <b>from</b> texture ends in <b>_n</b> or <b>_ao</b>
are automatically locked to <b>REPLACE</b> to prevent an invalid rule type.

The <b>from</b> field contains the original game texture name that will be
replaced. The detected names from the base BLK file and the imported textures
are available in <b>Original BLK Texture Names</b> and
<b>Original Imported Texture Names</b> at the bottom of the editor.

The <b>to</b> field selects the WT Studio material that will become the new
texture. You do not need to assign a new material to every existing BLK rule.
Any original rule that is left without a new material selection remains
unchanged, so you can replace only the textures you actually want to modify
without rebuilding the rest of the file.

The final order of rules in the BLK file follows the order of the rule panels
in the editor.
""".strip()

WTS_FILES_TEXT = """
WT Studio project files use the <b>.wts</b> extension. A WTS file stores the
project configuration, selected options, and paths to the files used by the
workflow.

It does not contain, copy, or archive the referenced textures. Moving or
renaming source files after saving a project can therefore break those stored
references.
""".strip()

TECHNICAL_TEXT = """
WT Studio is an independent open-source project built with Python and PySide6.
Texture encoding uses the bundled DirectXTex <b>texconv</b> executable; no
external NVIDIA Texture Tools installation is required or used as a fallback.

The current game-export formats are TGA, DDS ARGB 8.8.8.8, BC1, and BC3.
BC7 files can be used as source material, but BC7 game export is intentionally
disabled. License information and third-party notices are included with the
application.

WT Studio is a community tool and is not affiliated with, endorsed by, or
supported by Gaijin Entertainment. War Thunder and related names and marks
belong to their respective owners.
""".strip()


class HelpAboutWindow(FramelessDialog):
    """Scrollable WT Studio help and technical information window."""

    SETTINGS_ORGANIZATION = "WTStudio"
    SETTINGS_APPLICATION = "WTStudio"
    DONT_SHOW_KEY = "help_about/dont_show_automatically"

    WINDOW_WIDTH = 920
    WINDOW_HEIGHT = 700

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.settings = QSettings(
            self.SETTINGS_ORGANIZATION,
            self.SETTINGS_APPLICATION,
        )

        self.setObjectName("helpAboutWindow")
        self.setWindowTitle("Help")
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

        body = QWidget()
        body.setObjectName("helpAboutBody")
        outer.addWidget(body, 1)

        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(34, 22, 28, 22)
        body_layout.setSpacing(16)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("helpScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll_area.setFrameShape(
            QFrame.Shape.NoFrame
        )
        body_layout.addWidget(self.scroll_area, 1)

        content = QWidget()
        content.setObjectName("helpContent")
        self.scroll_area.setWidget(content)

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(8, 4, 20, 20)
        content_layout.setSpacing(0)

        content_layout.addLayout(
            self._build_about_section()
        )
        content_layout.addSpacing(26)

        self._add_text_section(
            content_layout,
            "PBR WORKFLOW",
            PBR_WORKFLOW_TEXT,
        )
        self._add_text_section(
            content_layout,
            "DDS MATERIALS",
            DDS_MATERIALS_TEXT,
        )
        self._add_text_section(
            content_layout,
            "BLK EDITOR",
            BLK_EDITOR_TEXT,
        )
        self._add_text_section(
            content_layout,
            "NEW ASSETS",
            NEW_ASSETS_TEXT,
        )
        self._add_text_section(
            content_layout,
            "WTS FILES",
            WTS_FILES_TEXT,
        )
        self._add_text_section(
            content_layout,
            "TECHNICAL & OPEN-SOURCE NOTES",
            TECHNICAL_TEXT,
            final=True,
        )

        footer = QHBoxLayout()
        footer.setContentsMargins(2, 0, 0, 0)
        footer.setSpacing(14)

        self.dont_show_checkbox = QCheckBox(
            "Don't show this window automatically again"
        )
        self.dont_show_checkbox.setObjectName(
            "helpAboutDontShowCheckBox"
        )
        self.dont_show_checkbox.setChecked(
            self.dont_show_automatically()
        )
        footer.addWidget(self.dont_show_checkbox)
        footer.addStretch(1)

        self.ok_button = QPushButton("OK")
        self.ok_button.setObjectName("helpAboutOkButton")
        self.ok_button.setFixedSize(128, 42)
        self.ok_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.ok_button.setAutoDefault(False)
        self.ok_button.setDefault(False)
        self.ok_button.clicked.connect(self.accept)
        footer.addWidget(self.ok_button)

        body_layout.addLayout(footer)

    def _build_about_section(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(30)

        icon_label = QLabel()
        icon_label.setObjectName("helpAboutIllustration")
        icon_label.setFixedSize(170, 220)
        icon_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        icon_label.setPixmap(
            self._render_svg_contained(
                "help_snail.svg",
                width=170,
                height=220,
            )
        )
        row.addWidget(
            icon_label,
            0,
            Qt.AlignmentFlag.AlignTop,
        )

        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 10, 0, 0)
        text_column.setSpacing(12)

        title = self._section_title("ABOUT")
        text_column.addWidget(title)

        body = self._section_body(ABOUT_TEXT)
        text_column.addWidget(body)
        text_column.addStretch(1)

        row.addLayout(text_column, 1)
        return row

    @staticmethod
    def _render_svg_contained(
        filename: str,
        *,
        width: int,
        height: int,
    ) -> QPixmap:
        """Render SVG without stretching its original aspect ratio."""
        renderer = QSvgRenderer(
            str(icon_path(filename))
        )

        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)

        if not renderer.isValid():
            return pixmap

        source_box = renderer.viewBoxF()
        if (
            source_box.width() <= 0.0
            or source_box.height() <= 0.0
        ):
            return pixmap

        scale = min(
            width / source_box.width(),
            height / source_box.height(),
        )
        render_width = source_box.width() * scale
        render_height = source_box.height() * scale

        target = QRectF(
            (width - render_width) / 2.0,
            (height - render_height) / 2.0,
            render_width,
            render_height,
        )

        painter = QPainter(pixmap)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )
        renderer.render(painter, target)
        painter.end()

        return pixmap

    def _add_text_section(
        self,
        layout: QVBoxLayout,
        title_text: str,
        body_text: str,
        *,
        final: bool = False,
    ) -> None:
        layout.addWidget(
            self._section_title(title_text)
        )
        layout.addSpacing(9)
        layout.addWidget(
            self._section_body(body_text)
        )

        if not final:
            layout.addSpacing(26)

    @staticmethod
    def _section_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("helpSectionTitle")
        label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        return label

    @staticmethod
    def _section_body(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("helpSectionBody")
        label.setTextFormat(
            Qt.TextFormat.RichText
        )
        label.setWordWrap(True)
        label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignTop
        )
        label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        return label

    @classmethod
    def dont_show_automatically(cls) -> bool:
        settings = QSettings(
            cls.SETTINGS_ORGANIZATION,
            cls.SETTINGS_APPLICATION,
        )
        return settings.value(
            cls.DONT_SHOW_KEY,
            False,
            type=bool,
        )

    def _save_preference(self) -> None:
        self.settings.setValue(
            self.DONT_SHOW_KEY,
            self.dont_show_checkbox.isChecked(),
        )
        self.settings.sync()

    def accept(self) -> None:
        self._save_preference()
        super().accept()

    def reject(self) -> None:
        self._save_preference()
        super().reject()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_preference()
        event.accept()

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
