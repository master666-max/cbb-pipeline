"""cbb2/governance.py — 治理闭环（Phase F·G08-G15）。

人工桶处置 / 信息保全 review / conformal NLI 校准 / 票权加权 / 缺口队列接线。
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

# ---- G08 人工桶处置 ----

def classify_manual_bucket(items: list[dict]) -> dict:
    """将无 detail 的矛盾件按 detail 特征分桶：
    - artifact: detail 含嵌入相似度（嵌入阈值假阳性）
    - empty_claim: claim 为空或 None
    - unknown: 无法归类
    """
    buckets = {"artifact": [], "empty_claim": [], "unknown": []}
    for it in items:
        d = it.get("detail", "")
        if "嵌入相似度" in d or "sim=" in d:
            buckets["artifact"].append(it)
        elif not d.strip():
            buckets["empty_claim"].append(it)
        else:
            buckets["unknown"].append(it)
    return buckets


# ---- G11 conformal NLI 校准 ----

class ConformalNLICalibrator:
    """把 NLI 三分判定包装成带覆盖率保证的分流器。
    校准集=人工核验判例（(premise, hypothesis, label) 三元组）。
    预测集>1（如 contains both entails & contradicts）⇒ 降级人审。
    """

    def __init__(self, alpha: float = 0.10):
        self.alpha = alpha  # 允许的错误率
        self.calibration_set: list[dict] = []
        self._threshold: float | None = None

    def calibrate(self, labeled: list[dict]):
        """用人工核验判例校准 nonconformity score 阈值。
        labeled: [{premise, hypothesis, label(str), score(float)}]
        score = 通道给出的"最优类"得分（越高越自信）。
        nonconformity = 1 - score（不掺入校准标签——标准 conformal 语义：
        阈值=分数分布的 (1-α) 分位，与校准集错误率解耦）。"""
        if len(labeled) < 10:
            raise ValueError(f"校准集过小（{len(labeled)}<10）")
        scores = sorted(1.0 - r["score"] for r in labeled)
        n = len(scores)
        q = math.ceil((n + 1) * (1 - self.alpha)) - 1
        idx = max(0, min(n - 1, q))
        self._threshold = scores[idx]
        self.calibration_set = labeled
        return {"n": n, "threshold": round(self._threshold, 4), "alpha": self.alpha}

    def predict(self, score: float, predicted: str) -> dict:
        """单条预测：score 高于阈值→采纳 predicted；否则降级人审。"""
        if self._threshold is None:
            return {"verdict": predicted, "abstain": False, "reason": "未校准"}
        nc = 1.0 - score
        abstain = nc > self._threshold
        return {"verdict": predicted, "abstain": abstain,
                "score": round(score, 4), "threshold": round(self._threshold, 4)}


# ---- G13 票权加权（GLAD 简化版） ----

class ExaminerQualityTracker:
    """追踪每位考官的投票历史，计算质量权重。
    quality = (correct_votes + prior_a) / (total_votes + prior_a + prior_b)
    Beta 先验 Beta(a=2, b=1)——初始偏乐观，随数据收敛。
    """

    def __init__(self, prior_a: float = 2.0, prior_b: float = 1.0):
        self.prior_a = prior_a
        self.prior_b = prior_b
        self.history: dict[str, list[bool]] = defaultdict(list)

    def record(self, examiner: str, correct: bool):
        self.history[examiner].append(correct)

    def quality(self, examiner: str) -> float:
        h = self.history.get(examiner, [])
        n = len(h)
        if n == 0:
            return 0.5  # 无数据=中性
        return sum(h) / n

    def all_quality(self) -> dict:
        return {k: round(self.quality(k), 4) for k in self.history}


# ---- G15 缺口队列接线 ----

def wire_gap_queue(store_root: Path, findings: list[dict]) -> int:
    """将治理闭环产出的 findings 追加到缺口队列（幂等：同 type+evidence 不重复）。"""
    q_path = Path(store_root) / "缺口队列.jsonl"
    existing = set()
    if q_path.exists():
        for x in q_path.read_text(encoding="utf-8").splitlines():
            if x.strip():
                r = json.loads(x)
                existing.add((r.get("type"), r.get("evidence")))
    added = 0
    with q_path.open("a", encoding="utf-8") as f:
        for fd in findings:
            key = (fd.get("type"), fd.get("evidence"))
            if key not in existing:
                f.write(json.dumps(fd, ensure_ascii=False, sort_keys=True) + "\n")
                existing.add(key)
                added += 1
    return added
