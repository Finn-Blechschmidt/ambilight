"""Configuration: one TOML file, validated, no magic numbers in the pipeline code."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Layout:
    """LED counts per strip segment, in the order the strip runs from its start.

    The strip starts at the bottom centre right next to a gap of `gap` LEDs and first runs along the
    bottom towards the right (`bottom_right`), then up the right side, along the top towards the left,
    down the left side and back along the bottom to the gap (`bottom_left`).
    """
    bottom_right: int = 17
    right: int = 20
    top: int = 35
    left: int = 20
    bottom_left: int = 17
    gap: int = 1
    # "ccw": the strip runs bottom -> right -> top -> left as seen from the front of the TV.
    # "cw": mirrored. Unverified on the real strip (M2), so it is configurable.
    direction: str = "ccw"

    @property
    def count(self) -> int:
        return self.bottom_right + self.right + self.top + self.left + self.bottom_left

    @property
    def bottom_slots(self) -> int:
        return self.bottom_left + self.gap + self.bottom_right


@dataclass(frozen=True)
class Regions:
    frame_width: int = 720
    frame_height: int = 480
    # Border that is ignored (overscan / blanking), pixels.
    crop_left: int = 8
    crop_right: int = 8
    crop_top: int = 8
    crop_bottom: int = 8
    # How deep a region reaches into the picture, pixels.
    depth_x: int = 64
    depth_y: int = 48


@dataclass(frozen=True)
class Leds:
    gpio_pin: int = 18
    color_order: str = "GRB"   # unverified, see M2
    # Current budget for the whole strip in milliamperes, enforced in software.
    max_current_ma: float = 2000.0
    ma_per_channel: float = 20.0
    idle_ma_per_led: float = 1.0


@dataclass(frozen=True)
class Color:
    gamma: float = 2.2
    brightness: float = 1.0   # 0..1


@dataclass(frozen=True)
class Smoothing:
    """Adaptive exponential smoothing per LED. Time constants are in seconds, differences in 0..255 steps."""
    tau_slow_s: float = 0.30     # small changes (noise, flicker) are smoothed with this time constant
    tau_fast_s: float = 0.04     # large changes pass with this one
    delta_low: float = 6.0       # change below this is treated as noise
    delta_high: float = 40.0     # change above this is treated as a real change
    cut_threshold: float = 70.0  # mean change over all LEDs above this is a scene cut: jump immediately


@dataclass(frozen=True)
class Signal:
    """Signal monitoring: when to switch the LEDs off and how fast to fade."""
    no_signal_frames: int = 10     # frames showing the converter's test pattern before LEDs fade out
    frozen_frames: int = 60        # byte-identical frames in a row (a stalled capture) before LEDs fade out
    lost_timeout_s: float = 1.0    # no frame at all for this long
    fade_out_s: float = 0.5
    fade_in_s: float = 0.3


@dataclass(frozen=True)
class Capture:
    """How frames are read from the grabber (V4L2). The frame size comes from [regions]."""
    device: str = "/dev/video0"
    input: int = 0
    standard: str = "ntsc-m"        # ADR-004: the converter and the grabber must both be on NTSC
    buffers: int = 4
    restart_delay_s: float = 1.0    # pause before the capture process is restarted after it ended
    stall_timeout_s: float = 3.0    # no frame for this long: kill the capture process so it gets restarted


@dataclass(frozen=True)
class Metrics:
    interval_s: float = 10.0        # how often a summary is logged
    json_path: str = ""             # if set, the latest summary is also written there as JSON


@dataclass(frozen=True)
class Config:
    layout: Layout = field(default_factory=Layout)
    regions: Regions = field(default_factory=Regions)
    leds: Leds = field(default_factory=Leds)
    color: Color = field(default_factory=Color)
    smoothing: Smoothing = field(default_factory=Smoothing)
    signal: Signal = field(default_factory=Signal)
    capture: Capture = field(default_factory=Capture)
    metrics: Metrics = field(default_factory=Metrics)


def _section(cls, data: dict, name: str):
    known = set(cls.__dataclass_fields__)
    unknown = set(data) - known
    if unknown:
        raise ConfigError(f"[{name}] unknown keys: {sorted(unknown)}")
    return cls(**data)


def from_dict(data: dict) -> Config:
    unknown = set(data) - {"layout", "regions", "leds", "color", "smoothing", "signal", "capture", "metrics"}
    if unknown:
        raise ConfigError(f"unknown sections: {sorted(unknown)}")
    cfg = Config(
        layout=_section(Layout, data.get("layout", {}), "layout"),
        regions=_section(Regions, data.get("regions", {}), "regions"),
        leds=_section(Leds, data.get("leds", {}), "leds"),
        color=_section(Color, data.get("color", {}), "color"),
        smoothing=_section(Smoothing, data.get("smoothing", {}), "smoothing"),
        signal=_section(Signal, data.get("signal", {}), "signal"),
        capture=_section(Capture, data.get("capture", {}), "capture"),
        metrics=_section(Metrics, data.get("metrics", {}), "metrics"),
    )
    validate(cfg)
    return cfg


def load(path: str | Path) -> Config:
    with open(path, "rb") as f:
        return from_dict(tomllib.load(f))


def validate(cfg: Config) -> None:
    lay, reg = cfg.layout, cfg.regions
    if lay.direction not in ("ccw", "cw"):
        raise ConfigError("layout.direction must be 'ccw' or 'cw'")
    if min(lay.bottom_right, lay.right, lay.top, lay.left, lay.bottom_left) < 1 or lay.gap < 0:
        raise ConfigError("layout: every segment needs at least one LED")
    if reg.frame_width % 2:
        raise ConfigError("regions.frame_width must be even (UYVY macropixels)")
    usable_w = reg.frame_width - reg.crop_left - reg.crop_right
    usable_h = reg.frame_height - reg.crop_top - reg.crop_bottom
    if min(reg.crop_left, reg.crop_right, reg.crop_top, reg.crop_bottom) < 0:
        raise ConfigError("regions: crop values must not be negative")
    if usable_h - 2 * reg.depth_y < lay.left or usable_h - 2 * reg.depth_y < lay.right:
        raise ConfigError("regions: depth_y too large, side regions would have no height")
    if usable_w < lay.top or reg.depth_x < 2 or reg.depth_y < 1:
        raise ConfigError("regions: band depth or crop leaves no room")
    if not 0.0 < cfg.color.gamma <= 4.0:
        raise ConfigError("color.gamma must be in (0, 4]")
    if not 0.0 <= cfg.color.brightness <= 1.0:
        raise ConfigError("color.brightness must be in [0, 1]")
    if cfg.leds.max_current_ma <= 0:
        raise ConfigError("leds.max_current_ma must be positive")
    sm = cfg.smoothing
    if not 0.0 < sm.tau_fast_s <= sm.tau_slow_s:
        raise ConfigError("smoothing: need 0 < tau_fast_s <= tau_slow_s")
    if not 0.0 <= sm.delta_low < sm.delta_high:
        raise ConfigError("smoothing: need 0 <= delta_low < delta_high")
    if sm.cut_threshold <= 0:
        raise ConfigError("smoothing.cut_threshold must be positive")
    sg = cfg.signal
    if min(sg.no_signal_frames, sg.frozen_frames) < 1:
        raise ConfigError("signal: frame counts must be at least 1")
    if min(sg.lost_timeout_s, sg.fade_out_s, sg.fade_in_s) <= 0:
        raise ConfigError("signal: times must be positive")
    cp = cfg.capture
    if cp.buffers < 2 or cp.restart_delay_s <= 0 or cp.stall_timeout_s <= 0:
        raise ConfigError("capture: need buffers >= 2 and positive restart_delay_s / stall_timeout_s")
    if cfg.metrics.interval_s <= 0:
        raise ConfigError("metrics.interval_s must be positive")
