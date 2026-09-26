"""Version helper."""

from __future__ import annotations

import sys
from pathlib import Path


def _read_version() -> str:
    # В frozen (скомпилированном) режиме читаем из внутреннего бандла
    if getattr(sys, 'frozen', False):
        try:
            # sys._MEIPASS - это временная папка, куда распаковывается exe
            version_file = Path(sys._MEIPASS) / "VERSION"
            if version_file.exists():
                return version_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass
        return "0.0.0"

    # В режиме разработки читаем из файла VERSION в корне
    # src/hyperion/version.py -> src/hyperion -> src -> корень
    version_file = Path(__file__).resolve().parent.parent.parent / "VERSION"
    if version_file.exists():
        value = version_file.read_text(encoding="utf-8").strip()
        if value:
            return value
    return "0.0.0"


__version__ = _read_version()
