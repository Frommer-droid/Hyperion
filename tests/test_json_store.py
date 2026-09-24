import json

import pytest

from hyperion.services import json_store


def test_atomic_write_json_replaces_file(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"old": true}', encoding="utf-8")

    json_store.atomic_write_json(path, {"name": "Гиперион", "enabled": True})

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "name": "Гиперион",
        "enabled": True,
    }
    assert not list(tmp_path.glob("*.tmp"))


def test_atomic_write_json_preserves_original_if_replace_fails(monkeypatch, tmp_path):
    path = tmp_path / "settings.json"
    original = '{"font_size": 15}'
    path.write_text(original, encoding="utf-8")

    def fail_replace(source, target):
        raise OSError("replace failed")

    monkeypatch.setattr(json_store.os, "replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        json_store.atomic_write_json(path, {"font_size": 20})

    assert path.read_text(encoding="utf-8") == original
    assert not list(tmp_path.glob("*.tmp"))
