from hyperion.services import settings


def test_dev_autostart_uses_neighboring_pythonw(monkeypatch, tmp_path):
    python_path = tmp_path / "python.exe"
    pythonw_path = tmp_path / "pythonw.exe"
    pythonw_path.touch()
    monkeypatch.setattr(settings.sys, "executable", str(python_path))
    monkeypatch.setattr(settings.sys, "frozen", False, raising=False)

    target, arguments = settings.get_autostart_command()

    assert target == pythonw_path
    assert arguments == f'"{settings.get_app_executable_path()}"'


def test_frozen_autostart_targets_executable_without_arguments(monkeypatch, tmp_path):
    executable = tmp_path / "Hyperion.exe"
    monkeypatch.setattr(settings.sys, "executable", str(executable))
    monkeypatch.setattr(settings.sys, "frozen", True, raising=False)

    assert settings.get_autostart_command() == (executable, "")


def test_corrupt_settings_are_backed_up_before_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("not-json", encoding="utf-8")

    loaded = settings.load_settings(path)

    assert loaded == settings.Settings()
    backups = list(tmp_path.glob("settings.corrupt-*.json"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "not-json"
