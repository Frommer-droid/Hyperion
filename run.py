#!/usr/bin/env python
"""
Запуск Hyperion.

Использование:
    python run.py
"""

import sys
from pathlib import Path

# Добавляем src в PYTHONPATH
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from hyperion.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
