# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import os

ROOT = Path(SPECPATH).resolve().parent
SRC = ROOT / "src"
DEBUG_BUILD = os.environ.get("WT_STUDIO_BUILD_DEBUG", "0") == "1"

APP_NAME = "WT Studio Debug" if DEBUG_BUILD else "WT Studio"

datas = [
    (
        str(SRC / "ui" / "resources" / "icons"),
        "ui/resources/icons",
    ),
]

a = Analysis(
    [str(SRC / "main.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "texture2ddecoder",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=DEBUG_BUILD,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "build" / "WT_Studio.ico"),
    version=str(ROOT / "build" / "windows_version_info.txt"),
    contents_directory="_internal",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)
