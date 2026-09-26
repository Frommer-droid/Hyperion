"""
Ctypes структуры и константы Windows API для работы с клавиатурой.

Содержит:
- KBDLLHOOKSTRUCT — данные события клавиатуры из low-level hook
- INPUT, KEYBDINPUT — структуры для SendInput
- Константы сообщений и флагов
- Виртуальные коды клавиш (VK_*)
"""

import ctypes
from ctypes import wintypes


# ctypes.wintypes не экспортирует эти pointer-sized WinAPI-типы.
# WPARAM беззнаковый, LPARAM знаковый и оба имеют размер указателя.
ULONG_PTR = wintypes.WPARAM
LRESULT = wintypes.LPARAM

# =============================================================================
# Константы сообщений клавиатуры
# =============================================================================

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
PM_NOREMOVE = 0x0000


# =============================================================================
# Флаги KBDLLHOOKSTRUCT.flags
# =============================================================================

LLKHF_EXTENDED = 0x01  # Клавиша extended (E0 prefix)
LLKHF_INJECTED = 0x10  # Событие сгенерировано программно
LLKHF_ALTDOWN = 0x20  # Alt нажат
LLKHF_UP = 0x80  # Клавиша отпущена


# =============================================================================
# Типы ввода для SendInput
# =============================================================================

INPUT_KEYBOARD = 1


# =============================================================================
# Флаги KEYBDINPUT.dwFlags
# =============================================================================

KEYEVENTF_EXTENDEDKEY = 0x0001  # Extended key
KEYEVENTF_KEYUP = 0x0002  # Key up event
KEYEVENTF_SCANCODE = 0x0008  # Использовать scancode
KEYEVENTF_UNICODE = 0x0004  # Unicode character


# =============================================================================
# Виртуальные коды клавиш
# =============================================================================

# Модификаторы
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_LMENU = 0xA4  # Left Alt
VK_RMENU = 0xA5  # Right Alt
VK_LSHIFT = 0xA0
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_SHIFT = 0x10
VK_CAPITAL = 0x14  # CapsLock

# Специальные клавиши
VK_ESCAPE = 0x1B
VK_RETURN = 0x0D
VK_SPACE = 0x20
VK_BACK = 0x08
VK_TAB = 0x09
VK_PRIOR = 0x21  # Page Up
VK_NEXT = 0x22  # Page Down
VK_END = 0x23
VK_HOME = 0x24
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_INSERT = 0x2D
VK_DELETE = 0x2E

# Буквы A-Z (0x41-0x5A)
VK_A = 0x41
VK_B = 0x42
VK_C = 0x43
VK_D = 0x44
VK_E = 0x45
VK_F = 0x46
VK_G = 0x47
VK_H = 0x48
VK_I = 0x49
VK_J = 0x4A
VK_K = 0x4B
VK_L = 0x4C
VK_M = 0x4D
VK_N = 0x4E
VK_O = 0x4F
VK_P = 0x50
VK_Q = 0x51
VK_R = 0x52
VK_S = 0x53
VK_T = 0x54
VK_U = 0x55
VK_V = 0x56
VK_W = 0x57
VK_X = 0x58
VK_Y = 0x59
VK_Z = 0x5A

# NumPad
VK_NUMPAD0 = 0x60
VK_NUMPAD1 = 0x61
VK_NUMPAD2 = 0x62
VK_NUMPAD3 = 0x63
VK_NUMPAD4 = 0x64
VK_NUMPAD5 = 0x65
VK_NUMPAD6 = 0x66
VK_NUMPAD7 = 0x67
VK_NUMPAD8 = 0x68
VK_NUMPAD9 = 0x69

# F-клавиши
VK_F1 = 0x70
VK_F2 = 0x71
VK_F3 = 0x72
VK_F4 = 0x73
VK_F5 = 0x74
VK_F6 = 0x75
VK_F7 = 0x76
VK_F8 = 0x77
VK_F9 = 0x78
VK_F10 = 0x79
VK_F11 = 0x7A
VK_F12 = 0x7B
VK_F13 = 0x7C
VK_F14 = 0x7D
VK_F15 = 0x7E
VK_F16 = 0x7F
VK_F17 = 0x80
VK_F18 = 0x81
VK_F19 = 0x82
VK_F20 = 0x83
VK_F21 = 0x84
VK_F22 = 0x85
VK_F23 = 0x86
VK_F24 = 0x87

