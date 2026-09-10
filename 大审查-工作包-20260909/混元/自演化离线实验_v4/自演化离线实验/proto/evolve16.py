"""自演化推演 v16 —— 第十四轮：全面收口

E62 全系统集成 v3：组装 14 轮全部修正后的参数，在多种危险场景下测
E63 全场景对比矩阵：修正后架构 vs v3 基线 × 6 种场景
E64 注意力-自主性边界：定量刻画（每单位注意力买到多少自主代数）
E65 失败模式总枚举与检出覆盖率：把所有已知失效模式注入，看能检出多少
E66 实施路径验证：按 P0/P1/P2 顺序逐步加入机制，测边际收益
"""
import random, math, statistics, sys
from dataclasses import dataclass, asdict
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import (Cfg, build_world, build_tasks, retrieve, feats, U, W0,
                     mutate, rand_cfg, boot_lower, pareto_front, K, TOPICS)

# ═══ 14 轮修正后的推荐参数（"v4 配置"）═══
V4 = dict(
    margin=0.02,          # E36/E29b：标定量级，0.15 致命
    tol=0.04,             # E55：平滑最优平台，诱饵近严格，低谷够宽松
    cap=12,               # E30：Pareto+采样12 最优
    thresh=0.85,          # E34/E37：零误报区间右边界
    audit_every=3,
    monitor=True,         # E44：停摆监控（连续5代零采纳→margin减半）
    pareto=True,          # E7/E16/E30
    holdout=True,         # E3
    reanchor=True,        # E26：重锚而非简单恢复
)

V3 = dict(
    margin=0.01, tol=0.0, cap=1, thresh=None, audit_every=0,
    monitor=False, pareto=False, holdout=False, reanchor=False,
)


def build_spur_tasks(entries, rnd, n, want_spur, n_kws=6, offset=0):
    out = []
    for i in range(n):
        grp = [e for e in entries if e["kw"] == f"K{(i + offset) % n_kws}"]
        cands = [e for e in grp if e["spur"] == want_spur] or grp
        g = rnd.choice(cands)
        out.append({"q": f"{g['topic']} {g['kw']}", "kw": g["kw"], "golden": g["id"]})
    return out


def make_anchors(E, tr, n, rnd, cand_n=8):
    out, seen = [], set()
    while len(out) < n and len(seen) < n * 60:
        batch = []
        for _ in range(cand_n):
            a, b = rand_cfg(rnd), rand_cfg(rnd)
            k = (str(asdict(a)), str(asdict(b)))
            if k in seen: continue
            seen.add(k)
            batch.append((math.dist(feats(E, tr, a), feats(E, tr, b)), a, b))
        if not batch: break
        batch.sort(key=lambda x: -x[0])
        _, a, b = batch[0]
        ua, ub = U(E, tr, a), U(E, tr, b)
        if abs(ua - ub) > 1e-9:
            out.append((a, b, 1.0 if ua > ub else -1.0))
    return out


