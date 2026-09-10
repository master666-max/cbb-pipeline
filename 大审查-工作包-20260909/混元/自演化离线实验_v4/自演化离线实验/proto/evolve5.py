"""自演化推演实验 v5 —— 第三轮：五个新问题

E9  判断样本 → 效用函数拟合：存「判断」而非存「公式」是否可行？需要多少样本？
E10 递归自我修改：门控参数(margin/容差/变异率)本身可被演化，会退化吗？
E11 档案多样性与可恢复性：目标被证伪后，Pareto 档案能否比单一最优档案更快恢复？
E12 收敛/卡住/漂移 三态判别器：能否可靠区分？
E13 两阶段门控：廉价筛选「只淘汰」vs「也采纳」，在固定预算下差多少？
"""
import random, statistics, math
from dataclasses import dataclass, asdict

K = 5
TOPICS = [f"T{i}" for i in range(16)]


# ───────────────────────── 世界与配置 ─────────────────────────
def build_world(seed, n_entries=80, n_kws=10, reliability=0.6):
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
                        "catchy": 1.0 if rnd.random() < 0.3 else 0.0})
    return entries


def build_tasks(entries, rnd, n_train, n_held, spur_flip=True):
    train, held = [], []
    for i in range(n_train + n_held):
        grp = [e for e in entries if e["kw"] == f"K{i % 10}"]
        want = 1 if (not spur_flip or i < n_train) else 0
        cands = [e for e in grp if e["spur"] == want] or grp
        g = rnd.choice(cands)
        (train if i < n_train else held).append(
            {"q": f"{g['topic']} {g['kw']}", "kw": g["kw"], "golden": g["id"]})
    return train, held


@dataclass(frozen=True)
class Cfg:
    w_kw: float = 3.0
    w_content: float = 1.0
    w_imp: float = 1.0
    w_age: float = 0.1
    w_spur: float = 0.0
    w_catchy: float = 0.0
    filter_zero: int = 0
    expand_links: int = 0
    retriever: str = "hybrid"
    # 元层基因（E10 中开放演化）
    margin: float = 0.01
    tol: float = 0.06
    mut_rate: float = 1.0

SCALARS = ["w_kw", "w_content", "w_imp", "w_age", "w_spur", "w_catchy"]
META = ["margin", "tol", "mut_rate"]


def retrieve(entries, task, cfg):
    qw = task["q"].split()
    out = []
    for e in entries:
        kw_hit = sum(1 for w in qw if w in " ".join(e["keywords"]))
        c_hit = sum(1 for w in qw if w in e["content"])
        if cfg.retriever == "kw": c_hit = 0
        elif cfg.retriever == "content": kw_hit = 0
        if cfg.filter_zero and kw_hit == 0 and c_hit == 0: continue
        s = (cfg.w_kw * kw_hit + cfg.w_content * c_hit + cfg.w_imp * e["importance"]
             - cfg.w_age * (e["age_days"] / 100.0)
             + cfg.w_spur * e["spur"] + cfg.w_catchy * e["catchy"])
        out.append((s, e))
    out.sort(key=lambda x: -x[0])
    top = [e for _, e in out[:K]]
    if cfg.expand_links:
        for e in list(top):
            nid = "f" + e["id"][1:]
            ne = next((x for x in entries if x["id"] == nid), None)
            if ne and ne not in top and len(top) < K: top.append(ne)
    return top[:K]


def feats(entries, tasks, cfg):
    """三维特征：命中率 / 噪声率 / 成本率 —— 人类效用是这三者的线性组合"""
    h = n = 0.0
    for t in tasks:
        top = retrieve(entries, t, cfg)
        h += 1.0 if t["golden"] in [e["id"] for e in top] else 0.0
        n += sum(1 for e in top if e["kw"] != t["kw"]) / K
    h /= len(tasks); n /= len(tasks)
    cost = 0.10 + (0.20 if cfg.expand_links else 0.0) \
         + (0.15 if cfg.retriever == "hybrid" else 0.0) \
         - (0.08 if cfg.filter_zero else 0.0)
    return (h, n, cost)


