"""통과 후보 중 목표 하나를 고른다."""
from typing import List, Optional

from vision_basic.domain.config import SelectionConfig
from vision_basic.domain.model import Candidate


def _center_r2(c: Candidate, w: int, h: int) -> float:
    ex = (c.cx - w / 2) / (w / 2)
    ey = (c.cy - h / 2) / (h / 2)
    return ex * ex + ey * ey


def select_target(
        cands: List[Candidate], cfg: SelectionConfig, w: int, h: int) -> Optional[Candidate]:
    """
    목표 하나를 고른다.

    largest: 가장 큰 후보. priority: 가장 큰 것과 크기가 비슷한 후보 중 화면 중앙에 가까운 것.

    cands는 면적 큰 순으로 정렬돼 있어야 한다 (extract_candidates 결과 순서).
    """
    if not cands:
        return None
    if cfg.mode == 'largest':
        return cands[0]
    a_max = cands[0].area_px
    similar = [c for c in cands
               if a_max <= 0 or (a_max - c.area_px) / a_max <= cfg.similar_area_ratio]
    return min(similar, key=lambda c: _center_r2(c, w, h))
