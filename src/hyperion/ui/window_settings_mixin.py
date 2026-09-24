"""Настройки, фильтры, импорт и экспорт главного окна."""

from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QListWidgetItem,
    QMessageBox,
)

from ..services.config import (
    config_to_engine_config,
    load_config,
    save_config,
)
from ..services.settings import load_settings, save_settings


class WindowSettingsMixin:
    """UI-обработчики конфигурации без кода построения виджетов."""

    @Slot()
    def _on_add_process_clicked(self) -> None:
        """Добавить процесс в blacklist."""
        process = self.process_input.text().strip()
        if not process:
            return

        # Проверяем, нет ли уже такого процесса
        existing_names = [p.get("name", "").lower() for p in self.config.process_blacklist]
        if process.lower() not in existing_names:
            self.config.process_blacklist.append({"name": process, "enabled": True})
            self._save_config()
            self._refresh_blacklist()
            self._update_engine_config()

        self.process_input.clear()

    @Slot()
    def _on_remove_process_clicked(self) -> None:
        """Удалить выбранные процессы из blacklist."""
        selected_items = self.blacklist_list.selectedItems()
        if not selected_items:
            return

        # Собираем имена выбранных процессов
        selected_names = {item.text().lower() for item in selected_items}

        # Удаляем из конфига
        self.config.process_blacklist = [
            p
            for p in self.config.process_blacklist
            if p.get("name", "").lower() not in selected_names
        ]

        self._save_config()
        self._refresh_blacklist()
        self._update_engine_config()

    @Slot(QListWidgetItem)
    def _on_blacklist_item_changed(self, item: QListWidgetItem) -> None:
        """Изменено состояние чекбокса в blacklist."""
        process_name = item.text()
        enabled = item.checkState() == Qt.Checked

        # Обновляем состояние в конфиге
        for entry in self.config.process_blacklist:
            if entry.get("name", "").lower() == process_name.lower():
                entry["enabled"] = enabled
                break

        self._save_config()
        self._update_engine_config()

    @Slot()
    def _on_select_all_clicked(self) -> None:
        """Выделить все (включить блокировку для выбранных или всех)."""
        selected_items = self.blacklist_list.selectedItems()
        if selected_items:
            # Только выбранные
            selected_names = {item.text().lower() for item in selected_items}
            for entry in self.config.process_blacklist:
                if entry.get("name", "").lower() in selected_names:
                    entry["enabled"] = True
        else:
            # Все
            for entry in self.config.process_blacklist:
                entry["enabled"] = True
        self._save_config()
        self._refresh_blacklist()
        self._update_engine_config()

    @Slot()
    def _on_unselect_all_clicked(self) -> None:
        """Снять все (отключить блокировку для выбранных или всех)."""
        selected_items = self.blacklist_list.selectedItems()
        if selected_items:
            # Только выбранные
            selected_names = {item.text().lower() for item in selected_items}
            for entry in self.config.process_blacklist:
                if entry.get("name", "").lower() in selected_names:
                    entry["enabled"] = False
        else:
            # Все
            for entry in self.config.process_blacklist:
                entry["enabled"] = False
        self._save_config()
        self._refresh_blacklist()
        self._update_engine_config()

    @Slot()
    def _on_invert_selection_clicked(self) -> None:
        """Обратить выделение (инвертировать состояние для выбранных или всех)."""
        selected_items = self.blacklist_list.selectedItems()
        if selected_items:
            # Только выбранные
            selected_names = {item.text().lower() for item in selected_items}
            for entry in self.config.process_blacklist:
                if entry.get("name", "").lower() in selected_names:
                    entry["enabled"] = not entry.get("enabled", True)
        else:
            # Все
            for entry in self.config.process_blacklist:
                entry["enabled"] = not entry.get("enabled", True)
        self._save_config()
        self._refresh_blacklist()
        self._update_engine_config()

    @Slot()
    def _on_options_changed(self) -> None:
        """Изменены опции."""
        self.config.ignore_top_number_row = self.ignore_numbers_cb.isChecked()
        self.config.ignore_function_keys = self.ignore_fkeys_cb.isChecked()
        self.config.capture_numpad = self.capture_numpad_cb.isChecked()
        self.config.ignore_injected_events = self.ignore_injected_cb.isChecked()

        self._save_config()
        self._update_engine_config()

    @Slot(int)
    def _on_font_size_changed(self, value: int) -> None:
        """Изменён размер шрифта."""
        from .stylesheet import get_stylesheet

        self._settings.font_size = value
        QApplication.instance().setStyleSheet(get_stylesheet(value))

        # Сохраняем настройки
        try:
            save_settings(self._settings)
        except Exception:
            pass

    @Slot()
    def _on_start_minimized_changed(self) -> None:
        """Изменена настройка запуска свёрнутым."""
        self._settings.start_minimized = self.start_minimized_cb.isChecked()
        try:
            save_settings(self._settings)
        except Exception:
            pass

    @Slot()
    def _on_autostart_changed(self) -> None:
        """Изменена настройка автозагрузки."""
        from ..services.settings import set_autostart

        enabled = self.autostart_cb.isChecked()
        success = set_autostart(enabled)

        if success:
            self._settings.autostart = enabled
            try:
                save_settings(self._settings)
            except Exception:
                pass
        else:
            # Откатываем чекбокс при ошибке
            self.autostart_cb.blockSignals(True)
            self.autostart_cb.setChecked(not enabled)
            self.autostart_cb.blockSignals(False)
            QMessageBox.warning(self, "Ошибка", "Не удалось изменить настройку автозагрузки.")

    @Slot()
    def _on_export_config_clicked(self) -> None:
        """Экспортировать конфигурацию в файл."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт конфигурации (keys, blacklist)", "config.json", "JSON файлы (*.json)"
        )
        if file_path:
            try:
                save_config(self.config, Path(file_path))
                QMessageBox.information(self, "Успех", "Конфигурация экспортирована.")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось экспортировать: {e}")

    @Slot()
    def _on_export_settings_clicked(self) -> None:
        """Экспортировать настройки приложения."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт настроек (window, fonts)", "settings.json", "JSON файлы (*.json)"
        )
        if file_path:
            try:
                save_settings(self._settings, Path(file_path))
                QMessageBox.information(self, "Успех", "Настройки экспортированы.")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось экспортировать: {e}")

    @Slot()
    def _on_export_all_clicked(self) -> None:
        """Экспортировать всё (в папку)."""
        dir_path = QFileDialog.getExistingDirectory(self, "Выберите папку для экспорта")
        if dir_path:
            try:
                path = Path(dir_path)
                save_config(self.config, path / "config.json")
                save_settings(self._settings, path / "settings.json")
                QMessageBox.information(self, "Успех", "Все настройки экспортированы в папку.")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось экспортировать: {e}")

    @Slot()
    def _on_import_config_clicked(self) -> None:
        """Импортировать конфигурацию из файла."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Импорт конфигурации", "", "JSON файлы (*.json)"
        )
        if file_path:
            try:
                new_config = load_config(Path(file_path))
                # Применяем
                self.config = new_config
                save_config(self.config)
                self._update_engine_config()
                # UI
                self.enabled_checkbox.setChecked(self.config.enabled)
                self.ignore_numbers_cb.setChecked(self.config.ignore_top_number_row)
                self.ignore_fkeys_cb.setChecked(self.config.ignore_function_keys)
                self.capture_numpad_cb.setChecked(self.config.capture_numpad)
                self._refresh_keys_table()
                self._refresh_blacklist()
                QMessageBox.information(
                    self, "Успех", "Конфигурация (клавиши, фильтры) импортирована."
                )
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось импортировать config: {e}")

    @Slot()
    def _on_import_settings_clicked(self) -> None:
        """Импортировать настройки приложения."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Импорт настроек", "", "JSON файлы (*.json)"
        )
        if file_path:
            try:
                new_settings = load_settings(Path(file_path))
                self._settings = new_settings
                save_settings(self._settings)

                # Применяем (шрифт, размер, автостарт)
                # Геометрия применится только при след. запуске или можно тут
                self.font_size_spin.setValue(self._settings.font_size)
                self.start_minimized_cb.setChecked(self._settings.start_minimized)
                self.autostart_cb.setChecked(self._settings.autostart)

                # Принудительно обновить стиль прямо сейчас
                self._on_font_size_changed(self._settings.font_size)

                QMessageBox.information(self, "Успех", "Настройки (окно, шрифт) импортированы.")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось импортировать settings: {e}")

    @Slot()
    def _on_import_all_clicked(self) -> None:
        """Импортировать всё (выбор нескольких файлов)."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите файлы для импорта (config.json, settings.json)",
            "",
            "JSON файлы (*.json)",
        )
        if not file_paths:
            return

        imported_log = []
        errors_log = []

        for fp in file_paths:
            p = Path(fp)
            # Пытаемся определить тип по содержимому или имени
            # Самый простой способ: если имя содержит 'config' -> config, 'settings' -> settings
            # Или пробовать загрузить
            name_lower = p.name.lower()

            try:
                if "config" in name_lower:
                    # Config
                    new_conf = load_config(p)
                    self.config = new_conf
                    save_config(self.config)
                    self._update_engine_config()
                    # UI refresh
                    self.enabled_checkbox.setChecked(self.config.enabled)
                    self.ignore_numbers_cb.setChecked(self.config.ignore_top_number_row)
                    self.ignore_fkeys_cb.setChecked(self.config.ignore_function_keys)
                    self.capture_numpad_cb.setChecked(self.config.capture_numpad)
                    self._refresh_keys_table()
                    self._refresh_blacklist()
                    imported_log.append("Config")

                elif "settings" in name_lower:
                    # Settings
                    new_set = load_settings(p)
                    self._settings = new_set
                    save_settings(self._settings)
                    # UI refresh
                    self.font_size_spin.setValue(self._settings.font_size)
                    self.start_minimized_cb.setChecked(self._settings.start_minimized)
                    self.autostart_cb.setChecked(self._settings.autostart)
                    self._on_font_size_changed(self._settings.font_size)
                    imported_log.append("Settings")

                else:
                    errors_log.append(f"Пропущен неизвестный файл: {p.name}")

            except Exception as e:
                errors_log.append(f"Ошибка {p.name}: {e}")

        msg = []
        if imported_log:
            msg.append(f"Успешно импортировано: {', '.join(imported_log)}")
        if errors_log:
            msg.append("Ошибки:\n" + "\n".join(errors_log))

        QMessageBox.information(self, "Результат импорта", "\n\n".join(msg))

    # =========================================================================
    # Вспомогательные методы
    # =========================================================================

    def _refresh_blacklist(self) -> None:
        """Обновить список blacklist."""
        self.blacklist_list.clear()
        for entry in self.config.process_blacklist:
            name = entry.get("name", "")
            enabled = entry.get("enabled", True)

            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if enabled else Qt.Unchecked)
            self.blacklist_list.addItem(item)

    def _refresh_logs(self) -> None:
        """Обновить список логов."""
        filter_index = self.log_filter_combo.currentIndex()

        if filter_index == 0:
            entries = self.event_log.get_last(200)
        elif filter_index == 1:
            entries = self.event_log.get_filtered(["sent_combo"], 200)
        elif filter_index == 2:
            entries = self.event_log.get_filtered(["recorded_key", "ignored_key"], 200)
        else:
            entries = self.event_log.get_filtered(["error"], 200)

        self.logs_list.clear()
        for entry in entries:
            self.logs_list.addItem(entry.format_line())

        # Прокрутка вниз
        if self.logs_list.count() > 0:
            self.logs_list.scrollToBottom()

    def _save_config(self) -> None:
        """Сохранить конфигурацию."""
        try:
            save_config(self.config)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить конфиг: {e}")

    def _update_engine_config(self) -> None:
        """Обновить конфигурацию Engine."""
        engine_config = config_to_engine_config(self.config)
        self.engine.update_config(engine_config)
