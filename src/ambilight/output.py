"""LED output backends. The pipeline only knows the `LedOutput` interface.

`show` receives final colours as uint8 (n, 3) in logical R, G, B order; the backend deals with the strip's
colour order. `close` must leave all LEDs off.
"""
from __future__ import annotations

import collections
import logging
from typing import Protocol

import numpy as np

log = logging.getLogger(__name__)

COLOR_ORDERS = ("RGB", "RBG", "GRB", "GBR", "BRG", "BGR")


class LedOutput(Protocol):
    def show(self, rgb: np.ndarray) -> None: ...
    def close(self) -> None: ...


class NullOutput:
    """Discards everything. For dry runs on a machine without LEDs."""

    def show(self, rgb: np.ndarray) -> None:
        pass

    def close(self) -> None:
        pass


class RecordingOutput:
    """Keeps the last frames in memory. Used by the tests and for offline replays."""

    def __init__(self, count: int, keep: int = 100_000):
        self.count = count
        self.frames: collections.deque[np.ndarray] = collections.deque(maxlen=keep)
        self.closed = False

    def show(self, rgb: np.ndarray) -> None:
        if rgb.shape != (self.count, 3) or rgb.dtype != np.uint8:
            raise ValueError(f"expected uint8 {(self.count, 3)}, got {rgb.dtype} {rgb.shape}")
        self.frames.append(rgb.copy())

    def close(self) -> None:
        self.frames.append(np.zeros((self.count, 3), dtype=np.uint8))
        self.closed = True


class Ws281xOutput:
    """WS2812B strip through the `rpi_ws281x` library (PWM on GPIO 18, see ADR-005).

    NOT verified on real LEDs yet: no LED has lit so far (docs/hardware.md). Needs root and the analogue
    audio disabled. The library is imported lazily so this module works on a machine without it.
    """

    def __init__(self, count: int, pin: int, color_order: str = "GRB", freq: int = 800_000, dma: int = 10):
        if color_order not in COLOR_ORDERS:
            raise ValueError(f"color_order must be one of {COLOR_ORDERS}")
        import rpi_ws281x as lib

        self._lib = lib
        self.count = count
        strip_type = getattr(lib, f"WS2811_STRIP_{color_order}")
        # brightness stays at 255: scaling and the current limit are done by the pipeline
        self._strip = lib.PixelStrip(count, pin, freq, dma, False, 255, 1 if pin in (13, 19) else 0, strip_type)
        self._strip.begin()
        self.closed = False

    def show(self, rgb: np.ndarray) -> None:
        color = self._lib.Color
        for i, (r, g, b) in enumerate(rgb.tolist()):
            self._strip.setPixelColor(i, color(r, g, b))
        self._strip.show()

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        try:
            self.show(np.zeros((self.count, 3), dtype=np.uint8))
        finally:
            cleanup = getattr(self._strip, "_cleanup", None)
            if cleanup:
                cleanup()
