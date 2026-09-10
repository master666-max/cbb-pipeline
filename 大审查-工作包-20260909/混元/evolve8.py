"""自演化推演实验 v8 —— 第六轮：五个悬而未决的风险

E24 元参数剥削通道（第五轮标为最高优先级未验证假设）：
    让 margin 能直接影响「自己是否被采纳」，看系统会不会把门控降到形同虚设
E25 注意力成本模型：标注/审计/裁决 的非线性成本，重做预算分配
E26 解冻策略：恢复 / 重锚 / 人工裁决，在什么条件下各自最优
E27 漂移可逆性：回滚到历史时点 vs 继续演化，哪个更能保住真实效用
E28 层次化归并 vs 平铺：多目标(8维)下的样本效率对比
"""
import random, math, statistics
from dataclasses import dataclass, asdict

K = 5
TOPICS = [f"T{i}" for i in range(16)]
_WORLD = [0]
_FC = {}


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
    deep: int = 0
    margin: float = 0.02          # 元参数（E24 中可被演化）

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


def feats(entries, tasks, cfg, dims=3):
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
    if dims > 3:
        rnd = random.Random(str(asdict(cfg)))
        while len(base) < dims:
            base.append(0.10 + 0.02 * len(base) * (1.0 if rnd.random() < 0.5 else 0.0)
                        + 0.001 * (cfg.w_kw + cfg.w_content) * rnd.random())
    _FC[key] = tuple(base[:dims])
    return _FC[key]


W0 = (1.0, -0.60, -0.50)
def U_w(entries, tasks, cfg, w, dims=3):
    return sum(a * b for a, b in zip(w, feats(entries, tasks, cfg, dims)))


def rand_cfg(rnd, margin=0.02):
    return Cfg(w_kw=round(rnd.uniform(0, 8), 2), w_content=round(rnd.uniform(0, 4), 2),
               w_imp=round(rnd.uniform(-1, 3), 2), w_age=round(rnd.uniform(0, 0.5), 3),
               w_spur=round(rnd.uniform(-1, 1), 2),
               filter_zero=rnd.randint(0, 1), deep=rnd.randint(0, 1), margin=margin)


def mutate(cfg, rnd, meta=False):
    d = asdict(cfg)
    r = rnd.random()
    if meta and r < 0.15:
        # 演化门控阈值本身 —— 这就是剥削通道
        d["margin"] = round(max(-0.20, min(0.20, d["margin"] + rnd.choice([-0.02, -0.01, 0.01, 0.02])
                                           * rnd.choice([1, 2]))), 4)
    elif r < 0.10: d["deep"] = 1 - d["deep"]
    elif r < 0.18: d["filter_zero"] = 1 - d["filter_zero"]
    else:
        p = rnd.choice(SCALARS)
        d[p] = round(max(-5.0, min(20.0, d[p] * rnd.choice([0.5, 0.7, 0.85, 1.2, 1.5, 2.0])
                                 + rnd.choice([0, 0, 0.5, -0.5]))), 4)
    return Cfg(**d)


def boot_lower(deltas, rnd, B=150, alpha=0.05):
    n = len(deltas)
    if n == 0: return 0.0
    vals = [statistics.mean(deltas[rnd.randrange(n)] for _ in range(n)) for _ in range(B)]
    vals.sort()
    return vals[int(alpha / 2 * B)]


def fit_w(entries, tasks, samples, dims=3, epochs=150, lr=0.1):
    w = [0.0] * dims
    F = [(feats(entries, tasks, a, dims), feats(entries, tasks, b, dims), y) for a, b, y in samples]
    for _ in range(epochs):
        for fa, fb, y in F:
            d = [x - z for x, z in zip(fa, fb)]
            z = y * sum(wi * di for wi, di in zip(w, d))
            g = 1.0 / (1.0 + math.exp(max(-30, min(30, z))))
            for i in range(dims):
                w[i] += lr * g * y * d[i]
    n = math.sqrt(sum(x * x for x in w)) or 1.0
    return [x / n * math.sqrt(sum(y * y for y in W0)) for x in w]


