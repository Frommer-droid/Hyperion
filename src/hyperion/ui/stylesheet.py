"""Единая тема One Dark для PySide6."""


import sys
from pathlib import Path

THEME_COLORS = {
    "background": "#282C34",
    "surface": "#21252B",
    "surface_alt": "#2C313C",
    "surface_hover": "#353B45",
    "surface_pressed": "#181A1F",
    "alternate": "#262A32",
    "selection": "#3E4451",
    "primary": "#3E4451",
    "primary_hover": "#4B5263",
    "accent": "#61AFEF",
    "accent_hover": "#7BC0F6",
    "accent_pressed": "#4D95C7",
    "success": "#98C379",
    "text": "#ABB2BF",
    "text_strong": "#E6E6E6",
    "muted": "#9DA5B4",
    "on_accent": "#21252B",
    "border": "#3E4451",
    "focus": "#61AFEF",
    "danger": "#E06C75",
    "danger_text": "#E8838B",
    "danger_surface": "#352A31",
    "warning": "#D19A66",
    "disabled_text": "#5C6370",
    "disabled_background": "#21252B",
    "disabled_border": "#2C313C",
    "scrollbar": "#4B5263",
}
DERIVED_COLORS = {"warning_hover": "#E0AC78"}

COLORS = {
    "bg_main": THEME_COLORS["background"],
    "bg_element": THEME_COLORS["surface"],
    "accent": THEME_COLORS["accent"],
    "accent_light": THEME_COLORS["accent_hover"],
    "structural": THEME_COLORS["border"],
    "btn_standard": THEME_COLORS["primary"],
    "btn_warning": THEME_COLORS["warning"],
    "text_primary": THEME_COLORS["text_strong"],
    "text_dark": THEME_COLORS["on_accent"],
}

# Шрифты
FONT_FAMILY = "Tahoma, Segoe UI, Aptos"
DEFAULT_FONT_SIZE = 15


def get_assets_path() -> Path:
    """Получить путь к папке assets.

    Работает как в dev-режиме, так и в скомпилированном (frozen) приложении.
    """
    if getattr(sys, 'frozen', False):
        # Скомпилированное приложение - assets в _internal
        base_path = Path(sys._MEIPASS)
        return base_path / "assets"
    else:
        # Dev-режим - assets в корне проекта
        return Path(__file__).parent.parent.parent.parent / "assets"


