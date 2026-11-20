"""Test helpers: build synthetic UYVY frames."""
import numpy as np


def rgb_to_yuv(r, g, b):
    """BT.601 limited range, inputs 0..255."""
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    y = 16 + 65.481 * r + 128.553 * g + 24.966 * b
    u = 128 - 37.797 * r - 74.203 * g + 112.0 * b
    v = 128 + 112.0 * r - 93.786 * g - 18.214 * b
    return y, u, v


def make_frame(width, height, color_at):
    """UYVY frame; color_at(x, y) -> (r, g, b) evaluated per macropixel (left pixel of each pair)."""
    view = np.empty((height, width // 2, 4), dtype=np.uint8)
    for yy in range(height):
        for mx in range(width // 2):
            y, u, v = rgb_to_yuv(*color_at(mx * 2, yy))
            view[yy, mx] = (round(u), round(y), round(v), round(y))
    return view.reshape(-1).tobytes()


def uyvy_frame(width, height, left_rgb, right_rgb=None, luma_override=None):
    """Fast UYVY frame: left half one colour, right half another (default the same). Returns bytes."""
    right_rgb = right_rgb or left_rgb
    view = np.empty((height, width // 2, 4), dtype=np.uint8)
    for sl, rgb in ((slice(0, width // 4), left_rgb), (slice(width // 4, width // 2), right_rgb)):
        y, u, v = rgb_to_yuv(*rgb)
        view[:, sl] = (round(u), round(y), round(v), round(y))
    return view.reshape(-1).tobytes()


def bars_frame(width, height):
    """The converter's 8-bar grey pattern as a UYVY frame (bytes)."""
    levels = np.array([235, 215, 175, 145, 110, 80, 50, 25], dtype=np.uint8)
    luma = np.tile(levels[np.minimum(np.arange(width) * 8 // width, 7)], (height, 1))
    view = np.empty((height, width // 2, 4), dtype=np.uint8)
    view[..., 0], view[..., 2] = 128, 128
    view[..., 1], view[..., 3] = luma[:, 0::2], luma[:, 1::2]
    return view.reshape(-1).tobytes()
