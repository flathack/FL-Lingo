# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

project_root = Path(SPECPATH)
src_dir = project_root / "src"
data_files = collect_data_files("flatlas_translator", include_py_files=False)
data_files.extend(
    [
        (str(project_root / "scripts" / "install_ids_toolchain_windows.cmd"), "scripts"),
        (str(project_root / "scripts" / "install_fllingo_file_association.cmd"), "scripts"),
        (str(project_root / "images" / "FLLingo-JuniIcon-Clean.png"), "images"),
        (str(project_root / "images" / "FLLingo-JuniIcon-Clean.ico"), "images"),
        (str(project_root / "data"), "data"),
        (str(project_root / "Languages"), "Languages"),
    ]
)

analysis = Analysis(
    [str(project_root / "launch.py")],
    pathex=[str(project_root), str(src_dir)],
    binaries=[],
    datas=data_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="FL-Lingo",
    icon=str(project_root / "images" / "FLLingo-JuniIcon-Clean.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FL-Lingo",
)
