"""Защита Hyperion от одновременного запуска нескольких экземпляров."""

from __future__ import annotations

import ctypes
from ctypes import wintypes


ERROR_ALREADY_EXISTS = 183
MUTEX_NAME = r"Local\Frommer-droid.Hyperion"

kernel32 = ctypes.windll.kernel32

CreateMutexW = kernel32.CreateMutexW
CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
CreateMutexW.restype = wintypes.HANDLE

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL

GetLastError = kernel32.GetLastError
GetLastError.argtypes = []
GetLastError.restype = wintypes.DWORD

SetLastError = kernel32.SetLastError
SetLastError.argtypes = [wintypes.DWORD]
SetLastError.restype = None


class SingleInstanceGuard:
    """Удерживает именованный Win32 mutex до завершения процесса."""

    def __init__(self, name: str = MUTEX_NAME) -> None:
        SetLastError(0)
        self._handle = CreateMutexW(None, False, name)
        if not self._handle:
            raise OSError("Не удалось создать single-instance mutex")
        self.already_running = GetLastError() == ERROR_ALREADY_EXISTS

    def close(self) -> None:
        if self._handle:
            CloseHandle(self._handle)
            self._handle = None

    def __enter__(self) -> "SingleInstanceGuard":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
