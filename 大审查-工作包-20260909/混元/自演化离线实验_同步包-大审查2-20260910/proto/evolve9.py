"""自演化推演实验 v9 —— 第七轮：机制交互与未验证的工程建议

E29 端到端集成：把所有机制组装起来，看是否有交互产生的涌现问题
E30 档案压缩：宽松准入导致档案膨胀，压缩策略是否损害恢复能力
E31 留出集轮换节奏：多久换一次？自适应轮换是否优于固定周期
E32 记忆层核心主张（第二轮提出、从未验证）：importance 应实测而非自称
E33 廉价筛选校准：容忍度如何定？系统性偏差（非纯噪声）下还安全吗
"""
import random, math, statistics
from dataclasses import dataclass, asdict

K = 5
TOPICS = [f"T{i}" for i in range(16)]
_WORLD = [0]
_FC = {}


def build_world(seed, n_entries=60, n_kws=6, reliability=0.32):
    _WORLD[0] += 1; _FC.clear()
    rnd = random.Random(seed)
    entries = []
    for i in range(n_entries):
        k, t = i % n_kws, TOPICS[i % 16]
        tok = t if rnd.random() < reliability else rnd.choice(TOPICS)
        entries.append({"id": f"e{i}", "kw": f"K{k}", "topic": t,
                        "keywords": [f"K{k}"], "content": f"{tok} K{k} 片段{i}",
                        "importance": rnd.randint(1, 3),
                        "age_days": rnd.randint(0, 400),
                        "spur": 1 if rnd.random() < 0.5 else 0,
                        "true_quality": rnd.random()})     # E32 用：真实质量（系统不可见）
    return entries


def build_tasks(entries, rnd, n, n_kws=6, offset=0):
    out = []
    for i in range(n):
        grp = [e for e in entries if e["kw"] == f"K{(i + offset) % n_kws}"]
        g = rnd.choice(grp)
        out.append({"q": f"{g['topic']} {g['kw']}", "kw": g["kw"], "golden": g["id"]})
    return out


@dataclass(frozen=True)
class Cfg:
    w_kw: float = 3.0
    w_content: float = 1.0
    w_imp: float = 1.0
    w_age: float = 0.1
    w_spur: float = 0.0
    filter_zero: int = 0
    deep: int = 0

SCALARS = ["w_kw", "w_content", "w_imp", "w_age", "w_spur"]


def retrieve(entries, task, cfg):
    qw = task["q"].split()
    out = []
    for e in entries:
        kw_hit = sum(1 for w in qw if w in " ".join(e["keywords"]))
        c_hit = sum(1 for w in qw if w in e["content"])
        if cfg.filter_zero and kw_hit == 0 and c_hit == 0: continue
        s = (cfg.w_kw * kw_hit + cfg.w_content * c_hit + cfg.w_imp * e["importance"]
             - cfg.w_age * (e["age_days"] / 100.0) + cfg.w_spur * e["spur"])
        out.append((s, e))
    out.sort(key=lambda x: -x[0])
    if cfg.deep:
        kw = next((w for w in qw if w.startswith("K")), None)
        toks = [w for w in qw if w.startswith("T")]
        pool = [e for _, e in out if (kw is None or kw in e["keywords"])]
        if toks:
            pool.sort(key=lambda e: -(1 if toks[0] in e["content"] else 0))
        return pool[:K]
    return [e for _, e in out[:K]]


def feats(entries, tasks, cfg):
    key = (_WORLD[0], len(tasks), tuple(t["golden"] for t in tasks), str(asdict(cfg)))
    if key in _FC: return _FC[key]
    h = n = 0.0
    for t in tasks:
        top = retrieve(entries, t, cfg)
        h += 1.0 if t["golden"] in [e["id"] for e in top] else 0.0
        n += sum(1 for e in top if e["kw"] != t["kw"]) / K
    h /= len(tasks); n /= len(tasks)
    cost = 0.10 + (0.45 if cfg.deep else 0.0) - (0.08 if cfg.filter_zero else 0.0)
    _FC[key] = (h, n, cost)
    return _FC[key]


W0 = (1.0, -0.60, -0.50)
def U(entries, tasks, cfg, w=W0):
    return sum(a * b for a, b in zip(w, feats(entries, tasks, cfg)))


def mutate(cfg, rnd):
    d = asdict(cfg)
    r = rnd.random()
    if r < 0.10: d["deep"] = 1 - d["deep"]
    elif r < 0.18: d["filter_zero"] = 1 - d["filter_zero"]
    else:
        p = rnd.choice(SCALARS)
        d[p] = round(max(-5.0, min(20.0, d[p] * rnd.choice([0.5, 0.7, 0.85, 1.2, 1.5, 2.0])
                                 + rnd.choice([0, 0, 0.5, -0.5]))), 4)
    return Cfg(**d)


