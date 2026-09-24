"""
Главное окно приложения Hyperion.

Содержит:
- MainWindow с вкладками (QTabWidget)
- Вкладка "Статус" — toggle enabled, индикаторы
- Вкладка "Клавиши" — калибровка и маппинг (A-Z, NumPad)
- Вкладка "Фильтры" — blacklist процессов, настройки перехвата
- Вкладка "Логи" — просмотр событий
"""

import queue
import time
from typing import Optional

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QPushButton,
    QCheckBox,
    QComboBox,
    QLineEdit,
    QListWidget,
    QTableWidget,
    QHeaderView,
    QGroupBox,
    QSystemTrayIcon,
    QMenu,
    QApplication,
    QSpinBox,
)

from ..runtime.engine import Engine
from ..runtime.hook import HookThread
from ..runtime.input_dispatcher import InputDispatcher
from ..services.config import ConfigData
from ..services.logging_service import EventLog
from ..services.settings import load_settings
from ..services.window_events_mixin import WindowEventsMixin
from ..version import __version__
from .window_keys_mixin import WindowKeysMixin
from .window_runtime_mixin import WindowRuntimeMixin
from .window_settings_mixin import WindowSettingsMixin


KEYS_TABLE_HEADERS = ("Клавиша", "ScanCode", "Действие", "Управление")


