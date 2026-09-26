"""
State machine для tap-vs-hold логики CapsLock.

Содержит:
- EngineState — состояние движка
- KeyEvent — входное событие клавиатуры
- EngineAction — выходные действия (suppress, send_combo, ui_event)
- Engine — основной класс обработки логики
"""

from dataclasses import dataclass, field
from typing import Literal, Optional
import time

from .kbd_structs import VK_CAPITAL, VK_ESCAPE
from .keymap import (
    format_combo_string,
    is_function_key,
    is_top_number_row,
    make_key_id,
    vk_from_key_name,
    vk_from_numpad,
    vk_from_fkey,
)


@dataclass
class KeyEvent:
    """Входное событие клавиатуры от hook."""

    event_type: Literal["KEYDOWN", "KEYUP"]
    vk_code: int
    scan_code: int
    extended: bool
    key_id: str
    is_capslock: bool

    @classmethod
    def from_hook_data(
        cls,
        event_type: Literal["KEYDOWN", "KEYUP"],
        vk_code: int,
        scan_code: int,
        extended: bool,
    ) -> "KeyEvent":
        """Создать KeyEvent из данных hook."""
        return cls(
            event_type=event_type,
            vk_code=vk_code,
            scan_code=scan_code,
            extended=extended,
            key_id=make_key_id(scan_code, extended),
            is_capslock=(vk_code == VK_CAPITAL),
        )


@dataclass
class EngineAction:
    """Выходные действия движка."""

    suppress: bool = False
    send_combo: Optional[tuple[list[str], int]] = None  # (mods, vk)
    send_capslock_tap: bool = False  # Отправить CapsLock DOWN+UP для TAP
    ui_event: Optional[dict] = None


@dataclass
class Config:
    """Конфигурация движка."""

    enabled: bool = True
    hyper_modifiers: list[str] = field(default_factory=lambda: ["CTRL", "SHIFT", "ALT", "WIN"])
    ignore_top_number_row: bool = True
    ignore_function_keys: bool = True
    capture_numpad: bool = True
    ignore_injected_events: bool = True
    process_blacklist: list[dict] = field(default_factory=list)  # [{name: str, enabled: bool}]

    # Маппинги: key_id -> буква/numpad
    letters_sc_map: dict[str, str] = field(default_factory=dict)
    numpad_sc_map: dict[str, str] = field(default_factory=dict)

    # Разрешённые клавиши (заполняются при калибровке)
    allowed_main_keys: set[str] = field(default_factory=set)
    allowed_numpad_keys: set[str] = field(default_factory=set)

    # Карта кастомного вывода: key_id -> {vk: "VK_...", mods: [...]}
    output_map: dict[str, dict] = field(default_factory=dict)


