"""自演化推演实验 v7 —— 第五轮：五个未知问题

E19 自适应对手(红队变异)：变异算子主动寻找「刚好通过门控」的配置，能否被挡住？
    对比固定 margin 门控 vs bootstrap 门控的抗攻击性
E20 判断样本主动采集：随机配置对 vs 不确定性采样，样本效率差多少
E21 冻结机制的代价：误报导致系统停摆的损失，最优审计阈值与解冻策略
E22 注意力预算分配：固定预算下，标注 / 审计 / 解冻 三者怎么分最优
E23 效用维度与样本复杂度：E9 是 3 维，d=3/5/8 时达到 τ>0.9 需要多少样本
"""
import random, math, statistics
from dataclasses import dataclass, asdict

K = 5
TOPICS = [f"T{i}" for i in range(16)]


# ───────────────────────── 世界 ─────────────────────────
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
                        "len": rnd.randint(10, 100)})
    return entries


def build_tasks(entries, rnd, n_train, n_held, n_kws=6):
    train, held = [], []
    for i in range(n_train + n_held):
        grp = [e for e in entries if e["kw"] == f"K{i % n_kws}"]
        g = rnd.choice(grp)
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


_FC = {}
_WORLD = [0]          # 世界唯一编号（避免 id() 复用导致缓存串味）
def feats(entries, tasks, cfg, dims=3):
    """三维不可公度目标：命中 / 噪声 / 成本；可扩展到更高维（E23）"""
    key = (_WORLD[0], len(tasks), tuple(t["golden"] for t in tasks), str(asdict(cfg)), dims)
    if key in _FC: return _FC[key]
    h = n = 0.0
    for t in tasks:
        top = retrieve(entries, t, cfg)
        h += 1.0 if t["golden"] in [e["id"] for e in top] else 0.0
        n += sum(1 for e in top if e["kw"] != t["kw"]) / K
    h /= len(tasks); n /= len(tasks)
    cost = 0.10 + (0.45 if cfg.deep else 0.0) - (0.08 if cfg.filter_zero else 0.0)
    base = [h, n, cost]
    if dims > 3:                      # 额外维度：由配置派生的合成特征（E23）
        rnd = random.Random(str(asdict(cfg)))
        while len(base) < dims:
            base.append(0.10 + 0.02 * (len(base)) * (1.0 if rnd.random() < 0.5 else 0.0)
                        + 0.001 * (cfg.w_kw + cfg.w_content) * rnd.random())
    _FC[key] = tuple(base[:dims])
    return _FC[key]


W0 = (1.0, -0.60, -0.50)
def U_w(entries, tasks, cfg, w, dims=3):
    return sum(a * b for a, b in zip(w, feats(entries, tasks, cfg, dims)))


def rand_cfg(rnd):
    return Cfg(w_kw=round(rnd.uniform(0, 8), 2), w_content=round(rnd.uniform(0, 4), 2),
               w_imp=round(rnd.uniform(-1, 3), 2), w_age=round(rnd.uniform(0, 0.5), 3),
               w_spur=round(rnd.uniform(-1, 1), 2),
               filter_zero=rnd.randint(0, 1), deep=rnd.randint(0, 1))


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


def bootstrap_lower(deltas, rnd, B=200, alpha=0.05):
    n = len(deltas); vals = []
    for _ in range(B):
        vals.append(statistics.mean(deltas[rnd.randrange(n)] for _ in range(n)))
    vals.sort()
    return vals[int(alpha / 2 * B)]


