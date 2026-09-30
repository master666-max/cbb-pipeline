"""cbb2.schedule.py — FSRS 重验证调度器（Phase F·G12；心理路 B3）。

confirmed 记录=Card，区段=时间轴，巡检=review（改判 Again/维持 Good）。
N=f(S,r) 由幂遗忘曲线反解：r(t)=DECAY^(t/S) → t=S·log(r)/log(DECAY)。
冷启动 N≈0.1-0.2×预期存续区段（Cepeda 律）。
可选依赖 py-fsrs（MIT）；缺席时降级为固定间隔模式。
"""
from __future__ import annotations

import json
import math
from pathlib import Path

DECAY = 0.5  # 半衰期衰减基：R(t) = DECAY^(t/S)
FACTOR = 19.0 / 81.0
TARGET_RETENTION = 0.90
COLD_START_RATIO = 0.15

STATE_FILE = "巡检调度.json"


def retrievability(stability: float, elapsed: float) -> float:
    """幂遗忘曲线：R(t)=DECAY^(t/S)"""
    if stability <= 0:
        return 0.0
    return math.pow(DECAY, elapsed / stability)


def solve_interval(stability: float, target_r: float = TARGET_RETENTION) -> int:
    """给定稳定度 S 和目标可提取率 r，反解下次巡检间隔 N（区段数）。
    R(t) = DECAY^(t/S) → t = S * log(r) / log(DECAY)"""
    if stability <= 0 or target_r <= 0 or target_r >= 1:
        return 1
    return max(1, round(stability * math.log(target_r) / math.log(DECAY)))


class ReviewScheduler:
    """FSRS 式重验证调度：confirmed 记录按区段间隔排巡检。"""

    def __init__(self, store_root: Path, target_r: float = TARGET_RETENTION):
        self.state_path = Path(store_root) / STATE_FILE
        self.target_r = target_r
        self.state: dict = {}
        if self.state_path.exists():
            self.state = json.loads(self.state_path.read_text(encoding="utf-8"))

    def _save(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.state, ensure_ascii=False, sort_keys=True, indent=1),
                                   encoding="utf-8")

    def schedule(self, record_id: str, tenure_segments: int, stability: float | None = None) -> dict:
        """登记一条 confirmed 记录的巡检计划。"""
        if stability is None:
            stability = max(1.0, tenure_segments * COLD_START_RATIO / 0.15)
        interval = solve_interval(stability, self.target_r)
        entry = {"record_id": record_id, "stability": stability,
                 "interval": interval, "last_checked": 0, "checks": 0}
        self.state[record_id] = entry
        self._save()
        return entry

    def record_check(self, record_id: str, passed: bool, segment: int) -> dict:
        """巡检后更新：通过→S 增长间隔拉长；失败→S 重置回密集区。"""
        e = self.state.get(record_id)
        if e is None:
            return {"error": "not found"}
        e["checks"] += 1
        e["last_checked"] = segment
        if passed:
            e["stability"] = e["stability"] * 1.3  # 增长因子
        else:
            e["stability"] = max(1.0, e["stability"] * 0.5)  # 衰减
            e["failed_at"] = segment
        e["interval"] = solve_interval(e["stability"], self.target_r)
        self._save()
        return e

    def due(self, current_segment: int) -> list[str]:
        """返回当前区段应巡检的记录 id 列表。"""
        return [rid for rid, e in self.state.items()
                if current_segment - e.get("last_checked", 0) >= e["interval"]]

    def stats(self) -> dict:
        total = len(self.state)
        due = len(self.due(999999))
        return {"total": total, "due_estimate": due,
                "target_r": self.target_r}


def fsrs_available() -> bool:
    try:
        import fsrs  # noqa: F401
        return True
    except ImportError:
        return False
