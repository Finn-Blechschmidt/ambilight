"""Metrics: frame rate, per-stage time and CPU load, readable from the log or a JSON file without a debugger."""
from __future__ import annotations

import collections
import json
import os
import time
from pathlib import Path

import numpy as np


class Metrics:
    def __init__(self, window: int = 300):
        self._stages: dict[str, collections.deque] = collections.defaultdict(lambda: collections.deque(maxlen=window))
        self._frame_times: collections.deque = collections.deque(maxlen=window)
        self.counters: collections.Counter = collections.Counter()
        self._cpu_t = time.process_time()
        self._wall_t = time.monotonic()

    def observe(self, stage: str, ms: float) -> None:
        self._stages[stage].append(ms)

    def frame_done(self, t: float) -> None:
        self._frame_times.append(t)

    def inc(self, name: str, n: int = 1) -> None:
        self.counters[name] += n

    def snapshot(self) -> dict:
        ft = self._frame_times
        fps = (len(ft) - 1) / (ft[-1] - ft[0]) if len(ft) > 1 and ft[-1] > ft[0] else 0.0
        stages = {}
        for name, vals in self._stages.items():
            a = np.fromiter(vals, dtype=np.float64)
            stages[name] = {"median_ms": round(float(np.median(a)), 3), "p99_ms": round(float(np.percentile(a, 99)), 3)}
        cpu, wall = time.process_time(), time.monotonic()
        cpu_pct = 100.0 * (cpu - self._cpu_t) / (wall - self._wall_t) if wall > self._wall_t else 0.0
        self._cpu_t, self._wall_t = cpu, wall
        return {"fps": round(fps, 2), "stages": stages, "process_cpu_percent_of_one_core": round(cpu_pct, 1),
                "counters": dict(self.counters)}

    @staticmethod
    def write_json(path: str, snap: dict) -> None:
        tmp = Path(path + ".tmp")
        tmp.write_text(json.dumps(snap, indent=2))
        os.replace(tmp, path)                      # readers never see a half-written file
