"""The pipeline: capture -> regions -> colour correction -> smoothing -> signal gain -> current limit -> LEDs.

Order of the last steps: the signal gain (fade in/out) and the current limiter come after smoothing, so the limiter
sees exactly what is sent to the strip and the budget always holds.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable

import numpy as np

from . import color, extract, layout
from .capture import Frame, FrameSource
from .config import Config
from .metrics import Metrics
from .monitor import SignalMonitor, State
from .output import LedOutput
from .smoothing import Smoother

log = logging.getLogger(__name__)

IDLE_POLL_S = 0.05   # how long to wait for a frame before treating the source as idle


class Pipeline:
    def __init__(self, cfg: Config, source: FrameSource, output: LedOutput, metrics: Metrics | None = None):
        self.cfg = cfg
        self.source = source
        self.output = output
        self.metrics = metrics or Metrics()
        self.rects = layout.led_rects(cfg)
        self.smoother = Smoother(cfg.smoothing)
        self.monitor = SignalMonitor(cfg.signal, cfg.regions)
        self._last_t: float | None = None
        self._smoothed: np.ndarray | None = None
        self._last_log = time.monotonic()

    # -- one frame -------------------------------------------------------------------------------
    def handle_frame(self, frame: Frame) -> None:
        reg, m = self.cfg.regions, self.metrics
        t0 = time.perf_counter()
        try:
            view = extract.frame_view(frame.data, reg.frame_width, reg.frame_height)
        except ValueError as exc:
            log.error("dropping frame: %s", exc)
            m.inc("bad_frames")
            return
        rgb = extract.region_colors(view, reg.frame_width, reg.frame_height, self.rects)
        t1 = time.perf_counter()
        rgb = color.apply_gamma_brightness(rgb, self.cfg.color)
        dt = 0.0 if self._last_t is None else frame.t - self._last_t
        self._last_t = frame.t
        smoothed = self.smoother.step(rgb, dt)
        t2 = time.perf_counter()
        state, gain = self.monitor.update(view, frame.t)
        if state is not State.OK:
            self.smoother.reset()         # after the signal returns, start from the new picture, not the pattern
        t3 = time.perf_counter()
        self._smoothed = smoothed
        self._emit(smoothed, gain)
        t4 = time.perf_counter()

        m.observe("extract_ms", (t1 - t0) * 1000)
        m.observe("correct_smooth_ms", (t2 - t1) * 1000)
        m.observe("monitor_ms", (t3 - t2) * 1000)
        m.observe("limit_output_ms", (t4 - t3) * 1000)
        m.observe("total_ms", (t4 - t0) * 1000)
        m.frame_done(frame.t)
        m.inc("frames")

    def handle_idle(self) -> None:
        """No new frame: keep fading (signal lost) and keep the LEDs updated."""
        state, gain = self.monitor.tick(self.source.now())
        if self._smoothed is not None:
            self._emit(self._smoothed, gain)

    def _emit(self, smoothed: np.ndarray, gain: float) -> None:
        limited = color.limit_current(smoothed * gain, self.cfg.leds)
        self.output.show(color.to_bytes(limited, floor=True))   # floor: the budget must hold after rounding

    # -- loop ------------------------------------------------------------------------------------
    def run(self, stop: threading.Event) -> None:
        """Run until `stop` is set or the source is finished. Always leaves the LEDs off."""
        self.output.show(np.zeros((self.cfg.layout.count, 3), dtype=np.uint8))
        try:
            while not stop.is_set() and not self.source.finished:
                frame = self.source.read(IDLE_POLL_S)
                if frame is not None:
                    self.handle_frame(frame)
                elif not self.source.finished:
                    self.handle_idle()
                self._maybe_report()
        finally:
            self.output.close()
            self.source.close()

    def _maybe_report(self) -> None:
        now = time.monotonic()
        if now - self._last_log < self.cfg.metrics.interval_s:
            return
        self._last_log = now
        snap = self.metrics.snapshot()
        snap["state"] = self.monitor.state.value
        snap["gain"] = round(self.monitor.gain, 3)
        for attr in ("restarts", "dropped"):
            if hasattr(self.source, attr):
                snap["counters"][f"capture_{attr}"] = getattr(self.source, attr)
        log.info("metrics: %s", snap)
        if self.cfg.metrics.json_path:
            Metrics.write_json(self.cfg.metrics.json_path, snap)
