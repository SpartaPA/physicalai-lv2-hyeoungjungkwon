"""검출 결과 Overlay 이미지 (토픽으로 발행해 이미지 뷰어에서 확인)."""
import cv2
import numpy as np

from vision_basic.domain.config import VisionConfig
from vision_basic.domain.model import FrameResult

GRAY = (128, 128, 128)                    # 면적 필터 탈락
ORANGE = (0, 165, 255)                    # 통과 후보
GREEN = (0, 255, 0)                       # 선택된 목표
RED = (0, 0, 255)
WHITE = (255, 255, 255)
FONT = cv2.FONT_HERSHEY_SIMPLEX


def _label(img: np.ndarray, text: str, org, color) -> None:
    cv2.putText(img, text, org, FONT, 0.4, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, org, FONT, 0.4, color, 1, cv2.LINE_AA)


def render_overlay(image_bgr: np.ndarray, res: FrameResult, cfg: VisionConfig) -> np.ndarray:
    out = image_bgr.copy()
    w, h = res.width, res.height
    for r in res.rejected:
        c = r.candidate
        cv2.drawContours(out, [c.contour], -1, GRAY, 1)
        _label(out, f'#{c.index} {c.area_px:.0f}', (int(c.cx) + 4, int(c.cy)), GRAY)
    for c in res.passed:
        cv2.drawContours(out, [c.contour], -1, ORANGE, 1)
        _label(out, f'#{c.index} {c.area_px:.0f}', (int(c.cx) + 4, int(c.cy)), ORANGE)
    cv2.drawMarker(out, (w // 2, h // 2), WHITE, cv2.MARKER_CROSS, 24, 1)   # 영상 중심
    if res.target is not None:
        t = res.target
        x, y, bw, bh = t.candidate.bbox
        cv2.rectangle(out, (x, y), (x + bw, y + bh), GREEN, 2)
        p = (int(round(t.candidate.cx)), int(round(t.candidate.cy)))
        cv2.drawMarker(out, p, RED, cv2.MARKER_TILTED_CROSS, 16, 2)
        cv2.line(out, (w // 2, h // 2), p, RED, 1)
        status = (f'TARGET #{t.candidate.index} ex {t.ex:+.3f} ey {t.ey:+.3f}'
                  f' area {t.area_ratio:.4f}')
    else:
        status = 'NO TARGET'
    s = cfg.summary()
    lines = [
        status,
        f'contours {res.contours_total}  passed {len(res.passed)}  rejected {len(res.rejected)}'
        f'  mask_px {res.mask_pixels}',
        f'hsv {s["hsv_lower"]}~{s["hsv_upper"]}  kernel {s["morph_kernel"]}'
        f'  min_area {s["min_area_px"]:g}  sel {s["selection"]}',
    ]
    cv2.rectangle(out, (0, 0), (w, 18 * len(lines) + 4), (0, 0, 0), -1)
    for i, text in enumerate(lines):
        cv2.putText(out, text, (6, 16 + 18 * i), FONT, 0.45, WHITE, 1, cv2.LINE_AA)
    return out
