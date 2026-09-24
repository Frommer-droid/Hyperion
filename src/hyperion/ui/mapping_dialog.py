"""
Диалог настройки маппинга клавиши.
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QCheckBox,
    QPushButton,
    QGroupBox,
    QRadioButton,
    QButtonGroup,
)


class MappingDialog(QDialog):
    """
    Диалог для настройки того, что отправлять при нажатии клавиши.
    
    Варианты:
    1. Default (Hyper + Буква) - если маппинг удален
    2. Custom (F13..F24 + Модификаторы)
    """

    def __init__(self, parent=None, current_mapping: dict = None, letter_name: str = ""):
        super().__init__(parent)
        self.setWindowTitle(f"Настройка клавиши: {letter_name}")
        self.setModal(True)
        self.resize(400, 300)

        self.current_mapping = current_mapping or {}
        self.result_mapping = None

        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Группа выбора режима
        mode_group = QGroupBox("Режим вывода")
        mode_layout = QVBoxLayout(mode_group)

        self.radio_default = QRadioButton("По умолчанию (Hyper + Буква)")
        self.radio_custom = QRadioButton("Кастомный (F13-F24)")
        
        self.bg = QButtonGroup(self)
        self.bg.addButton(self.radio_default)
        self.bg.addButton(self.radio_custom)

        self.radio_default.toggled.connect(self._on_mode_changed)

        mode_layout.addWidget(self.radio_default)
        mode_layout.addWidget(self.radio_custom)
        layout.addWidget(mode_group)

        # Группа кастомных настроек
        self.custom_group = QGroupBox("Настройки кастомного вывода")
        custom_layout = QVBoxLayout(self.custom_group)

        # Выбор клавиши (F13-F24)
        fkey_layout = QHBoxLayout()
        fkey_layout.addWidget(QLabel("Клавиша:"))
        self.fkey_combo = QComboBox()
        self.fkey_combo.addItems([f"F{i}" for i in range(13, 25)]) # F13..F24
        fkey_layout.addWidget(self.fkey_combo)
        custom_layout.addLayout(fkey_layout)

        # Модификаторы
        mods_group = QGroupBox("Модификаторы")
        mods_layout = QVBoxLayout(mods_group)
        
        self.cb_ctrl = QCheckBox("CTRL")
        self.cb_alt = QCheckBox("ALT")
        self.cb_shift = QCheckBox("SHIFT")
        self.cb_win = QCheckBox("WIN")

        mods_layout.addWidget(self.cb_ctrl)
        mods_layout.addWidget(self.cb_alt)
        mods_layout.addWidget(self.cb_shift)
        mods_layout.addWidget(self.cb_win)

        custom_layout.addWidget(mods_group)
        layout.addWidget(self.custom_group)

        layout.addStretch()

        # Кнопки
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self._on_ok)
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def _load_data(self):
        """Загрузить текущие настройки в UI."""
        if not self.current_mapping:
            # Нет маппинга -> Default
            self.radio_default.setChecked(True)
        else:
            # Есть маппинг -> Custom
            self.radio_custom.setChecked(True)
            
            vk_name = self.current_mapping.get("vk", "VK_F13")
            mods = self.current_mapping.get("mods", [])

            # Устанавливаем F-клавишу
            # vk_name ожидается "VK_F13" -> "F13"
            short_name = vk_name.replace("VK_", "")
            index = self.fkey_combo.findText(short_name)
            if index >= 0:
                self.fkey_combo.setCurrentIndex(index)

            # Чекбоксы
            self.cb_ctrl.setChecked("CTRL" in mods)
            self.cb_alt.setChecked("ALT" in mods)
            self.cb_shift.setChecked("SHIFT" in mods)
            self.cb_win.setChecked("WIN" in mods)

        self._on_mode_changed()

    def _on_mode_changed(self):
        """Обновить доступность контролов."""
        is_custom = self.radio_custom.isChecked()
        self.custom_group.setEnabled(is_custom)

    def _on_ok(self):
        """Сохранить результат."""
        if self.radio_default.isChecked():
            # Если Default, возвращаем None (знак удаления маппинга)
            self.result_mapping = None
        else:
            # Сбор данных для Custom
            fkey = self.fkey_combo.currentText() # "F13"
            vk_str = f"VK_{fkey}"
            
            mods = []
            if self.cb_ctrl.isChecked():
                mods.append("CTRL")
            if self.cb_alt.isChecked():
                mods.append("ALT")
            if self.cb_shift.isChecked():
                mods.append("SHIFT")
            if self.cb_win.isChecked():
                mods.append("WIN")
            
            self.result_mapping = {
                "vk": vk_str,
                "mods": mods
            }
        
        self.accept()
