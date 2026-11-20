import numpy as np

from ambilight import config, extract, layout
from helpers import make_frame

W, H = 720, 480


def colors_for(color_at):
    cfg = config.Config()
    rects = layout.led_rects(cfg)
    return rects, extract.region_colors(make_frame(W, H, color_at), W, H, rects)


def test_solid_colours_are_recovered():
    for rgb in [(255, 255, 255), (0, 0, 0), (200, 40, 40), (30, 90, 220), (20, 180, 60)]:
        _, c = colors_for(lambda x, y, rgb=rgb: rgb)
        assert np.abs(c - np.array(rgb)).max() < 4.0, rgb


def test_left_and_right_halves_land_in_the_right_leds():
    red, blue = (230, 20, 20), (20, 20, 230)
    rects, c = colors_for(lambda x, y: red if x < W // 2 else blue)
    checked = 0
    for (x0, _, x1, _), col in zip(rects, c):
        if x0 < W // 2 < x1:      # the middle top LED covers both halves and is mixed by design
            continue
        want = np.array(red if x1 <= W // 2 else blue)
        assert np.abs(col - want).max() < 6.0
        checked += 1
    assert checked == len(rects) - 1


def test_row_step_gives_nearly_the_same_result():
    cfg = config.Config()
    rects = layout.led_rects(cfg)
    frame = make_frame(W, H, lambda x, y: (x * 255 // W, y * 255 // H, 128))
    a = extract.region_colors(frame, W, H, rects, row_step=1)
    b = extract.region_colors(frame, W, H, rects, row_step=3)
    assert np.abs(a - b).max() < 6.0


def test_wrong_frame_size_is_rejected():
    import pytest
    with pytest.raises(ValueError):
        extract.frame_view(b"\x00" * 100, W, H)
