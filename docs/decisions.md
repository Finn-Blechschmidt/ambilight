# Decision log (ADR)

One entry per technical decision: context, options considered, decision, rationale, measurement, consequences.
Superseded decisions are not deleted; they are marked and linked to their replacement. Failed attempts are
documented on purpose.

| ADR | Title | Status |
|---|---|---|
| [001](#adr-001-deploy-with-rsync-over-an-ssh-host-alias) | Deploy with rsync over an SSH host alias | Accepted |
| [002](#adr-002-capture-basics-input-standard-format) | Capture basics (input, standard, format) | Partly superseded by ADR-004 |
| [003](#adr-003-keep-developing-on-the-faulty-pi-move-measurements-to-the-replacement-pi) | Keep developing on the faulty Pi, move measurements to the replacement | Accepted |
| [004](#adr-004-ntsc-instead-of-pal-on-converter-and-grabber-supersedes-adr-002) | NTSC instead of PAL on converter and grabber | Accepted |
| [005](#adr-005-led-output-via-pwm-on-gpio-18-with-rpi_ws281x) | LED output via PWM on GPIO 18 with `rpi_ws281x` | Provisional, not yet validated end to end |
| [006](#adr-006-hard-safety-limits-in-the-led-test-tool) | Hard safety limits in the LED test tool | Accepted |
| [007](#adr-007-python-with-numpy-for-the-pipeline-provisional-with-an-exit-criterion) | Python with NumPy for the pipeline | Provisional, exit criterion defined |
| [008](#adr-008-adaptive-smoothing-with-hysteresis-and-scene-cut-bypass) | Adaptive smoothing with hysteresis and scene-cut bypass | Accepted, parameters unverified on real LEDs |
| [009](#adr-009-signal-monitoring-by-pattern-structure-and-exact-frame-repeats) | Signal monitoring by pattern structure and exact frame repeats | Accepted, PAL pattern only |
| [010](#adr-010-v4l2-ctl-subprocess-with-a-reader-thread-newest-frame-wins-and-floor-rounding-for-the-current-limit) | `v4l2-ctl` subprocess with a reader thread; newest frame wins; floor rounding for the current limit | Accepted, capture unverified on hardware |

---

## ADR-001: Deploy with rsync over an SSH host alias

- Date: 2026-10-30
- Context: Development happens on a Mac, the code runs on the Pi. The repository is public, so it must not contain
  IP addresses or user names. Deploying must work with a single command.
- Options considered:
  1. `rsync` from the Mac to the Pi. Pro: fast, no Git access needed on the Pi, uncommitted changes can be tested.
     Con: the state on the Pi is not automatically tied to a commit.
  2. `git pull` on the Pi. Pro: the state is a commit. Con: needs a remote and a commit/push per test run, slower
     iteration.
  3. CI / package build (for example a `.deb`). Pro: clean. Con: oversized for this project.
- Decision: Option 1, `deploy/deploy.sh`. The target is the SSH alias `ambilight` (overridable with
  `AMBILIGHT_HOST`).
- Rationale: shortest iteration time; host details stay in `~/.ssh/config` and therefore outside the repository.
- Measurement: a deploy of the (then tiny) tree took 1.7 s end to end.
- Consequences / trade-offs: `--delete` removes files on the Pi that do not exist locally, so `~/ambilight` must
  not hold hand-made files.
- Amendment (2026-10-30), a failed attempt: the first version of the script did not exclude the Python virtual
  environment `~/ambilight/.venv`. A later deploy deleted it on the Pi and the next LED test failed with
  `python: command not found`. Fix: `.venv/` is now excluded in `deploy/deploy.sh`.

## ADR-002: Capture basics (input, standard, format)

- Date: 2026-10-30
- Status: the video standard part is superseded by [ADR-004](#adr-004-ntsc-instead-of-pal-on-converter-and-grabber-supersedes-adr-002).
  Input 0 and the UYVY format still hold.
- Context: The STK1160 (`/dev/video0`, driver `stk1160`) starts up with NTSC-M, 720x480. The signal chain was
  assumed to be PAL (625 lines, 25 Hz, interlaced).
- Options considered:
  1. Let the driver detect the standard automatically. Pro: no manual step. Con: the driver starts in NTSC,
     detection was not verified and can jump on signal loss.
  2. Fix the standard (later: from the config). Pro: deterministic. Con: no mixed PAL/NTSC sources, irrelevant
     for this setup.
- Decision (provisional at the time): input 0 (Composite0), PAL, UYVY 720x576, interlaced. The driver only offers
  UYVY.
- Rationale: a stable picture on the first try.
- Measurement: one frame (829,440 bytes = 720 x 576 x 2) captured and converted with `tools/uyvy2png.py`. It
  showed the converter's "NO SIGNAL" test pattern because the source was off.
- Finding: with no HDMI signal the HDMI-to-AV converter outputs a grey 8-bar pattern with the text "NO SIGNAL".
  Signal monitoring (M5) has to recognise this pattern (grey scale, no colour) or the LEDs would show garbage.
- Follow-up with a live source (same day): stable picture at 25.00 fps (100 frames, `v4l2-ctl --stream-count`),
  about 8 px black border on every side (luma about 26 to 35 versus about 215 in the picture; overscan/blanking,
  to be cropped later). **The picture was completely black and white**: U and V were exactly 128 in every pixel
  (chroma 0.0). This did not change with PAL-BG, PAL-N, PAL-Nc, SECAM, PAL-60 or NTSC-443 on the grabber, and the
  decoder's chroma AGC gain sat at 15 (default 40), meaning the decoder saw no colour subcarrier. Inputs 0 to 3 gave
  identical pictures (one physical composite input), input 4 (S-Video) gave black. `dmesg`: `saa7113 found @ 0x4a`.
- Consequences: led to ADR-004.

## ADR-003: Keep developing on the faulty Pi, move measurements to the replacement Pi

- Date: 2026-10-30
- Context: The Pi reports persistent under-voltage (`get_throttled=0x50005`), also without the grabber, with two
  cables and two power supplies (see [hardware.md](hardware.md)). The board is visibly bent; the owner suspects a
  hardware defect and orders a replacement Pi 3 B+.
- Options considered:
  1. Stop until the new Pi arrives. Pro: no measurements on broken hardware. Con: standstill although most of the
     work is hardware independent.
  2. Keep developing on the old Pi; do measurements and LED tests later on the new one. Pro: progress. Con: results
     from the old Pi are only partly valid.
  3. Clone the old Pi's image onto the new Pi. Pro: quick. Con: carries over leftovers, not reproducible and not
     documented.
- Decision: Option 2. The new Pi is set up with `deploy/setup.sh`, not by cloning an image.
- Rationale: capture, pipeline logic, colour maths, smoothing and tests are hardware independent. The setup script
  keeps a fresh image reproducible.
- Not reliable on the old Pi: CPU load, latency, fps under load, temperature, every timing result (the clock is
  limited by under-voltage; 600 MHz at idle). The language choice (ADR) is therefore postponed until there are
  measurements on a healthy Pi. Until then only language-independent code and documentation are produced.
- LEDs: the original plan was to run the first LED test (M2) only on the new Pi. The owner chose to try it on the
  old Pi anyway, see ADR-005/006 and [hardware.md](hardware.md).
- Consequences / trade-offs: M3 to M6 move back. Numbers measured on the old Pi are labelled as such in
  [benchmarks.md](benchmarks.md).

## ADR-004: NTSC instead of PAL on converter and grabber (supersedes ADR-002)

- Date: 2026-10-30
- Context: With converter and grabber on PAL the picture arrived completely black and white (chroma exactly 0, see
  ADR-002). Changing the standard on the grabber alone did not help. The converter has a PAL/NTSC switch.
- Options considered:
  1. Keep PAL (625 lines, 25 Hz, 720x576). Pro: more lines. Con: no colour, unusable.
  2. Converter and grabber on NTSC (525 lines, about 29.97 Hz, 720x480). Pro: colour arrives, higher frame rate,
     shorter frame interval. Con: fewer lines (irrelevant for edge colours).
  3. Look for another converter or input. Not needed.
- Decision: Option 2. Converter switch on NTSC, grabber `ntsc-m`, 720x480, UYVY, interlaced.
- Rationale: the only tested configuration in which colour arrives.
- Measurement: source was the YouTube video "Ambilight Color Test - All Colors" (colour wheel).
  PAL: chroma 0.00 / 0.00, grey wheel. NTSC-M: chroma 27.96 / 26.45, full colour wheel, decoder chroma gain rose
  from 15 to 54. Frame rate: 150 frames in 5.15 s = 29.13 fps including stream start-up (nominal 30000/1001). The
  value comes from the faulty Pi and is indicative only (ADR-003). The owner confirmed that the captured frame
  matches the picture on the TV.
- Presumed cause (not proven): in its PAL position the converter delivers no colour signal, or one the decoder
  cannot lock to. Not investigated further.
- Consequences / trade-offs: the converter switch has to stay on NTSC. The picture shows interlacing combing and
  colour fringing, which pre-processing has to account for. The converter's "NO SIGNAL" pattern still has to be
  checked in NTSC mode for signal monitoring (M5).
- Replaces: the PAL assumption in ADR-002 (input 0 and UYVY stay).

## ADR-005: LED output via PWM on GPIO 18 with `rpi_ws281x`

- Date: 2026-10-30
- Status: provisional. The signal leaves the Pi correctly, but no LED has reacted yet, so the method is not
  validated end to end.
- Context: The data wire was already connected to GPIO 18 (physical pin 12) and the strip is WS2812B-type, so the
  output method has to work on that pin.
- Options considered:
  1. PWM via the `rpi_ws281x` library (DMA-driven, GPIO 12/18 for PWM0, 13/19 for PWM1). Pro: works on the wired
     pin, mature library. Con: needs root, claims the PWM block (analogue audio must be disabled), only usable on
     certain pins.
  2. SPI (MOSI, GPIO 10, pin 19). Pro: no root for the hardware access, stable clock. Con: needs a different pin
     and `core_freq` care on the Pi 3.
  3. PCM (GPIO 21, pin 40). Pro: does not touch PWM. Con: a different pin as well.
  4. Bit-banging from user space. Con: cannot meet the 400 ns timing reliably.
- Decision: Option 1 on GPIO 18. Options 2 and 3 are kept as fallback if the pin turns out to be damaged
  (`tools/led_test.py --pin` already supports 12, 13, 18, 19, 21).
- Rationale: no re-wiring needed for the first test; the library exposes brightness, strip type and frequency.
- Measurement: with `led_test.py mark --stream` running, `tools/gpio_pulse.c` sampled the pin (111 ns per read):
  111,265 high pulses, widths 300 to 599 ns with the peak at 400 to 499 ns, rising-edge to rising-edge 1100 to
  1399 ns with the peak at 1200 to 1299 ns. That matches WS2812B at 800 kHz (0 bit about 0.4 us high, 1.25 us
  period). Idle pin: 0 level changes. Voltage amplitude cannot be judged this way.
- Setup consequences: `dtparam=audio=off` in `/boot/firmware/config.txt`, `python3-dev` and `scons` for the build,
  a virtual environment with `rpi_ws281x`, and root for each run (see [hardware.md](hardware.md)).
- Open: no LED lit with 800 or 400 kHz, 24 or 32 bit. Later the pin readback became abnormal (GPIO 18 stuck high),
  see [hardware.md](hardware.md).

## ADR-006: Hard safety limits in the LED test tool

- Date: 2026-10-30
- Context: Rule for this project: before the LEDs are driven for the first time use low brightness and few LEDs,
  and never all LEDs at full white without an active current limit. 109 LEDs can draw 6.5 A, the supply is
  rated 10 A, and the Pi itself had a power problem.
- Options considered:
  1. Safe defaults only (command-line flags can raise them). Pro: flexible. Con: easy to exceed by accident.
  2. Hard-coded limits in the tool. Pro: cannot be exceeded from the command line. Con: has to be edited for real
     use.
- Decision: Option 2. `tools/led_test.py` limits global brightness to 32 of 255 and the number of lit LEDs to 8.
  All LEDs are switched off on exit, on Ctrl-C and on SIGTERM.
- Consequences: the largest test load is about 8 LEDs x 60 mA x 32/255, roughly 60 mA. The production pipeline
  needs its own configurable current limit (planned, not implemented).

## ADR-007: Python with NumPy for the pipeline (provisional, with an exit criterion)

- Date: 2026-11-20
- Context: [ADR-003](#adr-003-keep-developing-on-the-faulty-pi-move-measurements-to-the-replacement-pi) postponed the
  language choice until there are measurements on a healthy Pi. The owner asked to implement M3 to M5 without the new
  Pi and to test later. The Pi was unreachable when this was decided, so nothing could be measured on it.
- Options considered:
  1. Python 3 + NumPy. Pro: fast iteration, easy tests on the Mac, `rpi_ws281x` and `tomllib` are available, regions
     need only a small part of each frame. Con: interpreter overhead on a Cortex-A53; the per-call cost of many small
     NumPy operations can dominate.
  2. C. Pro: lowest CPU use and latency, full control. Con: slower to write and test, manual memory handling, more
     code for configuration, tests and service logic.
  3. Rust or Go. Pro: fast and safe. Con: toolchain and cross-compilation overhead on the Pi, no mature WS281x
     library at hand, no experience reuse in this repository.
- Decision: Option 1 for everything, with the hot path kept narrow and measurable. The code is structured so that
  the frame-to-colours step (`extract.py`) can be replaced by a C extension without touching the other stages.
- Rationale: most of the pipeline logic (layout, colour maths, smoothing, signal monitoring, configuration) is cheap
  per frame and benefits most from quick iteration and tests. Only the extraction touches pixel data, and it only
  reads the border bands.
- Measurement (Mac, indicative only, not valid for the Pi): colour extraction for 109 regions plus gamma, current
  limit and conversion to bytes takes a median of 1.0 to 1.1 ms per frame (p99 1.1 to 2.2 ms), nearly independent of
  how many rows are sampled. That points to per-call overhead (109 small NumPy calls), not pixel work, as the cost.
  The Pi will be considerably slower; by how much is unknown.
- Exit criterion (to be checked on a healthy Pi, `get_throttled` = `0x0`): if the extraction plus colour stages exceed
  8 ms at the 99th percentile (about a quarter of the 33.4 ms frame interval), or the whole pipeline needs more than
  40 % of one core at 29.97 fps, first vectorise the extraction (one pass over the border bands instead of 109 calls),
  and if that is not enough, move the extraction to C.
- Consequences / trade-offs: the choice may be revised after the first real measurement; this ADR will then be
  marked superseded and linked, not deleted.

## ADR-008: Adaptive smoothing with hysteresis and scene-cut bypass

- Date: 2026-11-20
- Context: Analogue composite capture is noisy, so edge colours flicker from frame to frame. Smoothing has to hide
  that without making the LEDs lag behind real changes, and a hard scene cut should show immediately.
- Options considered:
  1. One fixed exponential moving average. Pro: trivial. Con: either flickers (short time constant) or lags
     (long one).
  2. Time constant that depends on the remaining difference between target and state. Pro: no extra state.
     Con: see "Failed attempt".
  3. Two time constants with hysteresis per LED, plus a global scene-cut bypass. Pro: noise is smoothed, real
     changes are fast and converge without a tail. Con: four parameters to tune.
- Failed attempt: the first implementation was option 2. A unit test caught that a large change (+60 steps) was only
  71 % done after three frames, against the 85 % that was required: the time constant grows as the remaining
  difference shrinks, which gives a slow tail at the end of every big change. Replaced by option 3.
- Decision: option 3 (`src/ambilight/smoothing.py`). An LED switches to `tau_fast_s` (0.04 s) when it is
  `delta_high` (40) or more away from its target and stays fast until it is within `delta_low` (6) of it. Otherwise
  it uses `tau_slow_s` (0.30 s). If the mean change over all LEDs exceeds `cut_threshold` (70) the state jumps to the
  new colours. The blend factor is `1 - exp(-dt / tau)` with the real frame interval, so the result does not depend
  on the frame rate.
- Measurement (unit tests, synthetic input, simulated time): noise with a standard deviation of 3 steps is reduced
  to less than half; +10 steps reach under 45 % after three frames, +60 steps over 85 %; a scene cut is exact in one
  frame; 15 frames at 30 fps and 30 frames at 60 fps differ by less than 3 steps. Cost on a Mac: 0.012 ms per frame
  (median), not valid for the Pi.
- Consequences / trade-offs: the default parameters are educated guesses. They have to be tuned by eye on the real
  strip (M4/M6). Smoothing runs in the gamma-corrected output space, and the current limiter runs after it, so the
  budget holds for what is actually sent to the strip.

## ADR-009: Signal monitoring by pattern structure and exact frame repeats

- Date: 2026-11-20
- Context: With no HDMI signal the converter outputs a grey 8-bar test pattern with the text "NO SIGNAL"
  ([ADR-002](#adr-002-capture-basics-input-standard-format)). The LEDs must fade out then instead of showing
  its bar colours. A stalled capture or a missing grabber must be handled as well.
- Options considered for the test pattern:
  1. "The picture has no colour" (chroma about 0). Pro: trivial. Con: a black-and-white film or a white web page also
     has no colour. The capture of the white login page on 2026-10-30 had chroma exactly 0, so this would switch the
     LEDs off during legitimate content.
  2. Compare with a stored reference image. Pro: exact. Con: breaks with any change in noise or crop, and needs the
     NTSC pattern, which has not been captured yet.
  3. Detect the structure: eight flat vertical bars whose brightness steps monotonically from left to right, in a
     colourless picture. Pro: independent of exact levels and of the text. Con: a thresholds-based heuristic.
- Options considered for a frozen picture:
  1. Frames "almost" identical. Con: a paused video and a static menu would count as frozen.
  2. Byte-identical frames in a row. Pro: analogue noise makes real pictures differ, only a stalled capture repeats
     exactly. Con: untested on live hardware, a very clean source could produce identical frames.
- Decision: structure detection for the pattern (`monitor.is_no_signal_pattern`): per-column median luma, at least
  90 % of the pixels within 12 steps of the column profile, eight bars whose middle halves have a standard deviation of
  at most 1.5 and whose means differ by at least 10 steps in one direction, and chroma deviation of at most 2.
  Frozen = 60 byte-identical frames in a row. Lost = no frame for 1.0 s. All three fade the LEDs out in 0.5 s and back in
  in 0.3 s (`src/ambilight/monitor.py`).
- Failed attempt: the first flatness threshold (standard deviation 4.0) accepted a smooth brightness ramp as the
  pattern. A test with a ramp caught it. Measured on the real pattern: at most 0.6; the ramp gives 3.9; the threshold is
  now 1.5.
- Measurement: on the real PAL capture of the pattern the detector says yes; on a real colour picture and on a real
  colourless picture (the white web page) it says no (fixtures in `tests/data`, built by
  `tools/make_test_fixtures.py`). Cost on a Mac: 0.20 ms per frame (median), not valid for the Pi.
- Consequences / trade-offs: **verified only against the PAL pattern.** The converter now runs NTSC
  ([ADR-004](#adr-004-ntsc-instead-of-pal-on-converter-and-grabber-supersedes-adr-002)) and its NTSC pattern has not
  been captured. Live analogue noise might push the bar flatness over the threshold. Both are to be checked on the
  Pi as soon as it is reachable. The frozen detector is likewise unverified on hardware.

## ADR-010: `v4l2-ctl` subprocess with a reader thread, newest frame wins, and floor rounding for the current limit

- Date: 2026-11-20
- Context: The pipeline needs a continuous stream of frames from the grabber, must survive a grabber that disappears or
  stalls, and must never build up latency. The Pi was not reachable, so nothing here could be tried on the real device.
- Options considered for reading frames:
  1. OpenCV `VideoCapture`. Pro: one call. Con: a heavy dependency on a Pi 3, hides buffering and error handling,
     UYVY/format control is indirect.
  2. Direct V4L2 ioctls with `ctypes` and `mmap`. Pro: no subprocess, full control. Con: a lot of low-level code that
     cannot be tested without the device.
  3. `v4l2-ctl --stream-mmap --stream-to=-` as a subprocess, raw frames from its stdout. Pro: the tool is already
     installed and was used successfully for every capture in M1, trivial to fake in tests, a crash of the capture is
     isolated from the pipeline process. Con: one pipe copy per frame (about 20 MB/s at 720x480 and 29.97 fps),
     depends on `v4l2-ctl` behaving as documented when writing to stdout (not tried yet).
- Decision for reading: option 3 (`capture.V4L2Capture`). A reader thread reads exactly one frame at a time and keeps only
  the newest. If the consumer is slower, older frames are dropped (counted), so latency cannot accumulate. If the
  process ends or delivers nothing for `stall_timeout_s`, it is killed and restarted after `restart_delay_s`.
- Concurrency model: one reader thread (blocking pipe reads release the GIL) and the main thread running the
  pipeline. Options considered: a single loop (a blocked read would stall fading and signal monitoring), several
  processes (more copying, more complexity). Revisit after measuring on a healthy Pi (the exit criterion of
  [ADR-007](#adr-007-python-with-numpy-for-the-pipeline-provisional-with-an-exit-criterion) applies).
- Measurement (Mac, synthetic noisy frames, 400 frames, not valid for the Pi): total per frame median 1.33 ms, p99
  1.48 ms. Extraction 1.11 ms, correction and smoothing 0.02 ms, monitor 0.20 ms, limit and output 0.005 ms.
- Failed attempt (caught by a test): the current limiter scaled in floating point, but the strip receives 8-bit values and
  `to_bytes` rounded to nearest. A full white frame then came out at an estimated 2006.9 mA against a 2000 mA budget,
  because rounding up adds up to half a step on each of the 327 channels. A safety limit has to hold after
  quantisation, so values going to the strip are now rounded down (`to_bytes(..., floor=True)`).
- Not verified: reading from the real grabber through `v4l2-ctl --stream-to=-`, behaviour when the grabber is
  unplugged, the real `rpi_ws281x` output (no LED has lit, see hardware.md), the systemd unit.
- Consequences / trade-offs: a pipe copy per frame; the Python reader thread competes for the GIL with the pipeline.
  Both are cheap at this data rate, but the numbers on the Pi decide.