class MainWindow(
    WindowEventsMixin,
    WindowRuntimeMixin,
    WindowSettingsMixin,
    WindowKeysMixin,
    QMainWindow,
):
    """Главное окно приложения."""

    is_closing = False  # Флаг для разрешения закрытия

    def __init__(
        self,
        engine: Engine,
        hook_thread: HookThread,
        event_queue: queue.Queue,
        config: ConfigData,
        event_log: EventLog,
        input_dispatcher: InputDispatcher,
    ):
        super().__init__()

        self.engine = engine
        self.hook_thread = hook_thread
        self.event_queue = event_queue
        self.config = config
        self.event_log = event_log
        self.input_dispatcher = input_dispatcher

        self._recording_type: Optional[str] = None
        self._logs_dirty = False
        self._last_logs_refresh = 0.0
        self._suspend_generation = 0
        self._suspend_active = False
        self._last_hook_health_check = 0.0
        self._last_hook_renewal = time.monotonic()

        # Загружаем настройки окна
        self._settings = load_settings()
        self._restore_window_geometry()

        self._setup_ui()
        self._setup_tray()
        self._setup_timer()

    def _setup_ui(self) -> None:
        """Настроить UI."""
        self.setWindowTitle(f"Hyperion v{__version__}")
        self.setMinimumSize(400, 300)

        # Центральный виджет
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Вкладки
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Создаём вкладки
        self._create_status_tab()
        self._create_keys_tab()
        self._create_filters_tab()
        self._create_settings_tab()

    def _create_status_tab(self) -> None:
        """Вкладка Статус."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Переключатель Enabled + кнопка Suspend в одном ряду
        top_row = QHBoxLayout()

        self.enabled_checkbox = QCheckBox("Включено (Enabled)")
        self.enabled_checkbox.setChecked(self.config.enabled)
        self.enabled_checkbox.stateChanged.connect(self._on_enabled_changed)
        top_row.addWidget(self.enabled_checkbox)

        self.suspend_btn = QPushButton("Приостановить на 10 сек")
        self.suspend_btn.setEnabled(self.config.enabled)
        self.suspend_btn.clicked.connect(self._on_suspend_clicked)
        top_row.addWidget(self.suspend_btn)

        top_row.addStretch()
        layout.addLayout(top_row)

        # Индикаторы состояния
        status_group = QGroupBox("Состояние")
        status_layout = QVBoxLayout(status_group)

        self.caps_indicator = QLabel("CapsLock: не нажат")
        status_layout.addWidget(self.caps_indicator)

        self.hyper_indicator = QLabel("Hyper: неактивен")
        status_layout.addWidget(self.hyper_indicator)

        self.hook_indicator = QLabel("Keyboard hook: проверка...")
        status_layout.addWidget(self.hook_indicator)

        self.last_combo_label = QLabel("Последний хоткей: —")
        status_layout.addWidget(self.last_combo_label)

        layout.addWidget(status_group)

        # Логи
        logs_group = QGroupBox("Логи")
        logs_layout = QVBoxLayout(logs_group)

        # Фильтры логов
        filter_layout = QHBoxLayout()

        self.log_filter_combo = QComboBox()
        self.log_filter_combo.addItems(
            [
                "Все события",
                "Только отправленные",
                "Только подавленные",
                "Только ошибки",
            ]
        )
        self.log_filter_combo.currentIndexChanged.connect(self._refresh_logs)
        filter_layout.addWidget(QLabel("Фильтр:"))
        filter_layout.addWidget(self.log_filter_combo)

        self.clear_logs_btn = QPushButton("Очистить")
        self.clear_logs_btn.setObjectName("dangerButton")
        self.clear_logs_btn.clicked.connect(self._on_clear_logs_clicked)
        filter_layout.addWidget(self.clear_logs_btn)

        filter_layout.addStretch()
        logs_layout.addLayout(filter_layout)

        # Список логов
        self.logs_list = QListWidget()
        self.logs_list.setFont(self.logs_list.font())
        logs_layout.addWidget(self.logs_list)

        layout.addWidget(logs_group, 1)  # stretch factor для растяжения

        self.tabs.addTab(tab, "Статус")

    def _create_keys_tab(self) -> None:
        """Вкладка Клавиши (Unified Keys Tab)."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Инструкция
        info_label = QLabel(
            "Настройка клавиш Hyperion.\n"
            "1. КАЛИБРОВКА: Программа должна запомнить вашу физическую клавишу (ScanCode).\n"
            "2. МАППИНГ: Настройте, что отправлять при нажатии (Hyper+Клавиша или F13-F24).\n"
            "Доступны буквы, NumPad и навигационные клавиши."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Таблица
        self.keys_table = QTableWidget()
        self.keys_table.setColumnCount(4)
        self.keys_table.setHorizontalHeaderLabels(KEYS_TABLE_HEADERS)

        self.keys_table.verticalHeader().setDefaultSectionSize(46)  # Высота строки под кнопки

        header = self.keys_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # KeyID
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Action
        header.setSectionResizeMode(3, QHeaderView.Fixed)  # Buttons

        self.keys_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.keys_table.setSelectionMode(QTableWidget.SingleSelection)
        self.keys_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.keys_table.doubleClicked.connect(self._on_table_double_clicked)

        layout.addWidget(self.keys_table)

        # Кнопка сброса всего
        btn_layout = QHBoxLayout()
        self.reset_all_btn = QPushButton("Сбросить ВСЕ настройки клавиш")
        self.reset_all_btn.setObjectName("dangerButton")
        self.reset_all_btn.clicked.connect(self._on_reset_all_keys_clicked)
        btn_layout.addStretch()
        btn_layout.addWidget(self.reset_all_btn)
        layout.addLayout(btn_layout)

        self._refresh_keys_table()
        self.tabs.addTab(tab, "Клавиши")

    def _on_table_double_clicked(self) -> None:
        """Обработка двойного клика (редактирование маппинга)."""
        # Если кликнули по строке, открываем редактор маппинга
        self._edit_row_mapping(self.keys_table.currentRow())

    def _create_filters_tab(self) -> None:
        """Вкладка Фильтры."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Blacklist процессов
        blacklist_group = QGroupBox("Blacklist процессов")
        bl_layout = QVBoxLayout(blacklist_group)

        # Добавление процесса
        add_layout = QHBoxLayout()
        self.process_input = QLineEdit()
        self.process_input.setPlaceholderText("Имя процесса (например, game.exe)")
        add_layout.addWidget(self.process_input)

        self.add_process_btn = QPushButton("Добавить")
        self.add_process_btn.clicked.connect(self._on_add_process_clicked)
        add_layout.addWidget(self.add_process_btn)

        bl_layout.addLayout(add_layout)

        # Список процессов
        self.blacklist_list = QListWidget()
        self.blacklist_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.blacklist_list.itemChanged.connect(self._on_blacklist_item_changed)
        self._refresh_blacklist()
        bl_layout.addWidget(self.blacklist_list)

        # Кнопки управления
        buttons_row = QHBoxLayout()

        self.remove_process_btn = QPushButton("Удалить выбранные")
        self.remove_process_btn.setObjectName("dangerButton")
        self.remove_process_btn.clicked.connect(self._on_remove_process_clicked)
        buttons_row.addWidget(self.remove_process_btn)

        self.select_all_btn = QPushButton("Выделить все")
        self.select_all_btn.clicked.connect(self._on_select_all_clicked)
        buttons_row.addWidget(self.select_all_btn)

        self.unselect_all_btn = QPushButton("Снять все")
        self.unselect_all_btn.clicked.connect(self._on_unselect_all_clicked)
        buttons_row.addWidget(self.unselect_all_btn)

        self.invert_selection_btn = QPushButton("Обратить")
        self.invert_selection_btn.clicked.connect(self._on_invert_selection_clicked)
        buttons_row.addWidget(self.invert_selection_btn)

        bl_layout.addLayout(buttons_row)

        layout.addWidget(blacklist_group, 1)  # stretch factor = 1

        # Опции
        options_group = QGroupBox("Опции")
        opt_layout = QVBoxLayout(options_group)

        self.ignore_numbers_cb = QCheckBox("Игнорировать верхний цифровой ряд")
        self.ignore_numbers_cb.setChecked(self.config.ignore_top_number_row)
        self.ignore_numbers_cb.stateChanged.connect(self._on_options_changed)
        opt_layout.addWidget(self.ignore_numbers_cb)

        self.ignore_fkeys_cb = QCheckBox("Игнорировать F-клавиши")
        self.ignore_fkeys_cb.setChecked(self.config.ignore_function_keys)
        self.ignore_fkeys_cb.stateChanged.connect(self._on_options_changed)
        opt_layout.addWidget(self.ignore_fkeys_cb)

        self.capture_numpad_cb = QCheckBox("Перехватывать NumPad")
        self.capture_numpad_cb.setChecked(self.config.capture_numpad)
        self.capture_numpad_cb.stateChanged.connect(self._on_options_changed)
        opt_layout.addWidget(self.capture_numpad_cb)

        self.ignore_injected_cb = QCheckBox("Игнорировать программно созданные события клавиатуры")
        self.ignore_injected_cb.setChecked(self.config.ignore_injected_events)
        self.ignore_injected_cb.stateChanged.connect(self._on_options_changed)
        opt_layout.addWidget(self.ignore_injected_cb)

        layout.addWidget(options_group)

        self.tabs.addTab(tab, "Фильтры")

    def _create_settings_tab(self) -> None:
        """Вкладка Настройки."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Интерфейс
        ui_group = QGroupBox("Интерфейс")
        ui_layout = QVBoxLayout(ui_group)

        # Размер шрифта
        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("Размер шрифта:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 24)
        self.font_size_spin.setValue(self._settings.font_size)
        self.font_size_spin.setSuffix(" px")
        self.font_size_spin.valueChanged.connect(self._on_font_size_changed)
        font_row.addWidget(self.font_size_spin)
        font_row.addStretch()
        ui_layout.addLayout(font_row)

        # Запуск свёрнутым в трей
        self.start_minimized_cb = QCheckBox("Запускать свёрнутым в трей")
        self.start_minimized_cb.setChecked(self._settings.start_minimized)
        self.start_minimized_cb.stateChanged.connect(self._on_start_minimized_changed)
        ui_layout.addWidget(self.start_minimized_cb)

        # Автозагрузка
        self.autostart_cb = QCheckBox("Автозагрузка при старте Windows")
        self.autostart_cb.setChecked(self._settings.autostart)
        self.autostart_cb.stateChanged.connect(self._on_autostart_changed)
        ui_layout.addWidget(self.autostart_cb)

        layout.addWidget(ui_group)

        # Конфигурация
        config_group = QGroupBox("Конфигурация")
        from PySide6.QtWidgets import QGridLayout

        config_layout = QGridLayout(config_group)

        # Labels
        config_layout.addWidget(QLabel("Экспорт:"), 0, 0)
        config_layout.addWidget(QLabel("Импорт:"), 1, 0)

        # Export Buttons
        self.export_config_btn = QPushButton("Config")
        self.export_config_btn.clicked.connect(self._on_export_config_clicked)
        config_layout.addWidget(self.export_config_btn, 0, 1)

        self.export_settings_btn = QPushButton("Settings")
        self.export_settings_btn.clicked.connect(self._on_export_settings_clicked)
        config_layout.addWidget(self.export_settings_btn, 0, 2)

        self.export_all_btn = QPushButton("Все")
        self.export_all_btn.clicked.connect(self._on_export_all_clicked)
        config_layout.addWidget(self.export_all_btn, 0, 3)

        # Import Buttons
        self.import_config_btn = QPushButton("Config")
        self.import_config_btn.clicked.connect(self._on_import_config_clicked)
        config_layout.addWidget(self.import_config_btn, 1, 1)

        self.import_settings_btn = QPushButton("Settings")
        self.import_settings_btn.clicked.connect(self._on_import_settings_clicked)
        config_layout.addWidget(self.import_settings_btn, 1, 2)

        self.import_all_btn = QPushButton("Все")
        self.import_all_btn.clicked.connect(self._on_import_all_clicked)
        config_layout.addWidget(self.import_all_btn, 1, 3)

        layout.addWidget(config_group)

        layout.addStretch()  # Прижимаем элементы к верху
        self.tabs.addTab(tab, "Настройки")

    def _setup_tray(self) -> None:
        """Настроить системный трей."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip(f"Hyperion v{__version__}")

        # Устанавливаем иконку трея из иконки приложения
        app_icon = QApplication.instance().windowIcon()
        if not app_icon.isNull():
            self.tray_icon.setIcon(app_icon)

        # Меню трея
        tray_menu = QMenu()

        self.tray_toggle_action = QAction("Отключить", self)
        self.tray_toggle_action.triggered.connect(self._on_tray_toggle)
        tray_menu.addAction(self.tray_toggle_action)

        show_action = QAction("Показать окно", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self._on_quit)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
