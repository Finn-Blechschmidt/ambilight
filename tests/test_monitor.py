from pathlib import Path

import numpy as np
import pytest

from ambilight import config, extract
from ambilight.monitor import SignalMonitor, State, is_no_signal_pattern

DATA = Path(__file__).parent / "data"
W, H = 720, 480
DT = 1 / 30


def uyvy(luma, u=128, v=128):
    """UYVY view from a luma plane (H, W) and constant chroma."""
    h, w = luma.shape
    view = np.empty((h, w // 2, 4), dtype=np.uint8)
    view[..., 0] = u
    view[..., 1] = luma[:, 0::2]
    view[..., 2] = v
    view[..., 3] = luma[:, 1::2]
    return view


def bars_luma(text=True):
    """The converter pattern: 8 grey bars, bright to dark, with a dark text block."""
    levels = [235, 215, 175, 145, 110, 80, 50, 25]
    x = np.arange(W)
    row = np.array(levels)[np.minimum(x * 8 // W, 7)].astype(np.uint8)
    luma = np.tile(row, (H, 1))
    if text:
        luma[80:110, 100:280] = 16
    return luma


def picture(seed, u=140, v=110):
    rng = np.random.default_rng(seed)
    return uyvy(rng.integers(30, 220, (H, W), dtype=np.uint8), u, v)


@pytest.fixture
def mon():
    cfg = config.Config()
    return SignalMonitor(cfg.signal, cfg.regions)


def feed(mon, view, n, t0=0.0):
    out = None
    for i in range(n):
        out = mon.update(view, t0 + (i + 1) * DT)
    return out


# --- pattern detector --------------------------------------------------------------------------------
def test_real_converter_pattern_is_recognised():
    assert is_no_signal_pattern(np.load(DATA / "no_signal_pal.npy"))


def test_real_colour_picture_is_not_a_pattern():
    assert not is_no_signal_pattern(np.load(DATA / "picture_ntsc_color.npy"))


def test_real_black_and_white_picture_is_not_a_pattern():
    assert not is_no_signal_pattern(np.load(DATA / "picture_bw_login.npy"))   # colourless, but a real picture


def test_synthetic_bars_with_and_without_text():
    assert is_no_signal_pattern(bars_luma(text=True))
    assert is_no_signal_pattern(bars_luma(text=False))


def test_bars_with_colour_are_not_the_pattern():
    assert not is_no_signal_pattern(bars_luma(), chroma_dev=20.0)


def test_noise_and_gradients_are_not_the_pattern():
    rng = np.random.default_rng(3)
    assert not is_no_signal_pattern(rng.integers(0, 255, (H, W), dtype=np.uint8))
    gradient = np.tile(np.linspace(20, 230, W).astype(np.uint8), (H, 1))      # smooth, not flat bars
    assert not is_no_signal_pattern(gradient)
    assert not is_no_signal_pattern(np.full((H, W), 16, dtype=np.uint8))      # black


# --- state machine -----------------------------------------------------------------------------------
def test_starts_dark_until_the_first_frame(mon):
    assert mon.state is State.LOST and mon.gain == 0.0


def test_normal_picture_fades_in_and_stays_ok(mon):
    state, gain = feed(mon, picture(1), 1)
    assert state is State.OK and gain == 0.0          # the first frame has no time step yet, so no fade yet
    state, gain = mon.update(picture(2), 2 * DT)
    assert 0.0 < gain < 1.0                           # fading in
    for s in range(3, 20):
        state, gain = mon.update(picture(s), s * DT)
    assert state is State.OK and gain == 1.0


def test_pattern_switches_off_after_the_configured_frames_and_fades(mon):
    for s in range(1, 20):
        mon.update(picture(s), s * DT)                                   # reach full brightness
    pat = uyvy(bars_luma())
    t = 20 * DT
    states = []
    for i in range(60):
        t += DT
        states.append(mon.update(pat, t))
    first = next(i for i, (s, _) in enumerate(states) if s is State.NO_SIGNAL)
    assert first == config.Signal().no_signal_frames - 1
    gains = [g for _, g in states[first:]]
    assert all(b <= a for a, b in zip(gains, gains[1:]))                 # monotone fade
    assert gains[-1] == 0.0
    assert gains[int(0.25 / DT)] < 0.9                                   # it really fades, not an instant cut


def test_pattern_gone_brings_the_leds_back(mon):
    pat = uyvy(bars_luma())
    t = 0.0
    for _ in range(30):
        t += DT
        mon.update(pat, t)
    assert mon.state is State.NO_SIGNAL and mon.gain == 0.0
    for s in range(30):
        t += DT
        state, gain = mon.update(picture(s), t)
    assert state is State.OK and gain == 1.0


def test_identical_frames_are_frozen_but_noisy_ones_are_not(mon):
    frame = picture(7)
    state, _ = feed(mon, frame, config.Signal().frozen_frames + 5)
    assert state is State.FROZEN
    mon2 = SignalMonitor(config.Signal(), config.Regions())
    for s in range(config.Signal().frozen_frames + 5):
        state, _ = mon2.update(picture(100 + s), (s + 1) * DT)           # a "still" picture with analogue noise
    assert state is State.OK


def test_no_frames_marks_the_signal_lost_after_the_timeout(mon):
    for s in range(1, 20):
        mon.update(picture(s), s * DT)
    t = 19 * DT
    state, gain = mon.tick(t + 0.5)
    assert state is State.OK                                              # not yet
    state, gain = mon.tick(t + 1.0)
    assert state is State.LOST
    for k in range(1, 30):
        state, gain = mon.tick(t + 1.0 + k * DT)
    assert gain == 0.0


def test_extract_view_feeds_the_monitor_directly(mon):
    frame_bytes = picture(9).reshape(-1).tobytes()
    view = extract.frame_view(frame_bytes, W, H)
    assert mon.update(view, DT)[0] is State.OK
