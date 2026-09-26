"""Обновление D:\\Portable_soft\\Hyperion с сохранением пользовательских настроек."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


APP_NAME = "Hyperion"
DESTINATION_PARENT = Path(r"D:\Portable_soft")
PRESERVE_FILES = ("config.json", "settings.json")


def validate_target(target: Path, parent: Path) -> None:
    resolved_parent = parent.resolve()
    resolved_target = target.resolve() if target.exists() else target.absolute()
    if resolved_target == resolved_parent:
        raise RuntimeError("Целевая папка совпадает с родительской")
    resolved_target.relative_to(resolved_parent)


def stop_target_process(target: Path) -> None:
    escaped = str(target.resolve()).replace("'", "''")
    script = (
        f"$root=[IO.Path]::GetFullPath('{escaped}');"
        "if(-not $root.EndsWith([IO.Path]::DirectorySeparatorChar))"
        "{$root += [IO.Path]::DirectorySeparatorChar};"
        "$processes=@(Get-Process -Name 'Hyperion' -ErrorAction SilentlyContinue);"
        "foreach($process in $processes){"
        "try{$path=[IO.Path]::GetFullPath($process.Path)}catch{continue};"
        "if($path.StartsWith($root,[StringComparison]::OrdinalIgnoreCase))"
        "{$process | Stop-Process -Force -ErrorAction Stop}"
        "};exit 0"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        check=True,
        capture_output=True,
    )


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    source = project_root / APP_NAME
    target = DESTINATION_PARENT / APP_NAME
    if not source.is_dir() or not (source / "Hyperion.exe").is_file():
        print(f"[ERROR] Неполная исходная сборка: {source}")
        return 1

    DESTINATION_PARENT.mkdir(parents=True, exist_ok=True)
    validate_target(target, DESTINATION_PARENT)
    preserved = {
        filename: (target / filename).read_bytes()
        for filename in PRESERVE_FILES
        if (target / filename).is_file()
    }

    stop_target_process(target)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    for filename, content in preserved.items():
        (target / filename).write_bytes(content)

    source_version = (source / "VERSION").read_text(encoding="utf-8").strip()
    target_version = (target / "VERSION").read_text(encoding="utf-8").strip()
    if source_version != target_version:
        print("[ERROR] Версии source и portable не совпадают")
        return 1
    print(f"[OK] Portable обновлён без запуска: {target}")
    print("[OK] Сохранены runtime-файлы: " + ", ".join(sorted(preserved)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