class Engine:
    """
    State machine для обработки CapsLock tap-vs-hold.

    Режимы:
    - NORMAL: обычная работа, tap vs hold
    - RECORD_MAIN: запись клавиш основного блока
    - RECORD_NUMPAD: запись клавиш NumPad
    """

    def __init__(self, config: Optional[Config] = None):
        """
        Инициализировать движок.

        Args:
            config: Конфигурация (если None, используется дефолтная)
        """
        self.config = config or Config()

        # Состояние
        self._enabled: bool = True
        self._mode: Literal["NORMAL", "RECORD_MAIN", "RECORD_NUMPAD"] = "NORMAL"
        self._caps_is_down: bool = False
        self._caps_used_as_prefix: bool = False
        self._caps_down_ts: int = 0
        self._recorded_keys: set[str] = set()
        self._suppressed_record_keydowns: set[str] = set()

    # =========================================================================
    # Публичные свойства
    # =========================================================================

    @property
    def enabled(self) -> bool:
        """Глобальный переключатель активности."""
        return self._enabled and self.config.enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        if not value:
            self.reset_input_state()

    @property
    def mode(self) -> Literal["NORMAL", "RECORD_MAIN", "RECORD_NUMPAD"]:
        """Текущий режим работы."""
        return self._mode

    @property
    def caps_is_down(self) -> bool:
        """CapsLock сейчас нажат."""
        return self._caps_is_down

    @property
    def caps_used_as_prefix(self) -> bool:
        """CapsLock был использован как Hyper-префикс."""
        return self._caps_used_as_prefix

    @property
    def recorded_keys(self) -> set[str]:
        """Записанные key_id в режиме калибровки."""
        return self._recorded_keys.copy()

    # =========================================================================
    # Управление режимами
    # =========================================================================

    def start_record_main(self) -> None:
        """Начать запись клавиш основного блока."""
        self.reset_input_state()
        self._mode = "RECORD_MAIN"
        self._recorded_keys.clear()

    def start_record_numpad(self) -> None:
        """Начать запись клавиш NumPad."""
        self.reset_input_state()
        self._mode = "RECORD_NUMPAD"
        self._recorded_keys.clear()

    def stop_record(self) -> set[str]:
        """
        Завершить запись и вернуть записанные клавиши.

        Returns:
            Набор записанных key_id
        """
        recorded = self._recorded_keys.copy()
        self._recorded_keys.clear()
        self._mode = "NORMAL"
        return recorded

    def update_config(self, config: Config) -> None:
        """Обновить конфигурацию."""
        self.config = config
        if not self.enabled:
            self.reset_input_state()

    def reset_input_state(self) -> None:
        """Сбросить состояние физически удерживаемых клавиш без отправки ввода."""
        self._caps_is_down = False
        self._caps_used_as_prefix = False
        self._caps_down_ts = 0

    # =========================================================================
    # Основная логика обработки
    # =========================================================================

    def handle(self, event: KeyEvent) -> EngineAction:
        """
        Обработать событие клавиатуры.

        Args:
            event: Событие от hook

        Returns:
            Действия: suppress, send_combo, ui_event
        """
        # Если отключено, пропускаем всё
        if event.event_type == "KEYUP" and event.key_id in self._suppressed_record_keydowns:
            self._suppressed_record_keydowns.discard(event.key_id)
            return EngineAction(suppress=True)

        if not self.enabled:
            return EngineAction(suppress=False)

        # Ветвление по режиму
        if self._mode == "NORMAL":
            return self._handle_normal(event)
        else:
            return self._handle_record(event)

    def _handle_normal(self, event: KeyEvent) -> EngineAction:
        """Обработка в нормальном режиме (tap-vs-hold)."""

        # --- CapsLock DOWN ---
        if event.is_capslock and event.event_type == "KEYDOWN":
            is_initial_press = not self._caps_is_down

            # Автоповтор CapsLock не должен стирать факт уже отправленной
            # Hyper-комбинации, иначе KEYUP ошибочно переключит регистр.
            if not is_initial_press:
                return EngineAction(suppress=True)

            self._caps_is_down = True
            self._caps_used_as_prefix = False
            self._caps_down_ts = int(time.time() * 1000)

            return EngineAction(
                suppress=True,  # Подавляем чтобы Windows не переключил CapsLock
                ui_event={
                    "type": "state_change",
                    "ts_ms": self._caps_down_ts,
                    "details": "CapsLock DOWN (suppressed)",
                },
            )

        # --- CapsLock UP ---
        if event.is_capslock and event.event_type == "KEYUP":
            # KEYUP может прийти сразу после установки/перезапуска hook.
            # Не превращаем такое событие в искусственный CapsLock TAP.
            if not self._caps_is_down:
                return EngineAction(suppress=False)

            was_prefix = self._caps_used_as_prefix

            # Сбрасываем состояние
            self._caps_is_down = False
            self._caps_used_as_prefix = False

            if was_prefix:
                # CapsLock был использован как Hyper — подавляем, не переключаем
                return EngineAction(
                    suppress=True,
                    ui_event={
                        "type": "state_change",
                        "ts_ms": int(time.time() * 1000),
                        "details": "CapsLock UP (HOLD, suppressed)",
                    },
                )
            else:
                # Tap — эмулируем нажатие CapsLock для переключения
                return EngineAction(
                    suppress=True,  # Подавляем оригинал, но отправим свой
                    send_capslock_tap=True,  # Флаг для hook чтобы отправил CapsLock
                    ui_event={
                        "type": "state_change",
                        "ts_ms": int(time.time() * 1000),
                        "details": "CapsLock UP (TAP, toggling)",
                    },
                )

        # --- Другие клавиши при зажатом CapsLock ---
        if self._caps_is_down and event.event_type == "KEYDOWN":
            return self._handle_hyper_key(event)

        # Всё остальное не трогаем
        return EngineAction(suppress=False)

    def _handle_hyper_key(self, event: KeyEvent) -> EngineAction:
        """Обработка клавиши в Hyper-режиме (CapsLock зажат)."""

        # Проверяем игнорируемые клавиши
        if self.config.ignore_top_number_row and is_top_number_row(event.scan_code):
            return EngineAction(
                suppress=False,
                ui_event={
                    "type": "ignored_key",
                    "ts_ms": int(time.time() * 1000),
                    "key_id": event.key_id,
                    "vk_code": event.vk_code,
                    "details": "Top number row (ignored)",
                },
            )

        if self.config.ignore_function_keys and is_function_key(event.scan_code):
            return EngineAction(
                suppress=False,
                ui_event={
                    "type": "ignored_key",
                    "ts_ms": int(time.time() * 1000),
                    "key_id": event.key_id,
                    "vk_code": event.vk_code,
                    "details": "Function key (ignored)",
                },
            )

        # 3. Проверяем output_map (кастомный вывод)
        if event.key_id in self.config.output_map:
            mapping = self.config.output_map[event.key_id]
            target_vk_name = mapping.get("vk", "")
            target_mods = mapping.get("mods", [])

            valid_vk = False
            target_vk = 0

            # Пытаемся распарсить VK
            try:
                if target_vk_name.startswith("VK_F"):
                    # F1-F24
                    target_vk = vk_from_fkey(target_vk_name.replace("VK_", ""))
                    valid_vk = True
                elif target_vk_name.startswith("VK_"):
                    # Другие VK (если понадобятся, пока можно через letter/numpad расширить)
                    # Для простоты пока поддерживаем F-keys и буквы через хак
                    pass
            except ValueError:
                pass

            if valid_vk:
                self._caps_used_as_prefix = True
                combo_str = format_combo_string(target_mods, target_vk)
                return EngineAction(
                    suppress=True,
                    send_combo=(target_mods, target_vk),
                    ui_event={
                        "type": "sent_combo",
                        "ts_ms": int(time.time() * 1000),
                        "key_id": event.key_id,
                        "vk_code": event.vk_code,
                        "scan_code": event.scan_code,
                        "extended": event.extended,
                        "details": f"sent mapped {combo_str}",
                    },
                )

        # 4. Проверяем маппинг для основных клавиш (старое поведение)
        if event.key_id in self.config.letters_sc_map:
            key_name = self.config.letters_sc_map[event.key_id]
            try:
                target_vk = vk_from_key_name(key_name)
            except ValueError:
                return EngineAction(suppress=False)

            self._caps_used_as_prefix = True
            combo_str = format_combo_string(self.config.hyper_modifiers, target_vk)

            return EngineAction(
                suppress=True,
                send_combo=(self.config.hyper_modifiers.copy(), target_vk),
                ui_event={
                    "type": "sent_combo",
                    "ts_ms": int(time.time() * 1000),
                    "key_id": event.key_id,
                    "vk_code": event.vk_code,
                    "scan_code": event.scan_code,
                    "extended": event.extended,
                    "details": f"sent {combo_str}",
                },
            )

        # Проверяем маппинг для NumPad
        if self.config.capture_numpad and event.key_id in self.config.numpad_sc_map:
            numpad_name = self.config.numpad_sc_map[event.key_id]
            try:
                target_vk = vk_from_numpad(numpad_name)
            except ValueError:
                return EngineAction(suppress=False)

            self._caps_used_as_prefix = True
            combo_str = format_combo_string(self.config.hyper_modifiers, target_vk)

            return EngineAction(
                suppress=True,
                send_combo=(self.config.hyper_modifiers.copy(), target_vk),
                ui_event={
                    "type": "sent_combo",
                    "ts_ms": int(time.time() * 1000),
                    "key_id": event.key_id,
                    "vk_code": event.vk_code,
                    "scan_code": event.scan_code,
                    "extended": event.extended,
                    "details": f"sent {combo_str}",
                },
            )

        # Клавиша не в маппинге — не перехватываем
        return EngineAction(suppress=False)

    def _handle_record(self, event: KeyEvent) -> EngineAction:
        """Обработка в режиме записи (калибровка)."""

        # Любой DOWN, подавленный режимом записи, запоминаем. Его парный UP
        # подавляется даже если UI уже успел завершить запись. UP от клавиши,
        # нажатой до входа в калибровку, проходит в систему.
        if event.event_type == "KEYDOWN":
            self._suppressed_record_keydowns.add(event.key_id)

        # Escape — выход из режима записи
        if event.vk_code == VK_ESCAPE and event.event_type == "KEYDOWN":
            recorded = self.stop_record()
            return EngineAction(
                suppress=True,
                ui_event={
                    "type": "state_change",
                    "ts_ms": int(time.time() * 1000),
                    "details": f"Recording stopped, {len(recorded)} keys",
                },
            )

        # Несвязанный KEYUP не подавляем.
        if event.event_type == "KEYUP":
            return EngineAction(suppress=False)

        # Игнорируем CapsLock в режиме записи
        if event.is_capslock:
            return EngineAction(suppress=True)

        # Проверяем игнорируемые клавиши
        if self.config.ignore_top_number_row and is_top_number_row(event.scan_code):
            return EngineAction(
                suppress=True,
                ui_event={
                    "type": "ignored_key",
                    "ts_ms": int(time.time() * 1000),
                    "key_id": event.key_id,
                    "details": "Top number row (skipped in record)",
                },
            )

        if self.config.ignore_function_keys and is_function_key(event.scan_code):
            return EngineAction(
                suppress=True,
                ui_event={
                    "type": "ignored_key",
                    "ts_ms": int(time.time() * 1000),
                    "key_id": event.key_id,
                    "details": "Function key (skipped in record)",
                },
            )

        # Записываем клавишу
        self._recorded_keys.add(event.key_id)

        return EngineAction(
            suppress=True,
            ui_event={
                "type": "recorded_key",
                "ts_ms": int(time.time() * 1000),
                "key_id": event.key_id,
                "vk_code": event.vk_code,
                "scan_code": event.scan_code,
                "extended": event.extended,
                "details": f"Recorded: {event.key_id}",
            },
        )
