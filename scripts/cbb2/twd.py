# -*- coding: utf-8 -*-
"""cbb2.twd — G5 门三支决策（TWD）影子层（补充工单 20260928）。

DTRS（Yao 决策粗糙集）：由损失矩阵导 (α, β)，票型后验 p(θ+|votes) 由 Dawid-Skene
两态发射模型估计。影子模式：只记分不判票——线上 ⌈2/3⌉ 继续服役（工单第五节），
替换属仪器变更 v2.0，须先过植株考试与回放验收。

公式核对说明：α/β 由期望损失不等式直接推出——
  R(aP|x) = λ_PP·p + λ_PN·(1−p) ≤ R(aB|x) = λ_BP·p + λ_BN·(1−p)  ⇒  p ≥ (λ_PN−λ_BN)/((λ_PN−λ_BN)+(λ_BP−λ_PP))
  R(aN|x) = λ_NP·p + λ_NN·(1−p) ≤ R(aB|x)                          ⇒  p ≤ (λ_BN−λ_NN)/((λ_NP−λ_BN)+(λ_BN−λ_NN))
部分二手文献印其补数形（1−α/1−β），以本推导为准：错晋升代价 λ_PN 越大 α 越高，方向自检通过。
"""
from __future__ import annotations

import math

VOTES = ("support", "against", "unsure")
STATES = (1, 0)  # 1=θ+（断言成立），0=θ−


def alpha_beta(loss: dict) -> tuple[float, float]:
    """λ 矩阵 → (α, β)。键：PP/PN/BP/BN/NP/NN（Yao 记法，动作×状态）。
    行为序约束：λ_PP ≤ λ_BP ≤ λ_NP 且 λ_NN ≤ λ_BN ≤ λ_PN；再检 1-单调（α ≥ β）。"""
    pp, pn, bp, bn, np_, nn = (float(loss[k]) for k in ("PP", "PN", "BP", "BN", "NP", "NN"))
    if not (pp <= bp <= np_ and nn <= bn <= pn):
        raise ValueError(f"损失矩阵违反行为序约束：{loss}")
    a_den = (pn - bn) + (bp - pp)
    b_den = (np_ - bn) + (bn - nn)
    if a_den <= 0 or b_den <= 0:
        raise ValueError("损失差非正，阈值退化")
    a = (pn - bn) / a_den
    b = (bn - nn) / b_den
    if a < b:
        raise ValueError(f"α < β（{a:.3f} < {b:.3f}）：1-单调性破坏，检查损失矩阵")
    return a, b


def _examiners(records: list[dict]) -> list[str]:
    es: list[str] = []
    for r in records:
        for e in (r.get("votes") or {}):
            if e not in es:
                es.append(e)
    return es


def _init_q(votes: dict) -> float:
    """软启动（仅初始化，EM 会重排）：any against→0.2；双 support→0.9；单 support→0.6；否则 0.3。"""
    vals = list((votes or {}).values())
    s = sum(1 for x in vals if x == "support")
    if any(x == "against" for x in vals):
        return 0.2
    if s >= 2:
        return 0.9
    if s == 1:
        return 0.6
    return 0.3


def dawid_skene_fit(records: list[dict], n_iter: int = 30, eps: float = 0.5) -> dict:
    """两态 DS-EM：records 元素为 {"votes": {考官: 票}}。返回
    {"prior": P(θ+), "emit": {考官: {1/0: {票: P(票|状态,考官)}}}}（Laplace eps 平滑）。"""
    es = _examiners(records)
    if not records or not es:
        raise ValueError("DS-EM 需要非空票面")
    q = [min(max(_init_q(r.get("votes")), 0.05), 0.95) for r in records]
    emit: dict = {}
    pi = sum(q) / len(q)
    for _ in range(n_iter):
        # M 步：按当前 q 重建发射计数
        counts = {e: {1: {t: eps for t in VOTES}, 0: {t: eps for t in VOTES}} for e in es}
        for r, qi in zip(records, q):
            z = 1 if qi >= 0.5 else 0
            for e, v in (r.get("votes") or {}).items():
                counts[e][z][v] += 1.0
        emit = {e: {z: {t: counts[e][z][t] / sum(counts[e][z].values()) for t in VOTES}
                    for z in STATES} for e in es}
        pi = sum(q) / len(q)
        # E 步
        newq = []
        for r in records:
            l1 = math.log(max(pi, 1e-9))
            l0 = math.log(max(1 - pi, 1e-9))
            for e, v in (r.get("votes") or {}).items():
                l1 += math.log(max(emit[e][1][v], 1e-9))
                l0 += math.log(max(emit[e][0][v], 1e-9))
            m = max(l1, l0)
            w1 = math.exp(l1 - m)
            w0 = math.exp(l0 - m)
            newq.append(w1 / (w1 + w0))
        q = newq
    return {"prior": pi, "emit": emit}


def posterior(votes: dict, model: dict) -> float:
    """票型 → p(θ+|votes)（log-sum-exp 数值稳定；未知考官略去；未见票型回落均匀 1/3）。"""
    l1 = math.log(max(model["prior"], 1e-9))
    l0 = math.log(max(1 - model["prior"], 1e-9))
    for e, v in (votes or {}).items():
        em = model["emit"].get(e)
        if not em:
            continue
        l1 += math.log(max(em[1].get(v, 1.0 / 3), 1e-9))
        l0 += math.log(max(em[0].get(v, 1.0 / 3), 1e-9))
    m = max(l1, l0)
    w1 = math.exp(l1 - m)
    w0 = math.exp(l0 - m)
    return w1 / (w1 + w0)


def decide(p: float, alpha: float, beta: float) -> str:
    """三支：p≥α→positive（晋升向）；p≤β→negative（隔离向）；否则 boundary（挂起向）。"""
    if not alpha >= beta:
        raise ValueError("要求 α ≥ β")
    if p >= alpha:
        return "positive"
    if p <= beta:
        return "negative"
    return "boundary"
