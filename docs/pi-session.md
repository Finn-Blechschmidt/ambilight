# Checklist for the next session with a healthy Pi

Everything that needs the real hardware, in the order it should be done. Each step says what to run, what counts as a
pass, and which document to update. Stop at the first failed step of 0 to 2: later numbers would be meaningless.

## 0. Power

Pass: `ssh ambilight vcgencmd get_throttled` prints `throttled=0x0` after a few minutes of idle, also with the grabber
plugged in. Anything else: fix the supply first ([hardware.md](hardware.md)); do not benchmark and do not drive the LEDs.

## 1. Set up a fresh Pi

```bash
deploy/deploy.sh
ssh ambilight '~/ambilight/deploy/setup.sh'     # asks for the sudo password; then: sudo reboot
```

Pass: setup finishes, the Pi reboots, `get_throttled` is still `0x0`, `~/ambilight/.venv/bin/python -c "import rpi_ws281x, numpy"`
works. Update: the system-changes table in [hardware.md](hardware.md) if anything differs.

## 2. Capture, NTSC pattern and live material (no LEDs needed)

1. Converter switch on NTSC, source on: `tools/capture_frame.sh` prints chroma well above 0.
2. Source off so the converter shows its pattern: `tools/record_frames.sh 60 captures/no_signal_ntsc.uyvy`.
3. Replay it on the Mac: `.venv/bin/python -m ambilight --output null --input-file captures/no_signal_ntsc.uyvy --log-level DEBUG`
   and check that the log shows `signal state: no_signal` (state changes are logged as they happen). If not, adjust `MAX_BAR_STD` or the thresholds in
   `src/ambilight/monitor.py`, add a fixture (`tools/make_test_fixtures.py`) and update [ADR-009](decisions.md).
4. Source on with the "Ambilight Color Test" video: `tools/record_frames.sh 300 captures/frames.uyvy`. Keep it for steps 3 and 4.
5. If possible record a letterboxed film scene as well and check `tools/preview.py captures/<frame>.png --letterbox`.

Pass: colour frames, the NTSC pattern is detected, no false positive on live material. Update: ADR-009, [verification.md](verification.md).

## 3. Benchmark on the Pi (decides ADR-007)

```bash
scp captures/frames.uyvy ambilight:/tmp/frames.uyvy
ssh ambilight '~/ambilight/.venv/bin/python ~/ambilight/tools/bench_pipeline.py --frames-file /tmp/frames.uyvy --json /tmp/bench.json'
```

Pass for the language decision: `throttled_before` and `throttled_after` are `0x0`, and extract plus correct/smooth p99
is at most 8 ms, and `cpu_percent_of_one_core_at_29_97_fps` is at most 40. If not: vectorise the extraction first,
then move it to C ([ADR-007](decisions.md)). Update: [benchmarks.md](benchmarks.md) (replace the "Mac only" rows with Pi numbers,
keep the Mac numbers labelled), ADR-007 (confirm or supersede).

## 4. The capture path end to end (null output)

```bash
ssh ambilight 'cd ~/ambilight && PYTHONPATH=src .venv/bin/python -m ambilight --output null'
```

with `[metrics] json_path` set in `config/ambilight.local.toml`. Pass: the log shows about 29.97 fps, few or no dropped
frames. Then unplug the grabber for 5 seconds and plug it in again: the log shows a restart, the state goes `lost`, and
it returns to `ok`. Update: [ADR-010](decisions.md), [verification.md](verification.md).

## 5. LED bring-up (M2), see [hardware.md](hardware.md)

1. Header without cables: drive pin 12 and the alternatives high/low with `pinctrl`, read back. Separates wiring from a damaged pin.
2. If GPIO 18 is bad: another data pin (`led_test.py --pin 12` with GND on pin 34, or `--pin 21` with GND on pin 39).
3. If the signal is right but no LED lights: a level shifter (74AHCT125) on the data line; check +5 V and GND at the strip.
4. First light: `led_test.py color`, then `walk`. Record the real colour order and the direction of travel; set
   `leds.color_order` and `layout.direction` in the config. Check LED 0 is right of the gap.

Pass: a single LED reacts, the colour order and direction are known. Update: M2 in the README, [hardware.md](hardware.md),
[ADR-005](decisions.md), `layout.direction` and `color_order` in the example config.

## 6. First pipeline run on the strip

Start with a low budget: `[leds] max_current_ma = 500`. Run `python -m ambilight` with the colour test video, look at the strip:
colours match the picture side for side, the gap is at the bottom centre, white looks white. Tune `white_balance`,
`gamma`, `brightness` and the smoothing parameters by eye, raise the budget in steps, measure the supply voltage at the far
end of the strip at the highest budget. Update: example config values, [ADR-008](decisions.md), the power section of [hardware.md](hardware.md).

## 7. Service and shutdown

```bash
ssh ambilight '~/ambilight/deploy/install_service.sh'
```

Pass: the strip lights after a reboot, `sudo systemctl stop ambilight` switches every LED off, `journalctl -u ambilight`
shows the metrics lines. Update: [verification.md](verification.md), the README.

## 8. Latency

Film the TV and the LEDs together with a phone in slow motion (240 fps) while a test video flashes white. Count the frames
between the flash on the TV and on the LEDs and convert to milliseconds. Pass: no perceptible offset, target under 100 ms.
Update: [benchmarks.md](benchmarks.md), the README key numbers.

## 9. Close out

Fill the README "Key numbers" section with the Pi values, set every milestone status, review [verification.md](verification.md)
until no "Open" is left that matters, and re-check the repository for private data before the next push.
