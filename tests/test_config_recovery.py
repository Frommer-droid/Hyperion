import json

import pytest

from hyperion.services.config import ConfigData, load_config, save_config


def test_corrupt_config_is_backed_up_before_error(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{broken", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_config(path)

    backups = list(tmp_path.glob("config.corrupt-*.json"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{broken"


def test_injected_event_policy_round_trips(tmp_path):
    path = tmp_path / "config.json"
    save_config(ConfigData(ignore_injected_events=False), path)

    assert load_config(path).ignore_injected_events is False