def collect(entries, tasks, n, rnd, w=None, dims=3, maxdiv=False):
    out, seen = [], set()
    while len(out) < n and len(seen) < n * 80:
        a, b = rand_cfg(rnd), rand_cfg(rnd)
        k = (str(asdict(a)), str(asdict(b)))
        if k in seen: continue
        seen.add(k)
        if maxdiv:
            for _ in range(6):
                c, d = rand_cfg(rnd), rand_cfg(rnd)
                if math.dist(feats(entries, tasks, c, dims), feats(entries, tasks, d, dims)) > \
                   math.dist(feats(entries, tasks, a, dims), feats(entries, tasks, b, dims)):
                    a, b = c, d
        ua, ub = U_w(entries, tasks, a, w or W0, dims), U_w(entries, tasks, b, w or W0, dims)
        if abs(ua - ub) < 1e-9: continue
        out.append((a, b, 1.0 if ua > ub else -1.0))
    return out


# ═══════════════ E24 元参数剥削通道 ═══════════════
def exp24(seed, mode, gens=30, kids=4, noise=0.05):
    """mode:
       frozen    —— margin 固定在 0.02（元参数冻结）
       free      —— margin 随配置一起演化（有剥削通道）
       bounded   —— margin 可演化但有下界 0.02
       bootstrap —— 门控用 bootstrap 下界 > margin，margin 可演化
       nolimit   —— margin 可演化，且有『采纳次数越多越好』的短期激励（最危险）
    """
    rnd = random.Random(seed)
    E = build_world(seed)
    tr, he = build_tasks(E, rnd, 14, 14)          # 小样本 → 噪声大，剥削空间大
    big, _ = build_tasks(E, random.Random(999), 5, 60)   # 真值：大样本无噪声
    root = Cfg(margin=0.02)
    arch = [root]; main = root
    adopts = 0
    for g in range(gens):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:])
            ch = mutate(cand, rnd, meta=(mode in ("free", "nolimit", "bounded", "bootstrap")))
            if mode == "bounded":
                ch = Cfg(**{**asdict(ch), "margin": max(0.02, ch.margin)})
            m = ch.margin
            d_tr = U_w(E, tr, ch, W0) - U_w(E, tr, cand, W0) + rnd.gauss(0, noise)
            d_he = U_w(E, he, ch, W0) - U_w(E, he, cand, W0) + rnd.gauss(0, noise)
            if mode == "bootstrap":
                dts = [U_w(E, [t], ch, W0) - U_w(E, [t], cand, W0) for t in tr]
                dhs = [U_w(E, [t], ch, W0) - U_w(E, [t], cand, W0) for t in he]
                ok = boot_lower(dts, rnd) > m and boot_lower(dhs, rnd) > m
            else:
                ok = d_tr > m and d_he > m
            if d_tr > -0.06: arch.append(ch)
            if ok:
                adopts += 1
                if mode == "nolimit" or U_w(E, tr, ch, W0) > U_w(E, tr, main, W0):
                    main = ch
        arch = arch[-30:]
    return U_w(E, big, main, W0), U_w(E, big, root, W0), main.margin, adopts


