"""
Mixin для перехвата системных событий Windows.

Позволяет различать левый и правый клик на кнопке закрытия окна:
- Левый клик (X) → полное закрытие приложения
- Правый клик (X) → сворачивание в system tray
"""

import ctypes
import ctypes.wintypes

from .windows_api import (
    HTCLOSE,
    SC_CLOSE,
    SC_MINIMIZE,
    WM_NCRBUTTONUP,
    WM_SYSCOMMAND,
    WIN_LIBS_LOADED,
)


class WindowEventsMixin:
    """Mixin для перехвата нативных событий Windows."""

    def nativeEvent(self, eventType, message):
        """Перехватываем системные сообщения Windows."""
        if WIN_LIBS_LOADED and eventType == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))

            # WM_NCRBUTTONUP — отпускание ПРАВОЙ кнопки в неклиентской области
            if msg.message == WM_NCRBUTTONUP:
                # HTCLOSE (0x14) — код зоны кнопки закрытия
                if msg.wParam == HTCLOSE:
                    self.hide_to_tray()  # Сворачиваем в tray
                    return True, 0       # Событие обработано

            # WM_SYSCOMMAND — системные команды (включая ЛЕВЫЙ клик на крестик)
            if msg.message == WM_SYSCOMMAND:
                # SC_CLOSE — команда закрытия (левый клик на X)
                if (msg.wParam & 0xFFF0) == SC_CLOSE:
                    self.quit_application()  # Закрываем приложение
                    return True, 0
                # SC_MINIMIZE — сворачивание
                elif (msg.wParam & 0xFFF0) == SC_MINIMIZE:
                    self.showMinimized()
                    return True, 0

        return super().nativeEvent(eventType, message)
