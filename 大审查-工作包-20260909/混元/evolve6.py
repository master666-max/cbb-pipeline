"""自演化推演实验 v6 —— 第四轮：五个更深层的问题

E14 内生评判者漂移：系统输出会塑造评判它的人吗？（"讨好人" vs "变好"）
E15 不可公度目标：Pareto 前沿上谁来做最终选择？人每次选 / 固定权重 / 词典式 / 约束式
E16 灾难性遗忘：转向新目标后旧能力保持多少？Pareto 档案与 replay 能否缓解
E17 margin 的统计基础：固定阈值 vs 置换检验 vs bootstrap，在样本量变化时谁更稳
E18 跨库迁移：一个库演化出的配置迁移到另一任务分布，什么条件下有效
"""
import random, math, statistics
from dataclasses import dataclass, asdict

K = 5
TOPICS = [f"T{i}" for i in range(16)]


# ───────────────────────── 世界 ─────────────────────────
def build_world(seed, n_entries=60, n_kws=6, reliability=0.32):
    rnd = random.Random(seed)
    entries = []
    for i in range(n_entries):
        k, t = i % n_kws, TOPICS[i % 16]
        tok = t if rnd.random() < reliability else rnd.choice(TOPICS)
        entries.append({"id": f"e{i}", "kw": f"K{k}", "topic": t,
                        "keywords": [f"K{k}"], "content": f"{tok} K{k} 片段{i}",
                        "importance": rnd.randint(1, 3),
                        "age_days": rnd.randint(0, 400),
                        "spur": 1 if rnd.random() < 0.5 else 0})
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
    expand_links: int = 0
    deep: int = 0
    retriever: str = "hybrid"

SCALARS = ["w_kw", "w_content", "w_imp", "w_age", "w_spur"]


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
             - cfg.w_age * (e["age_days"] / 100.0) + cfg.w_spur * e["spur"])
        out.append((s, e))
    out.sort(key=lambda x: -x[0])
    if cfg.deep:
        # 深度检索：先锁定同 keyword 组，再用 topic token 精确复核
        kw = next((w for w in qw if w.startswith("K")), None)
        toks = [w for w in qw if w.startswith("T")]
        pool = [e for _, e in out if (kw is None or kw in e["keywords"])]
        if toks:
            pool.sort(key=lambda e: -(1 if toks[0] in e["content"] else 0))
        top = pool[:K]
    else:
        top = [e for _, e in out[:K]]
    if cfg.expand_links:
        for e in list(top):
            idx = (int(e["id"][1:]) + 3) % len(entries)      # 链接到真实存在的邻居
            ne = entries[idx]
            if ne not in top and len(top) < K: top.append(ne)
    return top[:K]


_FC = {}
def feats(entries, tasks, cfg):
    """三维不可公度目标：命中率 / 噪声率 / 成本率"""
    key = (id(entries), len(tasks), tuple(t["golden"] for t in tasks), str(asdict(cfg)))
    if key in _FC: return _FC[key]
    h = n = 0.0
    for t in tasks:
        top = retrieve(entries, t, cfg)
        h += 1.0 if t["golden"] in [e["id"] for e in top] else 0.0
        n += sum(1 for e in top if e["kw"] != t["kw"]) / K
    h /= len(tasks); n /= len(tasks)
    cost = 0.10 + (0.20 if cfg.expand_links else 0.0) \
         + (0.15 if cfg.retriever == "hybrid" else 0.0) \
         - (0.08 if cfg.filter_zero else 0.0) \
         + (0.45 if cfg.deep else 0.0)        # 深度检索显著提成本
    _FC[key] = (h, n, cost)
    return _FC[key]


W0 = (1.0, -0.60, -1.50)          # 人类最初的真实偏好：很在意成本
W1 = (1.0, -0.60, 0.00)           # 人改主意：不在乎成本了
def U_w(entries, tasks, cfg, w):
    return sum(a * b for a, b in zip(w, feats(entries, tasks, cfg)))


def mutate(cfg, rnd):
    d = asdict(cfg)
    r = rnd.random()
    if r < 0.10: d["deep"] = 1 - d["deep"]
    elif r < 0.20: d[rnd.choice(["filter_zero", "expand_links"])] = 1 - d[rnd.choice(["filter_zero", "expand_links"])]
    elif r < 0.22: d["retriever"] = rnd.choice(["kw", "content", "hybrid"])
    else:
        p = rnd.choice(SCALARS)
        d[p] = round(max(-5.0, min(20.0, d[p] * rnd.choice([0.5, 0.7, 0.85, 1.2, 1.5, 2.0])
                                 + rnd.choice([0, 0, 0.5, -0.5]))), 4)
    return Cfg(**d)