# ═══════════════ E19 自适应对手（红队变异）═══════════════
def red_team_child(entries, train, held, parent, w, rnd, gate, margin, tries=8):
    """红队：生成多个变异，专挑『刚好通过门控』的那个（Δ 略高于 margin）"""
    cands = [mutate(parent, rnd) for _ in range(tries)]
    scored = []
    for c in cands:
        d_tr = U_w(entries, train, c, w) - U_w(entries, train, parent, w)
        d_he = U_w(entries, held, c, w) - U_w(entries, held, parent, w)
        if gate == "bootstrap":
            ok = (bootstrap_lower([U_w(entries, train, c, w) - U_w(entries, train, parent, w)
                                   for _ in range(0)], rnd) if False else
                  d_tr > margin and d_he > margin)
        else:
            ok = d_tr > margin and d_he > margin
        if ok: scored.append((abs(d_tr - margin) + abs(d_he - margin), c))
    if scored:
        scored.sort(key=lambda x: x[0])
        return scored[0][1]                     # 最接近阈值 = 最省力的通过
    return rnd.choice(cands)


def evolve_adversarial(seed, mode, gate, gens=25, kids=4, margin=0.01, tol=0.06,
                       noise=0.0):
    """mode: 'random' 普通变异 / 'redteam' 红队变异
    noise: 评估噪声（模拟小样本评估的随机性）"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr, he = build_tasks(E, rnd, 12, 12)        # 小样本 → 噪声大（E17 场景）
    w = W0
    root = Cfg(); arch = [root]; main = root
    for g in range(gens):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:])
            if mode == "random":
                ch = mutate(cand, rnd)
            else:
                ch = red_team_child(E, tr, he, cand, w, rnd, gate, margin)
            d_tr = U_w(E, tr, ch, w) - U_w(E, tr, cand, w) + rnd.gauss(0, noise)
            d_he = U_w(E, he, ch, w) - U_w(E, he, cand, w) + rnd.gauss(0, noise)
            if d_tr > -tol: arch.append(ch)
            if gate == "bootstrap":
                # 用逐任务 delta 做 bootstrap
                dts = [U_w(E, [t], ch, w) - U_w(E, [t], cand, w) for t in tr]
                dhs = [U_w(E, [t], ch, w) - U_w(E, [t], cand, w) for t in he]
                ok = (bootstrap_lower(dts, rnd) > margin and bootstrap_lower(dhs, rnd) > margin)
            else:
                ok = d_tr > margin and d_he > margin
            if ok and U_w(E, tr, ch, w) > U_w(E, tr, main, w): main = ch
        arch = arch[-30:]
    # 用【大样本、无噪声】的真值衡量
    big, _ = build_tasks(E, random.Random(999), 5, 60)
    return U_w(E, big, main, w), U_w(E, big, root, w)


# ═══════════════ E20 判断样本主动采集 ═══════════════
def fit_w(entries, tasks, samples, weights=None, dims=3, epochs=150, lr=0.1):
    w = [0.0] * dims
    if weights is None: weights = [1.0] * len(samples)
    F = [(feats(entries, tasks, a, dims), feats(entries, tasks, b, dims), y, wt)
         for (a, b, y), wt in zip(samples, weights)]
    for _ in range(epochs):
        for fa, fb, y, wt in F:
            d = [x - z for x, z in zip(fa, fb)]
            z = y * sum(wi * di for wi, di in zip(w, d))
            g = 1.0 / (1.0 + math.exp(max(-30, min(30, z))))
            for i in range(dims):
                w[i] += lr * wt * g * y * d[i]
    n = math.sqrt(sum(x * x for x in w)) or 1.0
    return [x / n * math.sqrt(sum(y * y for y in W0)) for x in w]


def collect(entries, tasks, n, rnd, w_cur=None, pool=None):
    """strategy: 随机配对 vs 不确定性采样（挑 w_cur 下最难分的一对）"""
    out, seen = [], set()
    tries = 0
    while len(out) < n and tries < n * 60:
        tries += 1
        if pool is not None and w_cur is not None and len(pool) >= 2:
            a, b = rnd.sample(pool, 2)
        else:
            a, b = rand_cfg(rnd), rand_cfg(rnd)
        ka, kb = str(asdict(a)), str(asdict(b))
        if (ka, kb) in seen: continue
        seen.add((ka, kb))
        ua, ub = U_w(entries, tasks, a, W0), U_w(entries, tasks, b, W0)
        if abs(ua - ub) < 1e-9: continue
        out.append((a, b, 1.0 if ua > ub else -1.0))
    return out


def active_collect(entries, tasks, n, rnd, w_cur, pool, cand_n=40):
    """不确定性采样：先随机抽 cand_n 个候选对，用 w_cur 打分，挑 |Δ| 最小的"""
    out, seen = [], set()
    while len(out) < n:
        batch = []
        for _ in range(cand_n):
            a, b = rnd.sample(pool, 2) if len(pool) >= 2 else (rand_cfg(rnd), rand_cfg(rnd))
            ka, kb = str(asdict(a)), str(asdict(b))
            if (ka, kb) in seen: continue
            seen.add((ka, kb))
            d = abs(U_w(entries, tasks, a, w_cur) - U_w(entries, tasks, b, w_cur))
            batch.append((d, a, b))
        if not batch: break
        batch.sort(key=lambda x: x[0])
        for d, a, b in batch[:max(1, n // 10)]:
            ua, ub = U_w(entries, tasks, a, W0), U_w(entries, tasks, b, W0)
            if abs(ua - ub) < 1e-9: continue
            out.append((a, b, 1.0 if ua > ub else -1.0))
            if len(out) >= n: break
    return out


def tau_of(entries, tasks, w_fit, cands, w_true, dims=3):
    agree = dis = 0
    for i in range(len(cands)):
        for j in range(i + 1, len(cands)):
            a = U_w(entries, tasks, cands[i], w_true, dims) - U_w(entries, tasks, cands[j], w_true, dims)
            b = U_w(entries, tasks, cands[i], w_fit, dims) - U_w(entries, tasks, cands[j], w_fit, dims)
            if a * b > 0: agree += 1
            elif a * b < 0: dis += 1
    return (agree - dis) / (agree + dis) if (agree + dis) else 0.0


# ═══════════════ E21 冻结机制的代价 ═══════════════
def freeze_sim(seed, thresh, unfreeze, alpha_real, gens=30):
    """alpha_real: 人【真的】改主意的速率（0 = 纯漂移；>0 = 真实偏好演化）
    unfreeze: 'auto' 第 k 代自动解冻 / 'human' 需人工（延迟 d 代）
    返回：真实效用终值、被冻结的代数"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr, he = build_tasks(E, rnd, 20, 40)
    w_human = list(W0)
    anchor = collect(E, tr, 30, rnd)
    root = Cfg(); arch = [root]; main = root
    frozen = 0; frozen_since = None
    for g in range(1, gens + 1):
        acc = sum(1 for a, b, y in anchor
                  if (U_w(E, tr, a, w_human) - U_w(E, tr, b, w_human)) * y > 0) / len(anchor)
        if frozen_since is None and acc < thresh:
            frozen_since = g
        if frozen_since is not None:
            frozen += 1
            if unfreeze == "auto" and g - frozen_since >= 5:
                frozen_since = None                      # 自动解冻（5 代后）
            elif unfreeze == "human":
                pass                                     # 需人工，本模拟中不解冻
            continue
        for _ in range(4):
            cand = rnd.choice(sorted(arch, key=lambda c: -U_w(E, tr, c, w_human))[:3])
            ch = mutate(cand, rnd)
            if U_w(E, tr, ch, w_human) - U_w(E, tr, cand, w_human) > -0.06: arch.append(ch)
            if (U_w(E, tr, ch, w_human) - U_w(E, tr, cand, w_human) > 0.01 and
                    U_w(E, he, ch, w_human) - U_w(E, he, cand, w_human) > 0.01 and
                    U_w(E, tr, ch, w_human) > U_w(E, tr, main, w_human)): main = ch
        arch = arch[-30:]
        # 人的偏好：真实演化(alpha_real) 或 被系统锚定
        f = feats(E, tr, main)
        fn = math.sqrt(sum(x * x for x in f)) or 1.0
        tgt = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
        w_human = [(1 - alpha_real) * wi + alpha_real * ti for wi, ti in zip(w_human, tgt)]
    return U_w(E, he, main, W0), frozen, U_w(E, he, root, W0)


