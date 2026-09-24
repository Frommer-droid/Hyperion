import threading

from hyperion.runtime import input_dispatcher


def test_dispatcher_processes_commands_in_order_on_one_worker(monkeypatch):
    calls = []
    completed = threading.Event()

    def fake_send_combo(modifiers, vk_code):
        calls.append(("combo", modifiers, vk_code, threading.get_ident()))
        return True

    def fake_toggle_capslock():
        calls.append(("capslock", [], 0, threading.get_ident()))
        completed.set()

    monkeypatch.setattr(input_dispatcher, "send_combo", fake_send_combo)
    monkeypatch.setattr(input_dispatcher, "toggle_capslock", fake_toggle_capslock)
    dispatcher = input_dispatcher.InputDispatcher()
    dispatcher.start()

    assert dispatcher.submit_combo(["CTRL", "SHIFT"], 0x41)
    assert dispatcher.submit_capslock_tap()
    assert completed.wait(1.0)
    assert dispatcher.stop()

    assert [call[0] for call in calls] == ["combo", "capslock"]
    assert calls[0][3] == calls[1][3]
    assert calls[0][3] != threading.get_ident()


def test_dispatcher_rejects_commands_after_stop():
    dispatcher = input_dispatcher.InputDispatcher()
    dispatcher.start()
    assert dispatcher.stop()

    assert not dispatcher.submit_capslock_tap()
