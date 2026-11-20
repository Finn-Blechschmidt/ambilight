# Verification matrix

What is proven, how, and what is still open. "Unit-tested" means automated tests on a Mac with synthetic data, fakes or
small fixtures built from real captures. It says nothing about the real hardware.

Legend: **Verified** = measured or observed on the real hardware. **Unit-tested** = automated test, no hardware.
**Open** = nothing yet. The ordered plan for closing the open items is [pi-session.md](pi-session.md).

| Area | Claim | State | Evidence |
|---|---|---|---|
| Deploy | One command syncs the project to the Pi | Verified | `deploy/deploy.sh`, 1.7 s |
| Capture | The grabber delivers colour NTSC frames, 720x480 UYVY, about 29 fps | Verified (old Pi) | [ADR-004](decisions.md), frame matched the TV |
| Capture | The converter shows a grey "NO SIGNAL" bar pattern when there is no HDMI signal | Verified in PAL only | [ADR-002](decisions.md); NTSC pattern not captured |
| Capture | `v4l2-ctl --stream-to=-` delivers raw frames on stdout | Open | the reader is unit-tested with a fake process only ([ADR-010](decisions.md)) |
| Capture | Restart after the grabber is unplugged or stalls | Unit-tested (fake) | `tests/test_capture_output.py`; real unplug not tried |
| Layout | 109 LEDs map to non-overlapping edge regions in the sketched order | Unit-tested, checked by eye on a real frame | `tests/test_layout.py`, `tools/preview.py` |
| Layout | The strip really runs in the configured direction (`ccw`) | Open | needs LEDs ([hardware.md](hardware.md)) |
| Colour | Region means, gamma, white balance, brightness | Unit-tested | `tests/test_extract.py`, `tests/test_color.py` |
| Colour | White balance and gamma look right on the strip | Open | needs LEDs; gains are placeholders |
| Colour | The strip's colour order (GRB assumed) | Open | needs LEDs |
| Power | Estimated current never exceeds the budget, also after rounding | Unit-tested | `tests/test_color.py`, `tests/test_pipeline.py`; the per-LED current figures are datasheet values, not measured |
| Smoothing | Flicker is reduced, scene cuts are immediate, no slow tail | Unit-tested | `tests/test_smoothing.py` ([ADR-008](decisions.md)); parameters not tuned by eye |
| Signal | The converter pattern is recognised, real pictures are not | Unit-tested against real PAL fixtures | `tests/test_monitor.py` ([ADR-009](decisions.md)) |
| Signal | Same for the NTSC pattern and live analogue noise | Open | needs a capture |
| Signal | A stalled capture (identical frames) is detected without flagging a paused video | Unit-tested | real behaviour of a paused source through the chain not observed |
| Signal | Fade out and in, lost signal | Unit-tested (simulated time) | `tests/test_monitor.py`, `tests/test_pipeline.py` |
| Letterbox | Black bars are found, dark scenes are not mistaken for bars, the crop is stable | Unit-tested | `tests/test_letterbox.py`, `tests/test_pipeline.py` ([ADR-011](decisions.md)) |
| Letterbox | Real letterboxed material through the analogue chain | Open | needs a capture |
| Output | The WS2812B backend drives the strip | Open | only a fake `rpi_ws281x`; **no LED has lit yet** |
| Output | The Pi produces correct WS2812B timing on GPIO 18 | Verified (old Pi) | [hardware.md](hardware.md): 400 ns / 1.25 us |
| Output | All LEDs off on exit, Ctrl-C and SIGTERM | Unit-tested | `tests/test_pipeline.py`; real SIGTERM through systemd not tried |
| Service | systemd unit starts the pipeline at boot and stops it cleanly | Open | written, never run |
| Metrics | fps, per-stage median/p99, CPU, retrievable without a debugger | Unit-tested | `tests/test_capture_output.py`; real values on the Pi missing |
| Performance | Whole pipeline about 1.6 ms per frame, about 5 % of one core | Mac only | [benchmarks.md](benchmarks.md); the Pi numbers decide ([ADR-007](decisions.md) exit criterion) |
| Latency | No perceptible offset between the TV and the LEDs | Open | no measurement yet; method in [benchmarks.md](benchmarks.md) |
| Hardware | The Pi runs without under-voltage | **Not met** | `get_throttled` was never `0x0`; replacement ordered ([ADR-003](decisions.md)) |
