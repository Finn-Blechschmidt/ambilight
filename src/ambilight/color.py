"""Colour correction: gamma, brightness and the current limit that protects the supply."""
from __future__ import annotations

import numpy as np

from .config import Color, Leds


def apply_gamma_brightness(rgb: np.ndarray, cfg: Color) -> np.ndarray:
    """Gamma curve on 0..255 floats, then global brightness."""
    norm = np.clip(rgb, 0.0, 255.0) / 255.0
    return (norm ** cfg.gamma) * 255.0 * cfg.brightness


def estimated_current_ma(rgb: np.ndarray, cfg: Leds) -> float:
    """Estimated strip current: each colour channel draws ma_per_channel at 255, plus idle current per LED."""
    return float(rgb.sum() / 255.0 * cfg.ma_per_channel + len(rgb) * cfg.idle_ma_per_led)


def limit_current(rgb: np.ndarray, cfg: Leds) -> np.ndarray:
    """Scale all channels down uniformly if the estimated current exceeds the budget.

    Uniform scaling keeps the hue. The idle current cannot be reduced, so it is subtracted from the budget first.
    """
    idle = len(rgb) * cfg.idle_ma_per_led
    drive = estimated_current_ma(rgb, cfg) - idle
    budget = cfg.max_current_ma - idle
    if budget <= 0:
        return np.zeros_like(rgb)
    if drive <= budget:
        return rgb
    return rgb * (budget / drive)


def to_bytes(rgb: np.ndarray, floor: bool = False) -> np.ndarray:
    """8-bit values, shape (n, 3) uint8. Rounds to nearest, or rounds down with `floor`.

    Anything that goes through `limit_current` must be floored: rounding up can add up to half a step on each of
    the 327 channels, enough to push the strip over its current budget.
    """
    clipped = np.clip(rgb, 0.0, 255.0)
    return (np.floor(clipped) if floor else np.rint(clipped)).astype(np.uint8)
