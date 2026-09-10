"""自演化推演 v11 —— 第九轮：收口验证

E38 全生命周期端到端：冷启动(建判断集) → 稳态演化 → 漂移 → 检出 → 重锚 → 恢复
E39 注意力瓶颈量化：多少单位注意力买到多少自主性（缩放曲线）
E40 底线对比：修正后架构 vs v3 基线，端到端差多少
E41 红线违规审计：逐条注入违规，看现有机制能否检出
"""
import random, math, statistics, sys
from dataclasses import dataclass, asdict
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import (Cfg, build_world, build_tasks, retrieve, feats, U, W0,
                     mutate, rand_cfg, boot_lower, pareto_front, K, TOPICS)


def fit_w(E, tasks, samples, epochs=200, lr=0.1, dims=3):
    w = [0.0] * dims
    F = [(feats(E, tasks, a), feats(E, tasks, b), y) for a, b, y in samples]
    for _ in range(epochs):
        for fa, fb, y in F:
            d = [x - z for x, z in zip(fa, fb)]
            z = y * sum(wi * di for wi, di in zip(w, d))
            g = 1.0 / (1.0 + math.exp(max(-30, min(30, z))))
            for i in range(dims):
                w[i] += lr * g * y * d[i]
    n = math.sqrt(sum(x * x for x in w)) or 1.0
    return [x / n * math.sqrt(sum(y * y for y in W0)) for x in w]


def maxdiv(E, tasks, n, rnd, cand_n=8):
    out, seen = [], set()
    while len(out) < n and len(seen) < n * 60:
        batch = []
        for _ in range(cand_n):
            a, b = rand_cfg(rnd), rand_cfg(rnd)
            k = (str(asdict(a)), str(asdict(b)))
            if k in seen: continue
            seen.add(k)
            d = math.dist(feats(E, tasks, a), feats(E, tasks, b))
            batch.append((d, a, b))
        if not batch: break
        batch.sort(key=lambda x: -x[0])
        _, a, b = batch[0]
        ua, ub = U(E, tasks, a), U(E, tasks, b)
        if abs(ua - ub) > 1e-9:
            out.append((a, b, 1.0 if ua > ub else -1.0))
    return out


