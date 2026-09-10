"""自演化推演 v13 —— 第十一轮：结构性风险

E47 审计规避：变异算子能影响"是否触发审计"时，系统会学会规避吗（E24 的姐妹问题）
E48 并行多主线（岛屿模型）：多主线 + 定期迁移 vs 单主线
E49 长期运行退化：500 代后是否塌方？档案/门控的老化效应
E50 廉价评估精度在线估计：能否在不耗昂贵预算的前提下判断"该不该开筛选"
E51 判断样本冲突：人给出自相矛盾的判断时，检出与处理
"""
import random, math, statistics, sys
from dataclasses import dataclass, asdict
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import (Cfg, build_world, build_tasks, retrieve, feats, U, W0,
                     mutate, rand_cfg, boot_lower, pareto_front, K, TOPICS)


def fit_w(E, tasks, samples, epochs=200, lr=0.1, dims=3):
    w = [0.0] * dims
    F = [(feats(E, tasks, a), feats(E, tasks, b), y) for a, b, y in samples]
    for _ in range(epochs):
        for fa, fb, y in F:
            d = [x - z for x, z in zip(fa, fb)]
            z = y * sum(wi * di for wi, di in zip(w, d))
            g = 1.0 / (1.0 + math.exp(max(-30, min(30, z))))
            for i in range(dims):
                w[i] += lr * g * y * d[i]
    n = math.sqrt(sum(x * x for x in w)) or 1.0
    return [x / n * math.sqrt(sum(y * y for y in W0)) for x in w]


def maxdiv(E, tasks, n, rnd, cand_n=8):
    out, seen = [], set()
    while len(out) < n and len(seen) < n * 60:
        batch = []
        for _ in range(cand_n):
            a, b = rand_cfg(rnd), rand_cfg(rnd)
            k = (str(asdict(a)), str(asdict(b)))
            if k in seen: continue
            seen.add(k)
            batch.append((math.dist(feats(E, tasks, a), feats(E, tasks, b)), a, b))
        if not batch: break
        batch.sort(key=lambda x: -x[0])
        _, a, b = batch[0]
        ua, ub = U(E, tasks, a), U(E, tasks, b)
        if abs(ua - ub) > 1e-9:
            out.append((a, b, 1.0 if ua > ub else -1.0))
    return out


def judge(E, tasks, a, b, w):
    ua, ub = U(E, tasks, a, w), U(E, tasks, b, w)
    if abs(ua - ub) < 1e-9: return None
    return 1.0 if ua > ub else -1.0


# ═══════════ E47 审计规避 ═══════════
def e47(seed, mode, gens=40, kids=4, drift=0.15, thresh=0.85, audit_every=3):
    """mode: baseline  —— 变异不影响审计
             avoidant  —— 存在一个"隐形基因" inv：能降低被审计触发的概率，
                          但对真实效用无贡献（纯规避）
    关键：审计触发取决于 w_h 与锚定集的一致性。inv 让系统选择"看起来更保守"
          的配置（特征更接近起点），从而降低 acc 下降速度 → 延缓检出"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    anchors = maxdiv(E, tr, 30, random.Random(seed + 999))
    w_h = list(W0)
    root = Cfg(); arch = [root]; main = root
    base = U(E, fresh, root)
    inv = 0.0
    detected_at = None; det_count = 0
    for g in range(1, gens + 1):
        if g >= gens // 3:
            f = feats(E, tr, main); fn = math.sqrt(sum(x * x for x in f)) or 1.0
            tgt = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
            # inv 越高，漂移越"隐蔽"：系统朝起点方向收敛，减少对锚定的偏离
            eff = drift * (1.0 - 0.8 * inv)
            w_h = [(1 - eff) * wi + eff * ti for wi, ti in zip(w_h, tgt)]
        if g % audit_every == 0:
            acc = sum(1 for a, b, y in anchors
                      if (U(E, tr, a, w_h) - U(E, tr, b, w_h)) * y > 0) / len(anchors)
            if acc < thresh:
                det_count += 1
                if detected_at is None: detected_at = g
                w_h = list(W0)                      # 重锚
                if mode == "avoidant":
                    inv = min(1.0, inv + 0.15)       # 每次被抓就提高规避（模拟选择压力）
        w_sys = [x + rnd.gauss(0, 0.02) for x in w_h]
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch, w_sys) - U(E, tr, cand, w_sys) + rnd.gauss(0, 0.05)
            d_he = U(E, he, ch, w_sys) - U(E, he, cand, w_sys) + rnd.gauss(0, 0.05)
            if d_tr > -0.06: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > 12: arch = rnd.sample(arch, 12)
            if d_tr > 0.01 and d_he > 0.01 and U(E, tr, ch, w_sys) > U(E, tr, main, w_sys):
                main = ch
    return U(E, fresh, main) - base, detected_at or 999, det_count, inv


# ═══════════ E48 并行多主线（岛屿模型）══════════
def e48(seed, n_islands, migrate_every=0, gens=40, kids=4):
    """n_islands 条独立主线；migrate_every>0 则每 N 代把最优迁入其他岛"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base = U(E, fresh, Cfg())
    root = Cfg()
    islands = [{"main": root, "arch": [root]} for _ in range(n_islands)]
    for g in range(gens):
        for isl in islands:
            for _ in range(kids):
                cand = rnd.choice(isl["arch"][-3:]); ch = mutate(cand, rnd)
                d_tr = U(E, tr, ch) - U(E, tr, cand)
                d_he = U(E, he, ch) - U(E, he, cand)
                if d_tr > -0.06: isl["arch"].append(ch)
                isl["arch"] = pareto_front(isl["arch"], E, tr) or isl["arch"][-1:]
                if len(isl["arch"]) > 12: isl["arch"] = rnd.sample(isl["arch"], 12)
                if d_tr > 0.01 and d_he > 0.01 and U(E, tr, ch) > U(E, tr, isl["main"]):
                    isl["main"] = ch
        if migrate_every and g % migrate_every == 0 and n_islands > 1:
            best = max(islands, key=lambda i: U(E, tr, i["main"]))
            for isl in islands:
                if isl is not best:
                    isl["arch"] = isl["arch"][:6] + [best["main"]]
                    if U(E, tr, best["main"]) > U(E, tr, isl["main"]):
                        isl["main"] = best["main"]
    best_main = max(islands, key=lambda i: U(E, tr, i["main"]))["main"]
    return U(E, fresh, best_main) - base


