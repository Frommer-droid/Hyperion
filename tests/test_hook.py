import ctypes
import queue

from hyperion.runtime.engine import Config, Engine
from hyperion.runtime.hook import HookThread
from hyperion.runtime.kbd_structs import KBDLLHOOKSTRUCT, VK_CAPITAL, WM_KEYDOWN


class RecordingDispatcher:
    def __init__(self):
        self.combos = []

    def submit_combo(self, modifiers, vk_code):
        self.combos.append((modifiers, vk_code))
        return True

    def submit_capslock_tap(self):
        return True


def send_hook_keydown(hook, vk_code, scan_code):
    event = KBDLLHOOKSTRUCT(
        vkCode=vk_code,
        scanCode=scan_code,
        flags=0,
        time=0,
        dwExtraInfo=0,
    )
    return hook._low_level_handler(0, WM_KEYDOWN, ctypes.addressof(event))


def test_suppressed_capslock_stays_active_until_keyup():
    engine = Engine(
        Config(
            letters_sc_map={"SC016": "G"},
            output_map={"SC016": {"vk": "VK_F19", "mods": ["CTRL"]}},
        )
    )
    dispatcher = RecordingDispatcher()
    hook = HookThread(engine, queue.Queue(), dispatcher)

    assert send_hook_keydown(hook, VK_CAPITAL, 0x3A) == 1
    assert send_hook_keydown(hook, ord("G"), 0x16) == 1

    assert dispatcher.combos == [(["CTRL"], 0x82)]
