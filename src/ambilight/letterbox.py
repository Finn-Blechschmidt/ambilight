"""Letterbox / pillarbox detection: find black bars around the picture so the LEDs follow the real image.

A bar is a run of rows (or columns) at the frame edge that is dark AND nearly constant. A dark picture is not a
bar: its rows vary, and a frame in which nothing inside is brighter than `content_min` is treated as "no bars"
instead of cropping everything away. The crop only changes after the same measurement was seen for `stable_frames`
frames in a row, so a dark scene or a fade does not make the LED regions jump around.

Crops are absolute pixels from the frame edge (the configured base crop is the minimum). Left/right values are
kept even because UYVY macropixels are two pixels wide.
"""
from __future__ import annotations

import numpy as np

from .config import Letterbox, Regions

EDGE_MARGIN_PX = 4   # step into the picture a little: chroma bleeds over the bar edge


def _leading(flags: np.ndarray) -> int:
    """Number of consecutive True values from the start."""
    if flags.all():
        return len(flags)
    return int(np.argmin(flags))


def measure_crop(view: np.ndarray, regions: Regions, cfg: Letterbox) -> tuple[int, int, int, int]:
    """Crop (left, right, top, bottom) in pixels for one frame. Falls back to the base crop when there is no bar."""
    h, mw = view.shape[0], view.shape[1]
    w = mw * 2
    base = (regions.crop_left, regions.crop_right, regions.crop_top, regions.crop_bottom)
    luma = view[:, :, 1]                                   # one luma sample per macropixel: enough for bars

    c0, c1 = int(mw * 0.1), int(mw * 0.9)
    band = luma[:, c0:c1].astype(np.float32)
    row_dark = (band.mean(axis=1) < cfg.dark_threshold) & (band.std(axis=1) < cfg.uniform_std)
    top_run, bottom_run = _leading(row_dark), _leading(row_dark[::-1])
    top = top_run + EDGE_MARGIN_PX if top_run - regions.crop_top >= cfg.min_bar_px else regions.crop_top
    bottom = bottom_run + EDGE_MARGIN_PX if bottom_run - regions.crop_bottom >= cfg.min_bar_px else regions.crop_bottom
    top, bottom = max(top, regions.crop_top), max(bottom, regions.crop_bottom)
    if max(top, bottom) > cfg.max_bar_fraction * h or top + bottom >= h:
        return base                                        # implausible: most likely an all-dark frame

    r0, r1 = top + 1, h - bottom - 1
    if r1 - r0 < 8:
        return base
    inner = luma[r0:r1].astype(np.float32)
    if float(inner.mean(axis=1).max()) < cfg.content_min:
        return base                                        # nothing bright inside: a dark scene, not a bar

    col_dark = (inner.mean(axis=0) < cfg.dark_threshold) & (inner.std(axis=0) < cfg.uniform_std)
    left_run, right_run = _leading(col_dark) * 2, _leading(col_dark[::-1]) * 2
    left = left_run + EDGE_MARGIN_PX if left_run - regions.crop_left >= cfg.min_bar_px else regions.crop_left
    right = right_run + EDGE_MARGIN_PX if right_run - regions.crop_right >= cfg.min_bar_px else regions.crop_right
    left, right = max(left, regions.crop_left), max(right, regions.crop_right)
    if max(left, right) > cfg.max_bar_fraction * w or left + right >= w:
        left, right = regions.crop_left, regions.crop_right
    left, right = (left + 1) // 2 * 2, (right + 1) // 2 * 2    # even, so rectangles stay on macropixels
    return (left, right, top, bottom)


class LetterboxDetector:
    """Stabilises `measure_crop` over time. `update` returns (crop, changed)."""

    def __init__(self, cfg: Letterbox, regions: Regions):
        self.cfg = cfg
        self.regions = regions
        self.crop = (regions.crop_left, regions.crop_right, regions.crop_top, regions.crop_bottom)
        self._cand: tuple[int, int, int, int] | None = None
        self._count = 0

    def _same(self, a, b) -> bool:
        return all(abs(x - y) <= self.cfg.tolerance_px for x, y in zip(a, b))

    def update(self, view: np.ndarray) -> tuple[tuple[int, int, int, int], bool]:
        m = measure_crop(view, self.regions, self.cfg)
        if self._cand is not None and self._same(m, self._cand):
            self._count += 1
        else:
            self._cand, self._count = m, 1
        if self._count >= self.cfg.stable_frames and not self._same(self._cand, self.crop):
            self.crop = self._cand
            return self.crop, True
        return self.crop, False