def boot_lower(deltas, rnd, B=100, alpha=0.05):
    n = len(deltas)
    if n == 0: return 0.0
    vals = [statistics.mean(deltas[rnd.randrange(n)] for _ in range(n)) for _ in range(B)]
    vals.sort()
    return vals[int(alpha / 2 * B)]


def pareto_front(arch, entries, tasks):
    pts = [(feats(entries, tasks, c), c) for c in arch]
    front = []
    for f, c in pts:
        dom = False
        for g, _ in pts:
            if g is f: continue
            if (g[0] >= f[0] and g[1] <= f[1] and g[2] <= f[2]) and \
               (g[0] > f[0] or g[1] < f[1] or g[2] < f[2]):
                dom = True; break
        if not dom: front.append(c)
    return front


def rand_cfg(rnd):
    return Cfg(w_kw=round(rnd.uniform(0, 8), 2), w_content=round(rnd.uniform(0, 4), 2),
               w_imp=round(rnd.uniform(-1, 3), 2), w_age=round(rnd.uniform(0, 0.5), 3),
               w_spur=round(rnd.uniform(-1, 1), 2),
               filter_zero=rnd.randint(0, 1), deep=rnd.randint(0, 1))


# ═══════════════ E29 端到端集成 ═══════════════
def e29(seed, mode, gens=25, kids=4, noise=0.05):
    """mode:
      v3      —— 单门 + 单一最优档案（v3 现状的抽象）
      single  —— 两级门控 + 单一最优档案
      pareto  —— 两级门控 + Pareto 档案
      full    —— 全套：两级门控 + Pareto + bootstrap + 廉价筛选(reject-only)
                 + 留出集轮换 + 锚定审计(检出则重锚)
    """
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)   # 真值：从未参与选择
    pool = build_tasks(E, random.Random(4242), 60, offset=9)    # 轮换储备池
    anchor = [(rand_cfg(rnd), rand_cfg(rnd)) for _ in range(20)]
    anchor = [(a, b, 1.0 if U(E, tr, a) > U(E, tr, b) else -1.0) for a, b in anchor]

    w = list(W0)
    root = Cfg(); arch = [root]; main = root
    rot_used = 0; held = he; reanchors = 0
    for g in range(gens):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:])
            ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch, w) - U(E, tr, cand, w) + rnd.gauss(0, noise)
            d_he = U(E, held, ch, w) - U(E, held, cand, w) + rnd.gauss(0, noise)
            # 廉价筛选（只淘汰）
            if mode == "full":
                cheap = d_tr + rnd.gauss(0, 0.25)
                if cheap < -0.30: continue
            ok = False
            if mode in ("full",):
                dts = [U(E, [t], ch, w) - U(E, [t], cand, w) for t in tr]
                dhs = [U(E, [t], ch, w) - U(E, [t], cand, w) for t in held]
                ok = boot_lower(dts, rnd) > 0 and boot_lower(dhs, rnd) > 0
            elif mode == "v3":
                ok = d_tr > 0.01
            else:
                ok = d_tr > 0.01 and d_he > 0.01
            if d_tr > -0.06:                       # 档案准入（宽松）
                arch.append(ch)
                if mode in ("pareto", "full"):
                    arch = pareto_front(arch, E, tr) or arch[-1:]
                else:
                    arch = [max(arch, key=lambda c: U(E, tr, c, w))]
            if ok and U(E, tr, ch, w) > U(E, tr, main, w):
                main = ch
        # 留出集轮换
        if mode == "full":
            rot_used += 1
            if rot_used >= 5:
                held = build_tasks(E, rnd, 16, offset=rot_used)
                rot_used = 0
            # 锚定审计
            acc = sum(1 for a, b, y in anchor
                      if (U(E, tr, a, w) - U(E, tr, b, w)) * y > 0) / len(anchor)
            if acc < 0.90:
                reanchors += 1
                w = list(W0)
    return U(E, fresh, main), U(E, fresh, root), len(arch), reanchors


