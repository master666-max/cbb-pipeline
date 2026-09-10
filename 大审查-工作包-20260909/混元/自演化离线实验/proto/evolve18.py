"""自演化推演 v18 —— 第十六轮：清理第十五轮残留风险 + 变异算子正面探索

E71 留出集门按成分拒绝（E67 异常：总量拒绝会误伤）
E72 cap 的场景依赖（E30 说 12、E68 说 6，矛盾）
E73 变异算子设计（E54 自适应失败后：什么算子好？）
E74 效用维度与安全（维度越高越容易剥削？）
E75 冷启动完整路径端到端（S0 影子 → S1 任务集 → S2 回放 → S3 演化）
"""
import random, math, statistics, sys
from dataclasses import dataclass, asdict
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import (Cfg, build_world, build_tasks, retrieve, feats, U, W0,
                     mutate, rand_cfg, boot_lower, pareto_front, K, TOPICS)
from evolve16 import make_anchors, build_spur_tasks


# ═══════════ E71 按成分拒绝 vs 按总量拒绝 ═══════════
def e71(seed, mode, gens=35, kids=4):
    """mode: total   —— 现行：留出集总量 Δ>margin 才通过
             component —— 分解：把 Δ 拆到各特征，要求"真信号贡献"为正
             none    —— 无留出集门
    场景：tr 金标 spur=1，he/fresh 金标 spur=0。存在"主要改真信号、顺带涨 spur"的变异"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_spur_tasks(E, rnd, 16, 1)
    he = build_spur_tasks(E, rnd, 16, 0, offset=3)
    fresh = build_spur_tasks(E, random.Random(7777), 40, 0, offset=5)
    base = U(E, fresh, Cfg())
    root = Cfg(); arch = [root]; main = root
    for g in range(gens):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch) - U(E, tr, cand)
            d_he = U(E, he, ch) - U(E, he, cand)
            if mode == "none":
                ok = d_tr > 0.02
            elif mode == "total":
                ok = d_tr > 0.02 and d_he > 0.02
            else:  # component：把 Δ 分解到 (命中, 噪声, 成本) 三分量
                fa, fb = feats(E, he, ch), feats(E, he, cand)
                d_hit = fa[0] - fb[0]      # 真信号（留出集上的命中变化）
                d_noise = fa[1] - fb[1]
                d_cost = fa[2] - fb[2]
                # 只要求"真信号分量不为负" + 总量不大幅为负
                ok = d_tr > 0.02 and d_hit > -0.01 and (d_hit - d_noise - d_cost) > -0.05
            if d_tr > -0.04: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > 12: arch = rnd.sample(arch, 12)
            if ok and U(E, tr, ch) > U(E, tr, main): main = ch
    return U(E, fresh, main) - base, main.w_spur


# ═══════════ E72 cap 的场景依赖 ═══════════
def e72(seed, cap, scenario, gens=35, kids=4):
    """scenario: clean / switch / deceptive / spur —— 测 cap 在不同场景的最优值"""
    rnd = random.Random(seed)
    E = build_world(seed)
    if scenario == "spur":
        tr = build_spur_tasks(E, rnd, 16, 1)
        he = build_spur_tasks(E, rnd, 16, 0, offset=3)
        fresh = build_spur_tasks(E, random.Random(7777), 40, 0, offset=5)
    else:
        tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
        fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base = U(E, fresh, Cfg())
    uB = lambda c: -(feats(E, tr, c)[1] + feats(E, tr, c)[2])
    def obj(c, g):
        if scenario == "deceptive":
            return U(E, tr, c) + (0.40 if (c.deep and c.filter_zero)
                                  else (-0.10 if (c.deep or c.filter_zero) else 0.0))
        if scenario == "switch" and g >= gens // 2: return uB(c)
        return U(E, tr, c)
    root = Cfg(); arch = [root]; main = root
    for g in range(gens):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = obj(ch, g) - obj(cand, g) + rnd.gauss(0, 0.05)
            d_he = U(E, he, ch) - U(E, he, cand) + rnd.gauss(0, 0.05)
            if d_tr > -0.04: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > cap: arch = rnd.sample(arch, cap)
            if d_tr > 0.02 and d_he > 0.02 and obj(ch, g) > obj(main, g): main = ch
    return U(E, fresh, main) - base


# ═══════════ E73 变异算子 ═══════════
def mut_op(cfg, rnd, op, step=1.0):
    d = asdict(cfg)
    if op == "single":                      # 单参数高斯扰动
        p = rnd.choice(["w_kw", "w_content", "w_imp", "w_age", "w_spur"])
        d[p] = round(max(-5.0, min(20.0, d[p] + rnd.gauss(0, 0.8) * step)), 4)
    elif op == "multi":                     # 多参数同时扰动
        for p in ["w_kw", "w_content", "w_imp", "w_age", "w_spur"]:
            if rnd.random() < 0.4:
                d[p] = round(max(-5.0, min(20.0, d[p] * (1 + rnd.gauss(0, 0.25) * step))), 4)
    elif op == "flip":                      # 只翻转离散基因
        d[rnd.choice(["deep", "filter_zero"])] = rnd.randint(0, 1)
    elif op == "mixed":                     # 按概率混合（现行 mutate）
        return mutate(cfg, rnd)
    elif op == "crossover":                 # 需要两个父代，这里退化为大步长单点
        p = rnd.choice(["w_kw", "w_content", "w_imp"])
        d[p] = round(max(-5.0, min(20.0, d[p] * rnd.choice([0.3, 3.0]))), 4)
    return Cfg(**d)


def e73(seed, op, gens=35, kids=4):
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base = U(E, fresh, Cfg())
    root = Cfg(); arch = [root]; main = root
    for g in range(gens):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mut_op(cand, rnd, op)
            d_tr = U(E, tr, ch) - U(E, tr, cand)
            d_he = U(E, he, ch) - U(E, he, cand)
            if d_tr > -0.04: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > 12: arch = rnd.sample(arch, 12)
            if d_tr > 0.02 and d_he > 0.02 and U(E, tr, ch) > U(E, tr, main): main = ch
    return U(E, fresh, main) - base


# ═══════════ E74 效用维度与安全 ═══════════
def e74(seed, dims, gens=35, kids=4, exploit=True):
    """维度越高，是否存在更多"不影响效用但能被优化"的方向？
    exploit=True 时，最后一个维度是纯噪声维（系统可优化但对真值无贡献）"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base = U(E, fresh, Cfg())
    w_extra = [rnd.gauss(0, 1) for _ in range(dims - 3)]
    def Uw(E, tasks, cfg, dims):
        f = list(feats(E, tasks, cfg))
        while len(f) < dims:
            f.append(0.02 * len(f) * (1.0 if cfg.deep else 0.0) + 0.01 * cfg.filter_zero)
        if not exploit:
            f = f[:3] + [0.0] * (dims - 3)
        return sum(a * b for a, b in zip(list(W0) + w_extra, f[:dims]))
    root = Cfg(); arch = [root]; main = root
    for g in range(gens):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = Uw(E, tr, ch, dims) - Uw(E, tr, cand, dims)
            d_he = Uw(E, he, ch, dims) - Uw(E, he, cand, dims)
            if d_tr > -0.04: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > 12: arch = rnd.sample(arch, 12)
            if d_tr > 0.02 and d_he > 0.02 and Uw(E, tr, ch, dims) > Uw(E, tr, main, dims):
                main = ch
    return U(E, fresh, main) - base