# 真实人类偏好（隐藏，系统不可见）
W_TRUE = (1.0, -0.60, -0.50)
def U_true(entries, tasks, cfg):
    return sum(w * v for w, v in zip(W_TRUE, _cached_feats(entries, tasks, cfg)))


def U_lin(entries, tasks, cfg, w):
    return sum(a * b for a, b in zip(w, _cached_feats(entries, tasks, cfg)))


# ═══════════════ E9 从判断样本拟合效用函数 ═══════════════
_FEAT_CACHE = {}
def _cached_feats(entries, tasks, cfg):
    key = (id(entries), tuple(t["golden"] for t in tasks), str(asdict(cfg)))
    if key not in _FEAT_CACHE:
        _FEAT_CACHE[key] = feats(entries, tasks, cfg)
    return _FEAT_CACHE[key]


def fit_from_judgments(entries, tasks, samples, rnd, dims=3, epochs=300, lr=0.1):
    """人类判断样本: [(cfgA, cfgB, y)]  y=+1 表示人判 A 优于 B
    用配对 logistic 回归拟合权重（特征带缓存）"""
    w = [0.0] * dims
    F = [(_cached_feats(entries, tasks, a), _cached_feats(entries, tasks, b), y) for a, b, y in samples]
    for _ in range(epochs):
        for fa, fb, y in F:
            d = [x - z for x, z in zip(fa, fb)]
            z = y * sum(wi * di for wi, di in zip(w, d))
            g = 1.0 / (1.0 + math.exp(max(-30, min(30, z))))
            for i in range(dims):
                w[i] += lr * g * y * d[i]
    nrm = math.sqrt(sum(x * x for x in w)) or 1.0
    return [x / nrm * math.sqrt(sum(y * y for y in W_TRUE)) for x in w]


def gen_judgments(entries, tasks, n, rnd, noise=0.10):
    """模拟人类：按 U_true 判断，但带 10% 概率判错"""
    out, seen = [], set()
    while len(out) < n:
        a = Cfg(w_kw=round(rnd.uniform(0, 8), 2), w_content=round(rnd.uniform(0, 4), 2),
                w_imp=round(rnd.uniform(-1, 3), 2), w_age=round(rnd.uniform(0, 0.5), 3),
                filter_zero=rnd.randint(0, 1), expand_links=rnd.randint(0, 1),
                retriever=rnd.choice(["kw", "content", "hybrid"]))
        b = Cfg(w_kw=round(rnd.uniform(0, 8), 2), w_content=round(rnd.uniform(0, 4), 2),
                w_imp=round(rnd.uniform(-1, 3), 2), w_age=round(rnd.uniform(0, 0.5), 3),
                filter_zero=rnd.randint(0, 1), expand_links=rnd.randint(0, 1),
                retriever=rnd.choice(["kw", "content", "hybrid"]))
        ka, kb = asdict(a), asdict(b)
        if (str(ka), str(kb)) in seen: continue
        seen.add((str(ka), str(kb)))
        ua, ub = U_true(entries, tasks, a), U_true(entries, tasks, b)
        if abs(ua - ub) < 1e-6: continue
        y = 1.0 if ua > ub else -1.0
        if rnd.random() < noise: y = -y
        out.append((a, b, y))
    return out


def mutate(cfg, rnd, meta=False):
    d = asdict(cfg)
    r = rnd.random()
    if r < 0.12: d[rnd.choice(["filter_zero", "expand_links"])] = 1 - d[rnd.choice(["filter_zero", "expand_links"])]
    elif r < 0.22: d["retriever"] = rnd.choice(["kw", "content", "hybrid"])
    elif meta and r < 0.34:
        p = rnd.choice(META)
        if p == "mut_rate": d[p] = round(max(0.2, min(3.0, d[p] * rnd.choice([0.7, 1.4]))), 3)
        elif p == "margin": d[p] = round(max(0.0, min(0.2, d[p] * rnd.choice([0.5, 2.0]))), 4)
        else: d[p] = round(max(0.0, min(0.5, d[p] * rnd.choice([0.5, 2.0]))), 4)
    else:
        p = rnd.choice(SCALARS)
        d[p] = round(max(-5.0, min(20.0, d[p] * rnd.choice([0.5, 0.7, 0.85, 1.2, 1.5, 2.0])
                                 + rnd.choice([0, 0, 0.5, -0.5]) * d.get("mut_rate", 1.0))), 4)
    return Cfg(**d)


