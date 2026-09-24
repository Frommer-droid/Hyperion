# -*- coding: utf-8 -*-
"""Формирование корневой onedir-папки Hyperion после PyInstaller."""

from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


APP_NAME = "Hyperion"
RUNTIME_MANIFEST_FILENAME = "RUNTIME_MANIFEST.json"
RELEASE_FILES = (
    "VERSION",
    "logo.ico",
    "config.example.json",
    "README.md",
    "README.en.md",
    "RELEASE_NOTES.md",
    "LICENSE",
    "EULA.md",
    "THIRD_PARTY_NOTICES.md",
    "SOURCE_CODE_ACCESS.md",
    "QT_PYSIDE6_COMPLIANCE.md",
)
MANIFEST_PACKAGES = ("PySide6", "shiboken6", "PyInstaller")


def installed_version(package_name: str) -> str | None:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def remove_readonly(func, path, _exc_info) -> None:
    os.chmod(path, 0o700)
    func(path)


def copy_release_file(project_root: Path, target_dir: Path, filename: str) -> bool:
    source = project_root / filename
    if not source.is_file():
        print(f"[ERROR] Не найден обязательный release-файл: {source}")
        return False
    shutil.copy2(source, target_dir / filename)
    print(f"[OK] Скопирован: {filename}")
    return True


def scan_qt_runtime(target_dir: Path) -> dict:
    qt_dlls: list[str] = []
    plugin_directories: set[str] = set()
    for root, dirs, files in os.walk(target_dir):
        root_path = Path(root)
        relative_root = root_path.relative_to(target_dir)
        for filename in files:
            if filename.startswith("Qt") and filename.lower().endswith(".dll"):
                qt_dlls.append((relative_root / filename).as_posix())
        for dirname in dirs:
            if dirname.lower() in {"platforms", "imageformats", "styles", "iconengines", "tls"}:
                plugin_directories.add((relative_root / dirname).as_posix())
    return {
        "qt_dlls": sorted(qt_dlls),
        "qt_plugin_directories": sorted(plugin_directories),
    }


def write_runtime_manifest(project_root: Path, target_dir: Path) -> None:
    packages = {name: installed_version(name) for name in MANIFEST_PACKAGES}
    manifest = {
        "manifest_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "application": {
            "name": APP_NAME,
            "release_version": (project_root / "VERSION").read_text(encoding="utf-8").strip(),
        },
        "build_environment": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "pyinstaller_version": packages["PyInstaller"],
        },
        "bundled_python_packages": packages,
        "qt_runtime": scan_qt_runtime(target_dir),
        "release_documents": [name for name in RELEASE_FILES if (target_dir / name).is_file()],
    }
    (target_dir / RUNTIME_MANIFEST_FILENAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] Создан: {RUNTIME_MANIFEST_FILENAME}")


def cleanup(script_dir: Path, project_root: Path, final_dir: Path) -> None:
    for folder in (
        script_dir / "build",
        script_dir / "dist",
        script_dir / "__pycache__",
        project_root / "build",
        project_root / "dist",
        project_root / "__pycache__",
        final_dir / "__pycache__",
    ):
        if folder.exists():
            shutil.rmtree(folder, onerror=remove_readonly)
            print(f"[OK] Удалена временная папка: {folder}")


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    dist_dir = script_dir / "dist" / APP_NAME
    final_dir = project_root / APP_NAME

    if not dist_dir.is_dir():
        print(f"[ERROR] Не найдена папка PyInstaller: {dist_dir}")
        return 1

    missing = [name for name in RELEASE_FILES if not (project_root / name).is_file()]
    if missing:
        print("[ERROR] Не хватает release-файлов: " + ", ".join(missing))
        return 1

    for filename in RELEASE_FILES:
        if not copy_release_file(project_root, dist_dir, filename):
            return 1

    if final_dir.exists():
        shutil.rmtree(final_dir, onerror=remove_readonly)
    shutil.move(str(dist_dir), str(final_dir))
    print(f"[OK] Сборка перенесена: {final_dir}")

    write_runtime_manifest(project_root, final_dir)
    cleanup(script_dir, project_root, final_dir)

    exe_path = final_dir / f"{APP_NAME}.exe"
    if not exe_path.is_file():
        print(f"[ERROR] Не найден исполняемый файл: {exe_path}")
        return 1

    print(f"[OK] Post-build завершён без запуска приложения: {final_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
