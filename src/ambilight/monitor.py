"""Signal monitoring: fade the LEDs out instead of showing garbage when the picture is not real.

Three situations are detected:
  NO_SIGNAL  the HDMI-to-AV converter shows its own test pattern (grey bars with the text "NO SIGNAL")
  FROZEN     the capture delivers byte-identical frames in a row (stalled grabber or driver)
  LOST       no frame arrived for a while (call `tick` when a read produced nothing)

A paused video is NOT frozen: analogue noise makes consecutive frames differ, so only an exact repeat counts.
The monitor outputs a gain between 0 and 1 that the pipeline multiplies onto the colours. Time is passed in,
so the behaviour is testable without sleeping.
"""
from __future__ import annotations

import enum

import numpy as np

from .config import Regions, Signal

MAX_CHROMA_DEV = 2.0   # the converter's pattern is grey; anything with colour is a real picture
# Flatness of a bar (std of its middle half). Measured on the real pattern: at most 0.6. A smooth ramp gives 3.9.
# Checked on a PAL capture only; the NTSC pattern and live analogue noise still have to be measured.
MAX_BAR_STD = 1.5


class State(enum.Enum):
    OK = "ok"
    NO_SIGNAL = "no_signal"
    FROZEN = "frozen"
    LOST = "lost"


def is_no_signal_pattern(luma: np.ndarray, chroma_dev: float = 0.0, bars: int = 8) -> bool:
    """True if the luma plane looks like the converter's pattern: `bars` flat vertical grey bars whose
    brightness steps down (or up) monotonically from left to right, in a grey (colourless) picture.

    A black-and-white film frame is also colourless but does not have flat monotone vertical bars, so it passes.
    """
    if chroma_dev > MAX_CHROMA_DEV or luma.ndim != 2 or luma.shape[1] < bars * 4:
        return False
    plane = luma.astype(np.float32)
    col = np.median(plane, axis=0)                                  # robust against the text block
    if (np.abs(plane - col[None, :]) <= 12.0).mean() < 0.90:       # rows must agree with the column profile
        return False
    seg = plane.shape[1] // bars
    means = []
    for i in range(bars):
        part = col[i * seg + seg // 4:(i + 1) * seg - seg // 4]     # middle half of each bar, avoids the edges
        if part.std() > MAX_BAR_STD:                                # bars are flat, a ramp is not
            return False
        means.append(float(part.mean()))
    steps = np.diff(means)
    return bool((steps <= -10.0).all() or (steps >= 10.0).all())


class SignalMonitor:
    def __init__(self, cfg: Signal, regions: Regions):
        self.cfg = cfg
        self.regions = regions
        self.state = State.LOST          # LEDs stay dark until the first valid frame
        self.gain = 0.0
        self._last_frame_t: float | None = None
        self._last_t: float | None = None
        self._pattern_run = 0
        self._frozen_run = 0
        self._prev_sig: np.ndarray | None = None

    # -- frame analysis ------------------------------------------------------------------------------
    def _analyse(self, view: np.ndarray) -> tuple[bool, bool]:
        """Returns (pattern, identical_to_previous) for a (H, W/2, 4) UYVY view."""
        r = self.regions
        sub = view[r.crop_top:r.frame_height - r.crop_bottom:4, r.crop_left // 2:(r.frame_width - r.crop_right) // 2]
        luma = sub[..., (1, 3)].reshape(sub.shape[0], -1)
        chroma_dev = float(max(np.abs(sub[..., 0].astype(np.float32) - 128.0).mean(),
                               np.abs(sub[..., 2].astype(np.float32) - 128.0).mean()))
        pattern = is_no_signal_pattern(luma, chroma_dev)

        sig = view[::8, ::4].copy()
        identical = self._prev_sig is not None and np.array_equal(sig, self._prev_sig)
        self._prev_sig = sig
        return pattern, identical

    # -- public API ----------------------------------------------------------------------------------
    def update(self, view: np.ndarray, now: float) -> tuple[State, float]:
        """Analyse one captured frame taken at time `now` (seconds). Returns (state, gain)."""
        pattern, identical = self._analyse(view)
        self._pattern_run = self._pattern_run + 1 if pattern else 0
        self._frozen_run = self._frozen_run + 1 if identical else 0
        self._last_frame_t = now

        if self._pattern_run >= self.cfg.no_signal_frames:
            self.state = State.NO_SIGNAL
        elif self._frozen_run >= self.cfg.frozen_frames:
            self.state = State.FROZEN
        else:
            self.state = State.OK
        return self.state, self._fade(now)

    def tick(self, now: float) -> tuple[State, float]:
        """Call when a capture attempt delivered no frame. Marks the signal lost after `lost_timeout_s`."""
        if self._last_frame_t is not None and now - self._last_frame_t >= self.cfg.lost_timeout_s:
            self.state = State.LOST
        return self.state, self._fade(now)

    def _fade(self, now: float) -> float:
        dt = 0.0 if self._last_t is None else max(now - self._last_t, 0.0)
        self._last_t = now
        target = 1.0 if self.state is State.OK else 0.0
        if target > self.gain:
            self.gain = min(target, self.gain + dt / self.cfg.fade_in_s)
        else:
            self.gain = max(target, self.gain - dt / self.cfg.fade_out_s)
        return self.gain
