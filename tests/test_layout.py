import itertools

from ambilight import config, layout


def rects(direction="ccw"):
    cfg = config.from_dict({"layout": {"direction": direction}})
    return cfg, layout.led_rects(cfg)


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def test_one_rectangle_per_led():
    cfg, r = rects()
    assert len(r) == cfg.layout.count == 109


def test_rectangles_are_inside_the_cropped_frame_and_not_empty():
    cfg, r = rects()
    reg = cfg.regions
    for x0, y0, x1, y1 in r:
        assert reg.crop_left <= x0 < x1 <= reg.frame_width - reg.crop_right
        assert reg.crop_top <= y0 < y1 <= reg.frame_height - reg.crop_bottom


def test_x_coordinates_are_even_for_uyvy_macropixels():
    _, r = rects()
    assert all(x % 2 == 0 for rect in r for x in (rect[0], rect[2]))


def test_rectangles_do_not_overlap():
    _, r = rects()
    assert not [p for p in itertools.combinations(range(len(r)), 2) if overlap(r[p[0]], r[p[1]])]


def test_strip_order_ccw_matches_the_sketch():
    cfg, r = rects()
    cx = cfg.regions.frame_width / 2
    mid = lambda i: ((r[i][0] + r[i][2]) / 2, (r[i][1] + r[i][3]) / 2)
    h = cfg.regions.frame_height
    # LED 0: bottom, just right of the centre gap; LED 16: bottom right corner
    assert mid(0)[1] > h * 0.8 and cx < mid(0)[0] < cx + 30
    assert mid(16)[0] > cfg.regions.frame_width * 0.9
    # 17..36 right side going up, 37..71 top going left, 72..91 left going down, 92..108 bottom to the gap
    assert mid(17)[1] > mid(36)[1]
    assert mid(37)[0] > mid(71)[0] and mid(37)[1] < h * 0.2
    assert mid(72)[1] < mid(91)[1] and mid(72)[0] < cfg.regions.frame_width * 0.2
    assert mid(92)[0] < 40 and cx - 30 < mid(108)[0] < cx


def test_gap_is_left_uncovered_at_the_bottom_centre():
    cfg, r = rects()
    reg = cfg.regions
    bottom_y0 = reg.frame_height - reg.crop_bottom - reg.depth_y
    bottom = sorted(q for q in r if q[1] == bottom_y0)
    assert len(bottom) == 34                              # 17 + 17, the 35th slot is the gap
    holes = [(a[2], b[0]) for a, b in zip(bottom, bottom[1:]) if b[0] > a[2]]
    assert len(holes) == 1                                # exactly one hole, no other gaps or overlaps
    start, stop = holes[0]
    assert start < reg.frame_width / 2 < stop             # and it is at the centre


def test_cw_is_the_mirror_image_of_ccw():
    cfg, ccw = rects("ccw")
    _, cw = rects("cw")
    m = cfg.regions.crop_left + cfg.regions.frame_width - cfg.regions.crop_right
    assert cw[0] == (m - ccw[0][2], ccw[0][1], m - ccw[0][0], ccw[0][3])
    assert (cw[0][0] + cw[0][2]) / 2 < cfg.regions.frame_width / 2
