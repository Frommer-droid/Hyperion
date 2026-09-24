"""
Модуль работы с конфигурацией.

Содержит:
- Загрузка/сохранение config.json
- Дефолтная конфигурация
- Миграция версий конфига
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
import sys

from .json_store import atomic_write_json, backup_corrupt_json


CURRENT_CONFIG_VERSION = 2


@dataclass
class ConfigData:
    """Структура данных конфигурации."""

    enabled: bool = True
    tap_behavior: str = "capslock"
    hold_behavior: str = "hyper"
    hyper_modifiers: list[str] = field(default_factory=lambda: ["CTRL", "SHIFT", "ALT", "WIN"])
    ignore_top_number_row: bool = True
    ignore_function_keys: bool = True
    capture_numpad: bool = True
    ignore_injected_events: bool = True
    process_blacklist: list[dict] = field(default_factory=list)  # [{name: str, enabled: bool}]

    # Маппинги: key_id -> буква/numpad
    letters_sc_map: dict[str, str] = field(default_factory=dict)
    numpad_sc_map: dict[str, str] = field(default_factory=dict)

    # Кастомный вывод: key_id -> {vk: "VK_...", mods: [...]}
    output_map: dict[str, dict] = field(default_factory=dict)

    # Разрешённые клавиши (заполняются при калибровке)
    allowed_main_keys: list[str] = field(default_factory=list)
    allowed_numpad_keys: list[str] = field(default_factory=list)

    # Версия конфига для миграций
    config_version: int = CURRENT_CONFIG_VERSION


def get_default_config() -> ConfigData:
    """
    Получить дефолтную конфигурацию.

    Returns:
        Экземпляр ConfigData с дефолтными значениями
    """
    return ConfigData()


def get_config_path() -> Path:
    """
    Получить путь к файлу конфигурации.

    По умолчанию config.json в директории приложения.

    Returns:
        Path к config.json
    """
    if getattr(sys, "frozen", False):
        base_path = Path(sys.executable).parent
    else:
        # src/hyperion/services/config.py -> корень
        base_path = Path(__file__).resolve().parent.parent.parent.parent  # src/../..
    return base_path / "config.json"


def load_config(path: Optional[Path] = None) -> ConfigData:
    """
    Загрузить конфигурацию из файла.

    Args:
        path: Путь к файлу (если None, использует get_config_path())

    Returns:
        Загруженная конфигурация

    Raises:
        FileNotFoundError: Если файл не существует
        json.JSONDecodeError: Если JSON некорректный
    """
    if path is None:
        path = get_config_path()

    if not path.exists():
        # Пробуем скопировать из example
        example_path = path.parent / "config.example.json"
        if example_path.exists():
            import shutil

            shutil.copy(example_path, path)
        else:
            raise FileNotFoundError(f"Config not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        backup = backup_corrupt_json(path)
        exc.add_note(f"Повреждённый config сохранён: {backup}")
        raise

    # Миграция старого формата blacklist (list[str] -> list[dict])
    raw_blacklist = data.get("process_blacklist", [])
    if raw_blacklist and isinstance(raw_blacklist[0], str):
        # Старый формат: ["notepad.exe", "game.exe"]
        raw_blacklist = [{"name": p, "enabled": True} for p in raw_blacklist]

    # Создаём ConfigData из словаря
    config = ConfigData(
        enabled=data.get("enabled", True),
        tap_behavior=data.get("tap_behavior", "capslock"),
        hold_behavior=data.get("hold_behavior", "hyper"),
        hyper_modifiers=data.get("hyper_modifiers", ["CTRL", "SHIFT", "ALT", "WIN"]),
        ignore_top_number_row=data.get("ignore_top_number_row", True),
        ignore_function_keys=data.get("ignore_function_keys", True),
        capture_numpad=data.get("capture_numpad", True),
        ignore_injected_events=data.get("ignore_injected_events", True),
        process_blacklist=raw_blacklist,
        letters_sc_map=data.get("letters_sc_map", {}),
        numpad_sc_map=data.get("numpad_sc_map", {}),
        output_map=data.get("output_map", {}),
        allowed_main_keys=data.get("allowed_main_keys", []),
        allowed_numpad_keys=data.get("allowed_numpad_keys", []),
        config_version=max(int(data.get("config_version", 1)), CURRENT_CONFIG_VERSION),
    )

    return config


def save_config(config: ConfigData, path: Optional[Path] = None) -> None:
    """
    Сохранить конфигурацию в файл.

    Args:
        config: Конфигурация для сохранения
        path: Путь к файлу (если None, использует get_config_path())
    """
    if path is None:
        path = get_config_path()

    # Преобразуем dataclass в dict
    data = asdict(config)

    atomic_write_json(path, data)


def config_to_engine_config(config_data: ConfigData):
    """
    Преобразовать ConfigData в Config для Engine.

    Args:
        config_data: Данные конфигурации

    Returns:
        Экземпляр Config для Engine
    """
    from ..runtime.engine import Config

    return Config(
        enabled=config_data.enabled,
        hyper_modifiers=config_data.hyper_modifiers.copy(),
        ignore_top_number_row=config_data.ignore_top_number_row,
        ignore_function_keys=config_data.ignore_function_keys,
        capture_numpad=config_data.capture_numpad,
        ignore_injected_events=config_data.ignore_injected_events,
        process_blacklist=config_data.process_blacklist.copy(),
        letters_sc_map=config_data.letters_sc_map.copy(),
        numpad_sc_map=config_data.numpad_sc_map.copy(),
        output_map=config_data.output_map.copy(),
        allowed_main_keys=set(config_data.allowed_main_keys),
        allowed_numpad_keys=set(config_data.allowed_numpad_keys),
    )
