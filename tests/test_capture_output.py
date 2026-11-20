import sys
import time
import types

import numpy as np
import pytest

from ambilight import config
from ambilight.capture import FileSource, V4L2Capture
from ambilight.metrics import Metrics
from ambilight.output import RecordingOutput, Ws281xOutput

SMALL = config.Config(regions=config.Regions(frame_width=16, frame_height=8, crop_left=0, crop_right=0,
                                             crop_top=0, crop_bottom=0, depth_x=2, depth_y=1),
                      capture=config.Capture(restart_delay_s=0.05, stall_timeout_s=0.3))
FRAME_BYTES = 16 * 8 * 2

FAKE_STREAM = """
import sys, time
fb, n = int(sys.argv[1]), int(sys.argv[2])
for i in range(n):
    sys.stdout.buffer.write(bytes([i + 1]) * fb); sys.stdout.buffer.flush(); time.sleep(0.01)
"""


@pytest.fixture
def fake_stream(tmp_path):
    script = tmp_path / "fake_stream.py"
    script.write_text(FAKE_STREAM)
    return lambda n: [sys.executable, str(script), str(FRAME_BYTES), str(n)]


# --- FileSource ------------------------------------------------------------------------------------
def test_file_source_replays_frames_with_synthetic_time(tmp_path):
    path = tmp_path / "f.uyvy"
    path.write_bytes(b"".join(bytes([i]) * FRAME_BYTES for i in range(3)) + b"\x07" * 10)   # trailing junk
    src = FileSource(str(path), 16, 8, fps=10.0)
    got = [src.read(0.1) for _ in range(3)]
    assert [f.data[0] for f in got] == [0, 1, 2]
    assert [round(f.t, 3) for f in got] == [0.1, 0.2, 0.3]
    assert src.read(0.1) is None and src.finished
    src.close()


# --- V4L2Capture (with a fake v4l2-ctl) ------------------------------------------------------------
def test_v4l2_capture_delivers_frames_and_restarts_when_the_process_ends(fake_stream):
    cap = V4L2Capture(SMALL, setup_commands=[], stream_command=fake_stream(5))
    seen = set()
    deadline = time.monotonic() + 8
    while cap.restarts < 2 and time.monotonic() < deadline:
        f = cap.read(0.2)
        if f is not None:
            assert len(f.data) == FRAME_BYTES
            seen.add(f.data[0])
    cap.close()
    assert cap.restarts >= 2                       # the fake process exits after 5 frames, every time
    assert len(seen) >= 3                          # frames really arrived
    assert not cap._thread.is_alive()


def test_v4l2_capture_reports_failing_setup_and_keeps_retrying(fake_stream):
    bad = [[sys.executable, "-c", "import sys; sys.exit(3)"]]
    cap = V4L2Capture(SMALL, setup_commands=bad, stream_command=fake_stream(5))
    assert cap.read(0.4) is None
    time.sleep(0.3)
    cap.close()
    assert cap.restarts >= 1


def test_v4l2_capture_missing_command_does_not_crash():
    cap = V4L2Capture(SMALL, setup_commands=[["/nonexistent/v4l2-ctl"]], stream_command=["/nonexistent"])
    assert cap.read(0.3) is None
    cap.close()


def test_v4l2_capture_kills_a_stalled_process(tmp_path):
    script = tmp_path / "stall.py"
    script.write_text("import time; time.sleep(30)")
    cap = V4L2Capture(SMALL, setup_commands=[], stream_command=[sys.executable, str(script)])
    deadline = time.monotonic() + 8
    while cap.restarts < 1 and time.monotonic() < deadline:
        cap.read(0.1)
    cap.close()
    assert cap.restarts >= 1                        # stall_timeout_s = 0.3 killed it and it was restarted


# --- outputs ---------------------------------------------------------------------------------------
def test_recording_output_validates_and_closes_dark():
    out = RecordingOutput(4)
    out.show(np.full((4, 3), 9, dtype=np.uint8))
    with pytest.raises(ValueError):
        out.show(np.zeros((3, 3), dtype=np.uint8))
    out.close()
    assert out.closed and not out.frames[-1].any()


def test_ws281x_output_maps_the_colour_order_and_switches_off(monkeypatch):
    calls = {}

    class Strip:
        def __init__(self, *args):
            calls["args"] = args
            self.pixels = {}
            self.shown = 0
        def begin(self): calls["begin"] = True
        def setPixelColor(self, i, c): self.pixels[i] = c
        def show(self): self.shown += 1; calls["last"] = dict(self.pixels)
        def _cleanup(self): calls["cleanup"] = True

    fake = types.SimpleNamespace(PixelStrip=Strip, Color=lambda r, g, b: (r, g, b), WS2811_STRIP_GRB=0x00081000,
                                 WS2811_STRIP_RGB=0x00100800)
    monkeypatch.setitem(sys.modules, "rpi_ws281x", fake)
    out = Ws281xOutput(3, 18, "GRB")
    assert calls["args"][0] == 3 and calls["args"][1] == 18 and calls["args"][5] == 255
    assert calls["args"][7] == 0x00081000 and calls["begin"]
    out.show(np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.uint8))
    assert calls["last"] == {0: (1, 2, 3), 1: (4, 5, 6), 2: (7, 8, 9)}
    out.close()
    assert calls["last"] == {0: (0, 0, 0), 1: (0, 0, 0), 2: (0, 0, 0)} and calls["cleanup"]
    out.close()                                     # a second close must be harmless


def test_ws281x_output_rejects_unknown_colour_order():
    with pytest.raises(ValueError):
        Ws281xOutput(3, 18, "XYZ")


# --- metrics and entry point -----------------------------------------------------------------------
def test_metrics_json_is_written_atomically(tmp_path):
    m = Metrics()
    m.observe("a_ms", 1.0); m.observe("a_ms", 3.0); m.frame_done(1.0); m.frame_done(2.0); m.inc("frames", 2)
    snap = m.snapshot()
    path = tmp_path / "m.json"
    Metrics.write_json(str(path), snap)
    import json
    data = json.loads(path.read_text())
    assert data["fps"] == 1.0 and data["stages"]["a_ms"]["median_ms"] == 2.0 and data["counters"]["frames"] == 2
    assert not (tmp_path / "m.json.tmp").exists()


def test_cli_replays_a_file_with_the_null_output(tmp_path):
    from ambilight.__main__ import main
    from helpers import uyvy_frame
    f = tmp_path / "in.uyvy"
    f.write_bytes(uyvy_frame(720, 480, (200, 30, 30)) * 5)
    example = __import__("pathlib").Path(__file__).parent.parent / "config" / "ambilight.example.toml"
    assert main(["--config", str(example), "--output", "null", "--input-file", str(f)]) == 0


def test_cli_rejects_a_broken_config(tmp_path):
    from ambilight.__main__ import main
    bad = tmp_path / "bad.toml"
    bad.write_text("[layout]\ndirection = 'sideways'\n")
    assert main(["--config", str(bad), "--output", "null"]) == 2