def rand_cfg(rnd):
    return Cfg(w_kw=round(rnd.uniform(0, 8), 2), w_content=round(rnd.uniform(0, 4), 2),
               w_imp=round(rnd.uniform(-1, 3), 2), w_age=round(rnd.uniform(0, 0.5), 3),
               w_spur=round(rnd.uniform(-1, 1), 2), deep=rnd.randint(0, 1),
               filter_zero=rnd.randint(0, 1), expand_links=rnd.randint(0, 1),
               retriever=rnd.choice(["kw", "content", "hybrid"]))


def pareto_front(cfgs, entries, tasks):
    pts = [(feats(entries, tasks, c), c) for c in cfgs]
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


# ═══════════════ E14 内生评判者漂移 ═══════════════
def evolve_endog(seed, alpha, gens=25, kids=4, margin=0.01, tol=0.06,
                 anchor_audit=False, detect_thresh=0.75):
    """人类权重 w 被系统当前输出锚定：w ← (1-α)·w + α·dir(feats(main))
    测：感知效用(用 w_t) 上升 vs 真实效用(用 W0) 是否也上升
    anchor_audit: 用系统出现前采集的『锚定判断』定期审计，能否检出漂移"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr, he = build_tasks(E, rnd, 20, 40)
    w = list(W0)
    root = Cfg(); arch = [root]; main = root
    # 锚定样本：用 W0 在系统演化【之前】生成，之后不再更新
    anchor = []
    for _ in range(30):
        a, b = rand_cfg(rnd), rand_cfg(rnd)
        ua, ub = U_w(E, tr, a, W0), U_w(E, tr, b, W0)
        if abs(ua - ub) < 1e-9: continue
        anchor.append((a, b, 1.0 if ua > ub else -1.0))
    detected_at = None
    for g in range(1, gens + 1):
        for _ in range(kids):
            cand = rnd.choice(sorted(arch, key=lambda c: -U_w(E, tr, c, w))[:3])
            ch = mutate(cand, rnd)
            if U_w(E, tr, ch, w) - U_w(E, tr, cand, w) > -tol: arch.append(ch)
            if (U_w(E, tr, ch, w) - U_w(E, tr, cand, w) > margin and
                    U_w(E, he, ch, w) - U_w(E, he, cand, w) > margin and
                    U_w(E, tr, ch, w) > U_w(E, tr, main, w)):
                main = ch
        # 人类被系统输出锚定
        if alpha > 0:
            f = feats(E, tr, main)
            fn = math.sqrt(sum(x * x for x in f)) or 1.0
            target = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
            w = [(1 - alpha) * wi + alpha * ti for wi, ti in zip(w, target)]
        if anchor_audit and detected_at is None and g % 3 == 0:
            acc = sum(1 for a, b, y in anchor
                      if (U_w(E, tr, a, w) - U_w(E, tr, b, w)) * y > 0) / len(anchor)
            if acc < detect_thresh: detected_at = g
    return {"true": U_w(E, he, main, W0), "perceived": U_w(E, he, main, w),
            "root_true": U_w(E, he, root, W0), "drift": math.dist(w, W0),
            "detected": detected_at}


# ═══════════════ E15 不可公度目标的选择策略 ═══════════════
def choose(entries, tasks, cfgs, strategy, w, rnd):
    """从 Pareto 前沿选一个作为主线"""
    front = pareto_front(cfgs, entries, tasks) or list(cfgs)
    if strategy == "fixed":
        return max(cfgs, key=lambda c: U_w(entries, tasks, c, w))
    if strategy == "human_pick":        # 人按真实偏好 W0 从前沿里挑
        return max(front, key=lambda c: U_w(entries, tasks, c, W0))
    if strategy == "lexicographic":     # 词典式：先命中，再噪声，再成本
        return min(front, key=lambda c: (-round(feats(entries, tasks, c)[0], 2),
                                         round(feats(entries, tasks, c)[1], 2),
                                         round(feats(entries, tasks, c)[2], 2)))
    if strategy == "constrained":       # 命中≥阈值下最小化 (噪声+成本)
        ok = [c for c in front if feats(entries, tasks, c)[0] >= 0.75] or front
        return min(ok, key=lambda c: feats(entries, tasks, c)[1] + feats(entries, tasks, c)[2])
    return max(cfgs, key=lambda c: U_w(entries, tasks, c, w))


def evolve_choice(seed, strategy, gens=30, kids=4, switch_at=15, tol=0.06, margin=0.01):
    """第 switch_at 代：人的偏好从 W0 突变到 W1，看各策略恢复能力"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr, he = build_tasks(E, rnd, 20, 40)
    root = Cfg(); arch = [root]
    for g in range(1, gens + 1):
        w = W0 if g < switch_at else W1
        for _ in range(kids):
            cand = rnd.choice(sorted(arch, key=lambda c: -U_w(E, tr, c, w))[:3])
            ch = mutate(cand, rnd)
            if U_w(E, tr, ch, w) - U_w(E, tr, cand, w) > -tol: arch.append(ch)
        arch = arch[-40:]             # 档案上限，防爆炸
    final = choose(E, he, arch, strategy, W1, rnd)
    return U_w(E, he, final, W1), U_w(E, he, root, W1)


