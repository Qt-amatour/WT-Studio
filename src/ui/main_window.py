# ============================================================
# WT Studio
# Version : 0.1.0
#
# File:
# main_window.py
#
# Description:
# Main application window
#
# ============================================================

from __future__ import annotations

from pathlib import Path
import hashlib
import re

from PySide6.QtCore import QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QFrame,
    QLabel,
    QApplication,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.models.texture_info import TextureInfo
from app.version import APP_FULL_NAME
from app.project_manager import ProjectManager
from app.services.material_exporter import (
    MaterialBatchExportResult,
    MaterialExporter,
)
from app.services.new_asset_exporter import (
    NewAssetBatchExportResult,
    NewAssetExporter,
)
from app.services.texture_loader import TextureLoader
from app.services.pbr_converter import(
    PBRBatchConversionResult,
    PBRConverter,
)
from app.services.project_file_service import (
    ProjectFileError,
    ProjectFileService,
)
from app.services.path_settings import (
    PathSettings,
)
from app.services.dds_validator import (
    DDSValidationError,
    DDSValidator,
)
from app.services.texture_engine import TextureEngineResolver

from ui.widgets.message_box import QMessageBox
from ui.widgets.blk_panel import BLKPanel
from ui.operation_runner import OperationRunner
from ui.widgets.import_list import ImportList
from ui.widgets.material_export_dialog import MaterialExportDialog
from ui.widgets.materials_panel import MaterialsPanel
from ui.widgets.new_assets_panel import NewAssetsPanel
from ui.widgets.pbr_workflow import PBRWorkflow
from ui.widgets.preview_area import PreviewArea
from ui.widgets.project_identity_dialog import ProjectIdentityDialog
from ui.widgets.project_browser import ProjectBrowser
from ui.widgets.operation_progress_dialog import OperationProgressDialog
from ui.widgets.window_chrome import (
    FramelessMainWindow,
    WindowTitleBar,
)


