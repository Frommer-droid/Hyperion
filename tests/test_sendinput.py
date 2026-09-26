import ctypes

from hyperion.runtime import sendinput
from hyperion.runtime.kbd_structs import (
    INPUT,
    KBDLLHOOKSTRUCT,
    KEYEVENTF_KEYUP,
    KEYEVENTF_SCANCODE,
    VK_A,
    VK_LCONTROL,
    VK_LMENU,
    VK_LSHIFT,
    VK_LWIN,
)


def test_winapi_structs_use_pointer_sized_extra_info():
    pointer_size = ctypes.sizeof(ctypes.c_void_p)

    assert KBDLLHOOKSTRUCT.dwExtraInfo.size == pointer_size
    assert INPUT.union.offset % pointer_size == 0


def test_send_combo_includes_shift_and_releases_modifiers_in_reverse(monkeypatch):
    captured = []

    def fake_send_input(count, inputs, size):
        captured.extend(inputs[index] for index in range(count))
        return count

    scan_codes = {
        VK_LCONTROL: 0x1D,
        VK_LSHIFT: 0x2A,
        VK_LMENU: 0x38,
        VK_LWIN: 0x5B,
        VK_A: 0x1E,
    }
    monkeypatch.setattr(sendinput, "SendInput", fake_send_input)
    monkeypatch.setattr(sendinput, "vk_to_scan", scan_codes.__getitem__)

    assert sendinput.send_combo(["CTRL", "SHIFT", "ALT", "WIN"], VK_A)

    scans_and_flags = [
        (item.union.ki.wScan, item.union.ki.dwFlags) for item in captured
    ]
    assert [scan for scan, _ in scans_and_flags] == [
        0x1D,
        0x2A,
        0x38,
        0x5B,
        0x1E,
        0x1E,
        0x5B,
        0x38,
        0x2A,
        0x1D,
    ]
    assert all(flags & KEYEVENTF_SCANCODE for _, flags in scans_and_flags)
    assert not scans_and_flags[4][1] & KEYEVENTF_KEYUP
    assert all(flags & KEYEVENTF_KEYUP for _, flags in scans_and_flags[5:])
    assert all(item.union.ki.dwExtraInfo == sendinput.MARKER for item in captured)
