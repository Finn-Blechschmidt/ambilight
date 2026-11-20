import threading

import numpy as np

from ambilight import color, config, layout
from ambilight.capture import Frame, NTSC_FPS
from ambilight.output import RecordingOutput
from ambilight.pipeline import Pipeline
from helpers import bars_frame, uyvy_frame

W, H = 720, 480
DT = 1 / NTSC_FPS
RED, BLUE, WHITE = (230, 20, 20), (20, 20, 230), (255, 255, 255)


class ListSource:
    """Hands out a fixed list of frames, then reports finished. `None` entries simulate a read timeout."""

    def __init__(self, items):
        self.items = list(items)
        self.finished = False
        self.closed = False
        self._now = 0.0

    def read(self, timeout):
        if not self.items:
            self.finished = True
            return None
        item = self.items.pop(0)
        if item is None:
            self._now += 0.05
            return None
        self._now = item.t
        return item

    def now(self):
        return self._now

    def close(self):
        self.closed = True


def frames(data, n, start=0):
    return [Frame(data, (start + i + 1) * DT, start + i + 1) for i in range(n)]


def run(items, cfg=None):
    cfg = cfg or config.Config()
    out = RecordingOutput(cfg.layout.count)
    src = ListSource(items)
    pipe = Pipeline(cfg, src, out)
    pipe.run(threading.Event())
    return cfg, pipe, out, src


def test_left_red_right_blue_reaches_the_right_leds():
    cfg, _, out, _ = run(frames(uyvy_frame(W, H, RED, BLUE), 40))
    rects = layout.led_rects(cfg)
    last = out.frames[-2]                                     # the final entry is the all-off frame from close()
    for rect, rgb in zip(rects, last):
        if rect[0] < W // 2 < rect[2]:
            continue                                          # middle top LED sees both halves
        left = rect[2] <= W // 2
        r, _, b = (int(x) for x in rgb)
        assert (r > 4 * b) if left else (b > 4 * r)


def test_output_is_always_valid_and_within_the_current_budget():
    cfg, _, out, _ = run(frames(uyvy_frame(W, H, WHITE), 60))
    assert len(out.frames) >= 60
    worst = 0.0
    for f in out.frames:
        assert f.dtype == np.uint8 and f.shape == (109, 3)
        worst = max(worst, color.estimated_current_ma(f.astype(np.float32), cfg.leds))
    assert worst <= cfg.leds.max_current_ma + 1.0
    assert worst > 0.7 * cfg.leds.max_current_ma             # white really hit the limiter


def test_starts_dark_and_ends_dark_and_closes_everything():
    _, _, out, src = run(frames(uyvy_frame(W, H, RED), 20))
    assert not out.frames[0].any()
    assert not out.frames[-1].any()
    assert out.closed and src.closed


def test_stop_event_ends_the_loop_and_switches_off():
    cfg = config.Config()
    out = RecordingOutput(109)
    stop = threading.Event()
    stop.set()
    Pipeline(cfg, ListSource(frames(uyvy_frame(W, H, RED), 5)), out).run(stop)
    assert out.closed and not out.frames[-1].any()


def test_converter_pattern_fades_the_leds_out_and_back():
    good, pat = uyvy_frame(W, H, RED, BLUE), bars_frame(W, H)
    items = frames(good, 30) + frames(pat, 60, start=30) + frames(good, 40, start=90)
    cfg, pipe, out, _ = run(items)
    brightness = [int(f.max()) for f in out.frames]
    peak_before = max(brightness[:30])
    assert peak_before > 150
    dark = brightness[60:90]
    assert min(dark) == 0 and dark[-1] == 0                   # faded out completely during the pattern
    assert brightness[-3] > 0.8 * peak_before                  # and back after the picture returned


def test_lost_signal_fades_out_without_new_frames():
    good = uyvy_frame(W, H, RED)
    items = frames(good, 30) + [None] * 80                    # 80 timeouts of 50 ms = 4 s without frames
    _, pipe, out, _ = run(items)
    brightness = [int(f.max()) for f in out.frames]
    assert max(brightness) > 150
    assert brightness[-2] == 0
    assert pipe.monitor.state.value == "lost"


def test_wrong_sized_frame_is_counted_and_survived():
    good = uyvy_frame(W, H, RED)
    items = frames(good, 5) + [Frame(b"\x00" * 100, 6 * DT, 6)] + frames(good, 5, start=6)
    _, pipe, out, _ = run(items)
    assert pipe.metrics.counters["bad_frames"] == 1
    assert pipe.metrics.counters["frames"] == 10


def test_metrics_snapshot_has_fps_and_stage_times():
    _, pipe, _, _ = run(frames(uyvy_frame(W, H, RED), 40))
    snap = pipe.metrics.snapshot()
    assert 29 < snap["fps"] < 31
    assert {"extract_ms", "total_ms"} <= set(snap["stages"])
    assert snap["counters"]["frames"] == 40
