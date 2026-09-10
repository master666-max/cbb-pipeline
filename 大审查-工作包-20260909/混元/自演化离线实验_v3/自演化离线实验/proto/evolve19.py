"""自演化推演 v19 —— 第十七轮：最终验证与边界

E76 极简版 vs 完整版：只做 E66 前两项（审计+Pareto）够不够？
E77 护栏的"过度防御"代价：全部护栏开启时，在【良性环境】下损失多少
E78 系统能否识别自己的失败：无外部信号时，内部指标能否预警
E79 最脆弱环节：逐个移除单个机制，看哪个缺失最致命
E80 终局验证：v4 在"全部危险同时出现"的复合场景下
"""
import random, math, statistics, sys
from dataclasses import dataclass, asdict
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import (Cfg, build_world, build_tasks, retrieve, feats, U, W0,
                     mutate, rand_cfg, boot_lower, pareto_front, K, TOPICS)
from evolve16 import make_anchors, build_spur_tasks


def base_setup(seed, scenario="clean", gold_noise=0.0):
    rnd = random.Random(seed)
    E = build_world(seed)
    if scenario == "spur":
        tr = build_spur_tasks(E, rnd, 16, 1)
        he = build_spur_tasks(E, rnd, 16, 0, offset=3)
        fresh = build_spur_tasks(E, random.Random(7777), 40, 0, offset=5)
    else:
        tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
        fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    if gold_noise > 0:
        for t in tr + he:
            if rnd.random() < gold_noise: t["golden"] = rnd.choice(E)["id"]
    return E, rnd, tr, he, fresh


# ═══════════ 统一引擎（支持逐项开关）═══════════
def engine(seed, scenario="clean", gens=35, kids=4,
           audit=True, pareto=True, holdout=True, monitor=True,
           cap=8, tol=0.04, margin=0.02, gold_noise=0.0,
           drift=0.0, deceptive=False, switch=False,
           collect_stats=False):
    E, rnd, tr, he, fresh = base_setup(seed, scenario, gold_noise)
    base = U(E, fresh, Cfg())
    anchors = make_anchors(E, tr, 30, random.Random(seed + 999)) if audit else []
    root = Cfg(); arch = [root]; main = root
    w = list(W0); stall = 0; m = margin
    uB = lambda c: -(feats(E, tr, c)[1] + feats(E, tr, c)[2])
    drift_at = gens // 3 if drift > 0 else 10 ** 9
    switch_at = gens // 2 if switch else 10 ** 9
    stats = {"adopts": 0, "audits": 0, "reanchors": 0, "stalls": 0}

    def obj(c, g):
        if deceptive:
            return U(E, tr, c, w) + (0.40 if (c.deep and c.filter_zero)
                                     else (-0.10 if (c.deep or c.filter_zero) else 0.0))
        if g >= switch_at: return uB(c)
        return U(E, tr, c, w)

    for g in range(1, gens + 1):
        if g >= drift_at:
            f = feats(E, tr, main); fn = math.sqrt(sum(x * x for x in f)) or 1.0
            tgt = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
            w = [(1 - drift) * wi + drift * ti for wi, ti in zip(w, tgt)]
        adopts = 0
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = obj(ch, g) - obj(cand, g) + rnd.gauss(0, 0.05)
            d_he = U(E, he, ch, w) - U(E, he, cand, w) + rnd.gauss(0, 0.05)
            if d_tr > -tol: arch.append(ch)
            if pareto:
                arch = pareto_front(arch, E, tr) or arch[-1:]
                if len(arch) > cap: arch = rnd.sample(arch, cap)
            else:
                arch = [max(arch, key=lambda c: obj(c, g))]
            ok = (d_tr > m and d_he > m) if holdout else (d_tr > m)
            if ok and obj(ch, g) > obj(main, g): main = ch; adopts += 1
        stats["adopts"] += adopts
        if monitor:
            if adopts == 0:
                stall += 1; stats["stalls"] += 1
                if stall >= 5: m = max(0.005, m * 0.5); stall = 0
            else:
                stall = 0
        if audit and g % 3 == 0 and anchors:
            stats["audits"] += 1
            acc = sum(1 for a, b, y in anchors
                      if (U(E, tr, a, w) - U(E, tr, b, w)) * y > 0) / len(anchors)
            if acc < 0.85:
                stats["reanchors"] += 1
                w = list(W0)
                anchors = make_anchors(E, tr, 30, random.Random(seed + 1000 + g))
    res = U(E, fresh, main) - base
    return (res, stats) if collect_stats else res


# ═══════════ E76 极简版 vs 完整版 ═══════════
def e76(seed, tier, scenario="mixed"):
    if tier == "v3":
        return engine(seed, scenario, audit=False, pareto=False, holdout=False,
                      monitor=False, cap=1, tol=0.0, margin=0.01)
    if tier == "minimal":       # 只有审计 + Pareto
        return engine(seed, scenario, audit=True, pareto=True, holdout=False,
                      monitor=False, cap=8, tol=0.04, margin=0.01)
    if tier == "core":          # + 留出集门
        return engine(seed, scenario, audit=True, pareto=True, holdout=True,
                      monitor=False, cap=8, tol=0.04, margin=0.02)
    return engine(seed, scenario, audit=True, pareto=True, holdout=True,
                  monitor=True, cap=8, tol=0.04, margin=0.02)   # full


# ═══════════ E77 过度防御代价（良性环境）══════════
def e77(seed, tier):
    """纯良性环境：干净金标、无漂移、无伪特征、无欺骗
    测：护栏全开时损失多少（防御的代价）"""
    return e76(seed, tier, scenario="clean")


# ═══════════ E78 内部指标预警 ═══════════
def e78(seed, failure):
    """无外部信号时，内部指标（采纳率/档案规模/平台代数）能否预警失败"""
    kw = {"drift": dict(drift=0.15), "spur": dict(scenario="spur"),
          "deceptive": dict(deceptive=True), "gold": dict(gold_noise=0.3),
          "stop": dict(margin=0.15), "none": {}}
    bad = engine(seed, audit=False, monitor=False, collect_stats=True, **kw[failure])[1]
    good = engine(seed, audit=False, monitor=False, collect_stats=True)[1]
    return bad, good


# ═══════════ E79 最脆弱环节（留一法）══════════
MECHS = ["audit", "pareto", "holdout", "monitor"]


def e79(seed, drop, scenario="mixed"):
    kw = {m: True for m in MECHS}
    if drop in MECHS: kw[drop] = False
    return engine(seed, scenario, cap=8, tol=0.04, margin=0.02, **kw)


# ═══════════ E80 复合危险场景 ═══════════
def e80(seed, tier):
    """漂移 + 伪特征 + 欺骗地形 + 金标噪声 同时出现"""
    if tier == "v3":
        return engine(seed, scenario="spur", gold_noise=0.2, deceptive=True,
                      drift=0.15, switch=False,
                      audit=False, pareto=False, holdout=False, monitor=False,
                      cap=1, tol=0.0, margin=0.01)
    return engine(seed, scenario="spur", gold_noise=0.2, deceptive=True,
                  drift=0.15, switch=False,
                  audit=True, pareto=True, holdout=True, monitor=True,
                  cap=8, tol=0.04, margin=0.02)