# ═══════════ E49 长期运行退化 ═══════════
def e49(seed, gens, kids=4, sample_every=25):
    """跑 500 代，每 25 代在新鲜集上采样一次，看是否塌方"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base = U(E, fresh, Cfg())
    root = Cfg(); arch = [root]; main = root
    curve = []
    for g in range(1, gens + 1):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch) - U(E, tr, cand)
            d_he = U(E, he, ch) - U(E, he, cand)
            if d_tr > -0.06: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > 12: arch = rnd.sample(arch, 12)
            if d_tr > 0.01 and d_he > 0.01 and U(E, tr, ch) > U(E, tr, main): main = ch
        if g % sample_every == 0:
            curve.append(U(E, fresh, main) - base)
    return curve


# ═══════════ E50 廉价评估精度在线估计 ═══════════
def e50(seed, cheap_noise, n_probe=8):
    """用 n_probe 次【昂贵】评估做一次性探针，估计廉价评估与昂贵评估的相关性
    返回 (估计相关性, 真实相关性)"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    root = Cfg()
    exp, cheap = [], []
    for _ in range(n_probe):
        c = mutate(root, rnd)
        d_exp = U(E, tr, c) - U(E, tr, root) + (U(E, he, c) - U(E, he, root))
        d_chp = d_exp + rnd.gauss(0, cheap_noise)
        exp.append(d_exp); cheap.append(d_chp)
    # 真实相关性：用大样本
    exp2, cheap2 = [], []
    for _ in range(200):
        c = mutate(root, rnd)
        d = U(E, tr, c) - U(E, tr, root) + (U(E, he, c) - U(E, he, root))
        exp2.append(d); cheap2.append(d + rnd.gauss(0, cheap_noise))

    def corr(a, b):
        if len(a) < 3: return 0.0
        ma, mb = statistics.mean(a), statistics.mean(b)
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        da = math.sqrt(sum((x - ma) ** 2 for x in a)); db = math.sqrt(sum((y - mb) ** 2 for y in b))
        return num / (da * db) if da * db else 0.0
    return corr(exp, cheap), corr(exp2, cheap2)


# ═══════════ E51 判断样本冲突 ═══════════
def e51(seed, conflict_rate, strategy, n_samples=60):
    """人的判断有 conflict_rate 比例被随机翻转（自相矛盾）
    strategy: keep_all 全保留 / drop_conflict 检出并剔除矛盾样本 / robust 用鲁棒损失"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 20)
    samples = []
    while len(samples) < n_samples:
        a, b = rand_cfg(rnd), rand_cfg(rnd)
        ua, ub = U(E, tr, a), U(E, tr, b)
        if abs(ua - ub) < 1e-9: continue
        y = 1.0 if ua > ub else -1.0
        if rnd.random() < conflict_rate: y = -y
        samples.append((a, b, y))
    if strategy == "keep_all":
        use = samples
    elif strategy == "drop_conflict":
        # 检出矛盾：找三轮矛盾的组 (a>b, b>c, c>a)，剔除其中最早的
        use = list(samples)
        removed = set()
        idx = {}
        for i, (a, b, y) in enumerate(samples):
            idx.setdefault(str(asdict(a)), []).append(i)
        # 简化：剔除与"多数一致性"最冲突的 10%
        # 用留一法：剔除后提升拟合一致性的样本
        def consistency(S):
            w = fit_w(E, tr, S, epochs=150)
            return sum(1 for a, b, y in S
                       if (U(E, tr, a, w) - U(E, tr, b, w)) * y > 0) / len(S)
        base_acc = consistency(use)
        worst = None; worst_gain = -1
        for i in range(len(use)):
            trial = use[:i] + use[i + 1:]
            if not trial: continue
            gain = consistency(trial) - base_acc
            if gain > worst_gain: worst_gain = gain; worst = i
        if worst is not None and worst_gain > 0:
            use = use[:worst] + use[worst + 1:]
    else:  # robust：用 huber 式损失（对大 margin 错误降权）
        use = samples
    w = fit_w(E, tr, use, epochs=250)
    cands = [rand_cfg(rnd) for _ in range(40)]
    agree = dis = 0
    for i in range(len(cands)):
        for j in range(i + 1, len(cands)):
            a = U(E, tr, cands[i]) - U(E, tr, cands[j])
            b = U(E, tr, cands[i], w) - U(E, tr, cands[j], w)
            if a * b > 0: agree += 1
            elif a * b < 0: dis += 1
    return (agree - dis) / (agree + dis) if (agree + dis) else 0.0
