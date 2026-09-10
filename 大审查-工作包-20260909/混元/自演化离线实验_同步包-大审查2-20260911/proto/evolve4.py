"""自演化推演实验 v4 —— 五个尚未回答的问题

E4 标注效率：用「配置间分歧」挑任务，能否在低标注预算下保住门控效力
E5 代理失效(Goodhart)：优化代理指标时真目标会怎样；小样本人工审计能否及时捕获
E6 结构演化：离散结构基因（检索器/过滤/扩散）能否被同一套门控驱动
E7 档案 vs 主线：双门用于「准入」还是仅用于「晋升」（能否跨越适应度低谷）
E8 留出集污染：长期用同一留出集做选择，会不会把它变成第二个训练集
"""
import random, statistics
from dataclasses import dataclass, asdict, replace

K, LAMBDA = 5, 0.15
TOPICS = [f"T{i}" for i in range(16)]


# ─────────────────── 世界 ───────────────────
def build_world(seed, n_entries=80, n_kws=10, reliability=0.6, catchy=True):
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
                        "catchy": 1.0 if (catchy and rnd.random() < 0.3) else 0.0})
    return entries


def build_tasks(entries, rnd, n_train, n_held, spur_bias_train=1.0, n_kws=10):
    """训练集：金标 spur=1（可被利用）；留出集：金标 spur=0（方向反转）"""
    train, held = [], []
    for i in range(n_train + n_held):
        grp = [e for e in entries if e["kw"] == f"K{i % n_kws}"]
        want = 1 if i < n_train else 0
        cands = [e for e in grp if e["spur"] == want] or grp
        g = rnd.choice(cands)
        (train if i < n_train else held).append(
            {"q": f"{g['topic']} {g['kw']}", "kw": g["kw"], "golden": g["id"]})
    return train, held


# ─────────────────── 配置与检索 ───────────────────
@dataclass(frozen=True)
class Cfg:
    w_kw: float = 3.0
    w_content: float = 1.0
    w_imp: float = 1.0
    w_age: float = 0.1
    w_spur: float = 0.0
    w_catchy: float = 0.0          # 「吸引力」权重：只有代理指标能看见它
    filter_zero: int = 0
    expand_links: int = 0          # 结构基因：一跳扩散
    retriever: str = "hybrid"      # 结构基因：kw / content / hybrid

SCALARS = ["w_kw", "w_content", "w_imp", "w_age", "w_spur", "w_catchy"]
STRUCTS = ["filter_zero", "expand_links", "retriever"]
LINK = {"e": "f"}                  # 简化链接表：e{i} → f{i//2}


def retrieve(entries, task, cfg):
    qw = task["q"].split()
    out = []
    for e in entries:
        kw_hit = sum(1 for w in qw if w in " ".join(e["keywords"]))
        c_hit = sum(1 for w in qw if w in e["content"])
        if cfg.retriever == "kw":
            c_hit = 0
        elif cfg.retriever == "content":
            kw_hit = 0
        if cfg.filter_zero and kw_hit == 0 and c_hit == 0:
            continue
        s = (cfg.w_kw * kw_hit + cfg.w_content * c_hit + cfg.w_imp * e["importance"]
             - cfg.w_age * (e["age_days"] / 100.0)
             + cfg.w_spur * e["spur"] + cfg.w_catchy * e["catchy"])
        out.append((s, e))
    out.sort(key=lambda x: -x[0])
    top = [e for _, e in out[:K]]
    if cfg.expand_links:                       # 一跳扩散：把邻居拉进结果
        base = {e["id"]: s for s, e in out}
        for e in list(top):
            nid = "f" + e["id"][1:]
            ne = next((x for x in entries if x["id"] == nid), None)
            if ne and ne not in top and len(top) < K:
                top.append(ne)
    return top[:K]


def true_util(entries, task, cfg):
    top = retrieve(entries, task, cfg)
    hit = 1.0 if task["golden"] in [e["id"] for e in top] else 0.0
    return hit - LAMBDA * sum(1 for e in top if e["kw"] != task["kw"])


