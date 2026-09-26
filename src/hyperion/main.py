"""
Точка входа приложения Hyperion.

Запускает Qt приложение с hook-потоком и главным окном.
"""

import ctypes
import json
import os
import queue
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from .runtime.engine import Engine
from .runtime.hook import HookThread
from .runtime.input_dispatcher import InputDispatcher
from .services.config import load_config, get_config_path, config_to_engine_config
from .services.logging_service import EventLog
from .services.localization import (
    install_russian_qt_translations,
    set_russian_qt_locale,
)
from .services.settings import load_settings
from .services.single_instance import SingleInstanceGuard
from .ui.main_window import MainWindow
from .ui.stylesheet import get_stylesheet


def get_app_path() -> Path:
    """Получить путь к директории приложения."""
    if getattr(sys, "frozen", False):
        return Path(os.path.dirname(sys.executable))
    else:
        # src/hyperion/main.py -> корень проекта
        return Path(__file__).resolve().parent.parent.parent


def main() -> int:
    """Запустить единственный экземпляр Hyperion."""
    with SingleInstanceGuard() as instance:
        if instance.already_running:
            ctypes.windll.user32.MessageBoxW(
                None,
                "Hyperion уже запущен.",
                "Hyperion",
                0x00000040,
            )
            return 0
        return _run_application()


def _run_application() -> int:
    """
    Главная функция запуска приложения.

    Returns:
        Код возврата приложения
    """
    # Устанавливаем AppUserModelID для корректного отображения иконки в панели задач
    if sys.platform == "win32":
        app_id = "hyperion.capslock.hyper.1.0"
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass

    set_russian_qt_locale()

    # Создаём Qt приложение и стандартные русские переводы до виджетов
    app = QApplication(sys.argv)
    install_russian_qt_translations(app)
    app.setApplicationName("Hyperion")
    app.setQuitOnLastWindowClosed(False)  # Работаем в трее

    # Устанавливаем иконку приложения
    icon_path = get_app_path() / "logo.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Загружаем настройки интерфейса
    ui_settings = load_settings()

    # Применяем тему One Dark с сохранённым размером шрифта
    app.setStyleSheet(get_stylesheet(ui_settings.font_size))

    # Загружаем конфигурацию
    try:
        config_data = load_config()
        print(f"Loaded config from {get_config_path()}")
    except FileNotFoundError:
        print(f"Config not found at {get_config_path()}, using defaults")
        from .services.config import get_default_config

        config_data = get_default_config()
    except json.JSONDecodeError as exc:
        notes = "\n".join(getattr(exc, "__notes__", []))
        QMessageBox.critical(
            None,
            "Повреждён config.json",
            "Файл конфигурации повреждён. Hyperion запущен с безопасными "
            f"настройками по умолчанию.\n{notes}",
        )
        from .services.config import get_default_config

        config_data = get_default_config()
    except Exception as e:
        print(f"Error loading config: {e}")
        from .services.config import get_default_config

        config_data = get_default_config()

    # Очистка лог-файла при старте (Rule #4)
    try:
        log_path = get_app_path() / "hyperion.log"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("")
    except Exception:
        pass

    # Создаём Engine
    engine_config = config_to_engine_config(config_data)
    engine = Engine(engine_config)

    # Создаём очередь событий
    event_queue: queue.Queue = queue.Queue(maxsize=1000)

    def report_input_error(message: str) -> None:
        try:
            event_queue.put_nowait({"type": "error", "details": message})
        except queue.Full:
            pass

    input_dispatcher = InputDispatcher(error_callback=report_input_error)
    input_dispatcher.start()

    # Создаём лог событий
    event_log = EventLog(max_size=500)

    # Создаём и запускаем hook-поток
    hook_thread = HookThread(engine, event_queue, input_dispatcher)
    hook_thread.start()

    # Создаём главное окно
    window = MainWindow(
        engine=engine,
        hook_thread=hook_thread,
        event_queue=event_queue,
        config=config_data,
        event_log=event_log,
        input_dispatcher=input_dispatcher,
    )

    # Показываем окно или запускаем свёрнутым в трей
    if not ui_settings.start_minimized:
        window.show()

    # Запускаем Qt event loop
    try:
        result = app.exec()
    finally:
        # MainWindow может заменить hook при смене фокуса/конфигурации.
        # Останавливаем актуальный поток, а не только первоначальный объект.
        window.hook_thread.stop()
        input_dispatcher.stop()

    return result


if __name__ == "__main__":
    sys.exit(main())
