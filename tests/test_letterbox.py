import numpy as np

from ambilight import config
from ambilight.extract import frame_view
from ambilight.letterbox import LetterboxDetector, measure_crop
from helpers import uyvy_frame, with_bars

W, H = 720, 480
REG, LB = config.Regions(), config.Letterbox()
BASE = (REG.crop_left, REG.crop_right, REG.crop_top, REG.crop_bottom)
RED = (200, 40, 40)


def textured(seed=0, mean=110):
    """A picture with some structure so rows and columns are not uniform."""
    rng = np.random.default_rng(seed)
    luma = np.clip(rng.normal(mean, 35, (H, W)), 20, 235).astype(np.uint8)
    view = np.empty((H, W // 2, 4), dtype=np.uint8)
    view[..., 0], view[..., 2] = 120, 140
    view[..., 1], view[..., 3] = luma[:, 0::2], luma[:, 1::2]
    return view.reshape(-1).tobytes()


def crop_of(frame):
    return measure_crop(frame_view(frame, W, H), REG, LB)


def test_no_bars_gives_the_base_crop():
    assert crop_of(uyvy_frame(W, H, RED)) == BASE
    assert crop_of(textured()) == BASE


def test_letterbox_bars_top_and_bottom_are_found():
    left, right, top, bottom = crop_of(with_bars(textured(1), W, H, top=60, bottom=60))
    assert (left, right) == (REG.crop_left, REG.crop_right)
    assert 60 <= top <= 70 and 60 <= bottom <= 70


def test_pillarbox_bars_left_and_right_are_found():
    left, right, top, bottom = crop_of(with_bars(textured(2), W, H, left=100, right=100))
    assert 100 <= left <= 110 and 100 <= right <= 110
    assert (top, bottom) == (REG.crop_top, REG.crop_bottom)
    assert left % 2 == 0 and right % 2 == 0


def test_unequal_bars_are_measured_per_side():
    _, _, top, bottom = crop_of(with_bars(textured(3), W, H, top=30, bottom=90))
    assert 30 <= top <= 40 and 90 <= bottom <= 100


def test_a_dark_scene_is_not_a_bar():
    rng = np.random.default_rng(4)
    dark = np.empty((H, W // 2, 4), dtype=np.uint8)
    dark[..., 0] = dark[..., 2] = 128
    dark[..., 1] = dark[..., 3] = np.clip(rng.normal(18, 10, (H, W // 2)), 16, 50).astype(np.uint8)
    assert crop_of(dark.reshape(-1).tobytes()) == BASE


def test_an_all_black_frame_is_not_cropped_away():
    assert crop_of(uyvy_frame(W, H, (0, 0, 0))) == BASE


def test_bars_around_a_dark_picture_are_ignored():
    dim = uyvy_frame(W, H, (20, 20, 20))                 # inside nothing brighter than content_min
    assert crop_of(with_bars(dim, W, H, top=60, bottom=60)) == BASE


def test_small_bars_are_ignored():
    assert crop_of(with_bars(textured(5), W, H, top=REG.crop_top + 6)) == BASE


def test_implausibly_large_bars_are_ignored():
    assert crop_of(with_bars(textured(6), W, H, top=200, bottom=200)) == BASE


def test_the_crop_only_changes_after_stable_frames():
    det = LetterboxDetector(LB, REG)
    barred = frame_view(with_bars(textured(7), W, H, top=60, bottom=60), W, H)
    for _ in range(LB.stable_frames - 1):
        crop, changed = det.update(barred)
        assert not changed and crop == BASE
    crop, changed = det.update(barred)
    assert changed and crop[2] >= 60
    assert not det.update(barred)[1]                     # no repeated "changed"


def test_flickering_between_bars_and_no_bars_never_changes_the_crop():
    det = LetterboxDetector(LB, REG)
    barred = frame_view(with_bars(textured(8), W, H, top=60, bottom=60), W, H)
    plain = frame_view(textured(8), W, H)
    for i in range(100):
        _, changed = det.update(barred if i % 2 else plain)
        assert not changed


def test_bars_that_disappear_are_released_after_stable_frames():
    det = LetterboxDetector(LB, REG)
    barred = frame_view(with_bars(textured(9), W, H, top=60, bottom=60), W, H)
    plain = frame_view(textured(9), W, H)
    for _ in range(LB.stable_frames):
        det.update(barred)
    assert det.crop != BASE
    changed = False
    for _ in range(LB.stable_frames):
        crop, changed = det.update(plain)
    assert changed and crop == BASE