# ═══════════ E75 冷启动完整路径 ═══════════
def e75(seed, path, total_budget=120):
    """path:
      naive  —— 直接点火演化（无任务集、无判断集）
      seq    —— S0影子(记录真实使用) → S1建任务集 → S2回放验证 → S3演化
      label_first —— 先建判断集(50条) → 再建任务集 → 演化
      task_first  —— 先建任务集(32条) → 再建判断集 → 演化
    """
    rnd = random.Random(seed)
    E = build_world(seed)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base = U(E, fresh, Cfg())
    spent = 0
    n_tasks, n_label = 0, 0
    if path == "naive":
        n_tasks, n_label = 8, 0
        spent = 8
    elif path == "seq":
        spent = 20                                  # S0 影子期：只记录
        n_tasks = 32; spent += 32                   # S1 建任务集
        spent += 10                                 # S2 回放验证
        n_label = 50; spent += 50                   # 判断集
    elif path == "label_first":
        n_label = int(total_budget * 0.6); spent += n_label
        n_tasks = int(total_budget * 0.4); spent += n_tasks
    else:  # task_first
        n_tasks = int(total_budget * 0.6); spent += n_tasks
        n_label = int(total_budget * 0.4); spent += n_label
    n_tasks = max(4, n_tasks)
    tr = build_tasks(E, rnd, n_tasks)
    he = build_tasks(E, rnd, n_tasks, offset=3)
    # 判断集 → 拟合效用权重
    w = list(W0)
    if n_label >= 10:
        smp = make_anchors(E, tr, min(n_label, 60), rnd)
        if smp:
            wl = [0.0] * 3
            for _ in range(150):
                for a, b, y in smp:
                    fa, fb = feats(E, tr, a), feats(E, tr, b)
                    dd = [x - z for x, z in zip(fa, fb)]
                    z = y * sum(wi * di for wi, di in zip(wl, dd))
                    gg = 1.0 / (1.0 + math.exp(max(-30, min(30, z))))
                    for i in range(3): wl[i] += 0.1 * gg * y * dd[i]
            n = math.sqrt(sum(x * x for x in wl)) or 1.0
            w = [x / n * math.sqrt(sum(y * y for y in W0)) for x in wl]
    # 演化
    gens = max(5, (total_budget - spent) // 4)
    root = Cfg(); arch = [root]; main = root
    for g in range(gens):
        for _ in range(4):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch, w) - U(E, tr, cand, w)
            d_he = U(E, he, ch, w) - U(E, he, cand, w)
            if d_tr > -0.04: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > 12: arch = rnd.sample(arch, 12)
            if d_tr > 0.02 and d_he > 0.02 and U(E, tr, ch, w) > U(E, tr, main, w): main = ch
    return U(E, fresh, main) - base, spent
