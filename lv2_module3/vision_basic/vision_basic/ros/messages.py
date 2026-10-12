"""
FrameResult -> ROS 메시지 변환.

/target (PointStamped) : x = ex, y = ey, z = 면적비. 미검출이면 (0, 0, 0)  (모듈 5 인터페이스와 같은 규약)
/detections (String)   : 같은 프레임의 후보·탈락 사유·적용 설정을 담은 JSON (실험 비교용)
"""
import json

from geometry_msgs.msg import PointStamped
from std_msgs.msg import Header, String

from vision_basic.domain.config import VisionConfig
from vision_basic.domain.model import Candidate, FrameResult


def target_msg(header: Header, res: FrameResult) -> PointStamped:
    msg = PointStamped()
    msg.header = header                   # 원본 영상의 stamp·frame_id를 그대로 쓴다
    if res.target is not None:
        msg.point.x, msg.point.y, msg.point.z = res.target.ex, res.target.ey, res.target.area_ratio
    return msg


def _cand(c: Candidate) -> dict:
    return {'index': c.index, 'area_px': round(c.area_px, 1),
            'cx': round(c.cx, 1), 'cy': round(c.cy, 1), 'bbox': list(c.bbox)}


def detection_dict(header: Header, seq: int, encoding: str, res: FrameResult,
                   cfg: VisionConfig, config_rev: int) -> dict:
    target = None
    if res.target is not None:
        t = res.target
        target = dict(_cand(t.candidate), ex=round(t.ex, 4), ey=round(t.ey, 4),
                      area_ratio=round(t.area_ratio, 5))
    return {
        'stamp': {'sec': header.stamp.sec, 'nanosec': header.stamp.nanosec},
        'frame_id': header.frame_id,
        'seq': seq,
        'width': res.width,
        'height': res.height,
        'encoding': encoding,
        'config_rev': config_rev,
        'config': cfg.summary(),
        'mask_pixels': res.mask_pixels,
        'contours_total': res.contours_total,
        'passed': [_cand(c) for c in res.passed],
        'rejected': [dict(_cand(r.candidate), reason=r.reason) for r in res.rejected],
        'detected': res.detected,
        'target': target,
    }


def detection_msg(header: Header, seq: int, encoding: str, res: FrameResult,
                  cfg: VisionConfig, config_rev: int) -> String:
    d = detection_dict(header, seq, encoding, res, cfg, config_rev)
    return String(data=json.dumps(d, ensure_ascii=False))
