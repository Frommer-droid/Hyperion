from hyperion.runtime.process_guard import ForegroundProcessMonitor, is_blacklisted


def test_foreground_monitor_caches_resolved_process_outside_consumer():
    calls = []
    monitor = ForegroundProcessMonitor(resolver=lambda: calls.append(1) or "GAME.EXE")

    assert monitor.refresh() == "GAME.EXE"
    assert monitor.process_name == "GAME.EXE"
    assert len(calls) == 1


def test_blacklist_matching_is_case_insensitive_and_exact():
    assert is_blacklisted("game.exe", ["GAME.EXE"])
    assert not is_blacklisted("mygame.exe", ["game.exe"])


def test_monitor_skips_process_lookup_when_blacklist_is_inactive():
    calls = []
    monitor = ForegroundProcessMonitor(
        resolver=lambda: calls.append(1) or "game.exe",
        should_refresh=lambda: False,
    )

    assert monitor.refresh() == ""
    assert calls == []
