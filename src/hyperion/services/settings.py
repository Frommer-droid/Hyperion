"""
Сервис настроек приложения (settings.json).

Сохраняет и восстанавливает:
- Геометрию окна (x, y, width, height)
- Состояние развернутости (maximized)
- Запуск свёрнутым в трей
- Автозагрузка при старте Windows
"""

import ctypes
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from .json_store import atomic_write_json, backup_corrupt_json


@dataclass
class WindowSettings:
    """Настройки окна."""

    x: int = 100
    y: int = 100
    width: int = 700
    height: int = 500
    maximized: bool = False


@dataclass
class Settings:
    """Настройки приложения."""

    window: WindowSettings = field(default_factory=WindowSettings)
    font_size: int = 15  # Размер шрифта интерфейса (10-24)
    start_minimized: bool = False  # Запускать свёрнутым в трей
    autostart: bool = False  # Автозагрузка при старте Windows


def get_settings_path() -> Path:
    """Получить путь к файлу настроек."""
    if getattr(sys, "frozen", False):
        base_path = Path(os.path.dirname(sys.executable))
    else:
        # src/phonetic_hyper/services/settings.py -> корень проекта
        base_path = Path(__file__).resolve().parent.parent.parent.parent
    return base_path / "settings.json"


def get_app_executable_path() -> Path:
    """Получить путь к исполняемому файлу приложения."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    else:
        # В режиме разработки возвращаем run.py
        return Path(__file__).resolve().parent.parent.parent.parent / "run.py"


def get_autostart_command() -> tuple[Path, str]:
    """Получить исполняемый файл и аргументы для windowless-автозапуска."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable), ""

    run_path = get_app_executable_path()
    python_path = Path(sys.executable)
    pythonw_path = python_path.with_name("pythonw.exe")
    if not pythonw_path.exists():
        pythonw_path = python_path
    return pythonw_path, f'"{run_path}"'


def _vbs_string(value: object) -> str:
    """Экранировать значение для строкового литерала VBScript."""
    return str(value).replace('"', '""')


def get_startup_folder() -> Path:
    """Получить путь к папке автозагрузки Windows."""
    buffer = ctypes.create_unicode_buffer(260)
    # CSIDL_STARTUP остаётся поддерживаемым способом получить реальную Known Folder.
    result = ctypes.windll.shell32.SHGetFolderPathW(None, 0x0007, None, 0, buffer)
    if result == 0 and buffer.value:
        return Path(buffer.value)
    return (
        Path(os.environ.get("APPDATA", ""))
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Startup"
    )


def get_startup_shortcut_path() -> Path:
    """Получить путь к ярлыку в папке автозагрузки."""
    return get_startup_folder() / "Hyperion.lnk"


def is_autostart_enabled() -> bool:
    """Проверить, включена ли автозагрузка."""
    return get_startup_shortcut_path().exists()


def set_autostart(enabled: bool) -> bool:
    """Установить или удалить автозагрузку.

    Returns:
        True если операция успешна, False при ошибке
    """
    shortcut_path = get_startup_shortcut_path()

    if enabled:
        # Создаём ярлык
        vbs_path: Optional[Path] = None
        try:
            # Используем VBScript для создания ярлыка (работает без внешних зависимостей)
            target_path, arguments = get_autostart_command()
            shortcut_path.parent.mkdir(parents=True, exist_ok=True)
            vbs_script = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
Set oLink = oWS.CreateShortcut("{_vbs_string(shortcut_path)}")
oLink.TargetPath = "{_vbs_string(target_path)}"
oLink.Arguments = "{_vbs_string(arguments)}"
oLink.WorkingDirectory = "{_vbs_string(get_app_executable_path().parent)}"
oLink.Description = "Hyperion - CapsLock to Hyper modifier"
oLink.Save
'''
            # Уникальный UTF-16 файл исключает коллизии и корректно хранит
            # не-ASCII пути. Список аргументов не проходит через shell.
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-16",
                suffix=".vbs",
                delete=False,
            ) as handle:
                handle.write(vbs_script)
                vbs_path = Path(handle.name)

            result = subprocess.run(
                ["cscript.exe", "//nologo", str(vbs_path)],
                check=False,
                capture_output=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                timeout=15,
            )
            return result.returncode == 0 and shortcut_path.exists()
        except Exception:
            return False
        finally:
            if vbs_path is not None:
                vbs_path.unlink(missing_ok=True)
    else:
        # Удаляем ярлык
        try:
            if shortcut_path.exists():
                shortcut_path.unlink()
            return True
        except Exception:
            return False


def load_settings(path: Optional[Path] = None) -> Settings:
    """Загрузить настройки из файла."""
    if path is None:
        path = get_settings_path()

    if not path.exists():
        return Settings()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        window_data = data.get("window", {})
        window_settings = WindowSettings(
            x=window_data.get("x", 100),
            y=window_data.get("y", 100),
            width=window_data.get("width", 700),
            height=window_data.get("height", 500),
            maximized=window_data.get("maximized", False),
        )
        return Settings(
            window=window_settings,
            font_size=data.get("font_size", 15),
            start_minimized=data.get("start_minimized", False),
            autostart=data.get("autostart", False),
        )
    except json.JSONDecodeError:
        backup_corrupt_json(path)
        return Settings()
    except Exception:
        return Settings()


def save_settings(settings: Settings, path: Optional[Path] = None) -> None:
    """Сохранить настройки в файл."""
    if path is None:
        path = get_settings_path()

    data = {
        "window": asdict(settings.window),
        "font_size": settings.font_size,
        "start_minimized": settings.start_minimized,
        "autostart": settings.autostart,
    }

    atomic_write_json(path, data)
