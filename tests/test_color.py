import numpy as np

from ambilight import color, config


def test_gamma_one_keeps_values():
    rgb = np.array([[10.0, 128.0, 255.0]])
    assert np.allclose(color.apply_gamma_brightness(rgb, config.Color(gamma=1.0)), rgb)


def test_gamma_darkens_midtones_and_keeps_extremes():
    out = color.apply_gamma_brightness(np.array([[0.0, 128.0, 255.0]]), config.Color(gamma=2.2))
    assert out[0, 0] == 0 and abs(out[0, 2] - 255) < 1e-3 and out[0, 1] < 128 * 0.5


def test_brightness_scales_linearly():
    out = color.apply_gamma_brightness(np.array([[255.0, 255.0, 255.0]]), config.Color(gamma=1.0, brightness=0.5))
    assert np.allclose(out, 127.5)


def test_full_white_strip_is_limited_to_the_budget():
    leds = config.Leds(max_current_ma=2000)
    white = np.full((109, 3), 255.0)
    assert color.estimated_current_ma(white, leds) > 6000          # the hazard the limit protects against
    limited = color.limit_current(white, leds)
    assert color.estimated_current_ma(limited, leds) <= 2000 + 1e-6


def test_limit_keeps_the_hue():
    leds = config.Leds(max_current_ma=500)
    rgb = np.tile(np.array([255.0, 128.0, 0.0]), (109, 1))
    out = color.limit_current(rgb, leds)
    assert np.allclose(out[:, 1] / out[:, 0], 128.0 / 255.0)


def test_below_budget_is_untouched():
    leds = config.Leds(max_current_ma=2000)
    rgb = np.full((109, 3), 10.0)
    assert color.limit_current(rgb, leds) is rgb


def test_budget_below_idle_current_switches_everything_off():
    leds = config.Leds(max_current_ma=50)   # 109 LEDs idle at 1 mA each already exceed this
    assert not color.limit_current(np.full((109, 3), 255.0), leds).any()


def test_to_bytes_rounds_and_clips():
    out = color.to_bytes(np.array([[-5.0, 127.6, 300.0]]))
    assert out.tolist() == [[0, 128, 255]]


def test_floor_keeps_the_limit_where_rounding_does_not():
    leds = config.Leds(max_current_ma=2000)
    rng = np.random.default_rng(5)
    rgb = color.limit_current(rng.uniform(100, 255, (109, 3)), leds)
    floored = color.to_bytes(rgb, floor=True).astype(np.float32)
    assert color.estimated_current_ma(floored, leds) <= 2000.0
    assert color.to_bytes(np.array([[1.9, 2.5, 254.99]]), floor=True).tolist() == [[1, 2, 254]]
