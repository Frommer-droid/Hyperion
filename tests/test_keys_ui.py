import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QHeaderView, QPushButton, QTableWidget

from hyperion.ui.main_window import KEYS_TABLE_HEADERS
from hyperion.ui.stylesheet import get_stylesheet
from hyperion.ui.window_keys_mixin import (
    BUTTON_TEXT_EXTRA_WIDTH,
    WindowKeysMixin,
    fit_button_to_text,
)


def get_application() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_keys_table_headers_do_not_contain_internal_labels():
    assert KEYS_TABLE_HEADERS == ("Клавиша", "ScanCode", "Действие", "Управление")


def test_calibrate_button_width_accounts_for_large_font_and_padding():
    get_application()
    button = QPushButton("Калибровать")
    button.setFont(QFont(button.font().family(), 24))

    width = fit_button_to_text(button, 145)

    expected = button.fontMetrics().horizontalAdvance(button.text()) + BUTTON_TEXT_EXTRA_WIDTH
    assert width >= expected
    assert button.minimumWidth() == width


def test_keys_table_control_column_fits_both_buttons():
    app = get_application()
    app.setStyleSheet(get_stylesheet(15))
    host = WindowKeysMixin()
    host.keys_table = QTableWidget()
    host.keys_table.setColumnCount(4)
    host.keys_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
    host.config = SimpleNamespace(letters_sc_map={}, numpad_sc_map={}, output_map={})

    host._refresh_keys_table()

    container = host.keys_table.cellWidget(0, 3)
    buttons = container.findChildren(QPushButton)
    required_width = sum(button.minimumWidth() for button in buttons) + 12
    assert host.keys_table.columnWidth(3) >= required_width
    assert host.keys_table.isSortingEnabled() is False