def get_stylesheet(font_size: int = DEFAULT_FONT_SIZE) -> str:
    """Получить QSS stylesheet для темы One Dark.

    Args:
        font_size: Размер шрифта в пикселях (по умолчанию 15)
    """
    font_size_px = f"{font_size}px"

    # Путь к иконке стрелки (используем forward slashes для QSS)
    arrow_icon = str(get_assets_path() / "icons" / "arrowdown.png").replace("\\", "/")

    return f"""
/* ======================================
   ТЕМА ONE DARK
====================================== */

/* Основной виджет */
QMainWindow, QWidget {{
    background-color: {COLORS["bg_main"]};
    color: {COLORS["text_primary"]};
    font-family: {FONT_FAMILY};
    font-size: {font_size_px};
}}

/* Вкладки */
QTabWidget::pane {{
    border: 1px solid {COLORS["accent"]};
    background-color: {COLORS["bg_main"]};
}}

QTabBar::tab {{
    background-color: {COLORS["bg_element"]};
    color: {COLORS["text_primary"]};
    padding: 8px 16px;
    margin-right: 2px;
    border: 1px solid {COLORS["bg_element"]};
    border-bottom: none;
}}

QTabBar::tab:selected {{
    background-color: {COLORS["bg_main"]};
    border: 1px solid {COLORS["accent"]};
    border-bottom: none;
    color: {COLORS["accent"]};
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLORS["bg_main"]};
}}

/* Кнопки */
QPushButton {{
    background-color: {COLORS["btn_standard"]};
    color: {COLORS["text_primary"]};
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: bold;
}}

QPushButton:hover {{
    background-color: {THEME_COLORS["primary_hover"]};
}}

QPushButton:pressed {{
    background-color: {THEME_COLORS["surface_pressed"]};
}}

QPushButton:disabled {{
    background-color: {THEME_COLORS["disabled_background"]};
    color: {THEME_COLORS["disabled_text"]};
}}

/* Кнопка главного действия */
QPushButton#primaryButton {{
    background-color: {COLORS["accent_light"]};
    color: {COLORS["text_dark"]};
}}

QPushButton#primaryButton:hover {{
    background-color: {THEME_COLORS["accent"]};
}}

QPushButton#primaryButton:pressed {{
    background-color: {THEME_COLORS["accent_pressed"]};
}}

QPushButton#primaryButton:disabled {{
    background-color: {THEME_COLORS["disabled_background"]};
    color: {THEME_COLORS["disabled_text"]};
}}

/* Кнопка предупреждения */
QPushButton#warningButton {{
    background-color: {COLORS["btn_warning"]};
    color: {COLORS["text_primary"]};
}}

QPushButton#warningButton:hover {{
    background-color: {DERIVED_COLORS["warning_hover"]};
}}

QPushButton#warningButton:pressed {{
    background-color: {THEME_COLORS["surface_pressed"]};
}}

QPushButton#dangerButton {{
    background-color: {THEME_COLORS["danger"]};
    color: {THEME_COLORS["on_accent"]};
}}

QPushButton#dangerButton:hover {{
    background-color: {THEME_COLORS["danger_text"]};
}}

QPushButton#dangerButton:pressed {{
    background-color: {THEME_COLORS["danger_surface"]};
    color: {THEME_COLORS["text_strong"]};
}}

QPushButton#dangerButton:disabled {{
    background-color: {THEME_COLORS["disabled_background"]};
    color: {THEME_COLORS["disabled_text"]};
}}

/* Чекбоксы */
QCheckBox {{
    color: {COLORS["text_primary"]};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {COLORS["accent"]};
    border-radius: 3px;
    background-color: {COLORS["bg_element"]};
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS["accent"]};
}}

QCheckBox::indicator:hover {{
    border-color: {COLORS["accent_light"]};
}}

/* Метки */
QLabel {{
    color: {COLORS["accent"]};
}}

/* Группы */
QGroupBox {{
    border: 1px solid {COLORS["structural"]};
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: bold;
}}

QGroupBox::title {{
    color: {COLORS["structural"]};
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}}

/* Поля ввода */
QLineEdit, QSpinBox {{
    background-color: {COLORS["bg_element"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["accent"]};
    border-radius: 4px;
    padding: 6px;
}}

QLineEdit:focus, QSpinBox:focus {{
    border-color: {COLORS["accent_light"]};
}}

/* Выпадающие списки */
QComboBox {{
    background-color: {COLORS["bg_element"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["accent"]};
    border-radius: 4px;
    padding: 6px;
    padding-right: 25px;
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox::down-arrow {{
    image: url({arrow_icon});
    width: 12px;
    height: 12px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS["bg_element"]};
    color: {COLORS["text_primary"]};
    selection-background-color: {COLORS["accent"]};
    selection-color: {COLORS["text_dark"]};
}}

/* Списки */
QListWidget {{
    background-color: {COLORS["bg_element"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["accent"]};
    border-radius: 4px;
}}

QListWidget::item {{
    padding: 4px;
}}

QListWidget::item:selected {{
    background-color: {COLORS["accent"]};
    color: {COLORS["text_dark"]};
}}

QListWidget::item:hover:!selected {{
    background-color: {THEME_COLORS["surface_hover"]};
}}

/* Таблицы */
QTableWidget {{
    background-color: {COLORS["bg_element"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["accent"]};
    gridline-color: {THEME_COLORS["border"]};
}}

QTableWidget::item {{
    padding: 4px;
}}

QTableWidget::item:selected {{
    background-color: {COLORS["accent"]};
    color: {COLORS["text_dark"]};
}}

QHeaderView::section {{
    background-color: {COLORS["bg_main"]};
    color: {COLORS["accent"]};
    padding: 6px;
    border: none;
    border-bottom: 1px solid {COLORS["accent"]};
    font-weight: bold;
}}

/* Угловая ячейка таблицы */
QTableCornerButton::section {{
    background-color: {COLORS["bg_main"]};
    border: none;
    border-bottom: 1px solid {COLORS["accent"]};
}}

/* Скроллбары */
QScrollBar:vertical {{
    background-color: {COLORS["bg_element"]};
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS["accent"]};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {COLORS["bg_element"]};
    height: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLORS["accent"]};
    border-radius: 5px;
    min-width: 30px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Системный трей меню */
QMenu {{
    background-color: {COLORS["bg_element"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["accent"]};
}}

QMenu::item {{
    padding: 6px 20px;
}}

QMenu::item:selected {{
    background-color: {COLORS["accent"]};
    color: {COLORS["text_dark"]};
}}

QMenu::separator {{
    height: 1px;
    background-color: {COLORS["accent"]};
    margin: 4px 10px;
}}
"""