# OEM Keys
VK_OEM_1 = 0xBA  # ;:
VK_OEM_PLUS = 0xBB  # +
VK_OEM_COMMA = 0xBC  # ,
VK_OEM_MINUS = 0xBD  # -
VK_OEM_PERIOD = 0xBE  # .
VK_OEM_2 = 0xBF  # /?
VK_OEM_3 = 0xC0  # `~
VK_OEM_4 = 0xDB  # [{
VK_OEM_5 = 0xDC  # \|
VK_OEM_6 = 0xDD  # ]}
VK_OEM_7 = 0xDE  # '"


# =============================================================================
# Scancode наборы для игнорирования
# =============================================================================

# Верхний цифровой ряд (1-0, -, =)
TOP_NUMBER_ROW_SCANCODES = frozenset(
    [
        0x02,
        0x03,
        0x04,
        0x05,
        0x06,  # 1-5
        0x07,
        0x08,
        0x09,
        0x0A,
        0x0B,  # 6-0
        0x0C,
        0x0D,  # -, =
    ]
)

# F-клавиши
FUNCTION_KEY_SCANCODES = frozenset(
    [
        0x3B,
        0x3C,
        0x3D,
        0x3E,  # F1-F4
        0x3F,
        0x40,
        0x41,
        0x42,  # F5-F8
        0x43,
        0x44,  # F9-F10
        0x57,
        0x58,  # F11-F12
    ]
)


# =============================================================================
# Структуры ctypes
# =============================================================================


class KBDLLHOOKSTRUCT(ctypes.Structure):
    """
    Структура данных low-level keyboard hook.

    Поля:
        vkCode: Виртуальный код клавиши
        scanCode: Аппаратный скан-код клавиши
        flags: Флаги (extended, injected, etc.)
        time: Время события в миллисекундах
        dwExtraInfo: Дополнительная информация (используется для маркера)
    """

    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    """Структура для события клавиатуры в SendInput."""

    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    """Структура для события мыши (заглушка для union)."""

    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    """Структура для аппаратного события (заглушка для union)."""

    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_UNION(ctypes.Union):
    """Union для разных типов ввода."""

    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    """Структура INPUT для SendInput."""

    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


# =============================================================================
# Типы для callback функций
# =============================================================================

# LowLevelKeyboardProc callback type
HOOKPROC = ctypes.WINFUNCTYPE(
    LRESULT,
    ctypes.c_int,  # nCode
    wintypes.WPARAM,  # wParam
    wintypes.LPARAM,  # lParam
)

# Hook handle type
HHOOK = wintypes.HANDLE


# =============================================================================
# WinAPI функции
# =============================================================================

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# SetWindowsHookExW
SetWindowsHookExW = user32.SetWindowsHookExW
SetWindowsHookExW.argtypes = [
    ctypes.c_int,  # idHook
    HOOKPROC,  # lpfn
    wintypes.HINSTANCE,  # hMod
    wintypes.DWORD,  # dwThreadId
]
SetWindowsHookExW.restype = HHOOK

# UnhookWindowsHookEx
UnhookWindowsHookEx = user32.UnhookWindowsHookEx
UnhookWindowsHookEx.argtypes = [HHOOK]
UnhookWindowsHookEx.restype = wintypes.BOOL

# CallNextHookEx
CallNextHookEx = user32.CallNextHookEx
CallNextHookEx.argtypes = [HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
CallNextHookEx.restype = LRESULT

# GetMessageW
GetMessageW = user32.GetMessageW
GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
GetMessageW.restype = wintypes.BOOL

# PeekMessageW — явное создание message queue перед публикацией WM_QUIT
PeekMessageW = user32.PeekMessageW
PeekMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
    wintypes.UINT,
]
PeekMessageW.restype = wintypes.BOOL

# PostThreadMessageW
PostThreadMessageW = user32.PostThreadMessageW
PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
PostThreadMessageW.restype = wintypes.BOOL

# SendInput
SendInput = user32.SendInput
SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
SendInput.restype = wintypes.UINT

# GetModuleHandleW
GetModuleHandleW = kernel32.GetModuleHandleW
GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
GetModuleHandleW.restype = wintypes.HMODULE

# GetCurrentThreadId
GetCurrentThreadId = kernel32.GetCurrentThreadId
GetCurrentThreadId.argtypes = []
GetCurrentThreadId.restype = wintypes.DWORD

# =============================================================================
# Константы хуков
# =============================================================================

WH_KEYBOARD_LL = 13
WM_QUIT = 0x0012
