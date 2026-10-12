"""Raw Image -> HSV -> inRange -> 잡음 제거 (실험 1이 바꾸는 단계)."""
import cv2
import numpy as np

from vision_basic.domain.config import MaskConfig

SUPPORTED_ENCODINGS = ('rgb8', 'bgr8')


def to_hsv(image: np.ndarray, encoding: str) -> np.ndarray:
    """rgb8 / bgr8 영상을 HSV로 바꾼다. 인코딩을 확인하지 않으면 빨강·파랑이 뒤바뀐다."""
    if encoding == 'rgb8':
        return cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    if encoding == 'bgr8':
        return cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    raise ValueError(f'지원하지 않는 컬러 인코딩: {encoding} (지원: {SUPPORTED_ENCODINGS})')


def build_mask(hsv: np.ndarray, cfg: MaskConfig) -> np.ndarray:
    """세 채널 모두 lower <= 값 <= upper 인 픽셀만 255 (cv2.inRange는 양 끝 포함)."""
    mask = cv2.inRange(hsv, np.array(cfg.hsv_lower, np.uint8), np.array(cfg.hsv_upper, np.uint8))
    if cfg.morph_kernel > 1:
        ks = cfg.morph_kernel | 1         # 짝수 커널은 중심이 없어 마스크가 한쪽으로 밀린다
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ks, ks))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)    # 작은 점 잡음 제거
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)   # 물체 안의 작은 구멍 메우기
    return mask
