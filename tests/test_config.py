from pathlib import Path

import pytest

from ambilight import config

EXAMPLE = Path(__file__).parent.parent / "config" / "ambilight.example.toml"


def test_example_config_loads_and_matches_hardware():
    cfg = config.load(EXAMPLE)
    assert cfg.layout.count == 109
    assert cfg.layout.bottom_slots == 35
    assert cfg.regions.frame_width == 720 and cfg.regions.frame_height == 480


def test_defaults_are_valid():
    config.validate(config.Config())


def test_unknown_key_is_rejected():
    with pytest.raises(config.ConfigError):
        config.from_dict({"layout": {"bottom_rite": 17}})


def test_unknown_section_is_rejected():
    with pytest.raises(config.ConfigError):
        config.from_dict({"colour": {}})


def test_bad_direction_is_rejected():
    with pytest.raises(config.ConfigError):
        config.from_dict({"layout": {"direction": "left"}})


def test_depth_that_leaves_no_side_room_is_rejected():
    with pytest.raises(config.ConfigError):
        config.from_dict({"regions": {"depth_y": 230}})


def test_odd_frame_width_is_rejected():
    with pytest.raises(config.ConfigError):
        config.from_dict({"regions": {"frame_width": 721}})


def test_example_config_has_smoothing_and_signal_sections():
    cfg = config.load(EXAMPLE)
    assert cfg.smoothing.tau_fast_s < cfg.smoothing.tau_slow_s
    assert cfg.signal.no_signal_frames >= 1


def test_smoothing_time_constants_must_be_ordered():
    with pytest.raises(config.ConfigError):
        config.from_dict({"smoothing": {"tau_fast_s": 0.5, "tau_slow_s": 0.1}})


def test_smoothing_delta_thresholds_must_be_ordered():
    with pytest.raises(config.ConfigError):
        config.from_dict({"smoothing": {"delta_low": 50, "delta_high": 10}})


def test_signal_times_must_be_positive():
    with pytest.raises(config.ConfigError):
        config.from_dict({"signal": {"fade_out_s": 0}})


def test_example_config_has_capture_and_metrics_sections():
    cfg = config.load(EXAMPLE)
    assert cfg.capture.standard == "ntsc-m" and cfg.capture.buffers >= 2
    assert cfg.metrics.interval_s > 0


def test_capture_needs_at_least_two_buffers():
    with pytest.raises(config.ConfigError):
        config.from_dict({"capture": {"buffers": 1}})


def test_example_config_has_letterbox_and_white_balance():
    cfg = config.load(EXAMPLE)
    assert cfg.letterbox.enabled and cfg.letterbox.min_bar_px >= 1
    assert tuple(cfg.color.white_balance) == (1.0, 1.0, 1.0)


def test_white_balance_needs_three_sane_gains():
    for bad in ([1.0, 1.0], [1.0, 1.0, 5.0], [0.0, 1.0, 1.0]):
        with pytest.raises(config.ConfigError):
            config.from_dict({"color": {"white_balance": bad}})


def test_letterbox_limits_are_checked():
    with pytest.raises(config.ConfigError):
        config.from_dict({"letterbox": {"max_bar_fraction": 0.6}})
