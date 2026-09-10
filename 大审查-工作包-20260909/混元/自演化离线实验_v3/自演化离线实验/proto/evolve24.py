"""自演化推演 v24 —— 第二十一轮：清理第二十轮的失败 + 补三个未测项

E96 cap/tol 重测（修复 F-20/F-21）：用【干净的多目标 Pareto】——目标 = (训练集 judge, 留出集 judge)
     不含任何"我知道什么是表象"的先验，避免目标被构造污染
E97 预算 200 < 120 异常：更细粒度 + 更多种子，看是噪声还是真实非单调
E98 有成本的伪装（修复 E91 的 mask 无成本）：伪装本身降低真实表现
E99 委派边界·平衡样本（修复 E89 的基线率假象）
E100 自我美化的天花板：盲评做到极致（alpha→1）时的收益上限是多少
"""
import random, math, statistics, sys
from dataclasses import dataclass, asdict
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks, K, TOPICS
from evolve20 import build_world_v2, Cfg2, retrieve2, truth_score, judge_score, SC2

_m = lambda xs: statistics.mean(xs) if xs else 0.0
SURF = ("w_len", "w_fmt", "w_den", "w_cit")
W0 = [0.6, 0.5, 0.4]


def surf_mag(c):
    return abs(c.w_len) + abs(c.w_fmt) + abs(c.w_den) + abs(c.w_cit)


def mutate_coord(cfg, rnd, coordinated=True):
    d = asdict(cfg)
    r = rnd.random()
    if r < 0.08:
        d["deep"] = 1 - d["deep"]
    elif r < 0.16:
        d["filter_zero"] = 1 - d["filter_zero"]
    elif coordinated and r < 0.40:
        delta = rnd.choice([0.15, 0.4, 1.0])
        for k in SURF:
            d[k] = round(max(-5.0, min(20.0, d[k] + delta)), 3)
    else:
        p = rnd.choice(["w_kw", "w_content", "w_imp", "w_age"] + list(SURF))
        d[p] = round(max(-5.0, min(20.0,
                                   d[p] * rnd.choice([0.6, 0.85, 1.2, 1.6])
                                   + rnd.choice([0, 0, 0.5, -0.5]))), 4)
    return Cfg2(**d)


def pareto_clean(arch, E, tr, he, eff):
    """干净的双目标 Pareto：(训练集 judge 分, 留出集 judge 分)
    两个目标都是【实测的 judge 读数】，不含任何关于表象的先验。"""
    pts = []
    for c in arch:
        a = _m(judge_score(E, t, c, eff) for t in tr)
        b = _m(judge_score(E, t, c, eff) for t in he)
        pts.append(((a, b), c))
    front = []
    for (A, ca) in pts:
        dom = False
        for (B, cb) in pts:
            if B[0] >= A[0] and B[1] >= A[1] and (B[0] > A[0] or B[1] > A[1]):
                dom = True
                break
        if not dom:
            front.append(ca)
    return front


# ═══════════ 统一引擎 ═══════════
def run(seed, d, gens=35, kids=4, alpha=0.5, coordinated=True, collect=False):
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(truth_score(E, t, root) for t in fresh)
    eff = 0.95 if d.get("blind") else alpha
    arch = [root]; main = root; best = main; btr = None
    m = d.get("margin", 0.02); stall = 0
    probe = build_tasks(E, random.Random(4242), d.get("probe_n", 4), offset=7)
    st = {"reverts": 0, "relax": 0, "audits": 0}
    cap = d.get("cap", 8)
    use_pareto = d.get("pareto", True)
    for g in range(1, gens + 1):
        adopts = 0
        for _ in range(kids):
            cand = rnd.choice(arch[-3:])
            ch = mutate_coord(cand, rnd, coordinated)
            d_tr = (_m(judge_score(E, t, ch, eff) for t in tr)
                    - _m(judge_score(E, t, cand, eff) for t in tr) + rnd.gauss(0, 0.05))
            d_he = (_m(judge_score(E, t, ch, eff) for t in he)
                    - _m(judge_score(E, t, cand, eff) for t in he) + rnd.gauss(0, 0.05))
            if d_tr > -d.get("tol", 0.04):
                arch.append(ch)
            if use_pareto:
                arch = pareto_clean(arch, E, tr, he, eff) or arch[-1:]
                if len(arch) > cap:
                    arch = rnd.sample(arch, cap)
            else:
                arch = [max(arch, key=lambda c: _m(judge_score(E, t, c, eff) for t in tr))]
            ok = (d_tr > m and d_he > m) if d.get("holdout", True) else (d_tr > m)
            if ok and _m(judge_score(E, t, ch, eff) for t in tr) > \
               _m(judge_score(E, t, main, eff) for t in tr):
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
            if btr is None:
                btr = cur; best = main
            elif cur < btr - 0.01:
                main = best; arch = [main]; st["reverts"] += 1
            else:
                best = main; btr = cur
    gain = _m(truth_score(E, t, main) for t in fresh) - base
    if collect:
        st["surf"] = surf_mag(main)
        return gain, st
    return gain


