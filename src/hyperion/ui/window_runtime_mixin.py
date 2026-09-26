"""Runtime-поведение главного окна: hook, очередь событий, tray и геометрия."""

import queue
import time

from PySide6.QtCore import QTimer, Slot
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from ..runtime.hook import HookThread
from ..services.config import get_config_path
from ..services.settings import WindowSettings, save_settings
from ..services.window_geometry import ensure_visible_geometry


LOG_REFRESH_INTERVAL_SECONDS = 0.1
HOOK_HEALTH_CHECK_INTERVAL_SECONDS = 2.0
HOOK_RENEW_INTERVAL_SECONDS = 60.0


class WindowRuntimeMixin:
    """Изолирует lifecycle и Windows-runtime от сборки вкладок MainWindow."""

    def _setup_timer(self) -> None:
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_events)
        self.poll_timer.start(10)

    @Slot()
    def _poll_events(self) -> None:
        self._check_hook_health()
        events_processed = 0
        while events_processed < 20:
            try:
                event = self.event_queue.get_nowait()
                self._process_event(event)
                events_processed += 1
            except queue.Empty:
                break
        now = time.monotonic()
        if self._logs_dirty and now - self._last_logs_refresh >= LOG_REFRESH_INTERVAL_SECONDS:
            self._refresh_logs()
            self._logs_dirty = False
            self._last_logs_refresh = now
        self._update_indicators()

    def _check_hook_health(self) -> None:
        """Переустановить умерший или тихо снятый Windows hook."""
        now = time.monotonic()
        if now - self._last_hook_health_check < HOOK_HEALTH_CHECK_INTERVAL_SECONDS:
            return
        self._last_hook_health_check = now

        hook_missing = not self.hook_thread or not self.hook_thread.is_alive()
        hook_inactive = not hook_missing and not self.hook_thread.is_hook_active
        renewal_due = now - self._last_hook_renewal >= HOOK_RENEW_INTERVAL_SECONDS
        if hook_missing or hook_inactive or renewal_due:
            self.restart_hook(silent=True)

    def restart_hook(self, silent: bool = False) -> None:
        """Перезапустить hook без одновременной обработки двумя callback-ами."""
        if not silent:
            print("Restarting hook...")

        old_thread = self.hook_thread
        if old_thread and old_thread.is_alive():
            if not old_thread.stop():
                try:
                    self.event_queue.put_nowait(
                        {
                            "type": "error",
                            "details": "Не удалось остановить предыдущий keyboard hook",
                        }
                    )
                except queue.Full:
                    pass
                return

        new_thread = HookThread(self.engine, self.event_queue, self.input_dispatcher)
        self.hook_thread = new_thread
        new_thread.start()
        self._last_hook_renewal = time.monotonic()

    def quit_application(self) -> None:
        self.is_closing = True
        self._save_window_geometry()
        if self.hook_thread and self.hook_thread.is_alive():
            self.hook_thread.stop()
        self.event_log.save_to_file(get_config_path())
        QApplication.quit()

    def _process_event(self, event: dict) -> None:
        self.event_log.add_from_dict(event)
        event_type = event.get("type", "")

        if event_type == "sent_combo":
            details = event.get("details", "")
            self.last_combo_label.setText(f"Последний хоткей: {details}")

        if event_type == "recorded_key":
            self._process_recorded_key(event)

        self._logs_dirty = True

    def _process_recorded_key(self, event: dict) -> None:
        key_id = event.get("key_id", "")
        if self._recording_type != "recalibrate_key":
            self._stop_recording()
            return

        if hasattr(self, "_recalibrating_target_type") and hasattr(
            self, "_recalibrating_target_name"
        ):
            target_type = self._recalibrating_target_type
            target_name = self._recalibrating_target_name
            old_key_id = getattr(self, "_recalibrating_old_key_id", "")
            target_map = (
                self.config.letters_sc_map if target_type == "letter" else self.config.numpad_sc_map
            )

            target_map.pop(key_id, None)
            if old_key_id and old_key_id != key_id:
                target_map.pop(old_key_id, None)
            target_map[key_id] = target_name
            self._save_config()
            self._refresh_keys_table()
            self._update_engine_config()

            del self._recalibrating_target_type
            del self._recalibrating_target_name
            if hasattr(self, "_recalibrating_old_key_id"):
                del self._recalibrating_old_key_id

        self._stop_recording()

    def _update_indicators(self) -> None:
        hook_active = bool(
            self.hook_thread and self.hook_thread.is_alive() and self.hook_thread.is_hook_active
        )
        if hook_active:
            self.hook_indicator.setText("Keyboard hook: работает")
            self.hook_indicator.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.hook_indicator.setText("Keyboard hook: восстанавливается")
            self.hook_indicator.setStyleSheet("color: orange; font-weight: bold;")

        if self.engine.caps_is_down:
            self.caps_indicator.setText("CapsLock: НАЖАТ")
            self.caps_indicator.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.caps_indicator.setText("CapsLock: не нажат")
            self.caps_indicator.setStyleSheet("")

        if self.engine.caps_used_as_prefix:
            self.hyper_indicator.setText("Hyper: АКТИВЕН")
            self.hyper_indicator.setStyleSheet("color: blue; font-weight: bold;")
        else:
            self.hyper_indicator.setText("Hyper: неактивен")
            self.hyper_indicator.setStyleSheet("")

    @Slot()
    def _on_enabled_changed(self) -> None:
        self._cancel_suspend()
        enabled = self.enabled_checkbox.isChecked()
        self.config.enabled = enabled
        self.engine.enabled = enabled
        self.tray_toggle_action.setText("Отключить" if enabled else "Включить")
        self.suspend_btn.setEnabled(enabled)
        self._save_config()

    @Slot()
    def _on_suspend_clicked(self) -> None:
        if not self.engine.enabled:
            return
        self._suspend_generation += 1
        generation = self._suspend_generation
        self._suspend_active = True
        self.engine.enabled = False
        QTimer.singleShot(10000, lambda: self._resume_after_suspend(generation))
        self.suspend_btn.setEnabled(False)
        self.suspend_btn.setText("Приостановлено...")

    def _resume_after_suspend(self, generation: int) -> None:
        if not self._suspend_active or generation != self._suspend_generation:
            return
        self._suspend_active = False
        if self.enabled_checkbox.isChecked():
            self.engine.enabled = True
            self.suspend_btn.setEnabled(True)
        self.suspend_btn.setText("Приостановить на 10 сек")

    def _cancel_suspend(self) -> None:
        if not self._suspend_active:
            return
        self._suspend_active = False
        self._suspend_generation += 1
        self.suspend_btn.setText("Приостановить на 10 сек")

    @Slot()
    def _on_clear_logs_clicked(self) -> None:
        self.event_log.clear()
        self.logs_list.clear()
        self._logs_dirty = False

    @Slot()
    def _on_tray_toggle(self) -> None:
        self.enabled_checkbox.setChecked(not self.enabled_checkbox.isChecked())

    @Slot()
    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self.show()
            self.activateWindow()

    @Slot()
    def _on_quit(self) -> None:
        self.quit_application()

    def closeEvent(self, event) -> None:
        self._save_window_geometry()
        if not self.is_closing:
            event.ignore()
        else:
            event.accept()

    def hide_to_tray(self) -> None:
        self._save_window_geometry()
        self.hide()

    def _restore_window_geometry(self) -> None:
        window = self._settings.window
        screens = [
            (
                screen.availableGeometry().x(),
                screen.availableGeometry().y(),
                screen.availableGeometry().width(),
                screen.availableGeometry().height(),
            )
            for screen in QApplication.screens()
        ]
        geometry = ensure_visible_geometry(
            (window.x, window.y, window.width, window.height),
            screens,
        )
        self.setGeometry(*geometry)
        if window.maximized:
            self.showMaximized()

    def _save_window_geometry(self) -> None:
        geometry = self.geometry()
        self._settings.window = WindowSettings(
            x=geometry.x(),
            y=geometry.y(),
            width=geometry.width(),
            height=geometry.height(),
            maximized=self.isMaximized(),
        )
        try:
            save_settings(self._settings)
        except Exception:
            pass
