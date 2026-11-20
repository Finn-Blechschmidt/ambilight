"""Temporal smoothing: no flicker without feeling sluggish, scene cuts pass immediately.

Per LED an exponential moving average with two time constants. An LED switches to the fast constant
(`tau_fast_s`) when its colour differs from the target by more than `delta_high`, and stays fast until it is within
`delta_low` of the target; otherwise it uses the slow constant (`tau_slow_s`), which hides analogue noise. The
hysteresis avoids a slow tail at the end of a big change. If the mean change over all LEDs is above
`cut_threshold` the state jumps to the new colours at once. The blend factor is derived from the real frame
interval, so the behaviour does not depend on the frame rate.
"""
from __future__ import annotations

import numpy as np

from .config import Smoothing


class Smoother:
    def __init__(self, cfg: Smoothing):
        self.cfg = cfg
        self.state: np.ndarray | None = None
        self.fast: np.ndarray | None = None       # per LED: currently tracking a real change

    def reset(self) -> None:
        self.state = None
        self.fast = None

    def step(self, rgb: np.ndarray, dt: float) -> np.ndarray:
        """Feed one frame of colours (n, 3), `dt` seconds since the previous frame. Returns the smoothed colours."""
        cfg = self.cfg
        rgb = np.asarray(rgb, dtype=np.float32)
        if self.state is None or self.state.shape != rgb.shape:
            self.state = rgb.copy()
            self.fast = np.zeros(len(rgb), dtype=bool)
            return self.state.copy()

        delta = np.abs(rgb - self.state).max(axis=1)                  # per LED, worst channel
        if float(delta.mean()) > cfg.cut_threshold:
            self.state = rgb.copy()
            self.fast[:] = False
            return self.state.copy()

        self.fast = (self.fast | (delta >= cfg.delta_high)) & (delta >= cfg.delta_low)
        tau = np.where(self.fast, cfg.tau_fast_s, cfg.tau_slow_s)      # (n,)
        alpha = 1.0 - np.exp(-max(dt, 0.0) / tau)
        self.state = self.state + (rgb - self.state) * alpha[:, None].astype(np.float32)
        return self.state.copy()