# ═══════════ E62/E63 统一引擎 ═══════════
def run(seed, cfg_d, scenario="clean", gens=35, kids=4, noise=0.05):
    """scenario: clean / drift / spur / deceptive / switch / noisy_gold"""
    rnd = random.Random(seed)
    E = build_world(seed)
    if scenario == "spur":
        tr = build_spur_tasks(E, rnd, 16, 1)
        he = build_spur_tasks(E, rnd, 16, 0, offset=3)
    elif scenario == "noisy_gold":
        tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
        for t in tr + he:
            if rnd.random() < 0.30: t["golden"] = rnd.choice(E)["id"]
    else:
        tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    if scenario == "spur":
        fresh = build_spur_tasks(E, random.Random(7777), 40, 0, offset=5)  # 与 spur 反相关
    else:
        fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base = U(E, fresh, Cfg())
    anchors = make_anchors(E, tr, 30, random.Random(seed + 999)) if cfg_d["thresh"] else []
    root = Cfg(); arch = [root]; main = root
    m = cfg_d["margin"]; stall = 0
    w = list(W0)
    # 目标切换场景：第 gens//2 代切换优化目标
    switch_at = gens // 2 if scenario == "switch" else 10 ** 9
    drift_at = gens // 3 if scenario == "drift" else 10 ** 9
    uB = lambda c: -(feats(E, tr, c)[1] + feats(E, tr, c)[2])

    def obj(c, g):
        if scenario == "deceptive":
            v = U(E, tr, c) + (0.40 if (c.deep and c.filter_zero)
                               else (-0.10 if (c.deep or c.filter_zero) else 0.0))
            return v
        if g >= switch_at: return uB(c)
        return U(E, tr, c, w)

    for g in range(1, gens + 1):
        if g >= drift_at:
            f = feats(E, tr, main); fn = math.sqrt(sum(x * x for x in f)) or 1.0
            tgt = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
            w = [(1 - 0.15) * wi + 0.15 * ti for wi, ti in zip(w, tgt)]
        adopts = 0
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = obj(ch, g) - obj(cand, g) + rnd.gauss(0, noise)
            d_he = U(E, he, ch, w) - U(E, he, cand, w) + rnd.gauss(0, noise)
            if d_tr > -cfg_d["tol"]: arch.append(ch)
            if cfg_d["pareto"]:
                arch = pareto_front(arch, E, tr) or arch[-1:]
                if len(arch) > cfg_d["cap"]: arch = rnd.sample(arch, cfg_d["cap"])
            else:
                arch = [max(arch, key=lambda c: obj(c, g))]
            ok = (d_tr > m and d_he > m) if cfg_d["holdout"] else (d_tr > m)
            if ok and obj(ch, g) > obj(main, g):
                main = ch; adopts += 1
        if cfg_d["monitor"]:
            stall = 0 if adopts else stall + 1
            if stall >= 5: m = max(0.005, m * 0.5); stall = 0
        if cfg_d["thresh"] and g % cfg_d["audit_every"] == 0 and anchors:
            acc = sum(1 for a, b, y in anchors
                      if (U(E, tr, a, w) - U(E, tr, b, w)) * y > 0) / len(anchors)
            if acc < cfg_d["thresh"] and cfg_d["reanchor"]:
                w = list(W0)
                anchors = make_anchors(E, tr, 30, random.Random(seed + 1000 + g))
    return U(E, fresh, main) - base


# ═══════════ E64 注意力-自主性边界 ═══════════
def e64(seed, budget, total_gens=60, drift=0.15):
    """budget 单位注意力：标注(1/条) + 审计(3/次) + 裁决(10/次)
    返回：在总代数内，系统能保持"未被漂移污染"的代数占比"""
    n_label = min(int(budget * 0.6), 80)
    audit_every = 10 if budget < 30 else (5 if budget < 80 else 3)
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base = U(E, fresh, Cfg())
    anchors = make_anchors(E, tr, 30, random.Random(seed + 999))
    root = Cfg(); arch = [root]; main = root
    w = list(W0); clean_gens = 0; spent = n_label
    for g in range(1, total_gens + 1):
        f = feats(E, tr, main); fn = math.sqrt(sum(x * x for x in f)) or 1.0
        tgt = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
        w = [(1 - drift) * wi + drift * ti for wi, ti in zip(w, tgt)]
        drifted = True
        if g % audit_every == 0 and spent + 3 <= budget:
            spent += 3
            acc = sum(1 for a, b, y in anchors
                      if (U(E, tr, a, w) - U(E, tr, b, w)) * y > 0) / len(anchors)
            if acc < 0.85 and spent + 10 <= budget:
                spent += 10
                w = list(W0)
                anchors = make_anchors(E, tr, 30, random.Random(seed + 1000 + g))
                drifted = False
            elif acc >= 0.85:
                drifted = False
        if not drifted: clean_gens += 1
        w_sys = [x + rnd.gauss(0, 0.02) for x in w]
        for _ in range(4):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch, w_sys) - U(E, tr, cand, w_sys) + rnd.gauss(0, 0.05)
            d_he = U(E, he, ch, w_sys) - U(E, he, cand, w_sys) + rnd.gauss(0, 0.05)
            if d_tr > -0.04: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > 12: arch = rnd.sample(arch, 12)
            if d_tr > 0.02 and d_he > 0.02 and U(E, tr, ch, w_sys) > U(E, tr, main, w_sys):
                main = ch
    return clean_gens / total_gens, U(E, fresh, main) - base, spent


# ═══════════ E65 失败模式检出覆盖率 ═══════════
FAILURES = ["drift", "spur", "deceptive", "switch", "noisy_gold", "margin_large",
            "strict_admit", "no_holdout", "single_archive"]


