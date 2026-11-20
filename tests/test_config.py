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
