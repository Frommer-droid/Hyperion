"""Сборка Hyperion Setup через Inno Setup без запуска установщика или приложения."""

from __future__ import annotations

import os
import shutil
import string
import subprocess
import tempfile
from pathlib import Path


APP_NAME = "Hyperion"
APP_PUBLISHER = "Frommer-droid"
APP_ID = "{{32F7695C-F7C6-449B-8A24-9F6B2436911D}"
REQUIRED_ITEMS = (
    "Hyperion.exe",
    "_internal",
    "VERSION",
    "logo.ico",
    "RUNTIME_MANIFEST.json",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "SOURCE_CODE_ACCESS.md",
    "QT_PYSIDE6_COMPLIANCE.md",
)
RUNTIME_NOISE = {"config.json", "settings.json", "hyperion.log"}


def resolve_desktop_dir() -> Path:
    override = os.environ.get("HYPERION_DESKTOP_DIR", "").strip()
    if override:
        return Path(override)
    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value, _ = winreg.QueryValueEx(key, "Desktop")
        return Path(os.path.expandvars(value))
    except Exception:
        return Path.home() / "Desktop"


def fixed_drives() -> list[Path]:
    try:
        import ctypes

        return [
            Path(f"{letter}:\\")
            for letter in string.ascii_uppercase
            if ctypes.windll.kernel32.GetDriveTypeW(f"{letter}:\\") == 3
        ]
    except Exception:
        return [Path("C:\\")]


def default_install_dir() -> Path:
    drives = fixed_drives()
    for drive in drives:
        if str(drive).upper().startswith("D:"):
            return drive / "Apps" / APP_NAME
    for drive in drives:
        if not str(drive).upper().startswith("C:"):
            return drive / "Apps" / APP_NAME
    return Path(r"C:\Apps") / APP_NAME


def find_iscc() -> Path | None:
    candidates = (
        os.environ.get("INNO_SETUP_ISCC", ""),
        shutil.which("ISCC.exe") or "",
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    )
    for candidate in candidates:
        path = Path(candidate) if candidate else None
        if path is not None and path.is_file():
            return path
    return None


def validate_release(source: Path) -> list[str]:
    return [item for item in REQUIRED_ITEMS if not (source / item).exists()]


def remove_runtime_noise(work_dir: Path) -> None:
    for path in work_dir.rglob("*"):
        if path.is_file() and (path.name.lower() in RUNTIME_NOISE or path.suffix.lower() == ".log"):
            path.unlink()


def inno_script(source: Path, output: Path, version: str) -> str:
    return f"""#define MyAppName \"{APP_NAME}\"
#define MyAppVersion \"{version}\"
#define MyAppPublisher \"{APP_PUBLISHER}\"
#define MyAppExeName \"Hyperion.exe\"

[Setup]
AppId={APP_ID}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
DefaultDirName=\"{default_install_dir()}\"
UsePreviousAppDir=no
DefaultGroupName={{#MyAppName}}
DisableProgramGroupPage=yes
OutputDir=\"{output}\"
OutputBaseFilename=Hyperion_v{{#MyAppVersion}}_Setup
SetupIconFile=\"{source / 'logo.ico'}\"
UninstallDisplayIcon={{app}}\\{{#MyAppExeName}}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion={{#MyAppVersion}}.0
VersionInfoCompany={{#MyAppPublisher}}
VersionInfoDescription={{#MyAppName}} Setup
VersionInfoProductName={{#MyAppName}}

[Languages]
Name: \"russian\"; MessagesFile: \"compiler:Languages\\Russian.isl\"

[Tasks]
Name: \"desktopicon\"; Description: \"Создать значок на рабочем столе\"; GroupDescription: \"Дополнительные значки:\"; Flags: checkedonce

[Files]
Source: \"{source}\\*\"; DestDir: \"{{app}}\"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: \"{{group}}\\{{#MyAppName}}\"; Filename: \"{{app}}\\{{#MyAppExeName}}\"; IconFilename: \"{{app}}\\logo.ico\"
Name: \"{{group}}\\Удалить {{#MyAppName}}\"; Filename: \"{{uninstallexe}}\"
Name: \"{{autodesktop}}\\{{#MyAppName}}\"; Filename: \"{{app}}\\{{#MyAppExeName}}\"; IconFilename: \"{{app}}\\logo.ico\"; Tasks: desktopicon

[Run]
Filename: \"{{app}}\\{{#MyAppExeName}}\"; Description: \"Запустить {{#MyAppName}}\"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: \"taskkill\"; Parameters: \"/F /IM {{#MyAppExeName}}\"; Flags: runhidden; RunOnceId: \"KillApp\"

[UninstallDelete]
Type: filesandordirs; Name: \"{{app}}\"
"""


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    release_dir = project_root / APP_NAME
    output_dir = resolve_desktop_dir()
    iscc = find_iscc()
    if iscc is None:
        print("[ERROR] Не найден Inno Setup 6 ISCC.exe")
        return 1
    missing = validate_release(release_dir)
    if missing:
        print("[ERROR] Неполная release-папка: " + ", ".join(missing))
        return 1

    version = (project_root / "VERSION").read_text(encoding="utf-8").strip()
    output_dir.mkdir(parents=True, exist_ok=True)
    installer_path = output_dir / f"{APP_NAME}_v{version}_Setup.exe"
    installer_path.unlink(missing_ok=True)

    with tempfile.TemporaryDirectory(prefix="Hyperion_installer_") as temp_dir:
        work_dir = Path(temp_dir) / APP_NAME
        shutil.copytree(release_dir, work_dir)
        remove_runtime_noise(work_dir)
        iss_path = Path(temp_dir) / "Hyperion.iss"
        iss_path.write_text(inno_script(work_dir, output_dir, version), encoding="utf-8-sig")
        subprocess.run([str(iscc), str(iss_path)], check=True)

    if not installer_path.is_file():
        print(f"[ERROR] Inno Setup не создал: {installer_path}")
        return 1
    print(f"[OK] Установщик создан без запуска: {installer_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
