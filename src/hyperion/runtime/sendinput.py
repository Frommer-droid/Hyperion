"""
Модуль отправки клавиатурного ввода через SendInput.

Содержит:
- Функции для отправки нажатий/отпусканий клавиш
- Функцию send_combo для отправки комбинаций модификаторов + клавиша
- Маркер MARKER для защиты от self-injection
"""

import ctypes
import threading

from .kbd_structs import (
    INPUT,
    INPUT_KEYBOARD,
    KEYBDINPUT,
    KEYEVENTF_KEYUP,
    KEYEVENTF_SCANCODE,
    KEYEVENTF_EXTENDEDKEY,
    SendInput,
    VK_CAPITAL,
    VK_LCONTROL,
    VK_LSHIFT,
    VK_LMENU,
    VK_LWIN,
    VK_RWIN,
    VK_PRIOR,
    VK_NEXT,
    VK_HOME,
    VK_END,
    VK_INSERT,
    VK_DELETE,
    VK_LEFT,
    VK_UP,
    VK_RIGHT,
    VK_DOWN,
)

# GetKeyState для проверки состояния CapsLock
user32 = ctypes.windll.user32
GetKeyState = user32.GetKeyState
GetKeyState.argtypes = [ctypes.c_int]
GetKeyState.restype = ctypes.c_short

MapVirtualKeyW = user32.MapVirtualKeyW
MapVirtualKeyW.argtypes = [ctypes.c_uint, ctypes.c_uint]
MapVirtualKeyW.restype = ctypes.c_uint

MAPVK_VK_TO_VSC = 0


# Уникальный маркер
MARKER = 0x50484859
_send_lock = threading.RLock()


EXTENDED_VK_CODES = frozenset([
    VK_LWIN,
    VK_RWIN,
    VK_INSERT,
    VK_DELETE,
    VK_HOME,
    VK_END,
    VK_PRIOR,
    VK_NEXT,
    VK_LEFT,
    VK_UP,
    VK_RIGHT,
    VK_DOWN,
])


def _is_extended_vk(vk: int) -> bool:
    return vk in EXTENDED_VK_CODES


def _make_keyboard_input(vk: int, scan: int, flags: int) -> INPUT:
    """Создать структуру INPUT."""
    # Если передан scancode, добавляем флаг
    if scan > 0:
        flags |= KEYEVENTF_SCANCODE
        if _is_extended_vk(vk):
            flags |= KEYEVENTF_EXTENDEDKEY

    ki = KEYBDINPUT(
        wVk=0 if scan > 0 else vk,
        wScan=scan,
        dwFlags=flags,
        time=0,
        dwExtraInfo=MARKER,
    )

    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki = ki

    return inp


def vk_to_scan(vk: int) -> int:
    """Получить scancode из VK."""
    # Для F13-F24 (и других чисто виртуальных кнопок) лучше НЕ использовать скан-коды,
    # так как системный маппинг (MapVirtualKey) может выдавать значения,
    # которые драйвером клавиатуры интерпретируются неверно (например 0x64 -> J).
    from .kbd_structs import VK_F13, VK_F24
    if VK_F13 <= vk <= VK_F24:
        return 0

    scan = MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    return scan


def send_key_down(vk: int, scan: int = 0) -> bool:
    """Отправить нажатие."""
    # Если скан-код не передан явно, пытаемся получить
    if scan == 0:
        scan = vk_to_scan(vk)
        
    inp = _make_keyboard_input(vk, scan, 0)
    with _send_lock:
        result = SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    return result == 1


def send_key_up(vk: int, scan: int = 0) -> bool:
    """Отправить отпускание."""
    if scan == 0:
        scan = vk_to_scan(vk)
        
    inp = _make_keyboard_input(vk, scan, KEYEVENTF_KEYUP)
    with _send_lock:
        result = SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    return result == 1


def send_combo(mods: list[str], vk: int) -> bool:
    """Отправить комбинацию (используя ScanCodes!!!)."""

    mod_vk_map = {
        "CTRL": VK_LCONTROL,
        "SHIFT": VK_LSHIFT,
        "ALT": VK_LMENU,
        "WIN": VK_LWIN,
        "CONTROL": VK_LCONTROL,
        "MENU": VK_LMENU,
    }

    # Подготавливаем список событий (scancodes)
    events = [] # list of (vk, scan, flags)

    # 1. Модификаторы DOWN
    for mod in mods:
        mod_upper = mod.upper()
        if mod_upper in mod_vk_map:
            m_vk = mod_vk_map[mod_upper]
            m_scan = vk_to_scan(m_vk)
            events.append((m_vk, m_scan, 0))

    # 2. Target DOWN
    t_scan = vk_to_scan(vk)
    events.append((vk, t_scan, 0))

    # 3. Target UP
    events.append((vk, t_scan, KEYEVENTF_KEYUP))

    # 4. Модификаторы UP (reversed)
    for i in range(len(events) - 3, -1, -1): # items before target
        m_vk, m_scan, _ = events[i]
        events.append((m_vk, m_scan, KEYEVENTF_KEYUP))

    # Формируем массив C-структур
    count = len(events)
    inputs = (INPUT * count)()

    for i, (v, s, f) in enumerate(events):
        inputs[i] = _make_keyboard_input(v, s, f)

    with _send_lock:
        result = SendInput(count, inputs, ctypes.sizeof(INPUT))
    return result == count


def get_marker() -> int:
    return MARKER


def get_capslock_state() -> bool:
    return bool(GetKeyState(VK_CAPITAL) & 0x0001)


def toggle_capslock() -> None:
    # 0x3A - сканкод CapsLock
    # RLock удерживает DOWN/UP вместе и не даёт другой комбинации вклиниться.
    with _send_lock:
        send_key_down(VK_CAPITAL, 0x3A)
        send_key_up(VK_CAPITAL, 0x3A)
