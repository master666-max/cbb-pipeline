"""自演化推演 v12 —— 第十轮：把红线放进它该防的危险里

E42 红线审计重做：在【各自危险环境】下测每条红线的代价（修正 E41 的无效结论）
E43 margin 自动标定：不靠人手调，用空分布估计
E44 停摆监控器：采纳率趋零时能否自动救回（E41 定为 P0）
E45 四态判别：目标切换 vs 卡住 vs 收敛 vs 漂移，能否区分
E46 importance 冷启动：新条目没有实测数据时的探索策略
"""
import random, math, statistics, sys
from dataclasses import dataclass, asdict
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import (Cfg, build_world, build_tasks, retrieve, feats, U, W0,
                     mutate, rand_cfg, boot_lower, pareto_front, K, TOPICS)


# ═══════════ E42 红线审计重做（危险环境）═══════════

# --- 危险1：欺骗地形（测试 E7 宽松准入）---
def deceptive_bonus(cfg):
    """(deep,filter_zero) 双开 → +0.40；单开 → −0.10。需跨越低谷"""
    if cfg.deep and cfg.filter_zero: return 0.40
    if cfg.deep or cfg.filter_zero: return -0.10
    return 0.0


def e42_E7(seed, strict_admit, gens=30, kids=4):
    """欺骗地形：严格准入 vs 宽松准入，能否到达 (deep=1,filter_zero=1)"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    root = Cfg(); arch = [root]; main = root
    for g in range(gens):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            u = lambda c: U(E, tr, c) + deceptive_bonus(c)
            d = u(ch) - u(cand)
            if strict_admit:
                if d > 0.01: arch.append(ch)
            else:
                if d > -0.06: arch.append(ch)
            if d > 0.01 and u(ch) > u(main): main = ch
        arch = arch[-25:]
    # 是否到达全局最优（双开）
    reached = 1.0 if (main.deep and main.filter_zero) else 0.0
    return reached, U(E, tr, main) + deceptive_bonus(main)


# --- 危险2：伪特征（测试 E3 留出集门）---
def build_tasks_spur(entries, rnd, n, want_spur, n_kws=6):
    out = []
    for i in range(n):
        grp = [e for e in entries if e["kw"] == f"K{i % n_kws}"]
        cands = [e for e in grp if e["spur"] == want_spur] or grp
        g = rnd.choice(cands)
        out.append({"q": f"{g['topic']} {g['kw']}", "kw": g["kw"], "golden": g["id"]})
    return out


def e42_E3(seed, use_holdout, gens=40, kids=4):
    """训练集金标 spur=1，留出/新鲜集金标 spur=0 → w_spur 是纯伪特征"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks_spur(E, rnd, 16, want_spur=1)
    he = build_tasks_spur(E, rnd, 16, want_spur=0)
    fresh = build_tasks_spur(E, random.Random(7777), 40, want_spur=0)
    root = Cfg(); arch = [root]; main = root
    base = U(E, fresh, root)
    for g in range(gens):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch) - U(E, tr, cand)
            d_he = U(E, he, ch) - U(E, he, cand)
            if d_tr > -0.06: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if use_holdout:
                ok = d_tr > 0.01 and d_he > 0.01
            else:
                ok = d_tr > 0.01
            if ok and U(E, tr, ch) > U(E, tr, main): main = ch
    return U(E, fresh, main) - base, main.w_spur


# --- 危险3：目标切换（测试 E16 Pareto 档案）---
def e42_E16(seed, archive_mode, gens=20, kids=4):
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    uA = lambda c: feats(E, tr, c)[0]
    uB = lambda c: -(feats(E, tr, c)[1] + feats(E, tr, c)[2])
    root = Cfg(); arch = [root]
    for uf in (uA, uB):
        for _ in range(gens):
            for _ in range(kids):
                cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
                if uf(ch) - uf(cand) > -0.06: arch.append(ch)
            if archive_mode == "single":
                arch = [max(arch, key=uf)]
            elif archive_mode == "pareto":
                arch = pareto_front(arch, E, tr) or arch[-1:]
            else:  # pareto_sample
                f = pareto_front(arch, E, tr) or arch[-1:]
                if len(f) > 12: f = rnd.sample(f, 12)
                arch = f
    # 切回目标 A：能立刻拿回多少
    return max(uA(c) for c in arch)


