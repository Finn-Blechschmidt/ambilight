#!/usr/bin/env python3
"""Draws what the pipeline would show on the LEDs for one picture (needs Pillow, a development-only dependency).

The picture is shown with the region of every LED outlined and the LED's colour as a block outside the frame, with
LED 0 and the segment starts numbered. Use it to check the layout (direction, gap, corners) and the colours
without a Pi or an LED strip.

Usage: .venv/bin/python tools/preview.py input.png [output.png] [--config FILE] [--letterbox]
  input.png      any picture; it is resized to the frame size from the config
  --letterbox    run the letterbox detector on the picture first (as the pipeline does)
"""
import argparse
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ambilight import config, extract, layout  # noqa: E402
from ambilight.letterbox import measure_crop  # noqa: E402

MARGIN = 44


def to_uyvy(img: Image.Image) -> bytes:
    """RGB picture to a UYVY frame (BT.601 limited range), chroma averaged over each pixel pair."""
    a = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    y = 16 + 65.481 * r + 128.553 * g + 24.966 * b
    u = 128 - 37.797 * r - 74.203 * g + 112.0 * b
    v = 128 + 112.0 * r - 93.786 * g - 18.214 * b
    h, w = y.shape
    out = np.empty((h, w // 2, 4), dtype=np.uint8)
    out[..., 0] = np.rint((u[:, 0::2] + u[:, 1::2]) / 2)
    out[..., 1] = np.rint(y[:, 0::2])
    out[..., 2] = np.rint((v[:, 0::2] + v[:, 1::2]) / 2)
    out[..., 3] = np.rint(y[:, 1::2])
    return out.reshape(-1).tobytes()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output", nargs="?", default=None)
    ap.add_argument("--config", default=str(ROOT / "config" / "ambilight.example.toml"))
    ap.add_argument("--letterbox", action="store_true")
    args = ap.parse_args()

    cfg = config.load(args.config)
    reg = cfg.regions
    img = Image.open(args.input).convert("RGB").resize((reg.frame_width, reg.frame_height), Image.BILINEAR)
    frame = to_uyvy(img)
    view = extract.frame_view(frame, reg.frame_width, reg.frame_height)

    if args.letterbox:
        crop = measure_crop(view, reg, cfg.letterbox)
        print("letterbox crop (left, right, top, bottom):", crop)
        cfg = replace(cfg, regions=config.with_crop(reg, *crop))
        config.validate(cfg)
    rects = layout.led_rects(cfg)
    colors = extract.region_colors(view, reg.frame_width, reg.frame_height, rects)

    canvas = Image.new("RGB", (reg.frame_width + 2 * MARGIN, reg.frame_height + 2 * MARGIN), (24, 24, 24))
    canvas.paste(img, (MARGIN, MARGIN))
    d = ImageDraw.Draw(canvas)
    lay = cfg.layout
    starts = {0: "0", lay.bottom_right: "R", lay.bottom_right + lay.right: "T",
              lay.bottom_right + lay.right + lay.top: "L", lay.count - lay.bottom_left: "B"}
    for i, ((x0, y0, x1, y1), c) in enumerate(zip(rects, colors)):
        fill = tuple(int(v) for v in c)
        d.rectangle([x0 + MARGIN, y0 + MARGIN, x1 + MARGIN - 1, y1 + MARGIN - 1], outline=(255, 255, 255))
        cx, cy = (x0 + x1) // 2 + MARGIN, (y0 + y1) // 2 + MARGIN
        near = {"bottom": y0 > reg.frame_height * 0.7, "top": y1 < reg.frame_height * 0.3}
        if near["bottom"]:
            box = [x0 + MARGIN, reg.frame_height + MARGIN + 6, x1 + MARGIN - 2, reg.frame_height + MARGIN + 30]
        elif near["top"]:
            box = [x0 + MARGIN, MARGIN - 30, x1 + MARGIN - 2, MARGIN - 6]
        elif x0 < reg.frame_width / 2:
            box = [MARGIN - 30, y0 + MARGIN, MARGIN - 6, y1 + MARGIN - 2]
        else:
            box = [reg.frame_width + MARGIN + 6, y0 + MARGIN, reg.frame_width + MARGIN + 30, y1 + MARGIN - 2]
        d.rectangle(box, fill=fill)
        if i in starts:
            d.text((cx - 3, cy - 5), starts[i], fill=(255, 255, 0))
    out = args.output or str(Path(args.input).with_name(Path(args.input).stem + "_preview.png"))
    canvas.save(out)
    print("saved", out)


if __name__ == "__main__":
    main()
