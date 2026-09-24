"""Быстрый кэш процесса активного окна для keyboard hook."""

from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes
from pathlib import Path
from typing import Callable


PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

GetForegroundWindow = user32.GetForegroundWindow
GetForegroundWindow.argtypes = []
GetForegroundWindow.restype = wintypes.HWND

GetWindowThreadProcessId = user32.GetWindowThreadProcessId
GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
GetWindowThreadProcessId.restype = wintypes.DWORD

OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE

QueryFullProcessImageNameW = kernel32.QueryFullProcessImageNameW
QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
QueryFullProcessImageNameW.restype = wintypes.BOOL

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL


def get_active_process_name() -> str:
    """Получить имя процесса активного окна с минимальными правами доступа."""
    hwnd = GetForegroundWindow()
    if not hwnd:
        return ""

    pid = wintypes.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return ""

    process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not process:
        return ""

    try:
        buffer = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(buffer))
        if not QueryFullProcessImageNameW(process, 0, buffer, ctypes.byref(size)):
            return ""
        return Path(buffer.value).name.lower()
    finally:
        CloseHandle(process)


def is_blacklisted(process_name: str, blacklist: list[str]) -> bool:
    """Проверить точное совпадение имени процесса без учёта регистра."""
    normalized = process_name.casefold()
    return bool(normalized) and any(name.casefold() == normalized for name in blacklist)


class ForegroundProcessMonitor:
    """Обновляет имя foreground-процесса вне чувствительного hook callback."""

    def __init__(
        self,
        poll_interval: float = 0.1,
        resolver: Callable[[], str] = get_active_process_name,
        should_refresh: Callable[[], bool] = lambda: True,
    ) -> None:
        self._poll_interval = max(0.02, poll_interval)
        self._resolver = resolver
        self._should_refresh = should_refresh
        self._process_name = ""
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def process_name(self) -> str:
        with self._lock:
            return self._process_name

    @property
    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def refresh(self) -> str:
        if not self._should_refresh():
            with self._lock:
                self._process_name = ""
            return ""
        try:
            process_name = self._resolver()
        except Exception:
            process_name = ""
        with self._lock:
            self._process_name = process_name
        return process_name

    def start(self) -> None:
        if self.is_alive:
            return
        self._stop_event.clear()
        self.refresh()
        self._thread = threading.Thread(
            target=self._run,
            name="ForegroundProcessMonitor",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 1.0) -> bool:
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        return not self.is_alive

    def _run(self) -> None:
        while not self._stop_event.wait(self._poll_interval):
            self.refresh()