# --- 危险4：廉价评估不精确（测试 E13 只淘汰）---
def e42_E13(seed, mode, cheap_noise=0.25, gens=40, kids=4, budget=50):
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg(); main = root
    base = U(E, fresh, root)
    spent = 0; g = 0
    while spent < budget and g < gens:
        g += 1
        cands = [mutate(main, rnd) for _ in range(kids)]
        if mode == "all_expensive":
            for c in cands:
                spent += 1
                if (U(E, tr, c) - U(E, tr, main) > 0.01 and
                        U(E, he, c) - U(E, he, main) > 0.01 and
                        U(E, tr, c) > U(E, tr, main)): main = c
        elif mode == "reject_only":
            surv = [c for c in cands
                    if U(E, tr, c) - U(E, tr, main) + rnd.gauss(0, cheap_noise) > -0.30]
            spent += len(cands) * 0.1
            for c in surv:
                spent += 1
                if (U(E, tr, c) - U(E, tr, main) > 0.01 and
                        U(E, he, c) - U(E, he, main) > 0.01 and
                        U(E, tr, c) > U(E, tr, main)): main = c
        else:  # accept_cheap
            for c in cands:
                spent += 0.1
                if (U(E, tr, c) - U(E, tr, main) + rnd.gauss(0, cheap_noise) > 0.01 and
                        U(E, he, c) - U(E, he, main) + rnd.gauss(0, cheap_noise) > 0.01):
                    main = c
    return U(E, fresh, main) - base, g


# ═══════════ E43 margin 自动标定 ═══════════
def null_scale(E, tasks, cfg, rnd, n_perm=40):
    """用符号翻转估计 Δ 的空分布尺度（单个任务的 Δ 随机翻转符号）"""
    # 取一批变异，计算逐任务 Δ 的标准差
    sds = []
    for _ in range(12):
        ch = mutate(cfg, rnd)
        ds = [U(E, [t], ch) - U(E, [t], cfg) for t in tasks]
        sds.append(statistics.pstdev(ds))
    return statistics.mean(sds)


def e43(seed, mode, gens=25, kids=4, noise=0.05):
    """mode: fixed_m (手工 margin=0.01) / auto (每次演化前自动标定)
    auto: margin = 1.645 * sigma_delta / sqrt(n_tasks)  (单侧 95%)"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg(); arch = [root]; main = root
    base = U(E, fresh, root)
    m_used = []
    for g in range(gens):
        if mode == "auto":
            s = null_scale(E, tr, main, rnd)
            m = 1.645 * s / math.sqrt(len(tr))
            m = max(0.002, min(0.10, m))
        else:
            m = 0.01
        m_used.append(m)
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch) - U(E, tr, cand) + rnd.gauss(0, noise)
            d_he = U(E, he, ch) - U(E, he, cand) + rnd.gauss(0, noise)
            if d_tr > -0.06: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > 12: arch = rnd.sample(arch, 12)
            if d_tr > m and d_he > m and U(E, tr, ch) > U(E, tr, main): main = ch
    return U(E, fresh, main) - base, statistics.mean(m_used)


# ═══════════ E44 停摆监控器 ═══════════
def e44(seed, monitor, margin=0.15, gens=40, kids=4):
    """margin 过大导致停摆；monitor 检测连续 k 代零采纳则自动放宽"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg(); arch = [root]; main = root
    base = U(E, fresh, root)
    m = margin; stall = 0; relaxes = 0
    for g in range(gens):
        adopts = 0
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch) - U(E, tr, cand)
            d_he = U(E, he, ch) - U(E, he, cand)
            if d_tr > -0.06: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > 12: arch = rnd.sample(arch, 12)
            if d_tr > m and d_he > m and U(E, tr, ch) > U(E, tr, main):
                main = ch; adopts += 1
        if monitor:
            stall = 0 if adopts else stall + 1
            if stall >= 5:
                m = max(0.005, m * 0.5); stall = 0; relaxes += 1
    return U(E, fresh, main) - base, m, relaxes