class MainWindow(FramelessMainWindow):
    quickStartRequested = Signal()
    helpAboutRequested = Signal()
    startupActionFinished = Signal()

    """
    Główne okno WT Studio.

    Lewa strona:

        Project Library
        ----------------
        Imported Textures

    Środkowy obszar:

        Texture Preview
        Texture Information

    Prawa strona:

        PBR Workflow
        DDS Materials
        BLK Editor
    """

    LEFT_PANEL_MINIMUM_WIDTH = 260
    LEFT_PANEL_DEFAULT_WIDTH = 300
    WORKSPACE_MINIMUM_WIDTH = 360
    WORKSPACE_DEFAULT_WIDTH = 420
    WORKSPACE_WIDTH_SETTINGS_KEY = (
        "main_window/workspace_width"
    )

    SETTINGS_ORGANIZATION = "WTStudio"
    SETTINGS_APPLICATION = "WTStudio"

    LEFT_SPLITTER_SETTINGS_KEY = (
        "main_window/left_splitter_state"
    )

    IMPORT_FILE_FILTER = (
        "Supported Textures "
        "(*.dds *.tga *.png *.jpg *.jpeg "
        "*.bmp *.tif *.tiff *.webp);;"
        "DDS Textures (*.dds);;"
        "TGA Textures (*.tga);;"
        "PNG Textures (*.png);;"
        "Image Files "
        "(*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp);;"
        "All Files (*.*)"
    )

    def __init__(self) -> None:
        super().__init__()

        self.settings = QSettings(
            self.SETTINGS_ORGANIZATION,
            self.SETTINGS_APPLICATION,
        )

        self.project = ProjectManager()
        self.pbr_converter = PBRConverter()
        self.project_file_path = None
        self.project_dirty = False
        self._loading_project = False

        PathSettings.reset_session_paths()
        self._last_import_directory = (
            PathSettings.session_working_dialog_path()
        )
        self._last_pbr_export_directory = (
            PathSettings.session_output_dialog_path()
        )

        self.material_exporter = MaterialExporter()
        self.new_asset_exporter = NewAssetExporter()
        self.operation_runner = OperationRunner(parent=self)
        self._pending_operation = ""
        self._pending_output_directory = ""
        self._pending_requested_count = 0

        self.project_browser = ProjectBrowser()
        self.import_list = ImportList()
        self.preview_area = PreviewArea()

        self.setWindowTitle(APP_FULL_NAME)
        self.resize(1600, 900)
        self.set_preferred_normal_size(1600, 900)

        self.title_bar = WindowTitleBar(
            self,
            include_menu=True,
            dialog=False,
            show_logo=True,
            show_minimize=True,
            show_maximize=True,
            show_close=True,
        )
        self.setMenuWidget(self.title_bar)

        self.build_panels()
        self.build_menu()
        self.connect_signals()

        self.statusBar().showMessage("Ready")
        self._update_project_title()

    # ========================================================
    # Menu
    # ========================================================

    def build_menu(self) -> None:
        menu_bar = self.title_bar.menu_bar
        if menu_bar is None:
            raise RuntimeError("WT Studio title bar has no menu bar.")

        menu_bar.clear()

        # File -------------------------------------------------
        file_menu = menu_bar.addMenu("File")

        self.new_project_action = file_menu.addAction("New Project")
        self.new_project_action.setShortcut("Ctrl+N")

        self.open_project_action = file_menu.addAction("Open Project...")
        self.open_project_action.setShortcut("Ctrl+O")

        self.save_project_action = file_menu.addAction("Save Project")
        self.save_project_action.setShortcut("Ctrl+S")

        self.save_project_as_action = file_menu.addAction(
            "Save Project As..."
        )
        self.save_project_as_action.setShortcut("Ctrl+Shift+S")

        file_menu.addSeparator()

        self.import_action = file_menu.addAction("Import Textures...")
        self.import_action.setShortcut("Ctrl+I")

        file_menu.addSeparator()

        self.close_project_action = file_menu.addAction("Close Project")
        self.close_project_action.setShortcut("Ctrl+W")

        self.exit_action = file_menu.addAction("Exit WT Studio")
        self.exit_action.setShortcut("Alt+F4")

        # Edit -------------------------------------------------
        edit_menu = menu_bar.addMenu("Edit")

        self.set_user_skins_path_action = edit_menu.addAction(
            "Set Path to UserSkins..."
        )
        self.clear_user_skins_path_action = edit_menu.addAction(
            "Clear UserSkins Path"
        )

        # View -------------------------------------------------
        view_menu = menu_bar.addMenu("View")

        self.left_panel_action = self.left_dock.toggleViewAction()
        self.left_panel_action.setText("Project Sidebar")
        view_menu.addAction(self.left_panel_action)

        self.workspace_panel_action = self.workspace_dock.toggleViewAction()
        self.workspace_panel_action.setText("Workspace Panel")
        view_menu.addAction(self.workspace_panel_action)

        self.texture_info_action = QAction(
            "Texture Information",
            self,
        )
        self.texture_info_action.setCheckable(True)
        self.texture_info_action.setChecked(
            self.preview_area.texture_info.toggle.isChecked()
        )
        view_menu.addAction(self.texture_info_action)

        view_menu.addSeparator()

        self.fit_preview_action = view_menu.addAction("Fit Preview")
        self.fit_preview_action.setShortcut("F")

        self.reset_layout_action = view_menu.addAction("Reset Layout")

        # Tools ------------------------------------------------
        tools_menu = menu_bar.addMenu("Tools")

        self.export_materials_action = tools_menu.addAction(
            "Export Available Materials..."
        )
        self.validate_dds_action = tools_menu.addAction(
            "Validate DDS File..."
        )
        tools_menu.addSeparator()
        self.texture_engine_action = tools_menu.addAction(
            "Texture Engine Diagnostic"
        )

        # Help -------------------------------------------------
        help_menu = menu_bar.addMenu("Help")
        self.quick_start_action = help_menu.addAction(
            "Quick Start..."
        )
        help_menu.addSeparator()
        self.third_party_action = help_menu.addAction(
            "Third-Party Notices"
        )
        self.about_action = help_menu.addAction("Help...")

        # Connections -----------------------------------------
        self.new_project_action.triggered.connect(self.new_project)
        self.open_project_action.triggered.connect(self.open_project)
        self.save_project_action.triggered.connect(self.save_project)
        self.save_project_as_action.triggered.connect(self.save_project_as)
        self.import_action.triggered.connect(self.import_files)
        self.close_project_action.triggered.connect(self.close_project)
        self.exit_action.triggered.connect(self.close)

        self.set_user_skins_path_action.triggered.connect(
            self.set_user_skins_path
        )
        self.clear_user_skins_path_action.triggered.connect(
            self.clear_user_skins_path
        )

        self.texture_info_action.toggled.connect(
            self.preview_area.texture_info.toggle.setChecked
        )
        self.preview_area.texture_info.toggle.toggled.connect(
            self.texture_info_action.setChecked
        )
        self.fit_preview_action.triggered.connect(
            self.preview_area.texture_preview.fit_to_view
        )
        self.reset_layout_action.triggered.connect(self.reset_layout)

        self.export_materials_action.triggered.connect(
            lambda: self.export_materials(
                self.materials_panel.exportable_materials()
            )
        )
        self.validate_dds_action.triggered.connect(
            self.validate_dds_file
        )
        self.texture_engine_action.triggered.connect(
            self.show_texture_engine_diagnostic
        )
        self.quick_start_action.triggered.connect(
            self.quickStartRequested.emit
        )
        self.third_party_action.triggered.connect(
            self.show_third_party_notices
        )
        self.about_action.triggered.connect(
            self.helpAboutRequested.emit
        )

    def set_user_skins_path(self) -> None:
        current = PathSettings.user_skins_dialog_path()

        path = QFileDialog.getExistingDirectory(
            self,
            "Set Path to UserSkins",
            current,
            QFileDialog.Option.ShowDirsOnly,
        )

        if not path:
            return

        saved_path = PathSettings.set_user_skins_path(path)

        PathSettings.reset_session_paths()
        self._last_import_directory = (
            PathSettings.session_working_dialog_path()
        )
        self._last_pbr_export_directory = (
            PathSettings.session_output_dialog_path()
        )

        self.statusBar().showMessage(
            f"UserSkins path set: {saved_path}",
            7000,
        )

        QMessageBox.information(
            self,
            "UserSkins Path",
            "Default UserSkins path saved.\n\n"
            f"{saved_path}",
        )

    def clear_user_skins_path(self) -> None:
        current = PathSettings.user_skins_path()

        if current is None:
            QMessageBox.information(
                self,
                "UserSkins Path",
                "No custom UserSkins path is currently saved.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Clear UserSkins Path",
            "Remove the saved default UserSkins path?\n\n"
            f"{current}",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        PathSettings.clear_user_skins_path()
        PathSettings.reset_session_paths()
        self._last_import_directory = (
            PathSettings.session_working_dialog_path()
        )
        self._last_pbr_export_directory = (
            PathSettings.session_output_dialog_path()
        )

        self.statusBar().showMessage(
            "Saved UserSkins path cleared",
            7000,
        )

    def reset_layout(self) -> None:
        self.left_dock.show()
        self.workspace_dock.show()
        self.left_splitter.setSizes([300, 600])
        self.resizeDocks(
            [self.left_dock, self.workspace_dock],
            [self.LEFT_PANEL_DEFAULT_WIDTH, self.WORKSPACE_DEFAULT_WIDTH],
            Qt.Orientation.Horizontal,
        )
        self.preview_area.texture_info.toggle.setChecked(False)
        self.preview_area.texture_preview.fit_to_view()
        self.statusBar().showMessage("Layout reset", 4000)

    def validate_dds_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Validate DDS File",
            PathSettings.session_working_dialog_path(),
            "DDS Textures (*.dds);;All Files (*.*)",
        )

        if not path:
            return

        try:
            report = DDSValidator.inspect(path)
        except DDSValidationError as error:
            QMessageBox.critical(
                self,
                "DDS Validation Failed",
                str(error),
            )
            return

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle("DDS Validation")
        box.setText("DDS validation completed successfully.")
        box.setInformativeText(
            f"{report.format.value} · {report.dimensions} · "
            f"{report.mipmap_count} mip level(s)\nValidation: PASS"
        )
        box.setDetailedText(report.to_text())
        box.exec()

    def show_texture_engine_diagnostic(self) -> None:
        resolver = TextureEngineResolver()
        info = resolver.resolve()

        if info is None:
            QMessageBox.critical(
                self,
                "Texture Engine",
                "Bundled DirectXTex texconv.exe was not found.\n\n"
                f"Required location:\n{resolver.expected_executable}",
            )
            return

        digest = hashlib.sha256(info.executable.read_bytes()).hexdigest()
        version = TextureEngineResolver.probe_version(info)

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle("Texture Engine Diagnostic")
        box.setText("Self-contained texture engine check: PASS")
        box.setInformativeText(
            f"{info.display_name}\n{version}\n"
            "Runtime policy: bundled DirectXTex only"
        )
        box.setDetailedText(
            f"Path: {info.executable}\n"
            f"Source: {info.source_name}\n"
            f"File size: {info.executable.stat().st_size} bytes\n"
            f"SHA-256: {digest}\n"
            "External NVTT fallback: DISABLED\n"
            "BC7 game export: DISABLED\n"
            "WT Studio 1.0 export formats: "
            "TGA, DDS ARGB 8.8.8.8, BC1, BC3"
        )
        box.exec()

    def show_third_party_notices(self) -> None:
        root = TextureEngineResolver().project_root
        notices_path = root / "THIRD_PARTY_NOTICES.txt"

        try:
            notices = notices_path.read_text(encoding="utf-8")
        except OSError:
            notices = (
                "DirectXTex is used under the MIT License.\n"
                "The notice file was not found in this development copy."
            )

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle("Third-Party Notices")
        box.setText("WT Studio third-party components")
        box.setInformativeText(
            "DirectXTex / texconv is bundled with WT Studio."
        )
        box.setDetailedText(notices)
        box.exec()

    def show_about(self) -> None:
        self.helpAboutRequested.emit()

    # ========================================================
    # Main panels
    # ========================================================

    def build_panels(self) -> None:
        self.build_left_sidebar()
        self.build_workspace()

        self.setCentralWidget(
            self.preview_area
        )

    def build_left_sidebar(self) -> None:
        """
        Buduje stały lewy panel z biblioteką projektów
        oraz listą zaimportowanych tekstur.
        """

        self.left_splitter = QSplitter(
            Qt.Orientation.Vertical
        )

        self.left_splitter.setObjectName(
            "leftSidebarSplitter"
        )

        self.left_splitter.setChildrenCollapsible(
            False
        )

        self.left_splitter.setHandleWidth(5)

        project_section = self.create_sidebar_section(
            title="Project Library",
            content=self.project_browser,
        )

        imported_section = self.create_sidebar_section(
            title="Imported Textures",
            content=self.import_list,
        )

        project_section.setMinimumHeight(150)
        imported_section.setMinimumHeight(150)

        self.left_splitter.addWidget(
            project_section
        )

        self.left_splitter.addWidget(
            imported_section
        )

        self.left_splitter.setStretchFactor(
            0,
            1,
        )

        self.left_splitter.setStretchFactor(
            1,
            2,
        )

        self.left_splitter.setSizes(
            [300, 600]
        )

        self.left_dock = QDockWidget(
            "",
            self,
        )

        self.left_dock.setObjectName(
            "leftSidebarDock"
        )

        self.left_dock.setWidget(
            self.left_splitter
        )

        self.left_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
        )

        self.left_dock.setFeatures(
            QDockWidget.DockWidgetFeature.NoDockWidgetFeatures
        )

        self.left_dock.setMinimumWidth(
            self.LEFT_PANEL_MINIMUM_WIDTH
        )

        self.left_dock.resize(
            self.LEFT_PANEL_DEFAULT_WIDTH,
            self.left_dock.height(),
        )

        self.addDockWidget(
            Qt.DockWidgetArea.LeftDockWidgetArea,
            self.left_dock,
        )

        self.restore_left_splitter_state()

    def build_workspace(self) -> None:
        """
        Buduje prawy panel Workspace.

        PBRWorkflow otrzymuje bezpośrednio wspólną
        TextureCollection projektu.
        """

        self.tabs = QTabWidget()

        self.pbr_workflow = PBRWorkflow(
            collection=self.project.textures
        )

        self.materials_panel = MaterialsPanel(
            collection=self.project.materials
        )
        self.blk_panel = BLKPanel(
            material_collection=self.project.materials,
            texture_collection=self.project.textures,
        )
        self.new_assets_panel = NewAssetsPanel(
            collection=self.project.new_assets
        )

        self.tabs.addTab(
            self.pbr_workflow,
            "PBR WORKFLOW",
        )

        self.tabs.addTab(
            self.materials_panel,
            "DDS MATERIALS",
        )

        self.tabs.addTab(
            self.blk_panel,
            "BLK EDITOR",
        )

        self.tabs.addTab(
            self.new_assets_panel,
            "NEW ASSETS",
        )

        self.workspace_dock = QDockWidget(
            "",
            self,
        )

        self.workspace_dock.setObjectName(
            "workspaceDock"
        )

        # Stage 3.2A.5: the right workspace starts directly
        # with its tabs. The empty title-bar widget removes
        # the unused "Workspace" header without changing the
        # dock's width persistence or docking behaviour.
        self.workspace_title_bar = QWidget(
            self.workspace_dock
        )
        self.workspace_title_bar.setObjectName(
            "workspaceTitleBar"
        )
        self.workspace_title_bar.setFixedHeight(0)
        self.workspace_dock.setTitleBarWidget(
            self.workspace_title_bar
        )

        self.workspace_dock.setWidget(
            self.tabs
        )

        self.workspace_dock.setMinimumWidth(
            self.WORKSPACE_MINIMUM_WIDTH
        )

        self.workspace_dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea
        )

        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea,
            self.workspace_dock,
        )

        saved_width = self.settings.value(
            self.WORKSPACE_WIDTH_SETTINGS_KEY,
            self.WORKSPACE_DEFAULT_WIDTH,
            type=int,
        )

        workspace_width = max(
            self.WORKSPACE_MINIMUM_WIDTH,
            saved_width,
        )

        self.resizeDocks(
            [self.workspace_dock],
            [workspace_width],
            Qt.Orientation.Horizontal,
        )

    # ========================================================
    # Signal connections
    # ========================================================

    def connect_signals(self) -> None:
        """
        Łączy listę tekstur, Thumbnail Browser,
        podgląd i działania PBR Workflow.
        """

        self.project_browser.projectOpenRequested.connect(
            self.open_project_path
        )

        self.project_browser.projectDeleteRequested.connect(
            self.delete_project
        )

        self.import_list.textureSelected.connect(
            self.show_texture
        )

        self.pbr_workflow.textureSelected.connect(
            self.show_texture
        )

        self.pbr_workflow.textureActivated.connect(
            self.show_texture
        )

        self.pbr_workflow.importRequested.connect(
            self.import_files
        )

        self.import_list.removeTexturesRequested.connect(
            self.remove_imported_textures
        )

        self.pbr_workflow.removeTexturesRequested.connect(
            self.remove_imported_textures
        )

        self.pbr_workflow.exportSelectedRequested.connect(
            self.export_selected_as_pbr
        )

        self.pbr_workflow.exportAllRequested.connect(
            self.export_all_as_pbr
        )
        self.pbr_workflow.workspaceChanged.connect(
            self.mark_project_dirty
        )

        self.materials_panel.materialPreviewRequested.connect(
            self.show_material
        )
        self.materials_panel.projectChanged.connect(
            self.mark_project_dirty
        )

        self.new_assets_panel.assetPreviewRequested.connect(
            self.show_material
        )
        self.new_assets_panel.projectChanged.connect(
            self.mark_project_dirty
        )
        self.new_assets_panel.exportRequested.connect(
            self.export_new_assets
        )

        self.tabs.currentChanged.connect(
            self._workspace_tab_changed
        )

        self.materials_panel.exportMaterialsRequested.connect(
            self.export_materials
        )

        self.operation_runner.completed.connect(
            self._operation_completed
        )
        self.operation_runner.cancelled.connect(
            self._operation_cancelled
        )
        self.operation_runner.failed.connect(
            self._operation_failed
        )

    def _workspace_tab_changed(
        self,
        index: int,
    ) -> None:
        if self.tabs.widget(index) is self.blk_panel:
            self.blk_panel.refresh_materials()

    # ========================================================
    # Sidebar helpers
    # ========================================================

    @staticmethod
    def create_sidebar_section(
        title: str,
        content: QWidget,
    ) -> QWidget:
        """
        Tworzy nierozłączną sekcję lewego panelu.
        """

        section = QFrame()

        section.setObjectName(
            "sidebarSection"
        )

        section.setFrameShape(
            QFrame.Shape.StyledPanel
        )

        section.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        layout = QVBoxLayout(section)

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.setSpacing(0)

        header = QLabel(title.upper())

        header.setObjectName(
            "sidebarSectionHeader"
        )

        header.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )

        header.setFixedHeight(24)

        header.setContentsMargins(
            6,
            0,
            6,
            0,
        )

        layout.addWidget(header)
        layout.addWidget(content, 1)

        return section

    def restore_left_splitter_state(self) -> None:
        """
        Przywraca wysokość obu części lewego panelu.
        """

        saved_state = self.settings.value(
            self.LEFT_SPLITTER_SETTINGS_KEY
        )

        if saved_state is not None:
            self.left_splitter.restoreState(
                saved_state
            )

    def save_left_splitter_state(self) -> None:
        """
        Zapamiętuje ustawienie separatora między panelami.
        """

        self.settings.setValue(
            self.LEFT_SPLITTER_SETTINGS_KEY,
            self.left_splitter.saveState(),
        )

    # ========================================================
    # WT Studio project files
    # ========================================================

    def mark_project_dirty(self):
        if not self._loading_project:
            self.project_dirty = True
            self._update_project_title()

    def _update_project_title(self):
        name = (
            "Untitled"
            if self.project_file_path is None
            else Path(self.project_file_path).stem
        )
        marker = " *" if self.project_dirty else ""
        self.setWindowTitle(f"{APP_FULL_NAME} — {name}{marker}")

    def _confirm_discard_project_changes(self):
        if not self.project_dirty:
            return True
        answer = QMessageBox.question(
            self,
            "Unsaved Project Changes",
            "The current WT Studio project has unsaved changes.\n\n"
            "Continue without saving the project?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def delete_project(
        self,
        path: str,
    ) -> None:
        project_path = Path(path)

        if not project_path.exists():
            self.project_browser.refresh()
            QMessageBox.information(
                self,
                "Delete Project",
                "The selected project file no longer exists.",
            )
            return

        current_project = (
            self.project_file_path is not None
            and project_path.resolve()
            == Path(
                self.project_file_path
            ).resolve()
        )

        if current_project and self.project_dirty:
            QMessageBox.warning(
                self,
                "Delete Project",
                (
                    "The selected project is currently open "
                    "and has unsaved changes.\n\n"
                    "Save or discard those changes first."
                ),
            )
            return

        if (
            current_project
            and self.blk_panel.document is not None
            and self.blk_panel.has_unsaved_changes()
        ):
            QMessageBox.warning(
                self,
                "Delete Project",
                (
                    "The selected project contains an open BLK "
                    "with unsaved changes.\n\n"
                    "Save or close the BLK first."
                ),
            )
            return

        answer = QMessageBox.question(
            self,
            "Delete Project",
            (
                f"Delete project '{project_path.stem}'?\n\n"
                "Only the .wts project file will be removed. "
                "Textures, materials and BLK source files "
                "will remain on disk."
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            project_path.unlink()
        except OSError as error:
            QMessageBox.warning(
                self,
                "Delete Project",
                f"Could not delete project:\n{error}",
            )
            return

        if current_project:
            self._reset_project_ui()
            self.project_file_path = None
            self.project_dirty = False
            self._update_project_title()

        self.project_browser.refresh()

        self.statusBar().showMessage(
            f"Deleted project: {project_path.stem}",
            5000,
        )

    def close_project(self) -> None:
        if (
            self.blk_panel.document is not None
            and self.blk_panel.has_unsaved_changes()
        ):
            self.blk_panel.close_blk()

            if self.blk_panel.document is not None:
                return

        if not self._confirm_discard_project_changes():
            return

        self._reset_project_ui()
        self.project_file_path = None
        self.project_dirty = False
        PathSettings.reset_session_paths()
        self._last_import_directory = (
            PathSettings.session_working_dialog_path()
        )
        self._last_pbr_export_directory = (
            PathSettings.session_output_dialog_path()
        )
        self._update_project_title()

        self.statusBar().showMessage(
            "Project closed",
            5000,
        )

    def new_project(self):
        if not self._confirm_discard_project_changes():
            return

        if (
            self.blk_panel.document is not None
            and self.blk_panel.has_unsaved_changes()
        ):
            QMessageBox.information(
                self,
                "Unsaved BLK Changes",
                "Save or close the edited BLK before creating a new project.",
            )
            return

        details = self._request_project_identity(
            title="New WT Studio Project",
            initial_name="",
        )

        if details is None:
            return

        project_name, category = details

        self._reset_project_ui()
        PathSettings.reset_session_paths()
        self._last_import_directory = (
            PathSettings.session_working_dialog_path()
        )
        self._last_pbr_export_directory = (
            PathSettings.session_output_dialog_path()
        )

        self.project_file_path = (
            self.project_browser.category_path(
                category
            )
            / f"{project_name}.wts"
        )
        self.project_dirty = True
        self._update_project_title()

        self.statusBar().showMessage(
            f"New project: {project_name}",
            5000,
        )

    def save_project(self):
        if self.project_file_path is None:
            self.save_project_as()
        else:
            self._save_project_to(self.project_file_path)

    def save_project_as(self):
        initial_name = (
            Path(self.project_file_path).stem
            if self.project_file_path
            else ""
        )

        details = self._request_project_identity(
            title="Save WT Studio Project As",
            initial_name=initial_name,
        )

        if details is None:
            return

        project_name, category = details

        target = (
            self.project_browser.category_path(
                category
            )
            / f"{project_name}.wts"
        )

        if (
            target.exists()
            and (
                self.project_file_path is None
                or target.resolve()
                != Path(
                    self.project_file_path
                ).resolve()
            )
        ):
            answer = QMessageBox.question(
                self,
                "Replace Project",
                (
                    f"A project named '{project_name}' already exists "
                    f"in {category}.\n\nReplace it?"
                ),
                (
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                ),
                QMessageBox.StandardButton.No,
            )

            if answer != QMessageBox.StandardButton.Yes:
                return

        self._save_project_to(target)

    def _save_project_to(self, path):
        if self.blk_panel.document is not None and self.blk_panel.has_unsaved_changes():
            QMessageBox.warning(
                self,
                "Unsaved BLK Changes",
                "Save the BLK before saving the WT Studio project.",
            )
            return

        project_path = ProjectFileService.ensure_extension(path)
        textures = []

        for texture in self.project.textures:
            manual_role = None
            if getattr(texture, "has_manual_type", False):
                role = getattr(texture, "effective_type", None)
                manual_role = str(getattr(role, "name", role))

            source_path = getattr(
                texture,
                "path",
                getattr(getattr(texture, "file", None), "path", None),
            )
            textures.append({
                "path": ProjectFileService.encode_path(
                    source_path,
                    project_path,
                ),
                "manual_role": manual_role,
            })

        payload = {
            "project": {"name": project_path.stem},
            "textures": textures,
            "materials": self.materials_panel.project_records(
                project_path=project_path,
                path_encoder=ProjectFileService.encode_path,
            ),
            "new_assets": self.new_assets_panel.project_record(
                project_path=project_path,
                path_encoder=ProjectFileService.encode_path,
            ),
            "blk": {
                "path": ProjectFileService.encode_path(
                    self.blk_panel.current_blk_path,
                    project_path,
                )
            },
            "workspace": {
                "active_tab": self.tabs.currentIndex(),
                "create_pbr_export_folder": (
                    self.pbr_workflow.create_export_folder
                ),
                "export_normal_map_as_opengl": (
                    self.pbr_workflow.export_normal_map_as_opengl
                ),
            },
        }

        try:
            saved = ProjectFileService.save(project_path, payload)
        except ProjectFileError as error:
            QMessageBox.warning(self, "Save Project", str(error))
            return

        self.project_file_path = saved
        self.project_dirty = False
        self.project_browser.refresh()
        self._update_project_title()
        QMessageBox.information(
            self,
            "Project Saved",
            f"WT Studio project saved successfully.\n\n{saved}",
        )

    def open_project(self):
        selected_path = (
            self.project_browser
            .selected_project_path()
        )

        if selected_path is None:
            QMessageBox.information(
                self,
                "Open Project",
                (
                    "Select a project in Project Library "
                    "or double-click its name."
                ),
            )
            return

        self.open_project_path(
            str(selected_path)
        )

    def open_project_path(
        self,
        path: str,
    ) -> None:
        if not self._confirm_discard_project_changes():
            self.startupActionFinished.emit()
            return

        if (
            self.blk_panel.document is not None
            and self.blk_panel.has_unsaved_changes()
        ):
            QMessageBox.information(
                self,
                "Unsaved BLK Changes",
                "Save or close the edited BLK before opening another project.",
            )
            self.startupActionFinished.emit()
            return

        project_path = Path(path)

        progress = OperationProgressDialog(
            title="Loading Project",
            cancellable=False,
            parent=self,
        )
        progress.set_indeterminate("Loading project...")
        progress.show()

        QApplication.processEvents()

        # QTimer allows the modal dialog to be painted before loading starts.
        QTimer.singleShot(
            0,
            lambda: self._load_project_with_progress(
                project_path,
                progress,
            ),
        )

    def _load_project_with_progress(
        self,
        path: Path,
        progress: OperationProgressDialog,
    ) -> None:
        try:
            document = ProjectFileService.load(
                path
            )
        except ProjectFileError as error:
            progress.finish_and_close()
            QMessageBox.warning(
                self,
                "Open Project",
                str(error),
            )
            self.startupActionFinished.emit()
            return

        warnings = []
        self._loading_project = True

        try:
            self._reset_project_ui()

            texture_records = list(
                document.get(
                    "textures",
                    [],
                )
            )
            material_records = list(
                document.get(
                    "materials",
                    [],
                )
            )
            new_assets_record = document.get(
                "new_assets",
                {},
            ) or {}
            new_asset_records = list(
                new_assets_record.get(
                    "materials",
                    [],
                ) or []
            )

            total_steps = max(
                1,
                len(texture_records)
                + len(material_records)
                + len(new_asset_records)
                + 4,
            )
            progress.setRange(
                0,
                total_steps,
            )
            step = 0

            for record in texture_records:
                source = ProjectFileService.decode_path(
                    record.get("path"),
                    path,
                )

                progress.setLabelText(
                    (
                        "Loading texture:\n"
                        f"{source.name if source else 'Unknown'}"
                    )
                )
                QApplication.processEvents()

                if source is not None:
                    texture = self.project.import_texture(
                        source
                    )

                    if texture is None:
                        warnings.append(
                            f"Texture: {source}"
                        )
                    else:
                        manual_role = record.get(
                            "manual_role"
                        )

                        if manual_role:
                            try:
                                texture.set_manual_type(
                                    manual_role
                                )
                            except Exception:
                                warnings.append(
                                    f"Manual role: {source}"
                                )

                step += 1
                progress.setValue(step)

            imported = list(
                self.project.textures
            )
            self.import_list.add_textures(
                imported
            )
            self.pbr_workflow.reload()

            progress.setLabelText(
                "Restoring materials..."
            )
            QApplication.processEvents()

            warnings.extend(
                self.materials_panel
                .restore_project_records(
                    material_records,
                    project_path=path,
                    path_decoder=(
                        ProjectFileService.decode_path
                    ),
                )
            )
            step += len(material_records)
            progress.setValue(step)

            progress.setLabelText(
                "Restoring New Assets..."
            )
            QApplication.processEvents()

            warnings.extend(
                self.new_assets_panel.restore_project_record(
                    new_assets_record,
                    project_path=path,
                    path_decoder=ProjectFileService.decode_path,
                )
            )
            step += len(new_asset_records) + 1
            progress.setValue(step)

            progress.setLabelText(
                "Opening BLK..."
            )
            QApplication.processEvents()

            blk_record = document.get(
                "blk",
                {},
            )
            blk_source = (
                ProjectFileService.decode_path(
                    blk_record.get("path"),
                    path,
                )
            )

            if blk_source is not None:
                try:
                    self.blk_panel.open_project_blk(
                        blk_source
                    )
                except Exception as error:
                    warnings.append(
                        f"BLK: {blk_source} — {error}"
                    )

            step += 1
            progress.setValue(step)

            workspace = document.get(
                "workspace",
                {},
            )

            self.pbr_workflow.create_export_folder_check.setChecked(
                bool(
                    workspace.get(
                        "create_pbr_export_folder",
                        True,
                    )
                )
            )
            self.pbr_workflow.export_opengl_normal_check.setChecked(
                bool(
                    workspace.get(
                        "export_normal_map_as_opengl",
                        False,
                    )
                )
            )

            tab = int(
                workspace.get(
                    "active_tab",
                    0,
                )
            )

            if 0 <= tab < self.tabs.count():
                self.tabs.setCurrentIndex(
                    tab
                )

            self.blk_panel.refresh_imported_names()
            self.preview_area.clear_preview()

            self.project_file_path = path
            self.project_dirty = False
            self._update_project_title()

            progress.setLabelText(
                "Project loaded."
            )
            progress.setValue(total_steps)
            QApplication.processEvents()

        finally:
            self._loading_project = False
            progress.finish_and_close()

        self.statusBar().showMessage(
            "Project opened",
            7000,
        )

        if warnings:
            warning_details = "\n".join(warnings)

            # Do not open another modal native window inside the same callback
            # that just closed the progress dialog. Deferring by one event-loop
            # turn avoids a fragile Windows/PySide modal transition.
            QTimer.singleShot(
                0,
                lambda details=warning_details:
                self._show_project_open_warnings(details),
            )
        else:
            QTimer.singleShot(
                0,
                self.startupActionFinished.emit,
            )

    def _show_project_open_warnings(
        self,
        details: str,
    ) -> None:
        box = QMessageBox(self)
        box.setIcon(
            QMessageBox.Icon.Warning
        )
        box.setWindowTitle(
            "Project Opened with Warnings"
        )
        box.setText(
            (
                "The project opened, but some resources "
                "could not be restored."
            )
        )
        box.setDetailedText(
            details
        )
        box.exec()
        self.startupActionFinished.emit()

    def _request_project_identity(
        self,
        *,
        title: str,
        initial_name: str,
    ):
        dialog = ProjectIdentityDialog(
            title=title,
            categories=(
                self.project_browser.CATEGORIES
            ),
            initial_name=initial_name,
            parent=self,
        )

        if not dialog.exec():
            return None

        project_name = self._safe_project_name(
            dialog.project_name()
        )

        if not project_name:
            QMessageBox.warning(
                self,
                title,
                "Enter a valid project name.",
            )
            return None

        category = dialog.category()

        if not category:
            return None

        return project_name, category

    @staticmethod
    def _safe_project_name(
        value: str,
    ) -> str:
        cleaned = re.sub(
            r'[<>:"/\\|?*\x00-\x1f]+',
            "_",
            str(value).strip(),
        )
        cleaned = re.sub(
            r"\s+",
            "_",
            cleaned,
        )
        return cleaned.strip(" ._")

    def _reset_project_ui(self):
        self.preview_area.clear_preview()
        self.import_list.clear()
        self.materials_panel.clear_project_materials()
        self.new_assets_panel.clear_project_assets(
            reset_export_directory=True
        )
        self.blk_panel.close_project_blk()

        reset = getattr(self.project, "reset_project", None)
        if callable(reset):
            reset()
        else:
            self.project.clear_textures()

        self.pbr_workflow.create_export_folder_check.setChecked(True)
        self.pbr_workflow.export_opengl_normal_check.setChecked(False)
        self.pbr_workflow.reload()
        self.blk_panel.refresh_imported_names()

    # ========================================================
    # File import
    # ========================================================

    def import_files(self) -> None:
        """
        Otwiera okno wyboru plików i importuje tekstury.

        Każda nowa tekstura trafia jednocześnie do:

        - ProjectManager / TextureCollection,
        - lewej listy Imported Textures,
        - Thumbnail Browser w PBR Workflow.
        """

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Textures",
            PathSettings.session_working_dialog_path(),
            self.IMPORT_FILE_FILTER,
        )

        if not files:
            self.startupActionFinished.emit()
            return

        selected_files = list(files)
        working_directory = PathSettings.set_session_working_directory(
            Path(selected_files[0]).parent
        )
        self._last_import_directory = str(working_directory)
        self._last_pbr_export_directory = (
            PathSettings.session_output_dialog_path()
        )

        self._pending_operation = "import"
        self._pending_requested_count = len(selected_files)
        self._set_operation_ui_running(True)

        def operation(context):
            total = len(selected_files)
            imported = []

            self.project.import_errors.clear()
            self.project.last_imported.clear()
            self.project.last_skipped_duplicates.clear()

            for index, file_path in enumerate(
                selected_files,
                start=1,
            ):
                if context.is_cancelled():
                    break

                path = Path(file_path)

                context.progress(
                    index - 1,
                    total,
                    path.name,
                )

                if path in self.project.textures:
                    self.project.last_skipped_duplicates.append(
                        path
                    )
                else:
                    try:
                        texture = TextureLoader.load(
                            path
                        )
                    except Exception as error:
                        self.project.import_errors.append(
                            (path, str(error))
                        )
                    else:
                        if self.project.textures.add_if_missing(
                            texture
                        ):
                            imported.append(texture)
                        else:
                            self.project.last_skipped_duplicates.append(
                                path
                            )

                context.progress(
                    index,
                    total,
                    path.name,
                )

            self.project.last_imported = list(imported)
            return imported

        started = self.operation_runner.start(
            title="Importing Textures",
            operation=operation,
            cancellable=True,
        )

        if not started:
            self._set_operation_ui_running(False)
            self.startupActionFinished.emit()

    def show_import_result(
        self,
        *,
        requested_count: int,
        imported_count: int,
    ) -> None:
        """
        Pokazuje wynik ostatniej operacji importu.
        """

        duplicate_count = (
            self.project.skipped_duplicate_count
        )

        error_count = len(
            self.project.import_errors
        )

        parts: list[str] = []

        if imported_count == 1:
            parts.append(
                "Imported 1 texture"
            )
        else:
            parts.append(
                f"Imported {imported_count} textures"
            )

        if duplicate_count == 1:
            parts.append(
                "1 duplicate skipped"
            )

        elif duplicate_count > 1:
            parts.append(
                f"{duplicate_count} duplicates skipped"
            )

        if error_count == 1:
            parts.append(
                "1 file failed"
            )

        elif error_count > 1:
            parts.append(
                f"{error_count} files failed"
            )

        message = " · ".join(parts)

        self.statusBar().showMessage(
            message,
            7000,
        )

        if error_count > 0:
            self.show_import_errors()

        if (
            requested_count > 0
            and imported_count == 0
            and duplicate_count == 0
            and error_count == 0
        ):
            self.statusBar().showMessage(
                "No textures were imported",
                5000,
            )

    def show_import_errors(self) -> None:
        """
        Wyświetla szczegóły błędów importu.

        Jeden uszkodzony plik nie przerywa importu
        pozostałych tekstur.
        """

        if not self.project.import_errors:
            return

        error_lines: list[str] = []

        for path, error_message in (
            self.project.import_errors
        ):
            error_lines.append(
                f"{path.name}: {error_message}"
            )

        details = "\n".join(
            error_lines
        )

        message_box = QMessageBox(self)

        message_box.setIcon(
            QMessageBox.Icon.Warning
        )

        message_box.setWindowTitle(
            "Texture Import"
        )

        message_box.setText(
            "Some textures could not be imported."
        )

        message_box.setInformativeText(
            (
                f"Failed files: "
                f"{len(self.project.import_errors)}"
            )
        )

        message_box.setDetailedText(
            details
        )

        message_box.exec()

    # ========================================================
    # Texture preview
    # ========================================================

    def remove_imported_textures(
        self,
        textures,
    ) -> None:
        textures = list(textures or [])

        if not textures:
            return

        count = len(textures)

        answer = QMessageBox.question(
            self,
            "Remove Imported Textures",
            (
                f"Remove {count} imported texture"
                f"{'s' if count != 1 else ''} from the project?\n\n"
                "Source files will remain on disk."
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.Cancel
            ),
            QMessageBox.StandardButton.Cancel,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        removed = []

        for texture in textures:
            result = self.project.remove_texture(
                texture
            )

            if result is not None:
                removed.append(result)

        self.import_list.remove_textures(
            removed
        )
        self.pbr_workflow.remove_textures(
            removed
        )
        self.blk_panel.refresh_imported_names()

        self.preview_area.clear_preview()

        self.statusBar().showMessage(
            (
                f"Removed {len(removed)} texture"
                f"{'s' if len(removed) != 1 else ''} "
                "from the project"
            ),
            5000,
        )
        if removed:
            self.mark_project_dirty()

    def show_texture(
        self,
        texture: TextureInfo,
    ) -> None:
        """
        Wyświetla teksturę wybraną z lewej listy
        albo z Thumbnail Browser.
        """

        self.preview_area.show_texture(
            texture
        )

    def show_material(self, material) -> None:
        self.preview_area.show_material(material)

    # ========================================================
    # PBR export placeholders
    # ========================================================

    def export_selected_as_pbr(
        self,
        textures: list[TextureInfo],
    ) -> None:
        """
        Eksportuje tekstury zaznaczone w Thumbnail Browser.
        """
        if not textures:
            QMessageBox.information(
                self,
                "PBR Export",
                "Select at least one texture to export.",
            )
            return

        self.export_textures_as_pbr(
            textures=textures,
            export_name="selected textures",
        )

    def export_all_as_pbr(
        self,
        textures: list[TextureInfo],
    ) -> None:
        """
        Eksportuje wszystkie tekstury widoczne w PBR Workflow.
        """

        if not textures:
            QMessageBox.information(
                self,
                "PBR Export",
                "There are no textures to export.",
            )
            return

        self.export_textures_as_pbr(
            textures=textures,
            export_name="all textures"
        )

    def export_textures_as_pbr(
        self,
        *,
        textures: list[TextureInfo],
        export_name: str,
    ) -> None:
        """
        Wspólna obsługa eksportu PBR.

        Użytkownik wybiera folder, a converter:

        - rozpoznaje _c, _n i _ao,
        - generuje odpowiednie mapy,
        - zapisuje je jako pliki PNG,
        - nie przerywa całego eksportu po błędzie jednego pliku.
        """

        output_directory = QFileDialog.getExistingDirectory(
            self,
            "Select PBR Export Folder",
            PathSettings.session_output_dialog_path(),
            QFileDialog.Option.ShowDirsOnly,
        )

        if not output_directory:
            return

        output_base = PathSettings.set_session_output_directory(
            output_directory
        )
        self._last_pbr_export_directory = str(output_base)

        if self.pbr_workflow.create_export_folder:
            output_directory = str(
                Path(output_directory)
                / "PBR Textures"
            )

            Path(output_directory).mkdir(
                parents=True,
                exist_ok=True,
            )

        selected_textures = list(textures)
        export_normal_map_as_opengl = (
            self.pbr_workflow.export_normal_map_as_opengl
        )
        self._pending_operation = "pbr_export"
        self._pending_output_directory = output_directory
        self._set_operation_ui_running(True)

        def operation(context):
            batch_result = PBRBatchConversionResult()
            total = len(selected_textures)

            for index, texture in enumerate(
                selected_textures,
                start=1,
            ):
                if context.is_cancelled():
                    break

                context.progress(
                    index - 1,
                    total,
                    texture.name,
                )

                try:
                    result = self.pbr_converter.convert_texture(
                        texture
                    )
                    self.pbr_converter.export_result(
                        result,
                        output_directory,
                        overwrite=True,
                        normal_map_opengl=(
                            export_normal_map_as_opengl
                        ),
                    )
                    batch_result.results.append(
                        result
                    )
                except Exception as error:
                    batch_result.errors.append(
                        (
                            Path(texture.path),
                            str(error),
                        )
                    )

                context.progress(
                    index,
                    total,
                    texture.name,
                )

            return batch_result

        started = self.operation_runner.start(
            title=f"Exporting {export_name}",
            operation=operation,
            cancellable=True,
        )

        if not started:
            self._set_operation_ui_running(False)

    def show_pbr_export_result(
        self,
        *,
        batch_result: PBRBatchConversionResult,
        output_directory: str,
    ) -> None:
        """
        Pokazuje podsumowanie eksportu map PBR.
        """

        converted_count = (
            batch_result.converted_texture_count
        )

        generated_count = (
            batch_result.generated_map_count
        )

        exported_count = len(
            batch_result.exported_paths
        )

        error_count = (
            batch_result.error_count
        )

        status_parts: list[str] = [
            f"Converted: {converted_count}",
            f"Generated maps: {generated_count}",
            f"Exported PNG: {exported_count}",
        ]

        if error_count > 0:
            status_parts.append(
                f"Errors: {error_count}"
            )

        self.statusBar().showMessage(
            " · ".join(status_parts),
            10000,
        )

        if error_count > 0:
            self.show_pbr_export_errors(
                batch_result=batch_result,
                output_directory=output_directory
            )
            return

        QMessageBox.information(
            self,
            "PBR Export Complete",
            (
                "PBR export completed successfully.\n\n"
                f"Source textures: {converted_count}\n"
                f"Exported PNG files: {exported_count}\n\n"
                f"Output folder:\n{output_directory}"
            ),
        )

    def show_pbr_export_errors(
        self,
        *,
        batch_result: PBRBatchConversionResult,
        output_directory: str,
    ) -> None:
        """
        Pokazuje szczegóły błędów konwersji lub zapisu.
        """

        error_lines: list[str] = []

        for source_path, error_message in (
            batch_result.errors
        ):
            error_lines.append(
                 f"{source_path.name}: {error_message}"
            )

        details = "\n".join(
            error_lines
        )

        exported_count = len(
            batch_result.exported_paths
        )

        message_box = QMessageBox(self)

        message_box.setIcon(
            QMessageBox.Icon.Warning
        )

        message_box.setWindowTitle(
            "PBR Export"
        )

        message_box.setText(
            "PBR export finished with errors."
        )

        message_box.setInformativeText(
            (
                f"Exported PNG files: {exported_count}\n"
                f"Failed textures or files: "
                f"{batch_result.error_count}\n\n"
                f"Output folder:\n{output_directory}"
            )
        )

        message_box.setDetailedText(
            details
        )

        message_box.exec()


    # ========================================================
    # Material export
    # ========================================================

    def export_materials(
        self,
        materials,
    ) -> None:
        materials = list(materials)

        if not materials:
            QMessageBox.information(
                self,
                "Material Export",
                "No materials are marked Available to export.",
            )
            return

        dialog = MaterialExportDialog(
            initial_directory=(
                PathSettings.session_output_dialog_path()
            ),
            parent=self,
        )

        if not dialog.exec():
            return

        options = dialog.options()

        material_output = PathSettings.set_session_output_directory(
            options.output_directory
        )
        self._last_pbr_export_directory = str(material_output)

        self._pending_operation = "material_export"
        self._pending_output_directory = str(
            options.output_directory
        )
        self._set_operation_ui_running(True)

        def operation(context):
            return self.material_exporter.export_many(
                materials,
                options,
                progress_callback=context.progress,
                cancel_callback=context.is_cancelled,
            )

        started = self.operation_runner.start(
            title="Exporting Materials",
            operation=operation,
            cancellable=True,
        )

        if not started:
            self._set_operation_ui_running(False)

    def show_material_export_result(
        self,
        result: MaterialBatchExportResult,
    ) -> None:
        status = (
            f"Exported materials: {result.exported_count}"
            f" · Validated: {result.verified_count}"
        )

        if result.error_count:
            status += (
                f" · Errors: {result.error_count}"
            )

        self.statusBar().showMessage(
            status,
            10000,
        )

        if not result.error_count:
            QMessageBox.information(
                self,
                "Material Export Complete",
                (
                    "All ready materials were exported.\n\n"
                    f"Exported: {result.exported_count}\n"
                    f"Validated: {result.verified_count}\n\n"
                    "Output folder:\n"
                    f"{self._pending_output_directory}"
                ),
            )
            return

        details = "\n".join(
            f"{item.material_name}: {item.error}"
            for item in result.errors
        )

        message_box = QMessageBox(
            self
        )
        message_box.setIcon(
            QMessageBox.Icon.Warning
        )
        message_box.setWindowTitle(
            "Material Export"
        )
        message_box.setText(
            "Material export finished with errors."
        )
        message_box.setInformativeText(
            (
                f"Exported: {result.exported_count}\n"
                f"Failed: {result.error_count}\n"
                f"Validated: {result.verified_count}"
            )
        )
        message_box.setDetailedText(
            details
        )
        message_box.exec()

    # ========================================================
    # New Assets export
    # ========================================================

    def export_new_assets(
        self,
        materials,
        output_directory: str,
    ) -> None:
        materials = list(materials)

        if not materials:
            QMessageBox.information(
                self,
                "New Assets Export",
                "There are no New Assets materials to export.",
            )
            return

        if not str(output_directory).strip():
            QMessageBox.information(
                self,
                "New Assets Export",
                "Select a New Assets export directory first.",
            )
            return

        self._pending_operation = "new_asset_export"
        self._pending_output_directory = str(output_directory)
        self._set_operation_ui_running(True)

        def operation(context):
            return self.new_asset_exporter.export_many(
                materials,
                output_directory,
                progress_callback=context.progress,
                cancel_callback=context.is_cancelled,
            )

        started = self.operation_runner.start(
            title="Exporting New Assets",
            operation=operation,
            cancellable=True,
        )

        if not started:
            self._set_operation_ui_running(False)

    def show_new_asset_export_result(
        self,
        result: NewAssetBatchExportResult,
    ) -> None:
        status = (
            f"Exported New Assets: {result.exported_count}"
            f" · Verified: {result.verified_count}"
        )

        if result.error_count:
            status += f" · Errors: {result.error_count}"

        self.statusBar().showMessage(status, 10000)

        if not result.error_count:
            QMessageBox.information(
                self,
                "New Assets Export Complete",
                (
                    "AssetViewer source TGA files were exported successfully.\n\n"
                    f"Exported: {result.exported_count}\n"
                    f"Verified: {result.verified_count}\n\n"
                    "Output folder:\n"
                    f"{self._pending_output_directory}"
                ),
            )
            return

        details = "\n".join(
            f"{item.asset_name}: {item.error}"
            for item in result.errors
        )

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("New Assets Export")
        box.setText("New Assets export finished with errors.")
        box.setInformativeText(
            f"Exported: {result.exported_count}\n"
            f"Failed: {result.error_count}\n"
            f"Verified: {result.verified_count}"
        )
        box.setDetailedText(details)
        box.exec()

    # ========================================================
    # Background operation handling
    # ========================================================

    def _set_operation_ui_running(
        self,
        running: bool,
    ) -> None:
        self.import_action.setEnabled(
            not running
        )
        self.pbr_workflow.setEnabled(
            not running
        )
        self.materials_panel.set_operation_running(
            running
        )
        self.new_assets_panel.set_operation_running(
            running
        )
        self.blk_panel.setEnabled(
            not running
        )

    def _operation_completed(
        self,
        result,
    ) -> None:
        operation = self._pending_operation
        self._set_operation_ui_running(
            False
        )

        if operation == "import":
            imported = list(result or [])

            if imported:
                self.import_list.add_textures(
                    imported
                )

                self.pbr_workflow.add_textures(
                    imported
                )

                self.blk_panel.refresh_imported_names()

            self.show_import_result(
                requested_count=(
                    self._pending_requested_count
                ),
                imported_count=len(imported),
            )
            if imported:
                self.mark_project_dirty()

        elif operation == "pbr_export":
            self.show_pbr_export_result(
                batch_result=result,
                output_directory=(
                    self._pending_output_directory
                ),
            )

        elif operation == "material_export":
            self.show_material_export_result(
                result
            )

        elif operation == "new_asset_export":
            self.show_new_asset_export_result(
                result
            )

        self._pending_operation = ""

        if operation == "import":
            self.startupActionFinished.emit()

    def _operation_cancelled(self) -> None:
        operation = self._pending_operation
        self._set_operation_ui_running(
            False
        )
        self.statusBar().showMessage(
            "Operation cancelled",
            5000,
        )
        self._pending_operation = ""

        if operation == "import":
            self.startupActionFinished.emit()

    def _operation_failed(
        self,
        message: str,
    ) -> None:
        operation = self._pending_operation
        self._set_operation_ui_running(
            False
        )
        self.statusBar().showMessage(
            f"Operation failed: {message}",
            7000,
        )
        self._pending_operation = ""

        if operation == "import":
            self.startupActionFinished.emit()

    # ========================================================
    # Window events
    # ========================================================

    def closeEvent(self, event) -> None:
        if self.blk_panel.document is not None and self.blk_panel.has_unsaved_changes():
            QMessageBox.information(
                self,
                "Unsaved BLK Changes",
                "Save or close the edited BLK before exiting WT Studio.",
            )
            event.ignore()
            return

        if not self._confirm_discard_project_changes():
            event.ignore()
            return

        self.save_left_splitter_state()
        self.settings.setValue(
            self.WORKSPACE_WIDTH_SETTINGS_KEY,
            self.workspace_dock.width(),
        )
        event.accept()