# ═══════════════ E25 注意力成本模型 ═══════════════
def exp25(seed, n_label, n_audit, audit_every, c_label=1.0, c_audit=3.0,
          c_arbitrate=10.0, gens=25, alpha=0.20):
    """非线性成本：标注 1 / 审计 3（上下文切换） / 裁决 10（深度思考）"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr, he = build_tasks(E, rnd, 20, 40)
    w_h = list(W0)
    samples = collect(E, tr, n_label, rnd, maxdiv=True)
    anchor = collect(E, tr, 30, rnd)
    w_fit = fit_w(E, tr, samples) if samples else list(W0)
    root = Cfg(); arch = [root]; main = root
    frozen = False; n_arb = 0
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
        f = feats(E, tr, main); fn = math.sqrt(sum(x * x for x in f)) or 1.0
        tgt = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
        w_h = [(1 - alpha) * wi + alpha * ti for wi, ti in zip(w_h, tgt)]
        if n_audit > 0 and g % audit_every == 0:
            samp = rnd.sample(anchor, min(n_audit, len(anchor)))
            acc = sum(1 for a, b, y in samp
                      if (U_w(E, tr, a, w_h) - U_w(E, tr, b, w_h)) * y > 0) / len(samp)
            if acc < 0.90:
                # 裁决：人判断是漂移还是真改主意 —— 这里假设人总能判对，并重新锚定
                n_arb += 1
                w_fit = fit_w(E, tr, collect(E, tr, max(8, n_label // 2), rnd))
                anchor = collect(E, tr, 30, rnd)
                w_h = list(W0)
    cost = n_label * c_label + (gens // max(1, audit_every)) * n_audit * c_audit + n_arb * c_arbitrate
    return U_w(E, he, main, W0), cost, U_w(E, he, root, W0)


# ═══════════════ E26 解冻策略 ═══════════════
def exp26(seed, strategy, drift_type, gens=30, alpha=0.15):
    """drift_type: 'transient' 瞬时污染（第10-13代被锚定，之后恢复）
                   'persistent' 持续漂移
                   'genuine' 人真的改主意（合法，应放行）
       strategy: 'resume' 冻结5代后恢复 / 'reanchor' 冻结后重采判断 / 'escalate' 先恢复，再触发则重锚"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr, he = build_tasks(E, rnd, 20, 40)
    w_h = list(W0); anchor = collect(E, tr, 30, rnd)
    w_fit = list(W0)
    root = Cfg(); arch = [root]; main = root
    frozen = 0; since = None; strikes = 0
    for g in range(1, gens + 1):
        acc = sum(1 for a, b, y in anchor
                  if (U_w(E, tr, a, w_h) - U_w(E, tr, b, w_h)) * y > 0) / len(anchor)
        if since is None and acc < 0.90:
            since = g; strikes += 1
        if since is not None:
            frozen += 1
            if g - since >= 5:
                if strategy == "resume":
                    since = None
                elif strategy == "reanchor":
                    w_fit = fit_w(E, tr, collect(E, tr, 20, rnd)); anchor = collect(E, tr, 30, rnd)
                    w_h = list(W0); since = None
                else:  # escalate：第二次触发才重锚
                    if strikes >= 2:
                        w_fit = fit_w(E, tr, collect(E, tr, 20, rnd)); anchor = collect(E, tr, 30, rnd)
                        w_h = list(W0)
                    since = None
            continue
        for _ in range(4):
            cand = rnd.choice(sorted(arch, key=lambda c: -U_w(E, tr, c, w_fit))[:3])
            ch = mutate(cand, rnd)
            if U_w(E, tr, ch, w_fit) - U_w(E, tr, cand, w_fit) > -0.06: arch.append(ch)
            if (U_w(E, tr, ch, w_fit) - U_w(E, tr, cand, w_fit) > 0.01 and
                    U_w(E, he, ch, w_fit) - U_w(E, he, cand, w_fit) > 0.01 and
                    U_w(E, tr, ch, w_fit) > U_w(E, tr, main, w_fit)): main = ch
        arch = arch[-30:]
        f = feats(E, tr, main); fn = math.sqrt(sum(x * x for x in f)) or 1.0
        tgt = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
        if drift_type == "transient" and 10 <= g <= 13:
            w_h = [(1 - alpha) * wi + alpha * ti for wi, ti in zip(w_h, tgt)]
        elif drift_type == "persistent":
            w_h = [(1 - alpha) * wi + alpha * ti for wi, ti in zip(w_h, tgt)]
        elif drift_type == "genuine":
            w_h = [(1 - 0.06) * wi + 0.06 * ti for wi, ti in zip(w_h, tgt)]  # 慢速、合法
        w_fit = [x + rnd.gauss(0, 0.02) for x in w_h]
    return U_w(E, he, main, W0), frozen, U_w(E, he, root, W0)


