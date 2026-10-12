"""Mask -> Contour 후보 -> 면적 필터 (실험 2가 바꾸는 단계). Mask 자체는 바꾸지 않는다."""
from typing import List, Tuple

import cv2
import numpy as np

from vision_basic.domain.config import CandidateConfig
from vision_basic.domain.model import Candidate, Rejection


def extract_candidates(mask: np.ndarray) -> List[Candidate]:
    """외곽 Contour 전부를 면적 큰 순으로 돌려준다 (필터 전)."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    items = []
    for c in contours:
        area = float(cv2.contourArea(c))
        m = cv2.moments(c)
        x, y, w, h = cv2.boundingRect(c)
        if m['m00'] > 0:
            cx, cy = m['m10'] / m['m00'], m['m01'] / m['m00']
        else:                             # 선·점 모양 Contour: 면적 0이라 어차피 필터에서 탈락
            cx, cy = x + w / 2, y + h / 2
        items.append((area, cx, cy, (x, y, w, h), c))
    items.sort(key=lambda t: t[0], reverse=True)
    return [Candidate(i, a, cx, cy, bb, c) for i, (a, cx, cy, bb, c) in enumerate(items)]


def filter_candidates(
        cands: List[Candidate], cfg: CandidateConfig) -> Tuple[List[Candidate], List[Rejection]]:
    """면적(cv2.contourArea) < min_area_px 이면 탈락. 탈락 후보도 사유와 함께 돌려줘 결과 토픽에 남긴다."""
    passed, rejected = [], []
    for c in cands:
        if c.area_px < cfg.min_area_px:
            reason = f'area {c.area_px:.1f} < min_area_px {cfg.min_area_px:g}'
            rejected.append(Rejection(c, reason))
        else:
            passed.append(c)
    return passed, rejected
