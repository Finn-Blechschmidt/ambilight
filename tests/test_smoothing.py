import numpy as np

from ambilight import config
from ambilight.smoothing import Smoother

DT = 1 / 30
N = 109


def run(sm, frames, dt=DT):
    return [sm.step(f, dt) for f in frames]


def make():
    return Smoother(config.Smoothing())


def test_first_frame_is_passed_through():
    sm = make()
    rgb = np.full((N, 3), 77.0)
    assert np.allclose(sm.step(rgb, DT), rgb)


def test_constant_input_stays_constant():
    sm = make()
    rgb = np.full((N, 3), 120.0)
    out = run(sm, [rgb] * 30)
    assert np.allclose(out[-1], rgb)


def test_noise_is_strongly_reduced():
    sm = make()
    rng = np.random.default_rng(0)
    frames = [np.full((N, 3), 100.0) + rng.normal(0, 3.0, (N, 3)) for _ in range(150)]
    out = np.array(run(sm, frames))
    assert out[60:].std(axis=0).mean() < 0.5 * np.array(frames)[60:].std(axis=0).mean()


def test_small_change_is_slow_large_change_is_fast():
    dark = np.full((N, 3), 100.0)
    small = run(make(), [dark] + [dark + 10.0] * 3)[-1]          # +10: near the noise floor
    large = run(make(), [dark] + [dark + 60.0] * 3)[-1]          # +60: a real change, but not a scene cut
    assert (small[0, 0] - 100.0) / 10.0 < 0.45                    # less than half way after 3 frames
    assert (large[0, 0] - 100.0) / 60.0 > 0.85                    # almost there after 3 frames


def test_scene_cut_jumps_immediately():
    sm = make()
    sm.step(np.zeros((N, 3)), DT)
    out = sm.step(np.full((N, 3), 255.0), DT)
    assert np.allclose(out, 255.0)


def test_single_led_change_is_not_a_scene_cut():
    sm = make()
    base = np.zeros((N, 3))
    sm.step(base, DT)
    one = base.copy()
    one[5] = 255.0
    out = sm.step(one, DT)
    assert 100.0 < out[5, 0] < 255.0          # fast, but blended
    assert out[6, 0] == 0.0                   # others untouched


def test_result_does_not_depend_on_the_frame_rate():
    base = np.full((N, 3), 100.0)
    target = base + 25.0                      # mid-sized change
    a = Smoother(config.Smoothing()); a.step(base, 1 / 30)
    b = Smoother(config.Smoothing()); b.step(base, 1 / 60)
    for _ in range(15):
        a_out = a.step(target, 1 / 30)        # 0.5 s in total
    for _ in range(30):
        b_out = b.step(target, 1 / 60)
    assert abs(a_out[0, 0] - b_out[0, 0]) < 3.0


def test_reset_forgets_the_state():
    sm = make()
    sm.step(np.zeros((N, 3)), DT)
    sm.reset()
    assert np.allclose(sm.step(np.full((N, 3), 50.0), DT), 50.0)


def test_zero_dt_does_not_move():
    sm = make()
    sm.step(np.zeros((N, 3)), DT)
    assert np.allclose(sm.step(np.full((N, 3), 30.0), 0.0), 0.0)
