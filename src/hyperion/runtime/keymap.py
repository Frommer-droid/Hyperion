"""
Модуль маппинга клавиш.

Содержит:
- Функции кодирования/декодирования key_id (SC{scanCode}_E0)
- Преобразование букв в VK-коды
- Наборы scancode для игнорирования (цифровой ряд, F-клавиши)
"""

from .kbd_structs import (
    FUNCTION_KEY_SCANCODES,
    TOP_NUMBER_ROW_SCANCODES,
    VK_A,
    VK_NUMPAD0,
    VK_F1,
    VK_F13,
    VK_F24,
    VK_SPACE,
    VK_PRIOR,
    VK_NEXT,
    VK_HOME,
    VK_END,
    VK_INSERT,
    VK_LEFT,
    VK_UP,
    VK_RIGHT,
    VK_DOWN,
    VK_OEM_4,
    VK_OEM_6,
    VK_OEM_COMMA,
    VK_OEM_PERIOD,
    VK_OEM_7,
    VK_OEM_2,
    VK_OEM_5,
)


_SPECIAL_KEY_VK_MAP = {
    "SPACE": VK_SPACE,
    "PGUP": VK_PRIOR,
    "PAGEUP": VK_PRIOR,
    "PGDOWN": VK_NEXT,
    "PGDN": VK_NEXT,
    "PAGEDOWN": VK_NEXT,
    "HOME": VK_HOME,
    "END": VK_END,
    "INSERT": VK_INSERT,
    "UP": VK_UP,
    "DOWN": VK_DOWN,
    "LEFT": VK_LEFT,
    "RIGHT": VK_RIGHT,
    "ARROWUP": VK_UP,
    "ARROWDOWN": VK_DOWN,
    "ARROWLEFT": VK_LEFT,
    "ARROWRIGHT": VK_RIGHT,
}


def _normalize_key_name(name: str) -> str:
    return name.upper().replace(" ", "").replace("-", "").replace("_", "")


def make_key_id(scan_code: int, extended: bool) -> str:
    """
    Создать строковый идентификатор клавиши из scancode и флага extended.

    Формат: SC{scanCode:03X} или SC{scanCode:03X}_E0

    Args:
        scan_code: Аппаратный скан-код клавиши
        extended: True если клавиша extended (E0 prefix)

    Returns:
        Строковый идентификатор, например "SC01E" или "SC047_E0"
    """
    base = f"SC{scan_code:03X}"
    if extended:
        return f"{base}_E0"
    return base


def parse_key_id(key_id: str) -> tuple[int, bool]:
    """
    Распарсить key_id обратно в scancode и флаг extended.

    Args:
        key_id: Строковый идентификатор, например "SC01E" или "SC047_E0"

    Returns:
        Tuple (scan_code, extended)

    Raises:
        ValueError: Если формат key_id неверный
    """
    if not key_id.startswith("SC"):
        raise ValueError(f"Invalid key_id format: {key_id}")

    extended = key_id.endswith("_E0")
    hex_part = key_id[2:5]  # Берём 3 символа после "SC"

    try:
        scan_code = int(hex_part, 16)
    except ValueError as e:
        raise ValueError(f"Invalid scancode in key_id: {key_id}") from e

    return scan_code, extended


def vk_from_letter(letter: str) -> int:
    """
    Преобразовать букву A-Z или символ в виртуальный код клавиши.

    Args:
        letter: Буква A-Z или символ [ ] , . ' " ? /

    Returns:
        VK-код

    Raises:
        ValueError: Если символ не поддерживается
    """
    letter = letter.upper()
    
    # Символы
    if letter == "[":
        return VK_OEM_4
    if letter == "]":
        return VK_OEM_6
    if letter == ",":
        return VK_OEM_COMMA
    if letter == ".":
        return VK_OEM_PERIOD
    if letter == "'" or letter == '"':
        return VK_OEM_7
    if letter == "\\":
        return VK_OEM_5
    if letter == "/" or letter == "?":
        return VK_OEM_2

    # A-Z
    if len(letter) != 1 or not ("A" <= letter <= "Z"):
        raise ValueError(f"Invalid letter/symbol: {letter}")

    return VK_A + (ord(letter) - ord("A"))


def vk_from_numpad(name: str) -> int:
    """
    Преобразовать имя NumPad-клавиши в виртуальный код.

    Args:
        name: Имя клавиши NUMPAD0..NUMPAD9

    Returns:
        VK-код (VK_NUMPAD0..VK_NUMPAD9)

    Raises:
        ValueError: Если имя не в формате NUMPADn
    """
    name = name.upper()
    if not name.startswith("NUMPAD"):
        raise ValueError(f"Invalid numpad name: {name}")

    try:
        digit = int(name[6:])
        if not (0 <= digit <= 9):
            raise ValueError(f"Invalid numpad digit: {digit}")
    except ValueError as e:
        raise ValueError(f"Invalid numpad name: {name}") from e

    return VK_NUMPAD0 + digit