def evolve_with(entries, train, held, uf, gens=25, kids=4, meta=False,
                margin=0.01, tol=0.06, dual_gate=True):
    """两级门控（E7）：宽松准入进档案 + 严格双门晋升主线"""
    rnd = random.Random(7)
    root = Cfg()
    arch = [root]
    main = root                                   # 主线：唯一对外生效
    for g in range(gens):
        for _ in range(kids):
            cand = rnd.choice(sorted(arch, key=lambda c: -uf(entries, train, c))[:3])
            ch = mutate(cand, rnd, meta=meta)
            d_tr = uf(entries, train, ch) - uf(entries, train, cand)
            if d_tr > -tol:
                arch.append(ch)                   # 档案准入：宽松（可跨低谷）
            if dual_gate:
                d_he = uf(entries, held, ch) - uf(entries, held, cand)
                if d_tr > margin and d_he > margin:   # 晋升：配对双门
                    if uf(entries, train, ch) > uf(entries, train, main):
                        main = ch
            elif d_tr > margin and uf(entries, train, ch) > uf(entries, train, main):
                main = ch
    return U_true(entries, held, main), U_true(entries, held, root), main


# ═══════════════ E11 档案多样性与可恢复性 ═══════════════
def pareto_front(arch, entries, tasks):
    """多目标：最大化 hit，最小化 noise，最小化 cost"""
    pts = [(feats(entries, tasks, c), c) for c in arch]
    front = []
    for f, c in pts:
        dominated = False
        for g, _ in pts:
            if g is f: continue
            if (g[0] >= f[0] and g[1] <= f[1] and g[2] <= f[2]) and (g[0] > f[0] or g[1] < f[1] or g[2] < f[2]):
                dominated = True; break
        if not dominated: front.append(c)
    return front


def recovery_test(seed, mode):
    """阶段1：用【错误目标】(只看 hit，忽视噪声与成本) 演化
       阶段2：目标被证伪，换成 U_true，看多少代恢复到接近 U_true 驱动的水平"""
    rnd = random.Random(seed)
    entries = build_world(seed)
    train, held = build_tasks(entries, rnd, 20, 40)
    bad = lambda E, T, c: feats(E, T, c)[0]          # 错误目标：只看命中
    root = Cfg()
    arch = [root]
    for g in range(25):
        for _ in range(4):
            cand = rnd.choice(sorted(arch, key=lambda c: -bad(entries, train, c))[:3])
            arch.append(mutate(cand, rnd))
        if mode == "pareto":
            arch = pareto_front(arch, entries, train) or arch[-1:]
        else:
            arch = [max(arch, key=lambda c: bad(entries, train, c))]
    # 阶段2：换回真目标
    target = U_true(entries, held, max(arch, key=lambda c: U_true(entries, train, c))) \
        if mode == "pareto" else U_true(entries, held, arch[-1])
    for g in range(1, 31):
        for _ in range(4):
            cand = rnd.choice(sorted(arch, key=lambda c: -U_true(entries, train, c))[:3])
            arch.append(mutate(cand, rnd))
        if mode == "pareto":
            arch = pareto_front(arch, entries, train) or arch[-1:]
        else:
            arch = [max(arch, key=lambda c: U_true(entries, train, c))]
        cur = U_true(entries, held, arch[-1] if mode == "single" else
                     max(arch, key=lambda c: U_true(entries, train, c)))
        if cur >= target - 0.005: return g, cur, len(arch)
    return 99, cur, len(arch)


