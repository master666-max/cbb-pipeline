"""自演化推演 v26 —— 第二十三轮：收口验证

第二十二轮最大发现：变异幅度 1.0→2.0 收益 +0.118（超过所有护栏）。
本轮验证这个发现的稳健性，并做最终配置对比。

E106 幅度稳健性：多个世界配置 × 多个种子，确认幅度效应不是偶然
E107 幅度 × 审计 × 温度 三元交互：找联合最优
E108 最终配置对决：v3 / v4 / v4-A / v4-B(加大幅度)
E109 幅度是否有上限：4.0 / 6.0 / 10.0 会崩溃吗
E110 二十三轮总账：把所有"有效改动"叠加，看总收益
"""
import random, math, statistics, sys
from dataclasses import asdict
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks, K
from evolve20 import build_world_v2, Cfg2, truth_score, judge_score
from evolve24 import mutate_coord, pareto_clean, surf_mag, _m, SURF
from evolve25 import e104, e101


def run(seed, d, gens=35, kids=4, alpha=0.5, coordinated=True, collect=False):
    """统一引擎（支持 scale / temp / audit / blind / cap / tol / margin）"""
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(truth_score(E, t, root) for t in fresh)
    eff = 0.95 if d.get("blind") else alpha
    eff0 = eff
    scale = d.get("scale", 1.0)
    temp = d.get("temp", 0.0)
    cap = d.get("cap", 8)
    m = d.get("margin", 0.02)
    tol = d.get("tol", 0.04)
    probe = build_tasks(E, random.Random(4242), d.get("probe_n", 4), offset=7)
    arch = [root]; main = root; best = main; btr = None; stall = 0
    st = {"reverts": 0, "relax": 0, "audits": 0, "surf": 0.0}
    label_gens = set()
    if d.get("label_every"):
        label_gens = set(range(1, gens + 1, d["label_every"]))

    def jsc(c, tasks):
        return _m(judge_score(E, t, c, eff) for t in tasks)

    def mut(c):
        dd = asdict(c); r = rnd.random()
        if r < 0.08: dd["deep"] = 1 - dd["deep"]
        elif r < 0.16: dd["filter_zero"] = 1 - dd["filter_zero"]
        else:
            p = rnd.choice(["w_kw", "w_content", "w_imp", "w_age"] + list(SURF))
            dd[p] = round(max(-5.0, min(20.0,
                                        dd[p] * (1 + rnd.choice([-0.4, -0.15, 0.2, 0.6]) * scale)
                                        + rnd.choice([0, 0, 0.5, -0.5]) * scale)), 4)
        return Cfg2(**dd)

    def pick(arch):
        if temp <= 0 or len(arch) == 1:
            return rnd.choice(arch[-3:])
        scores = [jsc(c, tr) for c in arch]
        lo, hi = min(scores), max(scores)
        if hi - lo < 1e-9: return rnd.choice(arch)
        wts = [math.exp((s - lo) / (hi - lo) / max(0.01, temp)) for s in scores]
        tot = sum(wts); r = rnd.random() * tot; acc = 0
        for c, w in zip(arch, wts):
            acc += w
            if r <= acc: return c
        return arch[-1]

    for g in range(1, gens + 1):
        if g in label_gens:
            eff = min(1.0, eff0 + 0.04)
        else:
            eff = max(alpha, eff - 0.004)
        adopts = 0
        for _ in range(kids):
            cand = pick(arch); ch = mut(cand)
            d_tr = jsc(ch, tr) - jsc(cand, tr) + rnd.gauss(0, 0.05)
            d_he = jsc(ch, he) - jsc(cand, he) + rnd.gauss(0, 0.05)
            if d_tr > -tol: arch.append(ch)
            if d.get("pareto", True):
                arch = pareto_clean(arch, E, tr, he, eff) or arch[-1:]
                if len(arch) > cap: arch = rnd.sample(arch, cap)
            else:
                arch = [max(arch, key=lambda c: jsc(c, tr))]
            ok = (d_tr > m and d_he > m) if d.get("holdout", True) else (d_tr > m)
            if ok and jsc(ch, tr) > jsc(main, tr):
                main = ch; adopts += 1
        if d.get("monitor", True):
            if adopts == 0:
                stall += 1
                if stall >= 5:
                    m = max(0.005, m * 0.5); stall = 0; st["relax"] += 1
            else:
                stall = 0
        if d.get("audit") and g % d.get("audit_every", 5) == 0:
            st["audits"] += 1
            cur = _m(truth_score(E, t, main) for t in probe)
            if btr is None: btr = cur; best = main
            elif cur < btr - 0.01:
                main = best; arch = [main]; st["reverts"] += 1
            else:
                best = main; btr = cur
    gain = _m(truth_score(E, t, main) for t in fresh) - base
    if collect:
        st["surf"] = surf_mag(main)
        return gain, st
    return gain


# 配置定义
V3 = dict(pareto=False, holdout=False, margin=0.01, tol=0.0, cap=1,
          blind=False, audit=False, monitor=False, scale=1.0, temp=0.0)
V4 = dict(pareto=True, holdout=True, margin=0.02, tol=0.04, cap=8,
          blind=False, audit=False, monitor=True, scale=1.0, temp=0.0)
V4A = dict(pareto=True, holdout=True, margin=0.02, tol=0.04, cap=8,
           blind=True, audit=True, monitor=True, scale=1.0, temp=0.0)
V4B = dict(pareto=True, holdout=True, margin=0.02, tol=0.04, cap=8,
           blind=True, audit=True, monitor=True, scale=2.0, temp=0.3)


def e106(seed, scale, gens=25):
    """幅度稳健性：固定其他，只变 scale"""
    return run(seed, dict(V4A, scale=scale, temp=0.3), gens=gens)


def e107(seed, scale, temp, audit, gens=25):
    return run(seed, dict(V4A, scale=scale, temp=temp, audit=audit), gens=gens)


def e108(seed, tier, gens=35):
    return run(seed, {"v3": V3, "v4": V4, "v4-A": V4A, "v4-B": V4B}[tier], gens=gens)


def e109(seed, scale, gens=25):
    return run(seed, dict(V4A, scale=scale, temp=0.3), gens=gens)


def e110(seed, tier, gens=35):
    """逐步叠加全部有效改动"""
    tiers = {
        "0_v3": V3,
        "1_幅度": dict(V3, scale=2.0, temp=0.3),
        "2_+Pareto": dict(V3, scale=2.0, temp=0.3, pareto=True, cap=8, tol=0.04),
        "3_+审计": dict(V3, scale=2.0, temp=0.3, pareto=True, cap=8, tol=0.04,
                     audit=True, probe_n=4, audit_every=5),
        "4_+盲评": dict(V3, scale=2.0, temp=0.3, pareto=True, cap=8, tol=0.04,
                     audit=True, probe_n=4, audit_every=5, blind=True),
        "5_+判断集刷新": dict(V3, scale=2.0, temp=0.3, pareto=True, cap=8, tol=0.04,
                        audit=True, probe_n=4, audit_every=5, blind=True, label_every=5),
        "6_+监控": dict(V3, scale=2.0, temp=0.3, pareto=True, cap=8, tol=0.04,
                     audit=True, probe_n=4, audit_every=5, blind=True,
                     label_every=5, monitor=True),
    }
    return run(seed, tiers[tier], gens=gens)
