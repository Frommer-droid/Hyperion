"""
Low-level keyboard hook.

Содержит:
- HookThread — поток с установкой WH_KEYBOARD_LL и message loop
- Callback LowLevelKeyboardProc
- Защита от self-injection через маркер
"""

import ctypes
import queue
import threading
from ctypes import wintypes
from typing import Optional

from .kbd_structs import (
    HOOKPROC,
    HHOOK,
    KBDLLHOOKSTRUCT,
    WH_KEYBOARD_LL,
    WM_KEYDOWN,
    WM_KEYUP,
    WM_SYSKEYDOWN,
    WM_SYSKEYUP,
    WM_QUIT,
    PM_NOREMOVE,
    LLKHF_EXTENDED,
    LLKHF_INJECTED,
    CallNextHookEx,
    GetMessageW,
    PeekMessageW,
    GetModuleHandleW,
    PostThreadMessageW,
    SetWindowsHookExW,
    UnhookWindowsHookEx,
    GetCurrentThreadId,
)
from .engine import Engine, EngineAction, KeyEvent
from .input_dispatcher import InputDispatcher
from .sendinput import get_marker
from .process_guard import ForegroundProcessMonitor, is_blacklisted


class HookThread(threading.Thread):
    """
    Поток с low-level keyboard hook.

    Устанавливает WH_KEYBOARD_LL, крутит message loop,
    передаёт события в Engine и выполняет действия (suppress, send_combo).
    """

    def __init__(
        self,
        engine: Engine,
        event_queue: queue.Queue,
        input_dispatcher: InputDispatcher,
        process_monitor: Optional[ForegroundProcessMonitor] = None,
        name: str = "KeyboardHookThread",
    ):
        """
        Инициализировать hook-поток.

        Args:
            engine: Экземпляр Engine для обработки событий
            event_queue: Очередь для передачи UI-событий в главный поток
            input_dispatcher: Единый worker отправки синтетического ввода
            name: Имя потока
        """
        super().__init__(name=name, daemon=True)

        self.engine = engine
        self.event_queue = event_queue
        self.input_dispatcher = input_dispatcher
        self.process_monitor = process_monitor or ForegroundProcessMonitor(
            should_refresh=lambda: any(
                entry.get("name") and entry.get("enabled", True)
                for entry in self.engine.config.process_blacklist
            )
        )

        self._hook_handle: Optional[HHOOK] = None
        self._thread_id: Optional[int] = None
        self._stop_event = threading.Event()
        self._running = False

        # Сохраняем callback чтобы GC не удалил его
        self._callback = HOOKPROC(self._low_level_handler)

        # Маркер для проверки self-injection
        self._marker = get_marker()

    @property
    def is_hook_active(self) -> bool:
        """Hook установлен и активен."""
        return self._hook_handle is not None and self._running

    def run(self) -> None:
        """Запуск потока: установка хука и message loop."""
        self._thread_id = GetCurrentThreadId()
        self._running = True
        self.process_monitor.start()

        # PostThreadMessage работает только после создания message queue.
        # PeekMessage гарантирует её наличие даже при очень раннем stop().
        msg = wintypes.MSG()
        PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_NOREMOVE)

        # Установка хука
        try:
            h_mod = GetModuleHandleW(None)
            self._hook_handle = SetWindowsHookExW(
                WH_KEYBOARD_LL,
                self._callback,
                h_mod,
                0,  # Глобальный хук
            )

            if not self._hook_handle:
                error = ctypes.get_last_error()
                self._put_error(f"SetWindowsHookExW failed: {error}")
                self._running = False
                self.process_monitor.stop()
                return

            self._put_event(
                {
                    "type": "state_change",
                    "details": "Hook installed successfully",
                }
            )

        except Exception as e:
            self._put_error(f"Hook installation error: {e}")
            self._running = False
            self.process_monitor.stop()
            return

        # Message loop
        while not self._stop_event.is_set():
            result = GetMessageW(ctypes.byref(msg), None, 0, 0)

            if result <= 0:  # WM_QUIT или ошибка
                break

        # Снятие хука
        self._cleanup()

    def stop(self) -> bool:
        """Остановить hook-поток и вернуть True после подтверждённой остановки."""
        self._stop_event.set()

        # Посылаем WM_QUIT чтобы выйти из GetMessage
        if self._thread_id:
            PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)

        # Ждём завершения потока
        if self.is_alive():
            self.join(timeout=2.0)

        return not self.is_alive()

    def _cleanup(self) -> None:
        """Снять хук и очистить ресурсы."""
        if self._hook_handle:
            UnhookWindowsHookEx(self._hook_handle)
            self._hook_handle = None

        self._running = False
        self.engine.reset_input_state()
        self.process_monitor.stop()

        self._put_event(
            {
                "type": "state_change",
                "details": "Hook uninstalled",
            }
        )

    def _low_level_handler(
        self,
        n_code: int,
        w_param: int,
        l_param: int,
    ) -> int:
        """
        Callback для LowLevelKeyboardProc.

        Args:
            n_code: HC_ACTION=0 означает что нужно обработать
            w_param: WM_KEYDOWN/UP или WM_SYSKEYDOWN/UP
            l_param: Указатель на KBDLLHOOKSTRUCT

        Returns:
            Ненулевое значение для подавления события
        """
        # Если n_code < 0, вызываем следующий хук без обработки
        if n_code < 0:
            return CallNextHookEx(self._hook_handle, n_code, w_param, l_param)

        try:
            # Получаем данные события
            kb_struct = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents

            # Проверяем self-injection по маркеру
            extra_info = int(kb_struct.dwExtraInfo)

            if extra_info == self._marker:
                # Это наше событие — пропускаем без обработки
                return CallNextHookEx(self._hook_handle, n_code, w_param, l_param)

            # По умолчанию инжектированные события не участвуют в Hyper-логике,
            # но опцию можно отключить для RDP/экранных клавиатур.
            if self.engine.config.ignore_injected_events and kb_struct.flags & LLKHF_INJECTED:
                return CallNextHookEx(self._hook_handle, n_code, w_param, l_param)

            # Определяем тип события
            if w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
                event_type = "KEYDOWN"
            elif w_param in (WM_KEYUP, WM_SYSKEYUP):
                event_type = "KEYUP"
            else:
                return CallNextHookEx(self._hook_handle, n_code, w_param, l_param)

            # Формируем KeyEvent до проверок состояния и blacklist.
            extended = bool(kb_struct.flags & LLKHF_EXTENDED)
            key_event = KeyEvent.from_hook_data(
                event_type=event_type,
                vk_code=kb_struct.vkCode,
                scan_code=kb_struct.scanCode,
                extended=extended,
            )

            # Не сверяем удерживаемый CapsLock через GetAsyncKeyState:
            # LowLevelKeyboardProc вызывается до обновления async-state, а
            # подавленный CapsLock DOWN может вообще не попасть в это состояние.

            # Проверяем blacklist процессов
            if self.engine.config.process_blacklist:
                active_process = self.process_monitor.process_name
                # Извлекаем только включённые процессы
                enabled_blacklist = [
                    p.get("name", "")
                    for p in self.engine.config.process_blacklist
                    if p.get("enabled", True)
                ]
                if is_blacklisted(active_process, enabled_blacklist):
                    # Если фокус сменился, пока CapsLock был зажат, его KEYUP
                    # может уйти в исключённый процесс. Не оставляем Engine в
                    # ложном состоянии удерживаемого CapsLock.
                    self.engine.reset_input_state()
                    # Процесс в blacklist — пропускаем обработку
                    return CallNextHookEx(self._hook_handle, n_code, w_param, l_param)

            # Обрабатываем в Engine
            action: EngineAction = self.engine.handle(key_event)

            # Передаём UI-событие
            if action.ui_event:
                self._put_event(action.ui_event)

            # Отправляем комбинацию асинхронно, чтобы не блокировать хук
            if action.send_combo:
                mods, vk = action.send_combo
                if not self.input_dispatcher.submit_combo(mods, vk):
                    self._put_error("Input queue is full or stopped")

            # Отправляем CapsLock TAP асинхронно
            if action.send_capslock_tap:
                if not self.input_dispatcher.submit_capslock_tap():
                    self._put_error("Input queue is full or stopped")

            # Подавляем или пропускаем
            if action.suppress:
                return 1  # Подавить событие

        except Exception as e:
            self._put_error(f"Hook handler error: {e}")

        return CallNextHookEx(self._hook_handle, n_code, w_param, l_param)

    def _put_event(self, event: dict) -> None:
        """Положить событие в очередь для UI."""
        try:
            self.event_queue.put_nowait(event)
        except queue.Full:
            pass  # Очередь переполнена, пропускаем

    def _put_error(self, message: str) -> None:
        """Положить ошибку в очередь."""
        print(f"HOOK ERROR: {message}")  # Debug print
        self._put_event(
            {
                "type": "error",
                "details": message,
            }
        )
