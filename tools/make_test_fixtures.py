#!/usr/bin/env python3
"""Builds the small luma fixtures in tests/data from real captures (needs Pillow; the tests themselves do not).

Usage: .venv/bin/python tools/make_test_fixtures.py
Inputs are in captures/ (git-ignored, produced by tools/capture_frame.sh); outputs are committed.
"""
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
# name: (source capture, downscale factor)
# The two picture fixtures come from real screen content, so they are shrunk until nothing is readable.
FIXTURES = {
    # converter test pattern with no HDMI signal (PAL mode capture, 720x576)
    "no_signal_pal.npy": ("frame_composite0_pal.png", 2),
    # real colourful picture, NTSC capture (720x480)
    "picture_ntsc_color.npy": ("frame_ntsc-m.png", 6),
    # real picture without any colour (PAL capture of a white web page, chroma exactly 0)
    "picture_bw_login.npy": ("frame_source_on.png", 6),
}

for out, (src, factor) in FIXTURES.items():
    img = Image.open(ROOT / "captures" / src).convert("L")
    img = img.resize((img.width // factor, img.height // factor), Image.BOX)
    np.save(ROOT / "tests" / "data" / out, np.asarray(img, dtype=np.uint8))
    print(out, img.size)
