from hyperion.services.window_geometry import ensure_visible_geometry


def test_visible_saved_geometry_is_preserved():
    saved = (100, 100, 900, 700)
    assert ensure_visible_geometry(saved, [(0, 0, 1920, 1040)]) == saved


def test_offscreen_geometry_is_centered_on_available_screen():
    result = ensure_visible_geometry((4000, 2000, 900, 700), [(0, 0, 1920, 1040)])
    assert result == (510, 170, 900, 700)
