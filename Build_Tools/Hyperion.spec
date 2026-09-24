# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir-конфигурация Hyperion для Windows."""

import os
import sys

import PySide6
from PyInstaller.building.datastruct import Tree


APP_NAME = "Hyperion"
spec_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
project_root = os.path.abspath(os.path.join(spec_dir, ".."))
entrypoint = os.path.join(project_root, "run.py")


def qt_translation_files():
    files = []
    pyside_root = os.path.dirname(PySide6.__file__)
    for relative_dir in ("translations", os.path.join("Qt", "translations")):
        source = os.path.join(pyside_root, relative_dir, "qtbase_ru.qm")
        if os.path.isfile(source):
            files.append((source, os.path.join("PySide6", relative_dir)))
            break
    return files


datas = [
    (os.path.join(project_root, "VERSION"), "."),
    (os.path.join(project_root, "logo.ico"), "."),
]
datas += qt_translation_files()

a = Analysis(
    [entrypoint],
    pathex=[project_root, os.path.join(project_root, "src")],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "hyperion.runtime.engine",
        "hyperion.runtime.hook",
        "hyperion.runtime.input_dispatcher",
        "hyperion.services.config",
        "hyperion.services.localization",
        "hyperion.services.settings",
        "hyperion.services.single_instance",
        "hyperion.services.window_geometry",
        "hyperion.ui.main_window",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "pydoc"],
    noarchive=False,
    optimize=2,
)

# Native DLLs from PATH or unrelated toolchains are a release blocker.
allowed_binary_roots = [
    project_root,
    sys.prefix,
    sys.base_prefix,
    os.environ.get("SystemRoot", r"C:\Windows"),
]
project_binary_allowlist = []
allowed_binary_roots += project_binary_allowlist
allowed_binary_roots = [os.path.normcase(os.path.realpath(root)) for root in allowed_binary_roots]
foreign_binaries = []
for destination, source, _typecode in a.binaries:
    resolved_source = os.path.normcase(os.path.realpath(source))
    trusted = False
    for root in allowed_binary_roots:
        try:
            if os.path.commonpath((resolved_source, root)) == root:
                trusted = True
                break
        except ValueError:  # Paths on different Windows drives.
            continue
    if not trusted:
        foreign_binaries.append((destination, source))
if foreign_binaries:
    details = "\n".join(f"  {destination}: {source}" for destination, source in foreign_binaries)
    raise RuntimeError("PyInstaller found binaries outside trusted roots:\n" + details)

# Qt and Python may ship different MSVC runtimes. The root bundle must use one
# complete set from the same PySide6 installation that supplies Qt6*.dll.
pyside_root = os.path.dirname(PySide6.__file__)
runtime_names = (
    "concrt140.dll",
    "msvcp140.dll",
    "msvcp140_1.dll",
    "msvcp140_2.dll",
    "msvcp140_codecvt_ids.dll",
    "vcamp140.dll",
    "vccorlib140.dll",
    "vcomp140.dll",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
)
for name in runtime_names:
    source = os.path.join(pyside_root, name)
    if not os.path.isfile(source):
        raise RuntimeError(f"PySide6 MSVC runtime is incomplete: {source}")
root_runtime_names = {name.casefold() for name in runtime_names}
a.binaries = [
    entry for entry in a.binaries
    if entry[0].replace("\\", "/").split("/")[-1].casefold() not in root_runtime_names
    or "/" in entry[0].replace("\\", "/")
]
for name in runtime_names:
    a.binaries.append((name, os.path.join(pyside_root, name), "BINARY"))

assets_dir = os.path.join(project_root, "assets")
if os.path.isdir(assets_dir):
    a.datas += Tree(assets_dir, prefix="assets")

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
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=os.path.join(project_root, "logo.ico"),
    version=os.path.join(spec_dir, "file_version_info.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
