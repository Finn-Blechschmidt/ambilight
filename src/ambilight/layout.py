"""Maps every LED to a rectangle at the picture edge.

Coordinates are pixels in the captured frame, rectangles are (x0, y0, x1, y1) with x1/y1 exclusive.
All x values are even so that a rectangle always covers whole UYVY macropixels (two pixels each).
"""
from __future__ import annotations

from .config import Config

Rect = tuple[int, int, int, int]


def _edges(start: int, stop: int, n: int, even: bool) -> list[int]:
    """n+1 integer boundaries splitting [start, stop) into n roughly equal parts."""
    out = []
    for i in range(n + 1):
        v = start + (stop - start) * i / n
        out.append(int(round(v / 2.0)) * 2 if even else int(round(v)))
    out[0], out[-1] = start, stop
    return out


def led_rects(cfg: Config) -> list[Rect]:
    """One rectangle per LED, in strip order (index 0 is the first LED after the start)."""
    lay, reg = cfg.layout, cfg.regions
    x0, x1 = reg.crop_left, reg.frame_width - reg.crop_right
    y0, y1 = reg.crop_top, reg.frame_height - reg.crop_bottom

    bx = _edges(x0, x1, lay.bottom_slots, even=True)       # bottom slots, left to right
    tx = _edges(x0, x1, lay.top, even=True)                # top slots, left to right
    ry = _edges(y0 + reg.depth_y, y1 - reg.depth_y, lay.right, even=False)
    ly = _edges(y0 + reg.depth_y, y1 - reg.depth_y, lay.left, even=False)

    bottom_y = (y1 - reg.depth_y, y1)
    top_y = (y0, y0 + reg.depth_y)
    right_x = (x1 - reg.depth_x, x1)
    left_x = (x0, x0 + reg.depth_x)

    rects: list[Rect] = []
    # bottom, from the gap towards the right: slots gap_end .. last
    first_right_slot = lay.bottom_left + lay.gap
    for k in range(lay.bottom_right):
        s = first_right_slot + k
        rects.append((bx[s], bottom_y[0], bx[s + 1], bottom_y[1]))
    # right side, upwards: last row first
    for r in range(lay.right):
        row = lay.right - 1 - r
        rects.append((right_x[0], ry[row], right_x[1], ry[row + 1]))
    # top, towards the left: last slot first
    for t in range(lay.top):
        s = lay.top - 1 - t
        rects.append((tx[s], top_y[0], tx[s + 1], top_y[1]))
    # left side, downwards
    for row in range(lay.left):
        rects.append((left_x[0], ly[row], left_x[1], ly[row + 1]))
    # bottom again, from the left corner towards the gap
    for j in range(lay.bottom_left):
        rects.append((bx[j], bottom_y[0], bx[j + 1], bottom_y[1]))

    if lay.direction == "cw":
        mirror = x0 + x1   # mirror about the centre of the usable area; keeps even x values
        rects = [(mirror - r[2], r[1], mirror - r[0], r[3]) for r in rects]
    return rects
