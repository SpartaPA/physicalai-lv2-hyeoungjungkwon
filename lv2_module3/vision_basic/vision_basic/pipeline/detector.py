"""Raw Image -> Mask -> 후보 -> 필터 -> 선택을 한 프레임 단위로 묶는다 (ROS 없이 시험 가능)."""
import cv2
import numpy as np

from vision_basic.domain.config import VisionConfig
from vision_basic.domain.model import FrameResult, Target
from vision_basic.pipeline.candidates import extract_candidates, filter_candidates
from vision_basic.pipeline.mask import build_mask, to_hsv
from vision_basic.pipeline.selection import select_target


class Detector:

    def __init__(self, config: VisionConfig) -> None:
        self._config = config.validate()

    @property
    def config(self) -> VisionConfig:
        return self._config

    def reconfigure(self, config: VisionConfig) -> None:
        """다음 프레임부터 새 설정을 쓴다. 유효하지 않으면 예외를 내고 기존 설정을 유지한다."""
        self._config = config.validate()

    def process(self, image: np.ndarray, encoding: str) -> FrameResult:
        cfg = self._config                # 한 프레임 처리 중에는 같은 설정을 쓴다
        h, w = image.shape[:2]
        mask = build_mask(to_hsv(image, encoding), cfg.mask)
        all_cands = extract_candidates(mask)
        passed, rejected = filter_candidates(all_cands, cfg.candidate)
        chosen = select_target(passed, cfg.selection, w, h)
        target = None
        if chosen is not None:
            target = Target(chosen,
                            ex=(chosen.cx - w / 2) / (w / 2),
                            ey=(chosen.cy - h / 2) / (h / 2),
                            area_ratio=chosen.area_px / (w * h))
        return FrameResult(w, h, mask, int(cv2.countNonZero(mask)), len(all_cands),
                           passed, rejected, target)