def vk_from_fkey(name: str) -> int:
    """
    Преобразовать имя F-клавиши в виртуальный код.

    Args:
        name: Имя клавиши F1..F24

    Returns:
        VK-код (VK_F1..VK_F24)

    Raises:
        ValueError: Если имя невалидно
    """
    name = name.upper()
    if not name.startswith("F"):
        raise ValueError(f"Invalid F-key name: {name}")

    try:
        number = int(name[1:])
    except ValueError as e:
        raise ValueError(f"Invalid F-key name: {name}") from e

    if 1 <= number <= 12:
        return VK_F1 + (number - 1)
    elif 13 <= number <= 24:
        return VK_F13 + (number - 13)
    else:
        raise ValueError(f"Invalid F-key number: {number}")


def vk_from_key_name(name: str) -> int:
    """
    Преобразовать имя клавиши в виртуальный код.

    Поддерживается:
    - Буквы A-Z и символы [ ] , . ' " ? / \\
    - NumPad (NUMPAD0..NUMPAD9)
    - F1..F24
    - Специальные: Space, PgUp, PgDown, Home, End, Insert, ArrowUp/Down/Left/Right
    """
    if not name:
        raise ValueError("Empty key name")

    raw = name.strip()
    if not raw:
        raise ValueError("Empty key name")

    # Одиночные символы и буквы
    if len(raw) == 1 or raw in ("[", "]", ",", ".", "'", '"', "/", "?"):
        return vk_from_letter(raw)

    raw_upper = raw.upper()
    if raw_upper.startswith("NUMPAD"):
        return vk_from_numpad(raw_upper)

    if raw_upper.startswith("F"):
        return vk_from_fkey(raw_upper)

    normalized = _normalize_key_name(raw)
    if normalized in _SPECIAL_KEY_VK_MAP:
        return _SPECIAL_KEY_VK_MAP[normalized]

    raise ValueError(f"Invalid key name: {name}")


def letter_from_vk(vk: int) -> str:
    """
    Преобразовать VK-код в букву.

    Args:
        vk: VK-код (VK_A..VK_Z)

    Returns:
        Буква A-Z

    Raises:
        ValueError: Если VK не в диапазоне VK_A..VK_Z
    """
    vk_z = VK_A + 25  # VK_Z
    if not (VK_A <= vk <= vk_z):
        raise ValueError(f"Invalid VK code for letter: {vk}")

    return chr(ord("A") + (vk - VK_A))


def is_top_number_row(scan_code: int) -> bool:
    """
    Проверить, является ли scancode клавишей верхнего цифрового ряда.

    Args:
        scan_code: Скан-код клавиши

    Returns:
        True если это клавиша 1-0, -, =
    """
    return scan_code in TOP_NUMBER_ROW_SCANCODES


def is_function_key(scan_code: int) -> bool:
    """
    Проверить, является ли scancode F-клавишей.

    Args:
        scan_code: Скан-код клавиши

    Returns:
        True если это F1-F12
    """
    return scan_code in FUNCTION_KEY_SCANCODES


def format_combo_string(mods: list[str], vk: int) -> str:
    """
    Сформировать строковое представление комбинации клавиш.

    Args:
        mods: Список модификаторов ["CTRL", "ALT", "WIN"]
        vk: VK-код целевой клавиши

    Returns:
        Строка вида "Ctrl+Alt+Win+A" или "Ctrl+Alt+Win+NUMPAD5"
    """
    parts = []
    for mod in mods:
        mod_upper = mod.upper()
        if mod_upper == "CTRL" or mod_upper == "CONTROL":
            parts.append("Ctrl")
        elif mod_upper == "ALT" or mod_upper == "MENU":
            parts.append("Alt")
        elif mod_upper == "SHIFT":
            parts.append("Shift")
        elif mod_upper == "WIN":
            parts.append("Win")
        else:
            parts.append(mod)

    # Определяем имя клавиши
    vk_z = VK_A + 25
    if VK_A <= vk <= vk_z:
        key_name = chr(ord("A") + (vk - VK_A))
    elif VK_NUMPAD0 <= vk <= VK_NUMPAD0 + 9:
        key_name = f"NUMPAD{vk - VK_NUMPAD0}"
    elif VK_F1 <= vk <= VK_F24:
        key_name = f"F{vk - VK_F1 + 1}"
    else:
        vk_to_name = {
            VK_SPACE: "Space",
            VK_PRIOR: "PgUp",
            VK_NEXT: "PgDown",
            VK_HOME: "Home",
            VK_END: "End",
            VK_INSERT: "Insert",
            VK_UP: "Up",
            VK_DOWN: "Down",
            VK_LEFT: "Left",
            VK_RIGHT: "Right",
        }
        key_name = vk_to_name.get(vk, f"0x{vk:02X}")

    parts.append(key_name)

    return "+".join(parts)