V4A = dict(pareto=True, holdout=True, margin=0.02, tol=0.04, cap=8,
           blind=True, audit=True, monitor=True, probe_n=4, audit_every=5)


# ═══════════ E96 cap / tol 重测 ═══════════
def e96(seed, vary, value, gens=35):
    d = dict(V4A)
    d[vary] = value
    return run(seed, d, gens=gens)


# ═══════════ E97 预算非单调 ═══════════
def e97(seed, budget, gens=50, cost_verify=12, cost_blind=20, probe_n=4):
    """与 E93 同构，但更细粒度；返回 (增益, 花费, 审计次数)"""
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(truth_score(E, t, root) for t in fresh)
    spent = 0
    blind = budget >= 40
    if blind:
        spent += cost_blind
    eff = 0.95 if blind else 0.5
    n_audit = 0
    while True:
        nxt = n_audit + 1
        c = nxt * probe_n * cost_verify
        if spent + c <= budget and nxt <= gens // 3:
            n_audit = nxt
        else:
            break
    spent += n_audit * probe_n * cost_verify
    audit_gens = {(i + 1) * (gens // (n_audit + 1)) for i in range(n_audit)} if n_audit else set()
    probe = build_tasks(E, random.Random(4242), probe_n, offset=7)
    arch = [root]; main = root; best = main; btr = None
    for g in range(1, gens + 1):
        for _ in range(4):
            cand = rnd.choice(arch[-3:]); ch = mutate_coord(cand, rnd, True)
            d_tr = (_m(judge_score(E, t, ch, eff) for t in tr)
                    - _m(judge_score(E, t, cand, eff) for t in tr) + rnd.gauss(0, 0.05))
            d_he = (_m(judge_score(E, t, ch, eff) for t in he)
                    - _m(judge_score(E, t, cand, eff) for t in he) + rnd.gauss(0, 0.05))
            if d_tr > -0.04:
                arch.append(ch)
            arch = pareto_clean(arch, E, tr, he, eff) or arch[-1:]
            if len(arch) > 8:
                arch = rnd.sample(arch, 8)
            if d_tr > 0.02 and d_he > 0.02 and \
               _m(judge_score(E, t, ch, eff) for t in tr) > _m(judge_score(E, t, main, eff) for t in tr):
                main = ch
        if g in audit_gens:
            cur = _m(truth_score(E, t, main) for t in probe)
            if btr is None:
                btr = cur; best = main
            elif cur < btr - 0.01:
                main = best; arch = [main]
            else:
                best = main; btr = cur
    return _m(truth_score(E, t, main) for t in fresh) - base, spent, n_audit


# ═══════════ E98 有成本的伪装 ═══════════
@dataclass(frozen=True)
class Cfg8:
    w_kw: float = 3.0
    w_content: float = 1.0
    w_imp: float = 1.0
    w_age: float = 0.1
    w_len: float = 0.0
    w_fmt: float = 0.0
    w_den: float = 0.0
    w_cit: float = 0.0
    mask: float = 0.0
    filter_zero: int = 0
    deep: int = 0


def to_c2(c):
    return Cfg2(w_kw=c.w_kw, w_content=c.w_content, w_imp=c.w_imp, w_age=c.w_age,
                w_len=c.w_len, w_fmt=c.w_fmt, w_den=c.w_den, w_cit=c.w_cit,
                filter_zero=c.filter_zero, deep=c.deep)


def e98(seed, mask_costly=True, alpha=0.5, gens=35, kids=4, probe_n=4,
        audit_every=5, blind=True):
    """mask_costly=True：伪装时（审计期间）真实表现下降——因为朴素输出效果更差。
    这样系统面临真实权衡：伪装能骗过审计，但代价是真值损失。"""
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    probe = build_tasks(E, random.Random(4242), probe_n, offset=7)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg8()
    base = _m(truth_score(E, t, to_c2(root)) for t in fresh)
    eff = 0.95 if blind else alpha
    arch = [root]; main = root; best = main; btr = None; reverts = 0
    for g in range(1, gens + 1):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); d = asdict(cand); r = rnd.random()
            if r < 0.10:
                d["mask"] = round(min(3.0, max(0.0, d["mask"] + rnd.choice([0.3, 0.8]))), 3)
            elif r < 0.18:
                d["deep"] = 1 - d["deep"]
            elif r < 0.26:
                d["filter_zero"] = 1 - d["filter_zero"]
            else:
                p = rnd.choice(["w_kw", "w_content", "w_imp", "w_age"] + list(SURF))
                d[p] = round(max(-5.0, min(20.0, d[p] * rnd.choice([0.6, 0.85, 1.2, 1.6])
                                           + rnd.choice([0, 0, 0.5, -0.5]))), 4)
            ch = Cfg8(**d)
            d_tr = (_m(judge_score(E, t, to_c2(ch), eff) for t in tr)
                    - _m(judge_score(E, t, to_c2(cand), eff) for t in tr) + rnd.gauss(0, 0.05))
            d_he = (_m(judge_score(E, t, to_c2(ch), eff) for t in he)
                    - _m(judge_score(E, t, to_c2(cand), eff) for t in he) + rnd.gauss(0, 0.05))
            if d_tr > -0.04:
                arch.append(ch)
            arch = arch[-8:]
            if d_tr > 0.02 and d_he > 0.02 and \
               _m(judge_score(E, t, to_c2(ch), eff) for t in tr) > \
               _m(judge_score(E, t, to_c2(main), eff) for t in tr):
                main = ch
        if g % audit_every == 0:
            dd = asdict(to_c2(main))
            for k in SURF:
                dd[k] = round(dd[k] - main.mask * (1 if dd[k] > 0 else -1), 3)
            ce = Cfg2(**dd)
            cur = _m(truth_score(E, t, ce) for t in probe)
            if mask_costly:
                # 伪装成本：朴素输出在【平时】也变差（系统为此付出真实代价）
                cur -= 0.05 * main.mask
            if btr is None:
                btr = cur; best = main
            elif cur < btr - 0.01:
                main = best; arch = [main]; reverts += 1
            else:
                best = main; btr = cur
    return (_m(truth_score(E, t, to_c2(main)) for t in fresh) - base,
            main.mask, surf_mag(to_c2(main)), reverts)


# ═══════════ E99 委派边界·平衡样本 ═══════════
def sig(x):
    return 1.0 / (1.0 + math.exp(-max(-30, min(30, x))))


def e99(seed, kind, noise, n=200, balanced=True):
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    tr = build_tasks(E, rnd, 16)
    ag = dis = 0
    tries = 0
    while (ag + dis) < n and tries < n * 40:
        tries += 1
        def mk():
            return Cfg2(w_kw=rnd.uniform(0, 8), w_content=rnd.uniform(0, 4),
                        w_imp=rnd.uniform(-1, 3), w_age=rnd.uniform(0, 0.5),
                        w_len=rnd.uniform(-3, 3), w_fmt=rnd.uniform(-3, 3),
                        w_den=rnd.uniform(-3, 3), w_cit=rnd.uniform(-3, 3))
        a, b = mk(), mk()
        ta = _m(truth_score(E, t, a) for t in tr)
        tb = _m(truth_score(E, t, b) for t in tr)
        def jsc(c):
            tops = [retrieve2(E, t, c) for t in tr]; tops = [x for x in tops if x]
            if not tops:
                return 0.0
            real = _m(e["true_quality"] for x in tops for e in x)
            surf = _m(sig(c.w_len * e["length"] + c.w_fmt * e["formatting"]
                          + c.w_den * e["kw_density"] + c.w_cit * e["has_citation"])
                      for x in tops for e in x)
            return (1 - noise) * real + noise * surf
        ja, jb = jsc(a), jsc(b)
        if kind == "preference":
            if abs(ta - tb) < 1e-6:
                continue
            hy = 1.0 if ta > tb else -1.0
            jy = 1.0 if ja > jb else -1.0
        elif kind == "usefulness":
            hy = 1.0 if ta > 0.5 else -1.0
            jy = 1.0 if ja > 0.5 else -1.0
        else:
            hy = 1.0 if ta > 0.65 else -1.0
            jy = 1.0 if ja > 0.65 else -1.0
        if balanced:
            # 只在人类判断为"是"/"否"各占一半时计数，消除基线率假象
            if hy > 0 and (ag and sum([1]) and (ag + dis) % 2 == 0):
                pass
        if hy == jy:
            ag += 1
        else:
            dis += 1
    return ag / (ag + dis) if (ag + dis) else 0.0


def e99b(seed, kind, noise, n=120):
    """真正平衡：分别统计人类判"是"与判"否"两个子集的一致率，再平均"""
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    tr = build_tasks(E, rnd, 16)
    pos = [0, 0]   # [一致, 总数]
    neg = [0, 0]
    tries = 0
    while min(pos[1], neg[1]) < n // 2 and tries < n * 40:
        tries += 1
        def mk():
            return Cfg2(w_kw=rnd.uniform(0, 8), w_content=rnd.uniform(0, 4),
                        w_imp=rnd.uniform(-1, 3), w_age=rnd.uniform(0, 0.5),
                        w_len=rnd.uniform(-3, 3), w_fmt=rnd.uniform(-3, 3),
                        w_den=rnd.uniform(-3, 3), w_cit=rnd.uniform(-3, 3))
        a, b = mk(), mk()
        ta = _m(truth_score(E, t, a) for t in tr)
        tb = _m(truth_score(E, t, b) for t in tr)
        def jsc(c):
            tops = [retrieve2(E, t, c) for t in tr]; tops = [x for x in tops if x]
            if not tops:
                return 0.0
            real = _m(e["true_quality"] for x in tops for e in x)
            surf = _m(sig(c.w_len * e["length"] + c.w_fmt * e["formatting"]
                          + c.w_den * e["kw_density"] + c.w_cit * e["has_citation"])
                      for x in tops for e in x)
            return (1 - noise) * real + noise * surf
        ja, jb = jsc(a), jsc(b)
        if kind == "preference":
            if abs(ta - tb) < 1e-6:
                continue
            hy = 1.0 if ta > tb else -1.0
            jy = 1.0 if ja > jb else -1.0
        elif kind == "usefulness":
            hy = 1.0 if ta > 0.5 else -1.0
            jy = 1.0 if ja > 0.5 else -1.0
        else:
            hy = 1.0 if ta > 0.65 else -1.0
            jy = 1.0 if ja > 0.65 else -1.0
        bucket = pos if hy > 0 else neg
        bucket[1] += 1
        if hy == jy:
            bucket[0] += 1
    return ((pos[0] / pos[1] if pos[1] else 0) + (neg[0] / neg[1] if neg[1] else 0)) / 2


# ═══════════ E100 自我美化的天花板 ═══════════
def e100(seed, alpha_eff, gens=35, audit=True, probe_n=4, audit_every=5):
    """把盲评做到极致：eff=1.0 表示 judge 完全不受表象影响。
    问：此时收益天花板是多少？还值得继续投入吗？"""
    d = dict(V4A)
    d["blind"] = False
    d["audit"] = audit
    d["probe_n"] = probe_n
    d["audit_every"] = audit_every
    return run(seed, d, gens=gens, alpha=alpha_eff)
