# Benchmarks

**No valid performance benchmark exists yet.** The only Pi available so far reports persistent under-voltage and
throttling (`get_throttled` = `0x50005` to `0x70007`, ARM clock 600 MHz at idle), so CPU, latency and
frame-rate-under-load numbers from it are meaningless. They will be measured on a healthy Pi (see
[ADR-003](decisions.md)) and entered here. A measurement counts only if `vcgencmd get_throttled` reads `0x0` before
and after the run.

## Method (planned)

| Quantity | How |
|---|---|
| Capture frame rate | `v4l2-ctl --stream-mmap --stream-count=N`, timing the whole run and the reported fps |
| Per-stage latency | timestamps at the stage boundaries inside the pipeline, reported as median and 99th percentile |
| End-to-end latency | camera or photodiode view of a flashing test frame on the TV versus the LEDs; no instrument available yet |
| CPU load | `top` / `/proc/stat` sampled during a 10-minute run with a moving test video, per core |
| Temperature and throttling | `vcgencmd measure_temp`, `vcgencmd get_throttled` before, during and after the run |
| LED output timing | `tools/gpio_pulse.c` (pulse widths) and the frame time of the output stage |

## Results so far (indicative only, measured on the faulty Pi)

| Measurement | Result | Validity |
|---|---|---|
| Capture rate, PAL, 720x576 | 25.00 fps (100 frames, reported by `v4l2-ctl`) | Indicative. Capture is DMA/USB driven, but the Pi was under-voltage |
| Capture rate, NTSC, 720x480 | 29.13 fps (150 frames in 5.15 s, including stream start-up; nominal 29.97) | Indicative. The start-up time lowers the average |
| GPIO 18 pulse widths with the PWM output running | high pulses 300 to 599 ns, peak 400 to 499 ns; rising-edge spacing 1100 to 1399 ns, peak 1200 to 1299 ns (111,265 pulses, 111 ns per register read) | Plausibility check only: matches the WS2812B 800 kHz timing within the sampling resolution |
| Colour extraction (109 regions) plus gamma, current limit and byte conversion, Python + NumPy | median 1.0 to 1.1 ms per frame, p99 1.1 to 2.2 ms, on a Mac (M-series) | **Not valid for the Pi.** Only shows that per-call overhead, not pixel work, dominates. Exit criterion for the Pi in ADR-007 |
| Whole pipeline per frame (letterbox, extract, correct and smooth, monitor, limit and output; null output), `tools/bench_pipeline.py --synthetic 600` | median 1.62 ms, CPU 1.65 ms per frame = 4.9 % of one core at 29.97 fps, capacity about 600 frames/s, on a Mac | **Not valid for the Pi.** Letterbox 0.32 ms and extraction about 1.1 ms of it |
| Smoothing step (109 LEDs) | median 0.012 ms per frame, p99 0.019 ms, on a Mac | **Not valid for the Pi** |
| Signal monitor update (pattern check + repeat check) | median 0.20 ms per frame, p99 0.28 ms, on a Mac | **Not valid for the Pi** |
| CPU load, per-stage latency, end-to-end latency, temperature under load | not measured | - |

## Reported system state at measurement time

| Date | `get_throttled` | Temperature | Remark |
|---|---|---|---|
| 2026-10-30 | `0x50005` to `0x70007` | 65 to 82 C at idle | under-voltage active, not a valid platform for benchmarks |
