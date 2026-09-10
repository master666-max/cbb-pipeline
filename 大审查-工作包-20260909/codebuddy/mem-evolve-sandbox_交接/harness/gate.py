"""两级门控 + Pareto 档案 + 锚定审计（实验报告 §5.2 的可运行形态）。

门控契约（红线 6/7/10/13/15）：
  - 廉价筛选：只能返回 reject / unknown，**类型上**不允许返回 accept（E13）
  - 档案准入：宽松（Δ > -tolerance）
  - 主线晋升：严格（配对比较 + 留出集 + bootstrap 95% 下界 > max(0, margin)）
  - margin 冻结在元层，系统不可演化（E24）
"""
from __future__ import annotations

import os
import random

TOLERANCE = 0.05      # 档案准入容忍度（报告 E55：0.02–0.06 折中；取上界以容纳跨越低谷所需的中性态）
MARGIN = 0.01         # 元层冻结（红线 13/15）
# 报告 E34 的教训：阈值必须先标定再用。0.85 在其实验里零误报，但换一个世界/换一种
# 锚定样本构造后，实测 α=0（无漂移）下 11/12 **误报**并冻结演化，净损失 Δ=0.127。
# 因此阈值改为"人侧标定产物"：由 run.py calibrate 在零漂移基线上测出，可用环境变量覆盖。
ANCHOR_THRESHOLD = float(os.environ.get("ANCHOR_THRESHOLD", "0.85"))
BOOTSTRAP_N = 1000


def boot_ci_lower(diffs, rng: random.Random, n=BOOTSTRAP_N, alpha=0.05):
    """配对差的 bootstrap 置信下界。报告 E17：优于置换检验（同假阳下检出 2×）。"""
    if not diffs:
        return 0.0, 0.0
    k = len(diffs)
    samples = []
    for _ in range(n):
        samples.append(sum(diffs[rng.randrange(k)] for _ in range(k)) / k)
    samples.sort()
    lo = samples[int(alpha * n)]
    return lo, sum(diffs) / k


def cheap_filter(cand: dict) -> str:
    """廉价筛选：只 reject，不 accept。返回 'reject' | 'unknown'。"""
    # 只用 O(1) 静态判据，不用评估；故意保守——宁可 unknown 也不 accept（E13 类型级约束）
    if cand["w_kw"] == 0 and cand["w_content"] == 0:
        return "reject"          # 打分恒等于重要性项：检索退化
    if cand["hot_budget"] < 20:
        return "reject"
    return "unknown"


def admit(archive_delta: float) -> bool:
    """档案准入：宽松。"""
    return archive_delta > -TOLERANCE


def promote(challenger_scores, champion_scores, rng, margin=MARGIN) -> dict:
    """主线晋升：严格。scores = 每个任务上的标量效用。

    判据必须写成 `下界 > max(0, margin)` —— 否则 margin 为负时判据被架空（红线 15）。
    """
    diffs = [a - b for a, b in zip(challenger_scores, champion_scores)]
    lo, mean = boot_ci_lower(diffs, rng)
    return {"lower": lo, "mean": mean,
            "passed": lo > max(0.0, margin), "n_tasks": len(diffs)}


class Archive:
    """开放式档案（E11/E16/E7）。

    两个容器，职责不同，混用会直接导致 E7 复现失败：
      front —— Pareto 前沿，用于**报告**与多样性度量；
      pool  —— 所有通过宽松准入的候选，是**变异取样池**。
    只保留 front 会把"比当前冠军略差的中性/退化中间态"全部支配掉，
    于是"先变差再变好"的路径在结构上不可达（实测 0/12 逃出局部最优）。
    DGM 的"开放式"意义正在于此。
    """

    def __init__(self, cap=60, keep_front=20, mode="pareto"):
        self.cap = cap
        self.keep_front = keep_front
        self.mode = mode                      # pareto | single
        self.front = []
        self.pool = []

    def _dominates(self, a, b):
        return (a["u"] >= b["u"] and a["cost"] <= b["cost"]
                and (a["u"] > b["u"] or a["cost"] < b["cost"]))

    def add(self, genome, u, cost, gen, rng):
        rec = {"genome": genome, "u": u, "cost": cost, "gen": gen}
        if self.mode == "single":
            # 只有更优才替换。无条件把 pool 设成最新候选会让"无档案"退化成
            # "末位候选档案"——仍然能跨越低谷，于是消融测不出档案的贡献（实测 11/12 vs 10/12）。
            if not self.front or u > self.front[0]["u"]:
                self.front = [rec]
                self.pool = [rec]
            return
        self.pool.append(rec)
        if not any(self._dominates(o, rec) for o in self.front):
            self.front = [o for o in self.front if not self._dominates(rec, o)]
            self.front.append(rec)
        if len(self.pool) > self.cap:
            self.front.sort(key=lambda r: (-r["u"], r["cost"]))
            keep = self.front[:self.keep_front]
            rest = [r for r in self.pool if r not in keep]
            rng.shuffle(rest)
            self.pool = keep + rest[:max(0, self.cap - len(keep))]

    def sample_parent(self, rng):
        """变异父本：前沿优先，但保留从池中随机取样的通道。"""
        if not self.pool:
            return None
        if self.front and rng.random() < 0.5:
            top = sorted(self.front, key=lambda r: -r["u"])[:5]
            return rng.choice(top)["genome"]
        return rng.choice(self.pool)["genome"]

    def best(self, rng):
        if not self.pool and not self.front:
            return None
        src = self.front or self.pool
        return max(src, key=lambda r: r["u"])

    def front_size(self):
        return len(self.front)

    def pool_size(self):
        return len(self.pool)

    def max_u(self):
        return max((r["u"] for r in self.pool), default=0.0)


class AnchorSet:
    """锚定集（E14/E14c）：系统启用前采集，永不衰减，系统不可触碰。

    samples = [(g_a, g_b, label)]，label 是**启用前**用初心权重 W0 标注的成对比较结果。
    审计时用当前（可能已漂移的）尺子对同一批对做预测，一致率跌破阈值即判漂移。
    """

    def __init__(self, samples):
        self.samples = samples

    def agreement(self, score) -> float:
        """score(g) -> float，用当前尺子给基因组打分；返回与 W0 标注的一致率。"""
        if not self.samples:
            return 1.0
        hit = 0
        for ga, gb, lab in self.samples:
            pred = 1 if score(ga) > score(gb) else 0
            hit += int(pred == lab)
        return hit / len(self.samples)

    def drifted(self, score):
        a = self.agreement(score)
        return a < ANCHOR_THRESHOLD, a


class StallMonitor:
    """停摆监控器（E44）：连续 N 代零采纳 → margin 减半，防 margin 过大导致饿死。"""

    def __init__(self, patience=5):
        self.patience = patience
        self.stall = 0
        self.margin = MARGIN

    def step(self, adopted: bool):
        if adopted:
            self.stall = 0
        else:
            self.stall += 1
        if self.stall >= self.patience:
            self.margin = max(self.margin / 2.0, 1e-4)
            self.stall = 0
            return True
        return False
