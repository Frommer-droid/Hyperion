"""Восстановление окна в видимой рабочей области мониторов."""

from __future__ import annotations

from typing import Iterable


Rect = tuple[int, int, int, int]


def ensure_visible_geometry(saved: Rect, screens: Iterable[Rect]) -> Rect:
    """Вернуть сохранённую геометрию либо центрировать окно на первом экране."""
    screen_list = list(screens)
    if not screen_list:
        return saved

    x, y, width, height = saved
    for sx, sy, sw, sh in screen_list:
        overlap_width = max(0, min(x + width, sx + sw) - max(x, sx))
        overlap_height = max(0, min(y + height, sy + sh) - max(y, sy))
        if overlap_width >= 64 and overlap_height >= 32:
            return saved

    sx, sy, sw, sh = screen_list[0]
    width = min(max(width, 400), sw)
    height = min(max(height, 300), sh)
    x = sx + max(0, (sw - width) // 2)
    y = sy + max(0, (sh - height) // 2)
    return x, y, width, height
