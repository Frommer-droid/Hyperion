"""Последовательная отправка синтетического клавиатурного ввода."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Callable, Literal, Optional

from .sendinput import send_combo, toggle_capslock


@dataclass(frozen=True)
class InputCommand:
    """Одна атомарная команда для worker-потока отправки ввода."""

    kind: Literal["combo", "capslock_tap"]
    modifiers: tuple[str, ...] = ()
    vk_code: int = 0


class InputDispatcher:
    """Один worker с ограниченной FIFO-очередью вместо потока на событие."""

    def __init__(
        self,
        max_queue_size: int = 256,
        error_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        if max_queue_size <= 0:
            raise ValueError("max_queue_size must be positive")

        self._commands: queue.Queue[InputCommand] = queue.Queue(maxsize=max_queue_size)
        self._error_callback = error_callback
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name="InputDispatcherThread",
            daemon=True,
        )
        self._started = False

    @property
    def is_alive(self) -> bool:
        return self._thread.is_alive()

    def start(self) -> None:
        """Запустить worker; повторный вызов безопасен."""
        if self._started:
            return
        self._started = True
        self._thread.start()

    def submit_combo(self, modifiers: list[str], vk_code: int) -> bool:
        """Поставить комбинацию в очередь без блокировки hook callback."""
        return self._submit(InputCommand("combo", tuple(modifiers), vk_code))

    def submit_capslock_tap(self) -> bool:
        """Поставить атомарный CapsLock DOWN/UP в очередь."""
        return self._submit(InputCommand("capslock_tap"))

    def stop(self, timeout: float = 2.0) -> bool:
        """Отменить ожидающие команды и дождаться завершения текущей."""
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=timeout)
        return not self._thread.is_alive()

    def _submit(self, command: InputCommand) -> bool:
        if not self._started or self._stop_event.is_set():
            return False
        try:
            self._commands.put_nowait(command)
            return True
        except queue.Full:
            return False

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                command = self._commands.get(timeout=0.05)
            except queue.Empty:
                continue

            if self._stop_event.is_set():
                self._commands.task_done()
                break

            try:
                if command.kind == "combo":
                    success = send_combo(list(command.modifiers), command.vk_code)
                    if not success:
                        self._report_error("SendInput не отправил комбинацию полностью")
                else:
                    toggle_capslock()
            except Exception as exc:
                self._report_error(f"Ошибка отправки ввода: {exc}")
            finally:
                self._commands.task_done()

    def _report_error(self, message: str) -> None:
        if self._error_callback is not None:
            try:
                self._error_callback(message)
            except Exception:
                pass