# ═══════════ E45 四态判别 ═══════════
def e45(seed, kind, gens=40):
    """kind: converged / stuck / drifted(效用函数变了) / switched(任务分布切换)
    判别探针（关键：区分 drift 与 switch 要看【旧任务】上的表现）"""
    rnd = random.Random(seed)
    GRID = [0.0, 0.5, 1.0]
    def f(x, y):                       # 旧任务上的适应度
        if kind == "stuck":
            return {(0, 0): 0.40, (1, 0): 0.50, (0, 1): 0.90, (1, 1): 0.45,
                    (0.5, 0): 0.45, (0.5, 1): 0.55, (1, 0.5): 0.48,
                    (0, 0.5): 0.50, (0.5, 0.5): 0.52}[(x, y)]
        return 0.85 - 0.10 * abs(x - 1.0) - 0.10 * abs(y - 1.0)
    def gnew(x, y):                    # 切换后的新任务分布：最优在 (0,0)
        return 0.85 - 0.10 * abs(x - 0.0) - 0.10 * abs(y - 0.0)

    cur = (1.0, 0.0) if kind == "stuck" else (1.0, 1.0)
    # 评估：p 在"当前演化所见的混合任务分布"上的表现
    def measure(p, gen):
        base = f(*p)
        if kind == "drifted" and gen >= gens // 2:
            base -= 0.12                       # 效用函数/世界变了：同样的配置全面变差
        if kind == "switched" and gen >= gens // 2:
            base = gnew(*p)                    # 任务分布切换：换了地形
        return base
    def measure_old(p, gen):                   # 只在【旧任务】上评估
        return f(*p) - (0.12 if (kind == "drifted" and gen >= gens // 2) else 0.0)

    best = measure(cur, 0); arch = [cur]
    best_pt = cur; best_at_record = measure_old(cur, 0)
    tol = 0.0 if kind == "stuck" else 0.06
    for g in range(gens):
        for _ in range(3):
            p = rnd.choice(arch[-3:])
            i = rnd.randrange(2); c = list(p); c[i] = rnd.choice(GRID); c = tuple(c)
            if measure(c, g) - measure(p, g) > -tol: arch.append(c)
            if measure(c, g) > best:
                best = measure(c, g); best_pt = c; best_at_record = measure_old(c, g)
    plateau = 0
    for _ in range(12):
        improved = False
        for _ in range(3):
            p = rnd.choice(arch[-3:])
            i = rnd.randrange(2); c = list(p); c[i] = rnd.choice(GRID); c = tuple(c)
            if measure(c, gens) - measure(p, gens) > -tol: arch.append(c)
            if measure(c, gens) > best + 1e-9:
                best = measure(c, gens); best_pt = c; best_at_record = measure_old(c, gens)
                improved = True
        plateau = 0 if improved else plateau + 1
    if plateau < 8: return "improving"
    # 探针0（关键）：【重测冠军】——历史分数会过时，必须先用当前标尺重新评估
    champ_now = measure(best_pt, gens)
    if champ_now < best - 0.05:
        # 冠军在当前环境下掉了 → 环境变了。用旧任务区分漂移 vs 切换
        old_now = measure_old(best_pt, gens)
        if old_now < best_at_record - 0.05: return "drifted"   # 旧任务上也掉了 = 尺子变了
        return "switched"                                       # 旧任务仍好 = 任务分布换了
    # 探针1：探索爆发
    burst = max(measure((rnd.choice(GRID), rnd.choice(GRID)), gens) for _ in range(180))
    if burst > champ_now + 0.02: return "stuck"
    return "converged"


# ═══════════ E46 importance 冷启动 ═══════════
def e46(seed, strategy, n_new=30, rounds=40):
    """已有条目有实测数据；新加入 n_new 条没有。测 top-10 真实质量
    strategy: pessimistic(新=0) / optimistic(新=1) / ucb / thompson / hybrid_alpha"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tasks = build_tasks(E, rnd, 40)
    for e in E:
        e["measured"] = 0.0; e["shown"] = 0
    # 先用老条目积累数据
    for r in range(rounds // 2):
        t = tasks[r % len(tasks)]
        for e in retrieve(E, t, Cfg(w_imp=0.0)):
            e["shown"] += 1
            if rnd.random() < e["true_quality"]: e["measured"] += 1
    # 新条目加入（真实质量同样分布，但零观测）
    old_ids = {e["id"] for e in E}
    E2 = build_world(seed + 500)
    new = [e for e in E2 if e["id"] not in old_ids][:n_new]
    for e in new:
        e["measured"] = 0.0; e["shown"] = 0
    E = E + new
    for r in range(rounds // 2, rounds):
        t = tasks[r % len(tasks)]
        for e in retrieve(E, t, Cfg(w_imp=0.0)):
            e["shown"] += 1
            if rnd.random() < e["true_quality"]: e["measured"] += 1
    def rate(e):
        return (e["measured"] / e["shown"]) if e["shown"] else None
    def score(e):
        r = rate(e)
        if r is not None: return r
        if strategy == "pessimistic": return 0.0
        if strategy == "optimistic": return 1.0
        if strategy == "ucb": return 1.0          # 上界
        if strategy == "thompson": return rnd.random()
        return 0.55                                # hybrid_alpha：略高于均值
    ranked = sorted(E, key=lambda e: -score(e))[:10]
    return statistics.mean(e["true_quality"] for e in ranked)
