# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys

project_root = Path.cwd()
conda_bin = Path(sys.base_prefix) / "Library" / "bin"
icon_path = project_root / "build_assets" / "app_icon.ico"
version_path = project_root / "build_assets" / "version_info.txt"

datas = [
    (str(project_root / "data"), "data"),
]

binaries = [
    (str(conda_bin / "libcrypto-3-x64.dll"), "."),
    (str(conda_bin / "liblzma.dll"), "."),
    (str(conda_bin / "libbz2.dll"), "."),
    (str(conda_bin / "ffi.dll"), "."),
    (str(conda_bin / "libssl-3-x64.dll"), "."),
    (str(conda_bin / "libexpat.dll"), "."),
    (str(conda_bin / "sqlite3.dll"), "."),
]

hiddenimports = [
    "matplotlib.backends.backend_qtagg",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "openpyxl",
    "pandas",
]

a = Analysis(
    ["desktop_app.py"],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="heater-zoning-optimizer",
    icon=str(icon_path),
    version=str(version_path),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
