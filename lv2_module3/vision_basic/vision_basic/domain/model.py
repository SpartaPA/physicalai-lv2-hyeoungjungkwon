"""한 프레임 처리 결과 모델 (ROS 메시지 형식과 분리)."""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

BBox = Tuple[int, int, int, int]          # x, y, w, h [px]


@dataclass
class Candidate:
    """Mask의 외곽 Contour 하나."""

    index: int                            # 프레임 안 Contour 번호 (면적 큰 순)
    area_px: float                        # cv2.contourArea [px^2]
    cx: float                             # moments 중심 [px]
    cy: float
    bbox: BBox
    contour: np.ndarray = field(repr=False)


@dataclass
class Rejection:

    candidate: Candidate
    reason: str                           # 예: 'area 42.0 < min_area_px 100.0'


@dataclass
class Target:
    """선택된 목표. ex·ey는 영상 중심 기준 정규화 오차 (오른쪽·아래 +, -1~1)."""

    candidate: Candidate
    ex: float
    ey: float
    area_ratio: float                     # contour 면적 / (W x H)


@dataclass
class FrameResult:

    width: int
    height: int
    mask: np.ndarray = field(repr=False)  # mono8, 0 = 배경, 255 = 전경(HSV 범위 안 + 잡음 제거 후)
    mask_pixels: int                      # 전경 픽셀 수
    contours_total: int                   # 필터 전 Contour 수
    passed: List[Candidate] = field(default_factory=list)
    rejected: List[Rejection] = field(default_factory=list)
    target: Optional[Target] = None

    @property
    def detected(self) -> bool:
        return self.target is not None
