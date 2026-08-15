from __future__ import annotations

from ui.icons import stylesheet_icon_url
from ui.theme.metrics import Metrics
from ui.theme.palette import Palette


def build_stylesheet(font_family: str = "Segoe UI") -> str:
    p = Palette
    m = Metrics
    safe_font_family = font_family.replace('"', "")

    tree_chevron_right = stylesheet_icon_url(
        "tree_chevron_right.svg"
    )
    tree_chevron_down = stylesheet_icon_url(
        "tree_chevron_down.svg"
    )

    return f"""
    * {{
        font-family: "{safe_font_family}";
        font-size: 9pt;
        outline: none;
    }}

    QWidget {{
        background-color: {p.PANEL};
        color: {p.TEXT};
    }}

    QMainWindow {{
        background-color: {p.WINDOW};
    }}

    QMainWindow::separator {{
        background-color: {p.SPLITTER};
        width: 1px;
        height: 1px;
    }}

    QMainWindow::separator:hover {{
        background-color: {p.SPLITTER_HOVER};
    }}

    QDockWidget {{
        background-color: {p.PANEL};
        color: {p.TEXT_MUTED};
        border: none;
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
    }}

    QDockWidget::title {{
        background-color: {p.PANEL_ALT};
        color: {p.TEXT_MUTED};
        text-align: left;
        padding-left: 6px;
        border-bottom: 1px solid {p.BORDER};
        height: {m.HEADER_HEIGHT}px;
    }}

    QFrame {{
        border: none;
    }}

    QFrame#sidebarSection {{
        background-color: {p.PANEL};
        border: none;
    }}

    QLabel {{
        background-color: transparent;
        color: {p.TEXT};
        border: none;
    }}

    QLabel:disabled {{
        color: {p.TEXT_MUTED};
    }}

    QLabel#sidebarSectionHeader {{
        background-color: {p.PANEL_ALT};
        color: {p.TEXT_HEADER};
        border: none;
        border-bottom: 1px solid {p.BORDER};
        padding-left: 8px;
        font-size: 8pt;
        font-weight: 700;
    }}

    QLabel#sectionHeader {{
        background-color: transparent;
        color: {p.TEXT_HEADER};
        border: none;
        padding: 2px 0px 4px 0px;
        font-size: 8pt;
        font-weight: 700;
    }}

    QPushButton#sectionHeaderButton {{
        min-height: 25px;
        background-color: transparent;
        color: {p.TEXT_HEADER};
        border: none;
        border-bottom: 1px solid {p.BORDER_SOFT};
        padding: 2px 7px;
        font-size: 8pt;
        font-weight: 700;
        text-align: center;
    }}

    QPushButton#sectionHeaderButton:hover {{
        background-color: {p.CONTROL_HOVER};
        color: {p.TEXT_BRIGHT};
        border-bottom-color: {p.ACCENT};
    }}

    /* Import is an action, not a section heading. */
    QPushButton#importSourceButton {{
        min-height: 25px;
        background-color: transparent;
        color: {p.TEXT};
        border: 1px solid transparent;
        padding: 2px 7px;
        font-size: 9pt;
        font-weight: 400;
        text-align: center;
    }}

    QPushButton#importSourceButton:hover {{
        background-color: {p.CONTROL_HOVER};
        color: {p.TEXT_BRIGHT};
        border-color: {p.BORDER_HOVER};
    }}

    QPushButton#importSourceButton:pressed {{
        background-color: {p.CONTROL_PRESSED};
        border-color: {p.BORDER_HOVER};
    }}

    QMenuBar {{
        background-color: {p.WINDOW};
        color: {p.TEXT_MUTED};
        border: none;
        border-bottom: 1px solid {p.BORDER_SOFT};
        spacing: 2px;
    }}

    QMenuBar::item {{
        background: transparent;
        padding: 5px 9px;
    }}

    QMenuBar::item:selected {{
        background-color: {p.CONTROL_HOVER};
        color: {p.TEXT_BRIGHT};
    }}

    QMenu {{
        background-color: {p.PANEL_ALT};
        color: {p.TEXT};
        border: 1px solid {p.BORDER};
        padding: 4px;
    }}

    QMenu::item {{
        padding: 5px 26px 5px 8px;
        background: transparent;
    }}

    QMenu::item:selected {{
        background-color: {p.SELECTION};
        color: {p.TEXT_BRIGHT};
    }}

    QMenu::separator {{
        height: 1px;
        background-color: {p.BORDER};
        margin: 4px 5px;
    }}

    QToolBar {{
        background-color: {p.WINDOW};
        border: none;
        border-bottom: 1px solid {p.BORDER_SOFT};
        spacing: 2px;
        padding: 1px;
    }}

    QStatusBar {{
        background-color: {p.WINDOW};
        color: {p.TEXT_MUTED};
        border-top: 1px solid {p.BORDER_SOFT};
    }}

    QStatusBar::item {{
        border: none;
    }}

    QPushButton,
    QToolButton {{
        min-height: {m.SMALL_CONTROL_HEIGHT}px;
        background-color: transparent;
        color: {p.TEXT};
        border: 1px solid transparent;
        padding: 2px 7px;
    }}

    QPushButton:hover,
    QToolButton:hover {{
        background-color: {p.CONTROL_HOVER};
        border-color: {p.BORDER_HOVER};
        color: {p.TEXT_BRIGHT};
    }}

    QPushButton:pressed,
    QToolButton:pressed {{
        background-color: {p.CONTROL_PRESSED};
        border-color: {p.ACCENT};
    }}

    QPushButton:checked,
    QToolButton:checked {{
        background-color: {p.SELECTION};
        border-color: {p.ACCENT};
        color: {p.TEXT_BRIGHT};
    }}

    QPushButton:disabled,
    QToolButton:disabled {{
        background-color: transparent;
        color: {p.TEXT_DISABLED};
        border-color: transparent;
    }}

    QLineEdit,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox {{
        min-height: {m.SMALL_CONTROL_HEIGHT}px;
        background-color: {p.CONTROL};
        color: {p.TEXT};
        border: 1px solid {p.BORDER};
        padding: 1px 6px;
        selection-background-color: {p.SELECTION};
        selection-color: {p.TEXT_BRIGHT};
    }}

    QLineEdit:hover,
    QComboBox:hover,
    QSpinBox:hover,
    QDoubleSpinBox:hover {{
        border-color: {p.BORDER_HOVER};
    }}

    QLineEdit:focus,
    QComboBox:focus,
    QSpinBox:focus,
    QDoubleSpinBox:focus {{
        border-color: {p.ACCENT};
    }}

    QComboBox#blkRuleTypeCombo:disabled {{
        background-color: {p.CONTROL};
        color: {p.TEXT_DISABLED};
        border-color: {p.BORDER_SOFT};
    }}

    QComboBox::drop-down {{
        width: 20px;
        border: none;
        background: transparent;
    }}

    QComboBox QAbstractItemView {{
        background-color: {p.PANEL_ALT};
        color: {p.TEXT};
        border: 1px solid {p.BORDER};
        selection-background-color: {p.SELECTION};
        selection-color: {p.TEXT_BRIGHT};
    }}

    QAbstractItemView,
    QListWidget,
    QTreeWidget {{
        background-color: {p.PANEL};
        alternate-background-color: {p.PANEL_ALT};
        color: {p.TEXT};
        border: none;
        selection-background-color: {p.SELECTION};
        selection-color: {p.TEXT_BRIGHT};
    }}

    QTreeWidget::branch {{
        background: transparent;
    }}

    QTreeWidget::branch:has-children:closed {{
        image: url("{tree_chevron_right}");
    }}

    QTreeWidget::branch:has-children:open {{
        image: url("{tree_chevron_down}");
    }}

    QAbstractItemView::item {{
        min-height: 22px;
        padding-left: 4px;
        border: none;
    }}

    QAbstractItemView::item:hover {{
        background-color: {p.CONTROL_HOVER};
    }}

    QAbstractItemView::item:selected {{
        background-color: {p.SELECTION};
        color: {p.TEXT_BRIGHT};
    }}

    QHeaderView {{
        background-color: {p.PANEL_ALT};
        color: {p.TEXT_MUTED};
        border: none;
    }}

    QHeaderView::section {{
        background-color: {p.PANEL_ALT};
        color: {p.TEXT_MUTED};
        border: none;
        border-right: 1px solid {p.BORDER};
        border-bottom: 1px solid {p.BORDER};
        padding: 4px 6px;
    }}

    QTabWidget::pane {{
        background-color: {p.PANEL};
        border: none;
        border-top: 1px solid {p.BORDER};
    }}

    QTabBar {{
        background-color: {p.WINDOW};
        border: none;
    }}

    QTabBar::tab {{
        background-color: {p.WINDOW};
        color: {p.TEXT_MUTED};
        border: none;
        border-right: 1px solid {p.BORDER_SOFT};
        padding: {m.TAB_VERTICAL_PADDING}px {m.TAB_HORIZONTAL_PADDING}px;
        font-size: 8pt;
        font-weight: 400;
    }}

    QTabBar::tab:hover {{
        background-color: {p.PANEL_ALT};
        color: {p.TEXT};
    }}

    QTabBar::tab:selected {{
        background-color: {p.PANEL};
        color: {p.TEXT_BRIGHT};
        border-top: 1px solid {p.ACCENT};
        font-weight: 700;
    }}

    QSplitter::handle {{
        background-color: {p.SPLITTER};
    }}

    QSplitter::handle:hover {{
        background-color: {p.SPLITTER_HOVER};
    }}

    QSplitter::handle:horizontal {{
        width: 1px;
    }}

    QSplitter::handle:vertical {{
        height: 1px;
    }}

    QScrollArea {{
        background-color: {p.PANEL};
        border: none;
    }}

    QScrollBar:vertical {{
        background: {p.SCROLL_TRACK};
        width: {m.SCROLLBAR_SIZE}px;
        margin: 0;
    }}

    QScrollBar:horizontal {{
        background: {p.SCROLL_TRACK};
        height: {m.SCROLLBAR_SIZE}px;
        margin: 0;
    }}

    QScrollBar::handle:vertical,
    QScrollBar::handle:horizontal {{
        background-color: {p.SCROLL_HANDLE};
        min-height: 24px;
        min-width: 24px;
        border: none;
    }}

    QScrollBar::handle:vertical:hover,
    QScrollBar::handle:horizontal:hover {{
        background-color: {p.SCROLL_HANDLE_HOVER};
    }}

    QScrollBar::add-line,
    QScrollBar::sub-line,
    QScrollBar::add-page,
    QScrollBar::sub-page {{
        background: transparent;
        border: none;
    }}

    QProgressBar {{
        background-color: {p.CONTROL};
        color: {p.TEXT_BRIGHT};
        border: 1px solid {p.BORDER};
        text-align: center;
        min-height: 18px;
    }}

    QProgressBar::chunk {{
        background-color: {p.ACCENT};
    }}

    QCheckBox {{
        color: {p.TEXT};
        spacing: 6px;
        background: transparent;
    }}

    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        border: 1px solid {p.BORDER_HOVER};
        background-color: {p.CONTROL};
    }}

    QCheckBox::indicator:hover {{
        border-color: {p.ACCENT};
    }}

    QCheckBox::indicator:checked {{
        background-color: {p.ACCENT};
        border-color: {p.ACCENT};
    }}

    QDialog,
    QMessageBox {{
        background-color: {p.PANEL_ALT};
        color: {p.TEXT};
    }}

    QMessageBox QLabel {{
        color: {p.TEXT};
        min-width: 320px;
    }}

    QMessageBox QPushButton {{
        min-width: 120px;
        min-height: 26px;
        background-color: {p.CONTROL};
        border: 1px solid {p.BORDER};
    }}

    QMessageBox QPushButton:hover {{
        background-color: {p.CONTROL_HOVER};
        border-color: {p.ACCENT};
    }}

    QToolTip {{
        background-color: {p.PANEL_ALT};
        color: {p.TEXT_BRIGHT};
        border: 1px solid {p.BORDER_HOVER};
        padding: 4px 6px;
    }}

    /* Stage 3.2A.5 */

    /* One uninterrupted central preview surface. */
    QWidget#centralPreviewArea,
    QWidget#centralPreviewArea QWidget,
    QGraphicsView#texturePreview,
    QWidget#zoomBar,
    QWidget#textureInfoPanel,
    QWidget#textureInfoPanel QFrame {{
        background-color: {p.CENTRAL};
        border: none;
    }}

    QWidget#centralPreviewArea QPushButton,
    QWidget#centralPreviewArea QToolButton {{
        background-color: transparent;
    }}

    QWidget#zoomBar {{
        border-top: 1px solid {p.BORDER_SOFT};
        border-bottom: 1px solid {p.BORDER_SOFT};
    }}

    QWidget#zoomBar QPushButton {{
        min-width: 34px;
        padding-left: 5px;
        padding-right: 5px;
    }}

    QLabel#zoomValueLabel {{
        min-width: 42px;
        color: {p.TEXT_MUTED};
        padding-left: 5px;
        padding-right: 5px;
    }}

    QWidget#textureInfoPanel QToolButton#textureInfoToggle {{
        min-height: 25px;
        padding-left: 7px;
        text-align: left;
        color: {p.TEXT_HEADER};
        background-color: {p.PANEL};
        border-top: 1px solid {p.BORDER};
        font-size: 8pt;
        font-weight: 700;
        border-bottom: none;
    }}

    QWidget#textureInfoPanel QToolButton#textureInfoToggle:hover {{
        background-color: {p.CONTROL_HOVER};
        border-top-color: {p.ACCENT};
    }}

    QWidget#textureInfoPanel QToolButton#textureInfoToggle:checked {{
        background-color: {p.PANEL};
        border-top: 1px solid {p.ACCENT};
        border-bottom: none;
    }}

    /* The workspace dock has no separate title strip. */
    QWidget#workspaceTitleBar {{
        min-height: 0px;
        max-height: 0px;
        margin: 0;
        padding: 0;
        border: none;
        background: transparent;
    }}

    QDockWidget#workspaceDock {{
        border: none;
    }}

    QMainWindow::separator {{
        background-color: {p.SPLITTER};
        width: 4px;
        height: 4px;
    }}

    QMainWindow::separator:hover {{
        background-color: {p.SPLITTER_HOVER};
    }}

    QSplitter::handle {{
        background-color: {p.SPLITTER};
    }}

    QSplitter::handle:hover {{
        background-color: {p.SPLITTER_HOVER};
    }}

    QSplitter::handle:horizontal {{
        width: 5px;
    }}

    QSplitter::handle:vertical {{
        height: 5px;
    }}

    QComboBox QAbstractItemView::item {{
        min-height: 24px;
        padding: 3px 6px;
    }}

    /* Compact and centered application messages. */
    QMessageBox {{
        min-width: 0px;
    }}

    QMessageBox QLabel {{
        min-width: 0px;
        max-width: 360px;
        color: {p.TEXT};
        qproperty-alignment: AlignCenter;
    }}

    QMessageBox QDialogButtonBox {{
        qproperty-centerButtons: true;
    }}

    QMessageBox QDialogButtonBox QPushButton,
    QMessageBox QPushButton {{
        min-width: 100px;
        max-width: 150px;
        min-height: 26px;
        padding-left: 12px;
        padding-right: 12px;
    }}


    /* Stage 3.2A.5.2 — deterministic WT Studio message dialogs. */
    QDialog#wtMessageBox {{
        background-color: {p.PANEL_ALT};
        color: {p.TEXT};
        border: none;
    }}

    QDialog#wtMessageBox QLabel#messageBoxText {{
        color: {p.TEXT};
        background: transparent;
        min-width: 460px;
        max-width: 620px;
        font-weight: 500;
    }}

    QDialog#wtMessageBox QLabel#messageBoxInformativeText {{
        color: {p.TEXT};
        background: transparent;
        min-width: 460px;
        max-width: 620px;
    }}

    QDialog#wtMessageBox QLabel#messageBoxIcon {{
        min-width: 48px;
        max-width: 48px;
        min-height: 48px;
        max-height: 48px;
        background: transparent;
    }}

    QDialog#wtMessageBox QFrame#messageBoxDetailsFrame {{
        background-color: {p.CENTRAL};
        border: 1px solid {p.BORDER};
    }}

    QDialog#wtMessageBox QPlainTextEdit#messageBoxDetails {{
        background-color: {p.CENTRAL};
        color: {p.TEXT};
        border: none;
        padding: 7px;
        selection-background-color: {p.SELECTION};
        selection-color: {p.TEXT_BRIGHT};
    }}

    QDialog#wtMessageBox QPushButton#messageBoxStandardButton,
    QDialog#wtMessageBox QPushButton#messageBoxDetailsButton {{
        min-width: 0px;
        min-height: 30px;
        background-color: transparent;
        color: {p.TEXT};
        border: 1px solid transparent;
        padding-left: 12px;
        padding-right: 12px;
    }}

    /*
       Focus/default must remain visually neutral, but this rule has to appear
       before :hover. A focused button can also be hovered; the later hover
       rule must win so every alert action highlights consistently.
    */
    QDialog#wtMessageBox QPushButton#messageBoxStandardButton:focus,
    QDialog#wtMessageBox QPushButton#messageBoxDetailsButton:focus,
    QDialog#wtMessageBox QPushButton#messageBoxStandardButton:default {{
        background-color: transparent;
        border-color: transparent;
        color: {p.TEXT};
    }}

    QDialog#wtMessageBox QPushButton#messageBoxStandardButton:hover,
    QDialog#wtMessageBox QPushButton#messageBoxDetailsButton:hover,
    QDialog#wtMessageBox QPushButton#messageBoxStandardButton:focus:hover,
    QDialog#wtMessageBox QPushButton#messageBoxDetailsButton:focus:hover,
    QDialog#wtMessageBox QPushButton#messageBoxStandardButton:default:hover {{
        background-color: {p.CONTROL_HOVER};
        border-color: {p.BORDER_HOVER};
        color: {p.TEXT_BRIGHT};
    }}

    QDialog#wtMessageBox QPushButton#messageBoxStandardButton:pressed,
    QDialog#wtMessageBox QPushButton#messageBoxDetailsButton:pressed,
    QDialog#wtMessageBox QPushButton#messageBoxStandardButton:focus:pressed,
    QDialog#wtMessageBox QPushButton#messageBoxDetailsButton:focus:pressed {{
        background-color: {p.CONTROL_PRESSED};
        border-color: {p.BORDER_HOVER};
        color: {p.TEXT_BRIGHT};
    }}

    /* Stage 3.2C.2 — unified material export actions. */
    QDialog#materialExportDialog QDialogButtonBox#materialExportButtonBox,
    QDialog#projectIdentityDialog QDialogButtonBox#projectIdentityButtonBox {{
        qproperty-centerButtons: true;
        background: transparent;
        padding-top: 8px;
    }}

    QDialog#materialExportDialog QPushButton#dialogActionButton,
    QDialog#projectIdentityDialog QPushButton#dialogActionButton {{
        min-width: 160px;
        min-height: 30px;
        background-color: transparent;
        color: {p.TEXT};
        border: 1px solid transparent;
        padding-left: 14px;
        padding-right: 14px;
    }}

    QDialog#materialExportDialog QPushButton#dialogActionButton:hover,
    QDialog#projectIdentityDialog QPushButton#dialogActionButton:hover {{
        background-color: {p.CONTROL_HOVER};
        border-color: {p.BORDER_HOVER};
        color: {p.TEXT_BRIGHT};
    }}

    QDialog#materialExportDialog QPushButton#dialogActionButton:pressed,
    QDialog#projectIdentityDialog QPushButton#dialogActionButton:pressed {{
        background-color: {p.CONTROL_PRESSED};
        border-color: {p.BORDER_HOVER};
    }}

    QDialog#materialExportDialog QPushButton#dialogActionButton:focus,
    QDialog#projectIdentityDialog QPushButton#dialogActionButton:focus {{
        background-color: transparent;
        border-color: {p.BORDER_SOFT};
        color: {p.TEXT};
    }}


    /* Stage 3.2D.1 — unified custom window chrome. */
    QMainWindow {{
        border: none;
    }}

    QWidget#mainTitleBar {{
        background-color: {p.WINDOW};
        border: none;
        border-bottom: 1px solid {p.BORDER_SOFT};
    }}

    QWidget#dialogTitleBar {{
        background-color: {p.PANEL_ALT};
        border: none;
    }}

    QMenuBar#titleMenuBar {{
        background: transparent;
        color: {p.TEXT_MUTED};
        border: none;
        padding: 0px;
        spacing: 1px;
    }}

    QMenuBar#titleMenuBar::item {{
        background: transparent;
        padding: 7px 8px;
        margin: 0px;
    }}

    QMenuBar#titleMenuBar::item:selected,
    QMenuBar#titleMenuBar::item:pressed {{
        background-color: {p.CONTROL_HOVER};
        color: {p.TEXT_BRIGHT};
    }}

    QLabel#windowLogo,
    QLabel#windowTitleLabel {{
        background: transparent;
        border: none;
    }}

    QLabel#windowTitleLabel {{
        color: {p.TEXT_MUTED};
        font-size: 8.5pt;
        padding-left: 8px;
        padding-right: 8px;
    }}

    QToolButton#windowMinimizeButton,
    QToolButton#windowMaximizeButton,
    QToolButton#windowCloseButton {{
        min-width: 44px;
        max-width: 44px;
        min-height: 30px;
        max-height: 34px;
        margin: 0px;
        padding: 0px;
        background: transparent;
        border: none;
    }}

    QToolButton#windowMinimizeButton:hover,
    QToolButton#windowMaximizeButton:hover {{
        background-color: {p.CONTROL_HOVER};
        border: none;
    }}

    QToolButton#windowMinimizeButton:pressed,
    QToolButton#windowMaximizeButton:pressed {{
        background-color: {p.CONTROL_PRESSED};
        border: none;
    }}

    QToolButton#windowCloseButton:hover {{
        background-color: #c42b1c;
        border: none;
    }}

    QToolButton#windowCloseButton:pressed {{
        background-color: #a92317;
        border: none;
    }}

    QDialog#wtMessageBox,
    QDialog#materialExportDialog,
    QDialog#projectIdentityDialog,
    QDialog#operationProgressDialog {{
        background-color: {p.PANEL_ALT};
        border: none;
    }}

    QWidget#messageBoxBody {{
        background-color: {p.PANEL_ALT};
        border: none;
    }}


    /* Stage 3.2F.1 — large Welcome / Quick Start screen. */
    QDialog#welcomeWindow {{
        background-color: {p.PANEL_ALT};
        border: none;
    }}

    QWidget#welcomeBody,
    QWidget#welcomeHomePage,
    QWidget#welcomeProjectsPage,
    QStackedWidget#welcomePages {{
        background-color: {p.PANEL_ALT};
        border: none;
    }}

    QLabel#welcomeLogo {{
        background: transparent;
        border: none;
    }}

    QLabel#welcomeTitle {{
        color: {p.TEXT_BRIGHT};
        font-size: 22pt;
        font-weight: 700;
        letter-spacing: 2px;
        padding-top: 2px;
    }}

    QLabel#welcomeVersion {{
        color: {p.ACCENT};
        font-size: 9pt;
        font-weight: 600;
        padding-top: 3px;
    }}

    QLabel#welcomeSubtitle {{
        color: {p.TEXT_MUTED};
        font-size: 10pt;
        padding-top: 12px;
    }}

    QFrame#welcomeActionColumn {{
        background: transparent;
        border: none;
    }}

    QPushButton#welcomePrimaryButton {{
        min-height: 50px;
        max-height: 50px;
        background-color: {p.PANEL_ALT};
        color: {p.TEXT_BRIGHT};
        border: 1px solid {p.BORDER};
        padding: 0px 18px;
        font-size: 11pt;
        font-weight: 600;
    }}

    QPushButton#welcomePrimaryButton:hover {{
        background-color: {p.CONTROL_HOVER};
        color: {p.TEXT_BRIGHT};
        border-color: {p.ACCENT};
    }}

    QPushButton#welcomePrimaryButton:pressed {{
        background-color: {p.CONTROL_PRESSED};
        border-color: {p.ACCENT_PRESSED};
    }}

    QPushButton#welcomePrimaryButton:disabled {{
        background-color: {p.PANEL_ALT};
        color: {p.TEXT_DISABLED};
        border-color: {p.BORDER_SOFT};
    }}

    QLabel#welcomeActionDescription {{
        color: {p.TEXT_MUTED};
        font-size: 9pt;
    }}

    QLabel#welcomeHint {{
        color: {p.TEXT_DISABLED};
        font-size: 8.5pt;
    }}

    QPushButton#welcomeSecondaryButton {{
        background-color: transparent;
        color: {p.TEXT};
        border: 1px solid transparent;
        font-size: 9pt;
    }}

    QPushButton#welcomeSecondaryButton:hover {{
        background-color: {p.CONTROL_HOVER};
        color: {p.TEXT_BRIGHT};
        border-color: {p.BORDER_HOVER};
    }}

    QLabel#welcomeProjectsTitle {{
        color: {p.TEXT_BRIGHT};
        font-size: 18pt;
        font-weight: 600;
    }}

    QLabel#welcomeProjectsSubtitle {{
        color: {p.TEXT_MUTED};
        font-size: 9.5pt;
    }}

    QFrame#welcomeProjectBrowserFrame {{
        background-color: {p.CENTRAL};
        border: 1px solid {p.BORDER};
    }}

    QTreeWidget#welcomeProjectBrowser {{
        background-color: {p.CENTRAL};
        color: {p.TEXT};
        border: none;
        padding: 8px;
    }}

    QTreeWidget#welcomeProjectBrowser::item {{
        min-height: 28px;
        padding-left: 6px;
    }}


    /* Stage 3.2F.2 — complete Help window. */
    QDialog#helpAboutWindow,
    QWidget#helpAboutBody,
    QWidget#helpContent,
    QScrollArea#helpScrollArea,
    QScrollArea#helpScrollArea > QWidget,
    QScrollArea#helpScrollArea > QWidget > QWidget {{
        background-color: {p.PANEL_ALT};
        border: none;
    }}

    QLabel#helpAboutIllustration {{
        background-color: transparent;
        border: none;
    }}

    QLabel#helpSectionTitle {{
        color: {p.TEXT_BRIGHT};
        background-color: transparent;
        border: none;
        font-size: 13pt;
        font-weight: 700;
        padding: 0px;
    }}

    QLabel#helpSectionBody {{
        color: {p.TEXT};
        background-color: transparent;
        border: none;
        font-size: 9.5pt;
        line-height: 1.35;
        padding: 0px;
    }}

    QCheckBox#helpAboutDontShowCheckBox {{
        color: {p.TEXT_MUTED};
        spacing: 8px;
        font-size: 9pt;
    }}

    QCheckBox#helpAboutDontShowCheckBox::indicator {{
        width: 14px;
        height: 14px;
        background-color: {p.PANEL_ALT};
        border: 1px solid {p.BORDER_HOVER};
    }}

    QCheckBox#helpAboutDontShowCheckBox::indicator:hover {{
        border-color: {p.ACCENT};
    }}

    QCheckBox#helpAboutDontShowCheckBox::indicator:checked {{
        background-color: {p.ACCENT};
        border-color: {p.ACCENT};
    }}

    QPushButton#helpAboutOkButton {{
        background-color: {p.PANEL_ALT};
        color: {p.TEXT_BRIGHT};
        border: 1px solid {p.BORDER};
        font-size: 9.5pt;
        font-weight: 600;
    }}

    QPushButton#helpAboutOkButton:hover {{
        background-color: {p.CONTROL_HOVER};
        border-color: {p.ACCENT};
    }}

    QPushButton#helpAboutOkButton:pressed {{
        background-color: {p.CONTROL_PRESSED};
        border-color: {p.ACCENT_PRESSED};
    }}
    """
