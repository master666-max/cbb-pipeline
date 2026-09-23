# -*- coding: utf-8 -*-
"""捕获再捕获.py — 双独立复查的残余缺陷估计（U-F 评审线·Chapman 估计量·2026-09-24）

用途：两个**独立**复查者各查同一批样本（n1=n2=40~60 条），统计双方共同查出的缺陷数 m，
      估计"还有多少缺陷没被发现"（N̂ ≈ 残余总量）。Chapman 估计量小样本偏差校正首选。
      独立性是命门：两人共用同一份抽取规范/上下文包 → 正相关 → N̂ **严重低估**。

出处：Chapman (1951)；R `Rcapture::closedp` 族；软件检查实证 Briand+2000 (IEEE TSE,
      DOI 10.1109/32.852741)、Petersson+2004 (JSS, DOI 10.1016/S0164-1212(03)00090-6)。
"""
from __future__ import annotations

import math


def chapman(n1: int, n2: int, m: int) -> dict:
    """双复查者捕获-再捕获。n1/n2=各自查出的缺陷条数（样本内），m=双方共同查出数。
    返回 {N_hat, sd, ci95, residual, 口径}。"""
    if n1 <= 0 or n2 <= 0:
        raise ValueError("n1/n2 必须为正（各自查出的缺陷数）")
    if m > min(n1, n2):
        raise ValueError(f"共同缺陷 m={m} 不能超过各自查出数 min({n1},{n2})")
    n_hat = (n1 + 1) * (n2 + 1) / (m + 1) - 1
    var = (n1 + 1) * (n2 + 1) * (n1 - m) * (n2 - m) / ((m + 1) ** 2 * (m + 2))
    sd = math.sqrt(max(var, 0.0))
    z = 1.96
    ci = (max(0.0, n_hat - z * sd), n_hat + z * sd)
    return {"N_hat": round(n_hat, 1), "sd": round(sd, 1),
            "ci95": (round(ci[0], 1), round(ci[1], 1)),
            "residual": round(max(n_hat - max(n1, n2), 0.0), 1),
            "口径": f"Chapman 估计量；n1={n1},n2={n2},m={m}；独立性是命门——共用规范/上下文包会低估"}


def agreement(a: set, b: set) -> dict:
    """两名复查者对同批样本的判定一致性（粗糙度检查：错误类型分布是否雷同）。"""
    inter, union = a & b, a | b
    jaccard = len(inter) / len(union) if union else 1.0
    return {"jaccard": round(jaccard, 3), "仅甲": len(a - b), "仅乙": len(b - a), "共同": len(inter),
            "口径": "jaccard 过高（如 >0.8）→ 两复查者不独立，N̂ 不可信"}


def batch_report(reviews: list[dict], sample_size: int) -> dict:
    """汇总多轮双复查：每轮 {n1, n2, m, note}。返回各轮估计＋平均残余。"""
    out = []
    for i, r0 in enumerate(reviews, 1):
        try:
            out.append({"轮": i, **chapman(r0["n1"], r0["n2"], r0["m"])})
        except ValueError as e:
            out.append({"轮": i, "error": str(e)})
    valid = [o for o in out if "N_hat" in o]
    avg = round(sum(o["N_hat"] for o in valid) / len(valid), 1) if valid else None
    return {"rounds": out, "avg_N_hat": avg, "sample_size": sample_size,
            "口径": "每轮样本量应固定（batch_report 的 sample_size）；轮间波动大→先查独立性"}