def proxy_util(entries, task, cfg):
    """代理指标：模拟「点击率」—— 相关 +1，位置越靠前越容易点，越『吸睛』越容易点"""
    top = retrieve(entries, task, cfg)
    hit = 1.0 if task["golden"] in [e["id"] for e in top] else 0.0
    pos = 0.25 / (1 + ([e["id"] for e in top].index(task["golden"])
                       if task["golden"] in [e["id"] for e in top] else K))
    return hit + pos + 1.30 * sum(e["catchy"] for e in top) / K


def score(entries, tasks, cfg, fn=true_util):
    return sum(fn(entries, t, cfg) for t in tasks) / len(tasks)


def paired(entries, tasks, a, b, fn=true_util):
    return sum(fn(entries, t, a) - fn(entries, t, b) for t in tasks) / len(tasks)


def mutate(cfg, rnd, structural=True):
    d = asdict(cfg)
    r = rnd.random()
    if structural and r < 0.15:
        d[rnd.choice(["filter_zero", "expand_links"])] = 1 - d[rnd.choice(["filter_zero", "expand_links"])]
    elif structural and r < 0.25:
        d["retriever"] = rnd.choice(["kw", "content", "hybrid"])
    else:
        p = rnd.choice(SCALARS)
        d[p] = round(max(-5.0, min(20.0, d[p] * rnd.choice([0.5, 0.7, 0.85, 1.2, 1.5, 2.0])
                                   + rnd.choice([0, 0, 0.5, -0.5]))), 4)
    return Cfg(**d)


# ═══════════════ E4 标注效率：分歧采样 ═══════════════
def disagreement(entries, task, cfgs):
    """多个配置在同一任务上的真值分歧 = 该任务的信息量"""
    vals = [true_util(entries, task, c) for c in cfgs]
    return max(vals) - min(vals)


def evolve_sel(seed, n_train, mode="random", gens=25, kids=4, margin=0.01):
    rnd = random.Random(seed)
    entries = build_world(seed)
    pool, _ = build_tasks(entries, rnd, n_train + 40 + 80, 40)
    held = pool[n_train:n_train + 40]
    if mode == "random":
        train = pool[:n_train]
    else:  # 分歧采样：从未标注池里挑「配置们意见最不一致」的任务
        cfgs = [Cfg(), Cfg(w_kw=6.0), Cfg(w_imp=0.0), Cfg(filter_zero=1),
                Cfg(retriever="content"), Cfg(retriever="kw"), Cfg(expand_links=1)]
        unl = pool[n_train + 40:]
        unl.sort(key=lambda t: -disagreement(entries, t, cfgs))
        train = unl[:n_train]                      # 只标这 n_train 个
    root = Cfg()
    r0 = score(entries, held, root)
    arch = [{"cfg": root, "tr": score(entries, train, root), "he": r0}]
    for g in range(gens):
        for _ in range(kids):
            cand = rnd.choice(sorted(arch, key=lambda x: -x["tr"])[:3])
            ch = mutate(cand["cfg"], rnd, structural=True)
            ctr = score(entries, train, ch)
            if paired(entries, train, ch, cand["cfg"]) > margin and \
               paired(entries, held, ch, cand["cfg"]) > margin:
                arch.append({"cfg": ch, "tr": ctr, "he": score(entries, held, ch)})
    sb = max(arch, key=lambda x: x["tr"])
    return sb["he"] - r0, sb["cfg"].w_spur


# ═══════════════ E5 代理失效 (Goodhart) ═══════════════
def evolve_goodhart(seed, gens=40, kids=4, margin=0.005, audit_every=5, audit_n=5):
    rnd = random.Random(seed)
    entries = build_world(seed)
    train, held = build_tasks(entries, rnd, 30, 30)
    root = Cfg()
    arch = [{"cfg": root, "px": score(entries, train, root, proxy_util)}]
    hist, flagged_at = [], None
    for g in range(1, gens + 1):
        for _ in range(kids):
            cand = rnd.choice(sorted(arch, key=lambda x: -x["px"])[:3])
            ch = mutate(cand["cfg"], rnd, structural=True)
            # 门控用的是【代理指标】
            if paired(entries, train, ch, cand["cfg"], proxy_util) > margin and \
               paired(entries, held, ch, cand["cfg"], proxy_util) > margin:
                arch.append({"cfg": ch, "px": score(entries, train, ch, proxy_util)})
        sb = max(arch, key=lambda x: x["px"])
        t_true, t_proxy = score(entries, held, sb["cfg"]), score(entries, held, sb["cfg"], proxy_util)
        hist.append((g, t_true, t_proxy, sb["cfg"].w_catchy))
        if audit_every and g % audit_every == 0 and flagged_at is None:
            # 人工审计：抽 n 个任务，比对代理与真值
            samp = rnd.sample(held, min(audit_n, len(held)))
            a_p = [proxy_util(entries, t, sb["cfg"]) for t in samp]
            a_t = [true_util(entries, t, sb["cfg"]) for t in samp]
            mp, mt = statistics.mean(a_p), statistics.mean(a_t)
            # 正确判据：相对起点的【移动方向】是否背离（而非绝对值差）
            rp = score(entries, samp, root, proxy_util); rt = score(entries, samp, root)
            if (mp - rp) > 0.05 and (mt - rt) < -0.02:
                flagged_at = g
    return hist, flagged_at