# ═══════════════ E27 漂移可逆性 ═══════════════
def exp27(seed, mode, gens=30, alpha=0.15):
    """mode: continue 继续演化 / rollback 检出后回滚到最早未污染配置 / rollback_then_evolve"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr, he = build_tasks(E, rnd, 20, 40)
    w_h = list(W0); anchor = collect(E, tr, 30, rnd)
    w_fit = list(W0)
    root = Cfg(); arch = [root]; main = root
    history = [root]
    rolled = False
    for g in range(1, gens + 1):
        acc = sum(1 for a, b, y in anchor
                  if (U_w(E, tr, a, w_h) - U_w(E, tr, b, w_h)) * y > 0) / len(anchor)
        if mode != "continue" and not rolled and acc < 0.90:
            # 回滚：回到档案中最早的、且当前真值最高的配置
            best_old = max(history[:max(1, len(history) // 3)], key=lambda c: U_w(E, he, c, W0))
            main = best_old
            w_fit = list(W0)
            arch = [main]
            if mode == "rollback_then_evolve":
                rolled = True           # 回滚后继续演化
            else:
                rolled = True
                history.append(main)
                continue
        if mode == "rollback" and rolled:
            continue                    # 回滚后停止演化
        for _ in range(4):
            cand = rnd.choice(sorted(arch, key=lambda c: -U_w(E, tr, c, w_fit))[:3])
            ch = mutate(cand, rnd)
            if U_w(E, tr, ch, w_fit) - U_w(E, tr, cand, w_fit) > -0.06: arch.append(ch)
            if (U_w(E, tr, ch, w_fit) - U_w(E, tr, cand, w_fit) > 0.01 and
                    U_w(E, he, ch, w_fit) - U_w(E, he, cand, w_fit) > 0.01 and
                    U_w(E, tr, ch, w_fit) > U_w(E, tr, main, w_fit)): main = ch
        arch = arch[-30:]; history.append(main)
        f = feats(E, tr, main); fn = math.sqrt(sum(x * x for x in f)) or 1.0
        tgt = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
        w_h = [(1 - alpha) * wi + alpha * ti for wi, ti in zip(w_h, tgt)]
        w_fit = [x + rnd.gauss(0, 0.02) for x in w_h]
    return U_w(E, he, main, W0), U_w(E, he, root, W0)


# ═══════════════ E28 层次化归并 vs 平铺 ═══════════════
def exp28(seed, n, flat=True, dims=8):
    """8 个目标：平铺(直接拟合 8 维权值) vs 层次化(先归 3 类，类内固定比例，只拟合 3 维权值)"""
    rnd = random.Random(seed * 31 + dims)
    E = build_world(seed)
    tr, _ = build_tasks(E, rnd, 20, 40)
    w_true = [rnd.gauss(0, 1) for _ in range(dims)]
    nrm = math.sqrt(sum(x * x for x in w_true)) or 1.0
    w_true = [x / nrm * 2.0 for x in w_true]
    samples = []
    while len(samples) < n:
        a, b = rand_cfg(rnd), rand_cfg(rnd)
        ua, ub = U_w(E, tr, a, w_true, dims), U_w(E, tr, b, w_true, dims)
        if abs(ua - ub) < 1e-9: continue
        samples.append((a, b, 1.0 if ua > ub else -1.0))
    if flat:
        w_fit = fit_w(E, tr, samples, dims=8, epochs=250)
        cands = [rand_cfg(rnd) for _ in range(40)]
        return _tau(E, tr, cands, w_fit, w_true, 8)
    # 层次化：把 8 维按固定分组压缩成 3 维（组内等权）
    G = [[0, 1, 2], [3, 4, 5], [6, 7]]
    def proj(f):
        return [sum(f[i] for i in g) / len(g) for g in G]
    wt3 = [sum(w_true[i] for i in g) / len(g) for g in G]
    s3 = [(a, b, y) for a, b, y in samples]
    w3 = fit_w(E, tr, s3, dims=3, epochs=250)
    # 用 3 维权值 + 组内等权，重建 8 维权重
    w8 = []
    for gi, g in enumerate(G):
        for _ in g: w8.append(w3[gi] / len(g))
    cands = [rand_cfg(rnd) for _ in range(40)]
    return _tau(E, tr, cands, w8, w_true, 8)


def _tau(E, tr, cands, w_fit, w_true, dims):
    agree = dis = 0
    for i in range(len(cands)):
        for j in range(i + 1, len(cands)):
            a = U_w(E, tr, cands[i], w_true, dims) - U_w(E, tr, cands[j], w_true, dims)
            b = U_w(E, tr, cands[i], w_fit, dims) - U_w(E, tr, cands[j], w_fit, dims)
            if a * b > 0: agree += 1
            elif a * b < 0: dis += 1
    return (agree - dis) / (agree + dis) if (agree + dis) else 0.0
