# -*- coding: utf-8 -*-
"""cbb2.audit — 对样双轨 + Wilson 区间（Phase D·U-D05；流程设计 P5）。

发现轨=可疑优先排序（找错，通过率不可外推——Northcutt 模式）；
估计轨=分层随机抽样估计错误率，LQAS 可选（每层 n=19 只出合格/不合格）；
一切通过率宣称带 **Wilson 95% 区间**（30 全过→下限仅 ~86%，不许点宣称）。
"""
from __future__ import annotations

import math
import random
from collections import defaultdict


def wilson(passed: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 区间（通过率宣称的合规形态）。"""
    if n == 0:
        return (0.0, 1.0)
    p = passed / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def suspicious_rank(records: list[dict]) -> list[dict]:
    """发现轨：最可疑优先——确定性启发式（缺 verified_against/置信低/证据少/孤立引用）。"""
    def suspicion(r: dict) -> tuple:
        prov = r.get("provenance") or {}
        conf = prov.get("extractor_confidence", 100) or 0
        n_ev = len(r.get("evidence") or [])
        va = r.get("verified_against") or {}
        sha_ok = bool(va.get("sha")) and set(va.get("sha", "0")) != {"0"}
        return (n_ev, conf, 0 if sha_ok else -1, r.get("record_id", ""))
    return sorted(records, key=suspicion)


def stratified_sample(records: list[dict], stratum_key, n_per_stratum: int,
                      seed: int = 20260927) -> list[dict]:
    """估计轨：分层随机（同层内真随机，固定种子可复算）。"""
    strata: dict = defaultdict(list)
    for r in records:
        strata[stratum_key(r)].append(r)
    rng = random.Random(seed)
    out = []
    for key in sorted(strata):
        pool = strata[key][:]
        rng.shuffle(pool)
        out.extend(pool[:n_per_stratum])
    return out


def lqas(passed: int, n: int, p0: float = 0.95) -> dict:
    """LQAS 验收抽样：n 条里 passed ≤ 阈值 d ⇒ 批合格。d 按 p0 与 n 查表近似（二项下界）。"""
    if n == 0:
        return {"verdict": "no-data"}
    d = 0
    while d <= n:
        # P(失败数 ≤ d | 真实通过率 = p0) ≤ 0.05 的最大 d —— 二项累计
        prob = sum(math.comb(n, k) * (1 - p0) ** k * p0 ** (n - k) for k in range(0, d + 1))
        if prob > 0.05:
            break
        d += 1
    failures = n - passed
    threshold_d = max(0, d - 1)
    verdict = "accept" if failures <= threshold_d else "reject"
    return {"verdict": verdict, "threshold_d": threshold_d, "passed": passed, "n": n,
            "failures": failures}


def report(passed: int, n: int, gate: float = 0.95) -> dict:
    """合规宣称形态：点值 + Wilson 区间 + 门槛判定（区间下限达门槛才算 PASS）。"""
    lo, hi = wilson(passed, n)
    return {"passed": passed, "n": n,
            "rate": round(passed / n, 4) if n else 0.0,
            "wilson95": [round(lo, 4), round(hi, 4)],
            "gate": "PASS" if lo >= gate else "FAIL",
            "口径": "Wilson 95% 区间下限达门槛才算过——点宣称禁用（发现偏倚纪律）"}
