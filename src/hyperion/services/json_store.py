"""Надёжное сохранение JSON с атомарной заменой целевого файла."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


def backup_corrupt_json(path: Path) -> Path:
    """Сохранить повреждённый JSON рядом с оригиналом для ручного восстановления."""
    source = Path(path)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = source.with_name(f"{source.stem}.corrupt-{timestamp}{source.suffix}")
    shutil.copy2(source, backup)
    return backup


def atomic_write_json(path: Path, data: Any) -> None:
    """Записать JSON через временный файл в той же директории и os.replace."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=target.parent,
            delete=False,
        ) as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)

        os.replace(temporary_path, target)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
