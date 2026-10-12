"""
검출 설정 값 객체 (ROS·OpenCV에 의존하지 않음).

설정은 처리 단계별로 나눈다. 실험 1(Mask 생성)과 실험 2(후보 필터)가 서로 다른 단계의 값을
바꾼다는 것이 코드 구조에서 바로 드러나도록 한다.

  MaskConfig      : Raw Image -> HSV -> inRange -> open·close  (Mask 토픽에 반영)
  CandidateConfig : Mask -> Contour -> 면적 필터               (Mask는 그대로, 후보만 달라짐)
  SelectionConfig : 통과 후보 중 목표 하나 선택
"""
from dataclasses import dataclass, field, replace
from typing import Tuple

Hsv = Tuple[int, int, int]

# OpenCV 8bit HSV 범위: H 0~179, S·V 0~255
HSV_MAX: Hsv = (179, 255, 255)
SELECTION_MODES = ('largest', 'priority')


class ConfigError(ValueError):
    """설정 값이 유효 범위를 벗어남."""


@dataclass(frozen=True)
class MaskConfig:

    hsv_lower: Hsv = (102, 120, 40)
    hsv_upper: Hsv = (110, 255, 255)
    morph_kernel: int = 5                 # [px] open -> close 커널 크기. 1 이하면 잡음 제거 안 함

    def validate(self) -> None:
        for name, v in (('hsv_lower', self.hsv_lower), ('hsv_upper', self.hsv_upper)):
            if len(v) != 3:
                raise ConfigError(f'{name}는 [H, S, V] 3개 값이어야 합니다: {v}')
            for x, hi, ch in zip(v, HSV_MAX, 'HSV'):
                if not 0 <= x <= hi:
                    raise ConfigError(f'{name} {ch}={x} 가 0~{hi} 범위 밖입니다')
        for lo, hi, ch in zip(self.hsv_lower, self.hsv_upper, 'HSV'):
            if lo > hi:
                raise ConfigError(f'{ch} 하한 {lo} > 상한 {hi} (빨강처럼 H가 0을 넘는 범위는 지원 안 함)')
        if self.morph_kernel < 0:
            raise ConfigError(f'morph_kernel={self.morph_kernel} 는 0 이상이어야 합니다')


@dataclass(frozen=True)
class CandidateConfig:

    min_area_px: float = 100.0            # [px^2] cv2.contourArea 가 이 값보다 작으면 탈락

    def validate(self) -> None:
        if self.min_area_px < 0:
            raise ConfigError(f'min_area_px={self.min_area_px} 는 0 이상이어야 합니다')


@dataclass(frozen=True)
class SelectionConfig:

    mode: str = 'largest'                 # largest | priority(면적 비슷하면 화면 중앙)
    similar_area_ratio: float = 0.2       # priority: |a1-a2|/max <= 0.2 면 '크기 비슷'

    def validate(self) -> None:
        if self.mode not in SELECTION_MODES:
            raise ConfigError(f'selection={self.mode!r} 는 {SELECTION_MODES} 중 하나여야 합니다')
        if not 0.0 <= self.similar_area_ratio <= 1.0:
            raise ConfigError(f'similar_area_ratio={self.similar_area_ratio} 는 0~1 이어야 합니다')


@dataclass(frozen=True)
class VisionConfig:

    mask: MaskConfig = field(default_factory=MaskConfig)
    candidate: CandidateConfig = field(default_factory=CandidateConfig)
    selection: SelectionConfig = field(default_factory=SelectionConfig)

    def validate(self) -> 'VisionConfig':
        self.mask.validate()
        self.candidate.validate()
        self.selection.validate()
        return self

    def with_mask(self, **kw) -> 'VisionConfig':
        return replace(self, mask=replace(self.mask, **kw))

    def with_candidate(self, **kw) -> 'VisionConfig':
        return replace(self, candidate=replace(self.candidate, **kw))

    def summary(self) -> dict:
        """검출 결과 메시지·Overlay에 함께 남길 현재 적용값."""
        return {
            'hsv_lower': list(self.mask.hsv_lower),
            'hsv_upper': list(self.mask.hsv_upper),
            'morph_kernel': self.mask.morph_kernel,
            'min_area_px': self.candidate.min_area_px,
            'selection': self.selection.mode,
        }
