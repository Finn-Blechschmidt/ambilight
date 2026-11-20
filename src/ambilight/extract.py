"""Colour extraction: one RGB colour per LED rectangle from a raw UYVY frame."""
from __future__ import annotations

import numpy as np

from .layout import Rect


def frame_view(frame: bytes | np.ndarray, width: int, height: int) -> np.ndarray:
    """View a UYVY frame as (height, width/2, 4): bytes [U, Y0, V, Y1] per macropixel. No copy."""
    arr = np.frombuffer(frame, dtype=np.uint8) if isinstance(frame, (bytes, bytearray, memoryview)) else frame
    if arr.size != width * height * 2:
        raise ValueError(f"frame has {arr.size} bytes, expected {width * height * 2}")
    return arr.reshape(height, width // 2, 4)


def yuv_to_rgb(y: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """ITU-R BT.601, limited range (matches what the STK1160 delivers). Returns floats 0..255, shape (..., 3)."""
    c = 1.164 * (y.astype(np.float32) - 16.0)
    d = u.astype(np.float32) - 128.0
    e = v.astype(np.float32) - 128.0
    rgb = np.stack((c + 1.596 * e, c - 0.392 * d - 0.813 * e, c + 2.017 * d), axis=-1)
    return np.clip(rgb, 0.0, 255.0)


def region_means(view: np.ndarray, rects: list[Rect], row_step: int = 1) -> np.ndarray:
    """Mean Y, U, V per rectangle, shape (n, 3). `row_step` > 1 skips rows (cheap vertical subsampling).

    Averaging in YUV and converting afterwards equals converting every pixel first, because the conversion
    is affine; only the final clipping differs, and it is applied to the mean.
    """
    out = np.empty((len(rects), 3), dtype=np.float32)
    for i, (x0, y0, x1, y1) in enumerate(rects):
        block = view[y0:y1:row_step, x0 // 2:x1 // 2]
        out[i, 0] = block[..., (1, 3)].mean(dtype=np.float32)
        out[i, 1] = block[..., 0].mean(dtype=np.float32)
        out[i, 2] = block[..., 2].mean(dtype=np.float32)
    return out


def region_colors(frame: bytes | np.ndarray, width: int, height: int, rects: list[Rect],
                  row_step: int = 1) -> np.ndarray:
    """RGB colour (floats 0..255, shape (n, 3)) for every rectangle."""
    yuv = region_means(frame_view(frame, width, height), rects, row_step)
    return yuv_to_rgb(yuv[:, 0], yuv[:, 1], yuv[:, 2])
