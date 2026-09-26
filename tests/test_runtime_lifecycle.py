from types import SimpleNamespace

from hyperion.runtime.engine import Engine
from hyperion.ui import window_runtime_mixin
from hyperion.ui.window_runtime_mixin import WindowRuntimeMixin


class FakeButton:
    def __init__(self):
        self.enabled = True
        self.text = ""

    def setEnabled(self, enabled):
        self.enabled = enabled

    def setText(self, text):
        self.text = text


class FakeCheckBox:
    def __init__(self, checked=True):
        self.checked = checked

    def isChecked(self):
        return self.checked


class FakeAction:
    def setText(self, text):
        self.text = text


def make_runtime_host():
    host = WindowRuntimeMixin()
    host.engine = Engine()
    host.config = SimpleNamespace(enabled=True)
    host.enabled_checkbox = FakeCheckBox(True)
    host.suspend_btn = FakeButton()
    host.tray_toggle_action = FakeAction()
    host._suspend_generation = 0
    host._suspend_active = False
    host._save_config = lambda: None
    return host


def test_manual_disable_cancels_pending_suspend_resume(monkeypatch):
    callbacks = []
    monkeypatch.setattr(
        window_runtime_mixin.QTimer,
        "singleShot",
        lambda _delay, callback: callbacks.append(callback),
    )
    host = make_runtime_host()

    host._on_suspend_clicked()
    host.enabled_checkbox.checked = False
    host._on_enabled_changed()
    callbacks[0]()

    assert host.engine.enabled is False
    assert host.config.enabled is False
    assert host.suspend_btn.enabled is False


def test_suspend_resumes_when_persistent_enabled_state_is_unchanged(monkeypatch):
    callbacks = []
    monkeypatch.setattr(
        window_runtime_mixin.QTimer,
        "singleShot",
        lambda _delay, callback: callbacks.append(callback),
    )
    host = make_runtime_host()

    host._on_suspend_clicked()
    callbacks[0]()

    assert host.engine.enabled is True
    assert host.config.enabled is True
    assert host.suspend_btn.enabled is True


def test_hook_watchdog_forces_periodic_renewal(monkeypatch):
    host = WindowRuntimeMixin()
    host.hook_thread = SimpleNamespace(is_alive=lambda: True, is_hook_active=True)
    host._last_hook_health_check = 0.0
    host._last_hook_renewal = 0.0
    calls = []
    host.restart_hook = lambda silent=False: calls.append(silent)
    monkeypatch.setattr(window_runtime_mixin.time, "monotonic", lambda: 61.0)

    host._check_hook_health()

    assert calls == [True]


def test_event_processing_marks_logs_dirty_without_immediate_full_rebuild():
    host = WindowRuntimeMixin()
    added = []
    refreshed = []
    host.event_log = SimpleNamespace(add_from_dict=added.append)
    host._logs_dirty = False
    host._refresh_logs = lambda: refreshed.append(True)

    host._process_event({"type": "state_change", "details": "test"})

    assert len(added) == 1
    assert host._logs_dirty is True
    assert refreshed == []