# ═══════════════ E7 档案准入 vs 晋升 ═══════════════
def deceptive(x, y):
    """欺骗性地形：起点 (1,0)=0.50 是局部最优，(0,1)=0.90 是全局最优，中间隔着低谷"""
    return {(0, 0): 0.40, (1, 0): 0.50, (0, 1): 0.90, (1, 1): 0.45,
            (0.5, 0): 0.45, (0.5, 1): 0.55, (1, 0.5): 0.48,
            (0, 0.5): 0.50, (0.5, 0.5): 0.52}[(x, y)]


def evolve_valley(mode, seed, gens=60, kids=3, tol=0.06):
    """mode='strict' 双门用于准入；mode='loose' 档案宽松准入 + 双门仅用于晋升"""
    rnd = random.Random(seed)
    GRID = [0.0, 0.5, 1.0]
    cur = (1.0, 0.0)                      # 起点 = 局部最优
    best = deceptive(*cur)
    arch = [cur]
    for g in range(gens):
        for _ in range(kids):
            pnt = rnd.choice(arch[-3:] if mode == "loose" else [max(arch, key=lambda p: deceptive(*p))])
            i = rnd.randrange(2)
            cand = list(pnt); cand[i] = rnd.choice(GRID); cand = tuple(cand)
            d = deceptive(*cand) - deceptive(*pnt)
            if mode == "strict":
                if d > 0.0: arch.append(cand)
            else:
                if d > -tol: arch.append(cand)          # 档案宽松：允许中性/小幅退化
            if d > 0.0 and deceptive(*cand) > best:     # 晋升：始终严格
                best = deceptive(*cand)
    return best


# ═══════════════ E8 留出集污染 ═══════════════
def evolve_contam(seed, held_n=12, gens=300, kids=4, margin=0.01):
    rnd = random.Random(seed)
    entries = build_world(seed)
    train, held = build_tasks(entries, rnd, 12, held_n)
    fresh, _ = build_tasks(entries, random.Random(seed + 999), 40, 5)
    root = Cfg(); r0_fresh = score(entries, fresh, root)
    arch = [{"cfg": root, "tr": score(entries, train, root), "he": score(entries, held, root)}]
    trace = []
    for g in range(1, gens + 1):
        for _ in range(kids):
            cand = rnd.choice(sorted(arch, key=lambda x: -x["tr"])[:3])
            ch = mutate(cand["cfg"], rnd, structural=True)
            if paired(entries, train, ch, cand["cfg"]) > margin and \
               paired(entries, held, ch, cand["cfg"]) > margin:
                arch.append({"cfg": ch, "tr": score(entries, train, ch),
                             "he": score(entries, held, ch)})
        if g % 50 == 0:
            sb = max(arch, key=lambda x: x["tr"])
            trace.append((g, sb["he"] - score(entries, held, root),
                          score(entries, fresh, sb["cfg"]) - r0_fresh))
    return trace