# ═══════════════ E30 档案压缩 ═══════════════
def e30(seed, strategy, phase1=15, phase2=15, kids=4):
    """先按目标 A 演化，再切到目标 B；测档案压缩对恢复的影响
    strategy: none / pareto / pareto_lineage(前沿+分叉点) / random_sample / pareto_sample"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    uA = lambda c: feats(E, tr, c)[0]
    uB = lambda c: -(feats(E, tr, c)[1] + feats(E, tr, c)[2])
    root = Cfg(); arch = [root]
    sizes = []
    for uf in (uA, uB):
        for _ in range(phase2):
            for _ in range(kids):
                cand = rnd.choice(arch[-3:])
                ch = mutate(cand, rnd)
                if uf(ch) - uf(cand) > -0.06: arch.append(ch)
            if strategy == "none":
                pass
            elif strategy == "pareto":
                arch = pareto_front(arch, E, tr) or arch[-1:]
            elif strategy == "pareto_lineage":
                f = pareto_front(arch, E, tr) or arch[-1:]
                arch = list(dict.fromkeys(f + [arch[0], arch[len(arch) // 2]] + arch[-2:]))
            elif strategy == "random_sample":
                if len(arch) > 12: arch = rnd.sample(arch, 12)
            else:  # pareto_sample
                f = pareto_front(arch, E, tr) or arch[-1:]
                if len(f) > 12: f = rnd.sample(f, 12)
                arch = f
            sizes.append(len(arch))
    final = max(arch, key=uB)
    return uA(final), statistics.mean(sizes), max(sizes)


# ═══════════════ E31 留出集轮换节奏 ═══════════════
def e31(seed, schedule, gens=120, kids=4):
    """schedule: never / fixed_N / adaptive(当新鲜集表现不再提升时换)
    返回：留出集自报提升 vs 新鲜任务集真实提升"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    mk = lambda off: build_tasks(E, random.Random(9000 + off), 16, offset=off)
    held = mk(1)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg(); arch = [root]; main = root
    base_fresh = U(E, fresh, root)
    N = schedule if isinstance(schedule, int) else 10**9
    used = 0; last_best = -9; stall = 0; off = 1
    for g in range(gens):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:])
            ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch) - U(E, tr, cand)
            d_he = U(E, held, ch) - U(E, held, cand)
            if d_tr > -0.06: arch.append(ch)
            if d_tr > 0.01 and d_he > 0.01 and U(E, tr, ch) > U(E, tr, main): main = ch
        arch = arch[-25:]
        used += 1
        if schedule == "adaptive":
            cur = U(E, fresh, main)
            if cur > last_best + 1e-6: last_best = cur; stall = 0
            else: stall += 1
            if stall >= 8:
                off += 1; held = mk(off); stall = 0; last_best = -9
        elif used >= N:
            off += 1; held = mk(off); used = 0
    return (U(E, held, main) - U(E, held, root),      # 自报
            U(E, fresh, main) - base_fresh, off)       # 真实


# ═══════════════ E32 importance 实测 vs 自称 ═══════════════
def e32(seed, mode, n_entries=60, rounds=25):
    """mode: self 用条目自称 importance 排序
             measured 用『被检索后是否真被采纳』的实测效用排序
             hybrid 两者加权
    真值 = 条目 true_quality（系统不可见，只能通过『是否被采纳』间接观测）"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tasks = build_tasks(E, rnd, 40)
    # 初始化
    for e in E:
        e["declared"] = rnd.randint(1, 10)                      # 自称（与真值弱相关）
        e["measured"] = 0.0; e["shown"] = 0
    # 模拟使用：检索 → 是否被采纳（采纳概率 ∝ true_quality）
    for r in range(rounds):
        t = tasks[r % len(tasks)]
        top = retrieve(E, t, Cfg(w_imp=1.0 if mode == "self" else 0.0,
                                 w_kw=3.0, w_content=1.0))
        for e in top:
            e["shown"] += 1
            if rnd.random() < e["true_quality"]:
                e["measured"] += 1
    # 用排序质量评价：top-5 中高真值条目的比例
    def key_self(e): return e["declared"]
    def key_meas(e): return (e["measured"] / e["shown"]) if e["shown"] else 0.0
    def key_hyb(e): return 0.5 * (e["declared"] / 10.0) + 0.5 * key_meas(e)
    kf = {"self": key_self, "measured": key_meas, "hybrid": key_hyb}[mode]
    ranked = sorted(E, key=lambda e: -kf(e))[:10]
    return statistics.mean(e["true_quality"] for e in ranked)


# ═══════════════ E33 廉价筛选校准 ═══════════════
def e33(seed, tol, bias, budget=50, kids=4, gens=40):
    """tol: 淘汰容忍度（cheap < -tol 则淘汰）
    bias: 廉价评估的系统性偏差（0 = 纯噪声；>0 = 偏向某类配置）"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg(); main = root; arch = [root]
    spent = 0; g = 0
    while spent < budget and g < gens:
        g += 1
        cands = [mutate(main, rnd) for _ in range(kids)]
        surv = []
        for c in cands:
            d = U(E, tr, c) - U(E, tr, main)
            cheap = d + rnd.gauss(0, 0.25) + bias * (1.0 if c.deep else -1.0)
            if cheap >= -tol: surv.append(c)
        spent += len(cands) * 0.1
        for c in surv:
            spent += 1
            if (U(E, tr, c) - U(E, tr, main) > 0.01 and
                    U(E, he, c) - U(E, he, main) > 0.01 and
                    U(E, tr, c) > U(E, tr, main)): main = c
    return U(E, fresh, main) - U(E, fresh, root), g
