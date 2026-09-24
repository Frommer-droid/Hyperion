"""
Сервис логирования событий.

Содержит:
- EventLog — кольцевой буфер логов
- Потокобезопасный доступ
- Фильтрация по типу
"""

import threading
from collections import deque
from dataclasses import dataclass
from typing import Literal, Optional
import time
from pathlib import Path


@dataclass
class LogEntry:
    """Запись в логе."""

    timestamp: float
    event_type: Literal[
        "sent_combo",
        "recorded_key",
        "ignored_key",
        "state_change",
        "error",
    ]
    key_id: Optional[str] = None
    vk_code: Optional[int] = None
    scan_code: Optional[int] = None
    extended: Optional[bool] = None
    details: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "LogEntry":
        """Создать LogEntry из словаря (UI-события)."""
        return cls(
            timestamp=data.get("ts_ms", time.time() * 1000) / 1000,
            event_type=data.get("type", "state_change"),
            key_id=data.get("key_id"),
            vk_code=data.get("vk_code"),
            scan_code=data.get("scan_code"),
            extended=data.get("extended"),
            details=data.get("details", ""),
        )

    def format_line(self) -> str:
        """Форматировать запись для отображения."""
        ts_str = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        ms = int((self.timestamp % 1) * 1000)

        parts = [f"[{ts_str}.{ms:03d}]"]

        if self.event_type == "sent_combo":
            parts.append("SENT")
        elif self.event_type == "recorded_key":
            parts.append("REC ")
        elif self.event_type == "ignored_key":
            parts.append("SKIP")
        elif self.event_type == "state_change":
            parts.append("INFO")
        elif self.event_type == "error":
            parts.append("ERR ")
        else:
            parts.append("    ")

        if self.key_id:
            parts.append(f"{self.key_id}")

        if self.details:
            parts.append(f"- {self.details}")

        return " ".join(parts)


class EventLog:
    """
    Кольцевой буфер логов с потокобезопасным доступом.

    Хранит последние N записей (по умолчанию 500).
    """

    def __init__(self, max_size: int = 500):
        """
        Инициализировать лог.

        Args:
            max_size: Максимальное количество записей
        """
        self._buffer: deque[LogEntry] = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def add(self, entry: LogEntry) -> None:
        """
        Добавить запись в лог.

        Args:
            entry: Запись лога
        """
        with self._lock:
            self._buffer.append(entry)

    def add_from_dict(self, data: dict) -> None:
        """
        Добавить запись из словаря (UI-события).

        Args:
            data: Словарь с данными события
        """
        entry = LogEntry.from_dict(data)
        self.add(entry)

    def get_all(self) -> list[LogEntry]:
        """
        Получить все записи.

        Returns:
            Копия списка записей (от старых к новым)
        """
        with self._lock:
            return list(self._buffer)

    def get_last(self, count: int = 50) -> list[LogEntry]:
        """
        Получить последние N записей.

        Args:
            count: Количество записей

        Returns:
            Список последних записей
        """
        with self._lock:
            entries = list(self._buffer)
            return entries[-count:] if len(entries) > count else entries

    def get_filtered(
        self,
        event_types: Optional[list[str]] = None,
        limit: int = 100,
    ) -> list[LogEntry]:
        """
        Получить записи с фильтрацией по типу.

        Args:
            event_types: Список типов для фильтрации (None = все)
            limit: Максимальное количество записей

        Returns:
            Отфильтрованный список записей
        """
        with self._lock:
            if event_types is None:
                entries = list(self._buffer)
            else:
                entries = [
                    e for e in self._buffer
                    if e.event_type in event_types
                ]

            return entries[-limit:] if len(entries) > limit else entries

    def clear(self) -> None:
        """Очистить лог."""
        with self._lock:
            self._buffer.clear()

    def __len__(self) -> int:
        """Количество записей в логе."""
        with self._lock:
            return len(self._buffer)

    def save_to_file(self, config_path: str) -> None:
        """Сохранить лог в файл (в корень проекта)."""
        try:
            # Лог файл в корне проекта: hyperion.log
            # config_path указывает на config.json в корне
            root_dir = Path(config_path).parent
            log_file = root_dir / "hyperion.log"
            
            with self._lock:
                lines = [entry.format_line() for entry in self._buffer]
            
            # Перезаписываем файл ('w'), сохраняя только текущую сессию
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
                
            print(f"Log saved to {log_file}")
        except Exception as e:
            print(f"Failed to save log: {e}")
