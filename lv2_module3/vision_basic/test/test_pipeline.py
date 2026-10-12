"""순수 처리 계층 시험 (ROS 없이 합성 영상으로)."""
import cv2
import numpy as np
import pytest

from vision_basic.domain.config import (CandidateConfig, ConfigError, MaskConfig,
                                        SelectionConfig, VisionConfig)
from vision_basic.pipeline.candidates import extract_candidates, filter_candidates
from vision_basic.pipeline.detector import Detector
from vision_basic.pipeline.mask import build_mask, to_hsv
from vision_basic.pipeline.overlay import render_overlay
from vision_basic.pipeline.selection import select_target

W, H = 640, 480
BLUE_HSV = (105, 200, 150)                # 기준 범위 [102,120,40]~[110,255,255] 안
PALE_BLUE_HSV = (105, 80, 150)            # S 80: S 하한 120에서는 빠지고 60에서는 남음


def hsv_to_bgr(hsv):
    px = np.uint8([[hsv]])
    return tuple(int(v) for v in cv2.cvtColor(px, cv2.COLOR_HSV2BGR)[0, 0])


def scene(rects):
    """회색 배경 위 (x, y, w, h, hsv) 사각형들. BGR 영상."""
    img = np.full((H, W, 3), 90, np.uint8)
    for x, y, w, h, hsv in rects:
        cv2.rectangle(img, (x, y), (x + w - 1, y + h - 1), hsv_to_bgr(hsv), -1)
    return img


def test_to_hsv_respects_encoding():
    bgr = scene([(0, 0, W, H, BLUE_HSV)])
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    assert to_hsv(bgr, 'bgr8')[0, 0, 0] == to_hsv(rgb, 'rgb8')[0, 0, 0]
    assert abs(int(to_hsv(rgb, 'bgr8')[0, 0, 0]) - 105) > 30   # 순서를 틀리면 색이 바뀐다
    with pytest.raises(ValueError):
        to_hsv(bgr, 'mono8')


def test_s_lower_bound_changes_mask():
    hsv = to_hsv(scene([(50, 50, 60, 60, BLUE_HSV), (300, 50, 60, 60, PALE_BLUE_HSV)]), 'bgr8')
    strict = build_mask(hsv, MaskConfig(hsv_lower=(102, 120, 40)))
    loose = build_mask(hsv, MaskConfig(hsv_lower=(102, 60, 40)))
    assert strict[80, 80] == 255 and strict[80, 330] == 0
    assert loose[80, 80] == 255 and loose[80, 330] == 255


def test_morph_open_removes_speckle():
    hsv = to_hsv(scene([(100, 100, 2, 2, BLUE_HSV), (300, 100, 50, 50, BLUE_HSV)]), 'bgr8')
    assert build_mask(hsv, MaskConfig(morph_kernel=1))[100, 100] == 255
    assert build_mask(hsv, MaskConfig(morph_kernel=5))[100, 100] == 0


def test_min_area_filters_candidates_not_mask():
    img = scene([(50, 50, 60, 60, BLUE_HSV), (300, 300, 12, 12, BLUE_HSV)])
    a = Detector(VisionConfig(candidate=CandidateConfig(min_area_px=100)))
    b = Detector(VisionConfig(candidate=CandidateConfig(min_area_px=600)))
    ra, rb = a.process(img, 'bgr8'), b.process(img, 'bgr8')
    assert np.array_equal(ra.mask, rb.mask)                     # Mask는 같고
    assert (len(ra.passed), len(ra.rejected)) == (2, 0)         # 후보만 달라진다
    assert (len(rb.passed), len(rb.rejected)) == (1, 1)
    assert 'min_area_px 600' in rb.rejected[0].reason


def test_filter_boundary_is_inclusive():
    hsv = to_hsv(scene([(50, 50, 11, 11, BLUE_HSV)]), 'bgr8')
    cands = extract_candidates(build_mask(hsv, MaskConfig(morph_kernel=1)))
    area = cands[0].area_px                                     # contourArea는 꼭짓점 기준이라 10x10=100
    assert filter_candidates(cands, CandidateConfig(min_area_px=area))[0]
    assert not filter_candidates(cands, CandidateConfig(min_area_px=area + 0.1))[0]


def test_target_center_and_normalized_error():
    res = Detector(VisionConfig()).process(scene([(470, 190, 101, 101, BLUE_HSV)]), 'bgr8')
    t = res.target
    assert res.detected and t is not None
    assert t.candidate.cx == pytest.approx(520, abs=0.5)
    assert t.ex == pytest.approx((520 - 320) / 320, abs=0.01)
    assert t.ey == pytest.approx(0.0, abs=0.01)
    assert t.area_ratio == pytest.approx(t.candidate.area_px / (W * H))


def test_no_target_scene():
    res = Detector(VisionConfig()).process(scene([]), 'bgr8')
    assert not res.detected and res.mask_pixels == 0 and res.contours_total == 0


def test_selection_modes():
    img = scene([(10, 10, 52, 52, BLUE_HSV), (300, 220, 50, 50, BLUE_HSV)])
    hsv = to_hsv(img, 'bgr8')
    cands = extract_candidates(build_mask(hsv, MaskConfig()))
    largest = select_target(cands, SelectionConfig('largest'), W, H)
    centered = select_target(cands, SelectionConfig('priority'), W, H)
    assert largest is not None and largest.cx < 100
    assert centered is not None and centered.cx > 300


@pytest.mark.parametrize('cfg', [
    VisionConfig(mask=MaskConfig(hsv_lower=(120, 0, 0), hsv_upper=(110, 255, 255))),
    VisionConfig(mask=MaskConfig(hsv_upper=(180, 255, 255))),
    VisionConfig(candidate=CandidateConfig(min_area_px=-1)),
    VisionConfig(selection=SelectionConfig('lock')),
])
def test_invalid_config_rejected_and_previous_kept(cfg):
    det = Detector(VisionConfig())
    with pytest.raises(ConfigError):
        det.reconfigure(cfg)
    assert det.config == VisionConfig()


def test_overlay_keeps_size():
    img = scene([(50, 50, 60, 60, BLUE_HSV)])
    cfg = VisionConfig()
    out = render_overlay(img, Detector(cfg).process(img, 'bgr8'), cfg)
    assert out.shape == img.shape and not np.array_equal(out, img)