# ═══════════════ E16 灾难性遗忘 ═══════════════
def evolve_forget(seed, mode, gens=20, kids=4, tol=0.06, margin=0.01):
    """阶段1 优化 A=命中；阶段2 优化 B=最小化(噪声+成本)；测 A 保留多少
    mode: single / pareto / pareto_replay(档案保留阶段1前沿且定期用 A 任务复测)"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr, he = build_tasks(E, rnd, 20, 40)
    uA = lambda c: feats(E, tr, c)[0]                       # 目标A：命中
    uB = lambda c: -(feats(E, tr, c)[1] + feats(E, tr, c)[2])   # 目标B：省
    root = Cfg(); arch = [root]
    for phase, uf in ((1, uA), (2, uB)):
        for _ in range(gens):
            for _ in range(kids):
                cand = rnd.choice(sorted(arch, key=lambda c: -uf(c))[:3])
                ch = mutate(cand, rnd)
                if uf(ch) - uf(cand) > -tol: arch.append(ch)
            if mode == "single":
                arch = [max(arch, key=uf)]
            elif mode == "pareto":
                arch = pareto_front(arch, E, tr) or arch[-1:]
            else:  # pareto_replay：前沿 + 阶段1最优常驻
                front = pareto_front(arch, E, tr) or arch[-1:]
                bestA = max(arch, key=uA)
                arch = front + [bestA]
            arch = arch[-40:]
    final = max(arch, key=uB)
    # 能力保持 = 档案里 A(命中) 的最高值 —— 若目标切回 A，能立刻拿回多少
    retained_A = max(feats(E, he, c)[0] for c in arch)
    return retained_A, feats(E, he, final)[1] + feats(E, he, final)[2], feats(E, he, root)[0]


# ═══════════════ E17 margin 的统计基础 ═══════════════
def gate_decide(deltas, method, margin, rnd):
    """deltas = 每个任务上的 Δutility。返回是否采纳"""
    n = len(deltas)
    mean = statistics.mean(deltas)
    if method == "fixed":
        return mean > margin
    if method == "perm":
        # 置换检验：随机翻转符号，看真实均值是否显著
        cnt = 0; B = 200
        obs = abs(mean)
        for _ in range(B):
            s = sum(d * rnd.choice([1, -1]) for d in deltas) / n
            if abs(s) >= obs: cnt += 1
        return (cnt + 1) / (B + 1) < 0.05
    if method == "bootstrap":
        B = 200; vals = []
        for _ in range(B):
            samp = [deltas[rnd.randrange(n)] for _ in range(n)]
            vals.append(statistics.mean(samp))
        vals.sort()
        lo = vals[int(0.025 * B)]
        return lo > 0
    return mean > margin


def margin_experiment(seed, n_tasks, method, margin, effect=0.0):
    """effect=0 → 测假阳性率（Δ 纯噪声）；effect>0 → 测检出率"""
    rnd = random.Random(seed)
    deltas = [rnd.gauss(effect, 0.5) for _ in range(n_tasks)]
    return 1.0 if gate_decide(deltas, method, margin, rnd) else 0.0


# ═══════════════ E18 跨库迁移 ═══════════════
def evolve_transfer(src_seed, dst_seed, mode, gens=25, kids=4, tol=0.06, margin=0.01,
                    ft_gens=10):
    """源库演化 → 迁移到目标库
    mode: from_scratch(目标库从零演化) / direct(直接搬) / finetune(搬后微调)"""
    def run(seed, init=None, gens=gens, tasks=None):
        rnd = random.Random(seed)
        E = build_world(seed)
        tr, he = tasks or build_tasks(E, rnd, 20, 40)
        arch = [init] if init else [Cfg()]
        main = arch[0]
        for _ in range(gens):
            for _ in range(kids):
                cand = rnd.choice(sorted(arch, key=lambda c: -U_w(E, tr, c, W0))[:3])
                ch = mutate(cand, rnd)
                if U_w(E, tr, ch, W0) - U_w(E, tr, cand, W0) > -tol: arch.append(ch)
                if (U_w(E, tr, ch, W0) - U_w(E, tr, cand, W0) > margin and
                        U_w(E, he, ch, W0) - U_w(E, he, cand, W0) > margin and
                        U_w(E, tr, ch, W0) > U_w(E, tr, main, W0)): main = ch
            arch = arch[-40:]
        return main, E, tr, he
    src, _, _, _ = run(src_seed, None, gens)
    E2 = build_world(dst_seed)
    rnd2 = random.Random(dst_seed * 31)
    tr2, he2 = build_tasks(E2, rnd2, 20, 40)
    if mode == "from_scratch":
        main, _, _, _ = run(dst_seed, None, gens, tasks=(tr2, he2))
    elif mode == "direct":
        main = src
    else:
        main, _, _, _ = run(dst_seed, src, ft_gens, tasks=(tr2, he2))
    base = U_w(E2, he2, Cfg(), W0)
    return U_w(E2, he2, main, W0) - base