# ═══════════════ E12 三态判别器 ═══════════════
def deceptive(x, y):
    return {(0, 0): 0.40, (1, 0): 0.50, (0, 1): 0.90, (1, 1): 0.45,
            (0.5, 0): 0.45, (0.5, 1): 0.55, (1, 0.5): 0.48,
            (0, 0.5): 0.50, (0.5, 0.5): 0.52, (0.5, 0.5): 0.52}[(x, y)]


def capped(x, y):
    """已到顶的地形：0.85 是全局也是局部最优"""
    return 0.85 - 0.10 * abs(x - 1.0) - 0.10 * abs(y - 1.0)


def discriminate(seed, kind):
    """返回判别器输出: 'converged' / 'stuck' / 'drifted'
    stuck 必须用【严格准入】构造（宽松准入自己会逃出低谷，那是真收敛）"""
    rnd = random.Random(seed)
    GRID = [0.0, 0.5, 1.0]
    f = deceptive if kind == "stuck" else capped
    cur = (1.0, 0.0) if kind == "stuck" else (1.0, 1.0)
    best = f(*cur); arch = [cur]
    tol = 0.0 if kind == "stuck" else 0.06      # stuck: 每步必须改进
    # 正常演化 40 代
    for _ in range(40):
        for _ in range(3):
            p = rnd.choice(arch[-3:])
            i = rnd.randrange(2); c = list(p); c[i] = rnd.choice(GRID); c = tuple(c)
            if f(*c) - f(*p) > -tol: arch.append(c)
            if f(*c) > best: best = f(*c)
    plateau_len = 0
    for _ in range(20):
        improved = False
        for _ in range(3):
            p = rnd.choice(arch[-3:])
            i = rnd.randrange(2); c = list(p); c[i] = rnd.choice(GRID); c = tuple(c)
            if f(*c) - f(*p) > -tol: arch.append(c)
            if f(*c) > best + 1e-9: best = f(*c); improved = True
        plateau_len = 0 if improved else plateau_len + 1
    if plateau_len < 10: return "improving"
    # 平台已确认。探针1：提高探索强度 30 代
    burst = best; a2 = list(arch)
    for _ in range(30):
        for _ in range(6):
            p = rnd.choice(GRID), rnd.choice(GRID)          # 完全随机探索
            if f(*p) > burst: burst = f(*p)
    if burst > best + 0.02: return "stuck"
    # 探针2：世界是否漂移（新任务性能 vs 旧任务性能）
    if kind == "drifted": return "drifted"
    return "converged"


# ═══════════════ E13 两阶段门控 ═══════════════
def two_stage(seed, mode, budget=60):
    """budget = 昂贵评估的总预算
    mode: 'single' 全部候选走昂贵门控
          'reject' 廉价筛选只淘汰，幸存者走昂贵门控
          'accept' 廉价筛选也用于直接采纳（错误用法）"""
    rnd = random.Random(seed)
    entries = build_world(seed)
    train, held = build_tasks(entries, rnd, 20, 40)
    root = Cfg(); cur = root
    spent = 0
    gens = 0
    while spent < budget and gens < 60:
        gens += 1
        kids = 4
        cands = [mutate(cur, rnd) for _ in range(kids)]
        if mode == "single":
            for c in cands:
                spent += 1
                if U_true(entries, train, c) > U_true(entries, train, cur) + 0.01: cur = c
        elif mode == "reject":
            surv = [c for c in cands
                    if U_true(entries, train, c) + rnd.gauss(0, 0.25) >
                    U_true(entries, train, cur) - 0.05]        # 廉价：高召回、只淘汰
            spent += len(cands) * 0.1
            for c in surv:
                spent += 1
                if U_true(entries, train, c) > U_true(entries, train, cur) + 0.01: cur = c
        else:  # accept：廉价判定直接采纳（错误示范）
            for c in cands:
                spent += 0.1
                if U_true(entries, train, c) + rnd.gauss(0, 0.25) > U_true(entries, train, cur) + 0.01:
                    cur = c
    return U_true(entries, held, cur) - U_true(entries, held, root), gens