if __name__ == "__main__":
    print("=" * 84)
    print("E4  标注效率：随机挑任务 vs 按「配置分歧」挑任务（20 种子）")
    print("=" * 84)
    print(f"{'标注预算':>8s} {'随机:留出集提升':>16s} {'分歧采样:留出集提升':>20s} {'提升差':>9s} {'随机采纳伪特征':>14s}")
    for nt in (6, 10, 16, 24):
        R = [evolve_sel(s, nt, "random") for s in range(1, 21)]
        D = [evolve_sel(s, nt, "disagree") for s in range(1, 21)]
        dr = statistics.mean(x[0] for x in R); dd = statistics.mean(x[0] for x in D)
        cr = sum(1 for x in R if x[1] > 0.5)
        print(f"{nt:>8d} {dr:>16.4f} {dd:>20.4f} {dd-dr:>9.4f} {cr:>11d}/20")

    print("\n" + "=" * 84)
    print("E5  代理失效(Goodhart)：门控用代理指标，真目标会怎样（12 种子，40 代）")
    print("=" * 84)
    flags, deltas = [], []
    for s in range(1, 13):
        hist, flag = evolve_goodhart(s)
        first, last = hist[0], hist[-1]
        deltas.append(last[1] - first[1])
        flags.append(flag)
    print(f"  真目标(留出集)变化   : {statistics.mean(deltas):+.4f}   为负的种子 {sum(1 for d in deltas if d<0)}/12")
    h0 = evolve_goodhart(1)[0]
    print(f"  单种子轨迹(seed=1)   : 代{h0[0][0]:>3d} 真={h0[0][1]:+.4f} 代理={h0[0][2]:.4f} w_catchy={h0[0][3]:.2f}")
    for g, t, p, w in h0:
        if g in (10, 20, 40): print(f"                        代{g:>3d} 真={t:+.4f} 代理={p:.4f} w_catchy={w:.2f}")
    det = [f for f in flags if f is not None]
    print(f"  人工审计(每5代审5条) : 捕获代理失效的种子 {len(det)}/12"
          f"   平均在第 {statistics.mean(det):.1f} 代捕获" if det else "  人工审计: 未捕获")

    print("\n" + "=" * 84)
    print("E6  结构演化：离散基因(检索器/过滤/扩散)加入后能否继续变好")
    print("=" * 84)
    for label, struct in (("仅标量参数", False), ("标量+结构基因", True)):
        res = []
        for s in range(1, 13):
            rnd = random.Random(s)
            entries = build_world(s)
            train, held = build_tasks(entries, rnd, 20, 40)
            root = Cfg(); r0 = score(entries, held, root)
            arch = [{"cfg": root, "tr": score(entries, train, root)}]
            for g in range(30):
                for _ in range(4):
                    cand = rnd.choice(sorted(arch, key=lambda x: -x["tr"])[:3])
                    ch = mutate(cand["cfg"], rnd, structural=struct)
                    if paired(entries, train, ch, cand["cfg"]) > 0.01 and \
                       paired(entries, held, ch, cand["cfg"]) > 0.01:
                        arch.append({"cfg": ch, "tr": score(entries, train, ch)})
            sb = max(arch, key=lambda x: x["tr"])
            res.append(score(entries, held, sb["cfg"]) - r0)
        print(f"  {label:12s}: 留出集提升 {statistics.mean(res):+.4f}  为正的种子 {sum(1 for x in res if x>0)}/12")

    print("\n" + "=" * 84)
    print("E7  档案准入 vs 晋升：双门该用在哪一层（欺骗性地形，局部0.50 / 全局0.90）")
    print("=" * 84)
    for mode, label in (("strict", "双门用于准入(每步必须变好)"), ("loose", "档案宽松准入 + 双门仅管晋升")):
        vals = [evolve_valley(mode, s) for s in range(1, 21)]
        esc = sum(1 for v in vals if v > 0.85)
        print(f"  {label:32s}: 终值均值 {statistics.mean(vals):.3f}   逃出局部最优 {esc}/20")

    print("\n" + "=" * 84)
    print("E8  留出集污染：长期用同一留出集做选择（12 条留出，300 代）")
    print("=" * 84)
    tr = [evolve_contam(s) for s in range(1, 9)]
    for i, g in enumerate([50, 100, 150, 200, 250, 300]):
        dh = statistics.mean(t[i][1] for t in tr)
        df = statistics.mean(t[i][2] for t in tr)
        print(f"  第{g:>3d} 代 : 留出集提升 {dh:+.4f}    全新任务集提升 {df:+.4f}    差距 {dh-df:+.4f}")
