#!/usr/bin/env python3
"""Pipeline throughput benchmark: runs the whole pipeline over frames as fast as possible and reports the cost.

Usage: python tools/bench_pipeline.py [--frames-file FILE] [--synthetic N] [--config FILE] [--json OUT]
  --frames-file  raw UYVY frames recorded with tools/record_frames.sh (best: real analogue noise)
  --synthetic N  N noisy synthetic frames instead (default 600)

A result only counts for the Pi if `vcgencmd get_throttled` reads 0x0 before and after (printed here when the
command exists). The frame rate reported is the CAPACITY of the pipeline, not the capture rate (about 29.97 fps).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ambilight import config  # noqa: E402
from ambilight.capture import NTSC_FPS, FileSource, Frame  # noqa: E402
from ambilight.output import NullOutput  # noqa: E402
from ambilight.pipeline import Pipeline  # noqa: E402


class SyntheticSource:
    """Noisy frames, generated up front (a few distinct ones, cycled) so that generating them is not measured."""

    def __init__(self, n, width, height, distinct=24):
        rng = np.random.default_rng(1)
        base = rng.integers(40, 200, width * height * 2, dtype=np.uint8)
        self.pool = [(base.astype(np.int16) + rng.integers(-3, 4, base.size)).clip(0, 255).astype(np.uint8).tobytes()
                     for _ in range(distinct)]
        self.n, self.i, self.finished = n, 0, False

    def read(self, timeout):
        if self.i >= self.n:
            self.finished = True
            return None
        self.i += 1
        return Frame(self.pool[self.i % len(self.pool)], self.i / NTSC_FPS, self.i)

    def now(self):
        return self.i / NTSC_FPS

    def close(self):
        pass


def throttled():
    if not shutil.which("vcgencmd"):
        return None
    return subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames-file")
    ap.add_argument("--synthetic", type=int, default=600)
    ap.add_argument("--config", default=str(ROOT / "config" / "ambilight.example.toml"))
    ap.add_argument("--json")
    a = ap.parse_args()

    cfg = config.load(a.config)
    reg = cfg.regions
    src = FileSource(a.frames_file, reg.frame_width, reg.frame_height) if a.frames_file \
        else SyntheticSource(a.synthetic, reg.frame_width, reg.frame_height)
    pipe = Pipeline(cfg, src, NullOutput())

    before = throttled()
    cpu0, t0 = time.process_time(), time.perf_counter()
    pipe.run(threading.Event())
    wall, cpu = time.perf_counter() - t0, time.process_time() - cpu0
    after = throttled()

    snap = pipe.metrics.snapshot()
    n = snap["counters"].get("frames", 0)
    result = {
        "frames": n, "wall_s": round(wall, 3), "cpu_s": round(cpu, 3),
        "capacity_fps": round(n / wall, 1) if wall else 0,
        "cpu_ms_per_frame": round(1000 * cpu / n, 3) if n else None,
        "cpu_percent_of_one_core_at_29_97_fps": round(100 * cpu / n * NTSC_FPS, 1) if n else None,
        "stages": snap["stages"], "throttled_before": before, "throttled_after": after,
        "host": os.uname().machine,
    }
    print(json.dumps(result, indent=2))
    if a.json:
        Path(a.json).write_text(json.dumps(result, indent=2))
    if before not in (None, "throttled=0x0") or after not in (None, "throttled=0x0"):
        print("\nWARNING: the Pi reports throttling or under-voltage, these numbers are NOT valid.", file=sys.stderr)


if __name__ == "__main__":
    main()
