from hyperion.runtime.engine import Config, Engine, KeyEvent
from hyperion.runtime.kbd_structs import VK_A, VK_CAPITAL, VK_RETURN


def key_event(event_type: str, vk_code: int, scan_code: int):
    return KeyEvent.from_hook_data(event_type, vk_code, scan_code, False)


def test_capslock_repeat_does_not_turn_hyper_hold_into_tap():
    engine = Engine(Config(letters_sc_map={"SC01E": "A"}))

    engine.handle(key_event("KEYDOWN", VK_CAPITAL, 0x3A))
    combo = engine.handle(key_event("KEYDOWN", VK_A, 0x1E))
    repeat = engine.handle(key_event("KEYDOWN", VK_CAPITAL, 0x3A))
    release = engine.handle(key_event("KEYUP", VK_CAPITAL, 0x3A))

    assert combo.send_combo is not None
    assert repeat.suppress is True
    assert release.suppress is True
    assert release.send_capslock_tap is False


def test_stray_capslock_keyup_is_not_converted_to_tap():
    engine = Engine()

    action = engine.handle(key_event("KEYUP", VK_CAPITAL, 0x3A))

    assert action.suppress is False
    assert action.send_capslock_tap is False


def test_disabling_engine_clears_pressed_state():
    engine = Engine()
    engine.handle(key_event("KEYDOWN", VK_CAPITAL, 0x3A))

    engine.enabled = False

    assert engine.caps_is_down is False
    assert engine.caps_used_as_prefix is False


def test_record_mode_does_not_suppress_keyup_pressed_before_recording():
    engine = Engine()
    engine.start_record_main()

    action = engine.handle(key_event("KEYUP", VK_RETURN, 0x1C))

    assert action.suppress is False


def test_record_mode_suppresses_matching_keyup_after_recording_stops():
    engine = Engine()
    engine.start_record_main()
    engine.handle(key_event("KEYDOWN", VK_A, 0x1E))
    engine.stop_record()

    release = engine.handle(key_event("KEYUP", VK_A, 0x1E))

    assert release.suppress is True