def e65(seed, failure, guard=True):
    """注入失败模式，guard=True 时启用对应护栏，返回终局效用"""
    rnd = random.Random(seed)
    E = build_world(seed)
    if failure == "spur":
        tr = build_spur_tasks(E, rnd, 16, 1); he = build_spur_tasks(E, rnd, 16, 0, offset=3)
    else:
        tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    if failure == "noisy_gold":
        for t in tr + he:
            if rnd.random() < 0.3: t["golden"] = rnd.choice(E)["id"]
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base = U(E, fresh, Cfg())
    anchors = make_anchors(E, tr, 30, random.Random(seed + 999))
    root = Cfg(); arch = [root]; main = root
    # 护栏开关：guard=False 表示"该失败对应的护栏缺失"
    m = 0.15 if (failure == "margin_large" and not guard) else 0.02
    tol = 0.0 if (failure == "strict_admit" and not guard) else 0.04
    use_hold = not (failure == "no_holdout" and not guard)
    use_par = not (failure == "single_archive" and not guard)
    use_mon = guard
    w = list(W0); stall = 0
    for g in range(35):
        if failure == "drift":
            f = feats(E, tr, main); fn = math.sqrt(sum(x * x for x in f)) or 1.0
            tgt = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
            w = [(1 - 0.15) * wi + 0.15 * ti for wi, ti in zip(w, tgt)]
        def obj(c):
            if failure == "deceptive":
                return U(E, tr, c, w) + (0.40 if (c.deep and c.filter_zero)
                                         else (-0.10 if (c.deep or c.filter_zero) else 0.0))
            if failure == "switch" and g >= 18:
                return -(feats(E, tr, c)[1] + feats(E, tr, c)[2])
            return U(E, tr, c, w)
        adopts = 0
        for _ in range(4):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = obj(ch) - obj(cand) + rnd.gauss(0, 0.05)
            d_he = U(E, he, ch, w) - U(E, he, cand, w) + rnd.gauss(0, 0.05)
            if d_tr > -tol: arch.append(ch)
            if use_par:
                arch = pareto_front(arch, E, tr) or arch[-1:]
                if len(arch) > 12: arch = rnd.sample(arch, 12)
            else:
                arch = [max(arch, key=obj)]
            ok = (d_tr > m and d_he > m) if use_hold else (d_tr > m)
            if ok and obj(ch) > obj(main): main = ch; adopts += 1
        if use_mon:
            stall = 0 if adopts else stall + 1
            if stall >= 5: m = max(0.005, m * 0.5); stall = 0
        if g % 3 == 0 and anchors:
            acc = sum(1 for a, b, y in anchors
                      if (U(E, tr, a, w) - U(E, tr, b, w)) * y > 0) / len(anchors)
            if acc < 0.85:
                w = list(W0)
                anchors = make_anchors(E, tr, 30, random.Random(seed + 1000 + g))
    return U(E, fresh, main) - base


# ═══════════ E66 实施路径 ═══════════
def e66(seed, stage, scenario="mixed", gens=35):
    """stage 0..5 逐步加入机制：
       0 v3基线  1 +monitor  2 +holdout  3 +pareto  4 +audit(0.85)+reanchor  5 +tol调参"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base = U(E, fresh, Cfg())
    anchors = make_anchors(E, tr, 30, random.Random(seed + 999)) if stage >= 4 else []
    m, tol, cap = 0.01, 0.0, 1
    monitor = stage >= 1; holdout = stage >= 2; par = stage >= 3
    audit = stage >= 4
    if stage >= 5: m, tol, cap = 0.02, 0.04, 12
    root = Cfg(); arch = [root]; main = root; w = list(W0); stall = 0
    for g in range(1, gens + 1):
        if scenario == "mixed" and g >= gens // 3:
            f = feats(E, tr, main); fn = math.sqrt(sum(x * x for x in f)) or 1.0
            tgt = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
            w = [(1 - 0.12) * wi + 0.12 * ti for wi, ti in zip(w, tgt)]
        adopts = 0
        for _ in range(4):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch, w) - U(E, tr, cand, w) + rnd.gauss(0, 0.05)
            d_he = U(E, he, ch, w) - U(E, he, cand, w) + rnd.gauss(0, 0.05)
            if d_tr > -tol: arch.append(ch)
            if par:
                arch = pareto_front(arch, E, tr) or arch[-1:]
                if len(arch) > cap: arch = rnd.sample(arch, cap)
            else:
                arch = [max(arch, key=lambda c: U(E, tr, c, w))]
            ok = (d_tr > m and d_he > m) if holdout else (d_tr > m)
            if ok and U(E, tr, ch, w) > U(E, tr, main, w): main = ch; adopts += 1
        if monitor:
            stall = 0 if adopts else stall + 1
            if stall >= 5: m = max(0.005, m * 0.5); stall = 0
        if audit and g % 3 == 0 and anchors:
            acc = sum(1 for a, b, y in anchors
                      if (U(E, tr, a, w) - U(E, tr, b, w)) * y > 0) / len(anchors)
            if acc < 0.85:
                w = list(W0)
                anchors = make_anchors(E, tr, 30, random.Random(seed + 1000 + g))
    return U(E, fresh, main) - base
