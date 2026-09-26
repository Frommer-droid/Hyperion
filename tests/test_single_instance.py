from hyperion.services import single_instance


def test_single_instance_detects_existing_mutex(monkeypatch):
    closed = []
    monkeypatch.setattr(single_instance, "CreateMutexW", lambda *_args: 123)
    monkeypatch.setattr(single_instance, "GetLastError", lambda: 183)
    monkeypatch.setattr(single_instance, "CloseHandle", closed.append)
    monkeypatch.setattr(single_instance, "SetLastError", lambda _value: None)

    guard = single_instance.SingleInstanceGuard("test")
    guard.close()

    assert guard.already_running is True
    assert closed == [123]
