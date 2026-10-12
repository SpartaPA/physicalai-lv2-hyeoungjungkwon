"""
ROS 2 파라미터 <-> VisionConfig 변환.

파라미터 이름은 config/vision.yaml과 같다. 노드 시작 때 읽고(--params-file),
실행 중 `ros2 param set` 으로 바꾼 값도 검증한 뒤 다음 프레임부터 적용한다.
"""
from typing import Any, Dict, Iterable

from rcl_interfaces.msg import ParameterDescriptor
from rclpy.node import Node
from rclpy.parameter import Parameter

from vision_basic.domain.config import (CandidateConfig, ConfigError, Hsv, MaskConfig,
                                        SelectionConfig, VisionConfig)

DEFAULTS = VisionConfig()

DETECTION_PARAMS: Dict[str, Any] = {
    'hsv_lower': list(DEFAULTS.mask.hsv_lower),
    'hsv_upper': list(DEFAULTS.mask.hsv_upper),
    'morph_kernel': DEFAULTS.mask.morph_kernel,
    'min_area_px': DEFAULTS.candidate.min_area_px,
    'selection': DEFAULTS.selection.mode,
    'similar_area_ratio': DEFAULTS.selection.similar_area_ratio,
}

DESCRIPTIONS = {
    'hsv_lower': 'inRange 하한 [H, S, V] (H 0~179, S·V 0~255) - Mask 단계',
    'hsv_upper': 'inRange 상한 [H, S, V] - Mask 단계',
    'morph_kernel': 'open·close 커널 크기 [px], 1 이하면 잡음 제거 안 함 - Mask 단계',
    'min_area_px': 'Contour 최소 면적 [px^2] - 후보 필터 단계 (Mask는 그대로)',
    'selection': 'largest | priority - 목표 선택 단계',
    'similar_area_ratio': 'priority에서 크기 비슷 기준 (0~1)',
}


def declare_detection_params(node: Node) -> None:
    for name, default in DETECTION_PARAMS.items():
        node.declare_parameter(name, default, ParameterDescriptor(description=DESCRIPTIONS[name]))


def _hsv(v: Any) -> Hsv:
    h, s, val = (int(x) for x in v)          # 3개가 아니면 ValueError
    return h, s, val


def _to_config(values: Dict[str, Any]) -> VisionConfig:
    try:
        return VisionConfig(
            mask=MaskConfig(hsv_lower=_hsv(values['hsv_lower']),
                            hsv_upper=_hsv(values['hsv_upper']),
                            morph_kernel=int(values['morph_kernel'])),
            candidate=CandidateConfig(min_area_px=float(values['min_area_px'])),
            selection=SelectionConfig(mode=str(values['selection']),
                                      similar_area_ratio=float(values['similar_area_ratio'])),
        ).validate()
    except (TypeError, ValueError) as e:
        if isinstance(e, ConfigError):
            raise
        raise ConfigError(str(e)) from e


def read_config(node: Node) -> VisionConfig:
    return _to_config({n: node.get_parameter(n).value for n in DETECTION_PARAMS})


def config_with_changes(node: Node, changes: Iterable[Parameter]) -> VisionConfig:
    """현재 파라미터에 변경분을 덮어쓴 설정 (검증 실패 시 ConfigError)."""
    values = {n: node.get_parameter(n).value for n in DETECTION_PARAMS}
    for p in changes:
        if p.name in values:
            values[p.name] = p.value
    return _to_config(values)
