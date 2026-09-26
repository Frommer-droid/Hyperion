"""Калибровка, отображение и редактирование клавиш."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QWidget,
)

from .mapping_dialog import MappingDialog


BUTTON_TEXT_EXTRA_WIDTH = 48


def fit_button_to_text(button: QPushButton, base_minimum: int) -> int:
    """Подобрать ширину кнопки с запасом под QSS-padding и крупный шрифт."""
    text_width = button.fontMetrics().horizontalAdvance(button.text())
    minimum_width = max(base_minimum, text_width + BUTTON_TEXT_EXTRA_WIDTH)
    button.setMinimumWidth(minimum_width)
    return minimum_width


class WindowKeysMixin:
    """UI-обработчики клавиш без кода построения главного окна."""

    def _stop_recording(self) -> None:
        """Остановить запись."""
        self.engine.stop_record()
        self._recording_type = None

        # Сбрасываем текст кнопок, если они есть (в виджетах таблицы) - не требуется, т.к. таблица обновится
        # Но если мы перешли на QMessageBox, то кнопки сами разблочатся

    def _refresh_keys_table(self) -> None:
        """Обновить таблицу клавиш (Unified)."""
        if not hasattr(self, "keys_table"):
            return

        self.keys_table.setSortingEnabled(False)
        self.keys_table.setRowCount(0)

        items = []

        # 1. Буквы A-Z
        letter_to_id = {v: k for k, v in self.config.letters_sc_map.items()}
        for i in range(ord("A"), ord("Z") + 1):
            name = chr(i)
            key_id = letter_to_id.get(name, "")
            items.append({"name": name, "key_id": key_id, "type": "letter"})

        # 1.1 Символы
        special_symbols = ["[", "]", "?", ",", ".", '"', "\\"]
        for sym in special_symbols:
            key_id = letter_to_id.get(sym, "")
            items.append({"name": sym, "key_id": key_id, "type": "letter"})

        # 1.2 Дополнительные клавиши
        extra_keys = [
            "Space",
            "PgUp",
            "PgDown",
            "Home",
            "End",
            "Insert",
            "ArrowUp",
            "ArrowDown",
            "ArrowLeft",
            "ArrowRight",
        ]
        for name in extra_keys:
            key_id = letter_to_id.get(name, "")
            items.append({"name": name, "key_id": key_id, "type": "letter"})

        # 2. NumPad
        numpad_to_id = {v: k for k, v in self.config.numpad_sc_map.items()}
        for i in range(10):
            name = f"NUMPAD{i}"
            key_id = numpad_to_id.get(name, "")
            items.append({"name": name, "key_id": key_id, "type": "numpad"})

        self.keys_table.setRowCount(len(items))
        controls_column_width = 0

        for i, item in enumerate(items):
            key_id = item["key_id"]
            name = item["name"]

            # Колонка Name
            self.keys_table.setItem(i, 0, QTableWidgetItem(name))

            # Колонка Status
            status_text = key_id if key_id else "НЕ ОТКАЛИБРОВАНА"
            st_item = QTableWidgetItem(status_text)
            if not key_id:
                st_item.setForeground(Qt.GlobalColor.red)
            self.keys_table.setItem(i, 1, st_item)

            # Колонка Action
            if not key_id:
                action_text = "—"
            elif key_id in self.config.output_map:
                m = self.config.output_map[key_id]
                vk = m.get("vk", "").replace("VK_", "")
                mods = "+".join(m.get("mods", []))
                action_text = f"{mods} + {vk}" if mods else vk
            else:
                action_text = f"Hyper + {name}"

            self.keys_table.setItem(i, 2, QTableWidgetItem(action_text))

            # Колонка Buttons (Widget)
            container = QWidget()
            h_layout = QHBoxLayout(container)
            h_layout.setContentsMargins(2, 2, 2, 2)
            h_layout.setSpacing(4)

            calib_btn = QPushButton("Калибровать")
            calib_width = fit_button_to_text(calib_btn, 145)
            calib_btn.clicked.connect(lambda checked=False, r=i: self._calibrate_row(r))

            edit_btn = QPushButton("Настроить")
            edit_width = fit_button_to_text(edit_btn, 125)
            edit_btn.clicked.connect(lambda checked=False, r=i: self._edit_row_mapping(r))

            # Кнопка настройки доступна только если клавиша откалибрована
            edit_btn.setEnabled(bool(key_id))

            h_layout.addWidget(calib_btn)
            h_layout.addWidget(edit_btn)
            h_layout.addStretch()

            controls_width = calib_width + edit_width + h_layout.spacing() + 8
            container.setMinimumWidth(controls_width)
            controls_column_width = max(controls_column_width, controls_width)

            self.keys_table.setCellWidget(i, 3, container)

        self.keys_table.setColumnWidth(3, controls_column_width)
        # Строки содержат QWidget-кнопки с привязкой к индексу. Сортировка
        # QTableWidget нарушает эту связь, поэтому порядок всегда канонический.
        self.keys_table.setSortingEnabled(False)

    def _calibrate_row(self, row_index: int) -> None:
        """Запустить калибровку для строки."""
        name_item = self.keys_table.item(row_index, 0)
        if not name_item:
            return
        name = name_item.text()

        # Определяем тип (Letter или NumPad)
        if name.startswith("NUMPAD"):
            target_type = "numpad"
            target_map = self.config.numpad_sc_map
        else:
            target_type = "letter"
            target_map = self.config.letters_sc_map

        # Ищем текущий key_id
        old_key_id = ""
        for k, v in target_map.items():
            if v == name:
                old_key_id = k
                break

        self._recalibrating_target_type = target_type
        self._recalibrating_target_name = name
        self._recalibrating_old_key_id = old_key_id

        # Запуск записи
        self._recording_type = "recalibrate_key"
        if target_type == "numpad":
            self.engine.start_record_numpad()
        else:
            self.engine.start_record_main()

        QMessageBox.information(self, "Калибровка", f"Нажмите физическую клавишу для '{name}'...")

    def _edit_row_mapping(self, row_index: int) -> None:
        """Редактировать маппинг строки."""
        name_item = self.keys_table.item(row_index, 0)
        if not name_item:
            return
        name = name_item.text()

        # Ищем key_id в конфиге
        key_id = ""
        for k, v in self.config.letters_sc_map.items():
            if v == name:
                key_id = k
                break
        if not key_id:
            for k, v in self.config.numpad_sc_map.items():
                if v == name:
                    key_id = k
                    break

        if not key_id:
            QMessageBox.warning(
                self, "Ошибка", f"Клавиша '{name}' не откалибрована! Сначала нажмите 'Калибровать'."
            )
            return

        # Открываем диалог
        current_map = self.config.output_map.get(key_id, None)
        dlg = MappingDialog(self, current_mapping=current_map, letter_name=name)
        if dlg.exec():
            new_map = dlg.result_mapping
            if new_map is None:
                # Вернули в дефолт
                if key_id in self.config.output_map:
                    del self.config.output_map[key_id]
            else:
                # Сохранили кастом
                self.config.output_map[key_id] = new_map

            self._save_config()
            self._refresh_keys_table()
            self._update_engine_config()

    def _on_reset_all_keys_clicked(self) -> None:
        """Сброс всех настроек."""
        res = QMessageBox.warning(
            self,
            "Сброс",
            "Это удалит ВСЕ калибровки и маппинги клавиш.\nВы уверены?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if res == QMessageBox.Yes:
            self.config.letters_sc_map.clear()
            self.config.numpad_sc_map.clear()
            self.config.output_map.clear()
            self._save_config()
            self._refresh_keys_table()
            self._update_engine_config()