# ═══════════════ E22 注意力预算分配 ═══════════════
def budget_sim(seed, n_label, n_audit, audit_every, gens=25, alpha=0.10):
    """预算 = 标注 n_label 条 + 每次审计 n_audit 条（每 audit_every 代一次）
    人的注意力成本 ≈ n_label + n_audit * (gens // audit_every)
    测：不同分配在【人被锚定】环境下的真实效用"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr, he = build_tasks(E, rnd, 20, 40)
    samples = collect(E, tr, n_label, rnd)
    anchor = collect(E, tr, 30, rnd)
    w_human = list(W0)
    w_fit = fit_w(E, tr, samples) if samples else list(W0)
    root = Cfg(); arch = [root]; main = root
    frozen = False
    for g in range(1, gens + 1):
        if not frozen:
            for _ in range(4):
                cand = rnd.choice(sorted(arch, key=lambda c: -U_w(E, tr, c, w_fit))[:3])
                ch = mutate(cand, rnd)
                if U_w(E, tr, ch, w_fit) - U_w(E, tr, cand, w_fit) > -0.06: arch.append(ch)
                if (U_w(E, tr, ch, w_fit) - U_w(E, tr, cand, w_fit) > 0.01 and
                        U_w(E, he, ch, w_fit) - U_w(E, he, cand, w_fit) > 0.01 and
                        U_w(E, tr, ch, w_fit) > U_w(E, tr, main, w_fit)): main = ch
            arch = arch[-30:]
        # 人被锚定
        f = feats(E, tr, main)
        fn = math.sqrt(sum(x * x for x in f)) or 1.0
        tgt = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
        w_human = [(1 - alpha) * wi + alpha * ti for wi, ti in zip(w_human, tgt)]
        # 审计
        if n_audit > 0 and g % audit_every == 0:
            samp = rnd.sample(anchor, min(n_audit, len(anchor)))
            acc = sum(1 for a, b, y in samp
                      if (U_w(E, tr, a, w_human) - U_w(E, tr, b, w_human)) * y > 0) / len(samp)
            if acc < 0.90:
                frozen = True
                w_fit = fit_w(E, tr, anchor[:n_label]) if n_label else list(W0)  # 回退到锚定
    cost = n_label + n_audit * (gens // max(1, audit_every))
    return U_w(E, he, main, W0), cost, U_w(E, he, root, W0)


# ═══════════════ E23 维度与样本复杂度 ═══════════════
def dim_experiment(seed, dims, n, rnd):
    E = build_world(seed)
    tr, _ = build_tasks(E, rnd, 20, 40)
    rnd2 = random.Random(seed * 7 + dims)
    w_true = [rnd2.gauss(0, 1) for _ in range(dims)]
    nrm = math.sqrt(sum(x * x for x in w_true)) or 1.0
    w_true = [x / nrm * 2.0 for x in w_true]
    samples = []
    while len(samples) < n:
        a, b = rand_cfg(rnd), rand_cfg(rnd)
        ua, ub = U_w(E, tr, a, w_true, dims), U_w(E, tr, b, w_true, dims)
        if abs(ua - ub) < 1e-9: continue
        samples.append((a, b, 1.0 if ua > ub else -1.0))
    w_fit = fit_w(E, tr, samples, dims=dims, epochs=250)
    cands = [rand_cfg(rnd) for _ in range(40)]
    return tau_of(E, tr, w_fit, cands, w_true, dims)