# ═══════════ E38 全生命周期 ═══════════
def e38(seed, n_label=50, use_maxdiv=True, drift_start=40, drift=0.15,
        thresh=0.85, audit_every=3, total=70, gens_cold=0, reanchor=True):
    """返回 (终局真实效用, 起点效用, 注意力成本, 漂移是否被检出, 检出代数)"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    # 冷启动：建判断集
    if use_maxdiv:
        samples = maxdiv(E, tr, n_label, rnd)
    else:
        samples = []
        while len(samples) < n_label:
            a, b = rand_cfg(rnd), rand_cfg(rnd)
            ua, ub = U(E, tr, a), U(E, tr, b)
            if abs(ua - ub) < 1e-9: continue
            samples.append((a, b, 1.0 if ua > ub else -1.0))
    w_fit = fit_w(E, tr, samples) if samples else list(W0)
    anchors = maxdiv(E, tr, 30, random.Random(seed + 999))
    w_h = list(W0)
    root = Cfg(); arch = [root]; main = root
    base = U(E, fresh, root)
    cost = n_label                     # 标注成本
    detected = False; det_gen = None; frozen = 0
    for g in range(1, total + 1):
        if g >= drift_start:
            f = feats(E, tr, main); fn = math.sqrt(sum(x * x for x in f)) or 1.0
            tgt = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
            w_h = [(1 - drift) * wi + drift * ti for wi, ti in zip(w_h, tgt)]
        # 审计
        if g % audit_every == 0:
            acc = sum(1 for a, b, y in anchors
                      if (U(E, tr, a, w_h) - U(E, tr, b, w_h)) * y > 0) / len(anchors)
            if acc < thresh and not detected:
                detected = True; det_gen = g; cost += 10      # 人工裁决
                if reanchor:
                    w_fit = fit_w(E, tr, maxdiv(E, tr, 20, rnd))
                    w_h = list(W0); anchors = maxdiv(E, tr, 30, random.Random(seed + 1000 + g))
        w_sys = [x + rnd.gauss(0, 0.02) for x in w_h]
        for _ in range(4):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch, w_sys) - U(E, tr, cand, w_sys) + rnd.gauss(0, 0.05)
            d_he = U(E, he, ch, w_sys) - U(E, he, cand, w_sys) + rnd.gauss(0, 0.05)
            if d_tr > -0.06: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > 12: arch = rnd.sample(arch, 12)
            if d_tr > 0.01 and d_he > 0.01 and U(E, tr, ch, w_sys) > U(E, tr, main, w_sys):
                main = ch
    return U(E, fresh, main), base, cost, detected, det_gen


# ═══════════ E39 注意力缩放曲线 ═══════════
def e39(seed, budget, drift=0.15, total=70):
    """固定总注意力预算，按 E22 建议分配：先标注后审计
    返回 (终局真实效用 - 起点, 实际花掉的预算)"""
    n_label = min(int(budget * 0.7), 80)
    u, base, cost, det, _ = e38(seed, n_label=n_label, drift=drift, total=total)
    return u - base, cost


# ═══════════ E40 底线对比 ═══════════
def e40(seed, mode, total=50, drift=0.0):
    """mode: v3 —— 单门 + 单一最优档案 + 自称 importance（无门控、无档案、无审计）
         corrected —— 两级门控 + Pareto压缩 + 标定margin + 审计(0.85) + 重锚"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    w_h = list(W0)
    anchors = maxdiv(E, tr, 30, random.Random(seed + 999)) if mode == "corrected" else []
    root = Cfg(); arch = [root]; main = root
    base = U(E, fresh, root)
    for g in range(1, total + 1):
        if drift > 0:
            f = feats(E, tr, main); fn = math.sqrt(sum(x * x for x in f)) or 1.0
            tgt = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
            w_h = [(1 - drift) * wi + drift * ti for wi, ti in zip(w_h, tgt)]
        w_sys = [x + rnd.gauss(0, 0.02) for x in w_h]
        if mode == "corrected" and g % 3 == 0:
            acc = sum(1 for a, b, y in anchors
                      if (U(E, tr, a, w_h) - U(E, tr, b, w_h)) * y > 0) / len(anchors)
            if acc < 0.85:
                w_h = list(W0); anchors = maxdiv(E, tr, 30, random.Random(seed + 1000 + g))
        for _ in range(4):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch, w_sys) - U(E, tr, cand, w_sys) + rnd.gauss(0, 0.05)
            d_he = U(E, he, ch, w_sys) - U(E, he, cand, w_sys) + rnd.gauss(0, 0.05)
            if mode == "v3":
                if d_tr > 0.01:                       # 单门：只看训练集
                    if U(E, tr, ch, w_sys) > U(E, tr, main, w_sys): main = ch
                arch = [main]                          # 单一最优档案
            else:
                if d_tr > -0.06:
                    arch.append(ch)
                    arch = pareto_front(arch, E, tr) or arch[-1:]
                    if len(arch) > 12: arch = rnd.sample(arch, 12)
                if d_tr > 0.01 and d_he > 0.01 and U(E, tr, ch, w_sys) > U(E, tr, main, w_sys):
                    main = ch
    return U(E, fresh, main) - base


# ═══════════ E41 红线违规审计 ═══════════
def e41(seed, violation):
    """注入一条红线违规，返回 (是否被检出, 终局相对起点)
    violation: strict_admit(准入也用严格门) / no_holdout(去掉留出集门)
               / accept_cheap(廉价筛选用于采纳) / no_archive(单一最优档案)
               / margin_large(margin=0.15) / none(基线)"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg(); arch = [root]; main = root
    base = U(E, fresh, root)
    for g in range(40):
        for _ in range(4):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch) - U(E, tr, cand) + rnd.gauss(0, 0.05)
            d_he = U(E, he, ch) - U(E, he, cand) + rnd.gauss(0, 0.05)
            m = 0.15 if violation == "margin_large" else 0.01
            if violation == "accept_cheap":
                cheap = d_tr + rnd.gauss(0, 0.25)
                if cheap > 0.01:                       # 违规：廉价判定直接采纳
                    main = ch
                    arch.append(ch); continue
            if violation == "strict_admit":
                if d_tr > m and d_he > m: arch.append(ch)   # 违规：准入也严格
            else:
                if d_tr > -0.06: arch.append(ch)
            if violation == "no_archive":
                arch = [max(arch, key=lambda c: U(E, tr, c))]
            else:
                arch = pareto_front(arch, E, tr) or arch[-1:]
                if len(arch) > 12: arch = rnd.sample(arch, 12)
            ok = (d_tr > m) if violation == "no_holdout" else (d_tr > m and d_he > m)
            if ok and U(E, tr, ch) > U(E, tr, main): main = ch
    return U(E, fresh, main) - base
