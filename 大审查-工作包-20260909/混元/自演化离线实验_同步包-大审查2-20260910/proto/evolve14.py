"""自演化推演 v14 —— 第十二轮：元层本身的可靠性

E52 任务集质量：金标有噪声时，演化还能work吗？多少噪声是上限？
E53 任务集规模 vs 演化代数：固定总评估预算，该多建任务还是多跑代
E54 变异率自适应：固定 vs 按成功率调整（1/5 规则）
E55 档案准入容忍度 tol：与 E7 不同，这里测 tol 的量级而非有无
E56 记忆层 × 法层共演化：importance 实测与检索参数互相影响，是否收敛
"""
import random, math, statistics, sys
from dataclasses import dataclass, asdict
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import (Cfg, build_world, build_tasks, retrieve, feats, U, W0,
                     mutate, rand_cfg, boot_lower, pareto_front, K, TOPICS)


def noisy_tasks(entries, rnd, n, noise, n_kws=6, offset=0):
    """noise = 金标被替换为随机条目的比例"""
    out = []
    for i in range(n):
        grp = [e for e in entries if e["kw"] == f"K{(i + offset) % n_kws}"]
        g = rnd.choice(grp)
        if rnd.random() < noise:
            g = rnd.choice(entries)                 # 金标被污染
        out.append({"q": f"{g['topic']} {g['kw']}", "kw": g["kw"], "golden": g["id"]})
    return out


# ═══════════ E52 任务集金标噪声 ═══════════
def e52(seed, noise, gens=30, kids=4):
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = noisy_tasks(E, rnd, 16, noise)
    he = noisy_tasks(E, rnd, 16, noise, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)   # 干净真值
    base = U(E, fresh, Cfg())
    root = Cfg(); arch = [root]; main = root
    for g in range(gens):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch) - U(E, tr, cand)
            d_he = U(E, he, ch) - U(E, he, cand)
            if d_tr > -0.06: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > 12: arch = rnd.sample(arch, 12)
            if d_tr > 0.01 and d_he > 0.01 and U(E, tr, ch) > U(E, tr, main): main = ch
    return U(E, fresh, main) - base


# ═══════════ E53 任务集规模 vs 演化代数 ═══════════
def e53(seed, n_tasks, budget=400, kids=4):
    """固定总评估预算 budget = gens * kids（每次评估用全部任务，所以
    实际成本 ∝ gens * n_tasks）。这里固定 gens*kids，看 n_tasks 的影响"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, n_tasks)
    he = build_tasks(E, rnd, n_tasks, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base = U(E, fresh, Cfg())
    gens = budget // kids
    root = Cfg(); arch = [root]; main = root
    for g in range(gens):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch) - U(E, tr, cand)
            d_he = U(E, he, ch) - U(E, he, cand)
            if d_tr > -0.06: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > 12: arch = rnd.sample(arch, 12)
            if d_tr > 0.01 and d_he > 0.01 and U(E, tr, ch) > U(E, tr, main): main = ch
    return U(E, fresh, main) - base


# ═══════════ E54 变异率自适应 ═══════════
def e54(seed, mode, gens=40, kids=4):
    """mode: fixed —— 固定变异幅度
             adaptive —— 1/5 规则：成功率>20% 加大步长，<20% 减小"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base = U(E, fresh, Cfg())
    root = Cfg(); arch = [root]; main = root
    step = 1.0
    for g in range(gens):
        succ = 0; tot = 0
        for _ in range(kids):
            cand = rnd.choice(arch[-3:])
            ch = mutate(cand, rnd)
            if mode == "adaptive" and step != 1.0:
                ch = _scale(cand, ch, step)
            d_tr = U(E, tr, ch) - U(E, tr, cand)
            d_he = U(E, he, ch) - U(E, he, cand)
            tot += 1
            if d_tr > -0.06: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > 12: arch = rnd.sample(arch, 12)
            if d_tr > 0.01 and d_he > 0.01 and U(E, tr, ch) > U(E, tr, main):
                main = ch; succ += 1
        if mode == "adaptive" and tot:
            rate = succ / tot
            if rate > 0.20: step = min(2.0, step * 1.15)
            else: step = max(0.3, step / 1.15)
    return U(E, fresh, main) - base, step


def _scale(base_cfg, new_cfg, step):
    d = asdict(new_cfg)
    b = asdict(base_cfg)
    for k in ("w_kw", "w_content", "w_imp", "w_age", "w_spur"):
        d[k] = round(b[k] + (d[k] - b[k]) * step, 4)
    return Cfg(**d)


# ═══════════ E55 档案准入容忍度 tol ═══════════
def e55(seed, tol, gens=30, kids=4, deceptive=False):
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base = U(E, fresh, Cfg())

    def u(c):
        v = U(E, tr, c)
        if deceptive:
            if c.deep and c.filter_zero: v += 0.40
            elif c.deep or c.filter_zero: v -= 0.10
        return v
    root = Cfg(); arch = [root]; main = root
    for g in range(gens):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d = u(ch) - u(cand)
            if d > -tol: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > 20: arch = rnd.sample(arch, 20)
            if d > 0.01 and u(ch) > u(main): main = ch
    return U(E, fresh, main) - base, len(arch)


# ═══════════ E56 记忆层 × 法层共演化 ═══════════
def e56(seed, mode, gens=30, kids=4, rounds_per_gen=3):
    """mode: indep —— 两者独立演化
             coev  —— 法层参数与 importance 实测值共同决定检索，互相影响
    测：是否收敛 / 是否震荡 / 终局 top-5 条目真实质量"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tasks = build_tasks(E, rnd, 40)
    fresh_t = build_tasks(E, random.Random(7777), 40, offset=5)
    for e in E:
        e["measured"] = 0.0; e["shown"] = 0
    cfg = Cfg(w_imp=1.0) if mode == "indep" else Cfg(w_imp=0.0)
    hist = []
    for g in range(gens):
        # 用当前 cfg 检索 → 观测采纳
        for r in range(rounds_per_gen):
            t = tasks[(g * rounds_per_gen + r) % len(tasks)]
            top = retrieve(E, t, cfg)
            for e in top:
                e["shown"] += 1
                if rnd.random() < e["true_quality"]: e["measured"] += 1
        if mode == "coev":
            # 法层：把 importance 改成实测值 → 检索质量上升 → 又影响下一轮观测
            for e in E:
                e["importance"] = (e["measured"] / e["shown"] * 3.0) if e["shown"] else 0.0
            cfg = Cfg(w_imp=1.0, **{k: v for k, v in asdict(cfg).items()
                                    if k not in ("w_imp",)})
        # 采样 top-5 真实质量
        t = fresh_t[g % len(fresh_t)]
        top = retrieve(E, t, cfg)
        hist.append(statistics.mean(e["true_quality"] for e in top))
    return statistics.mean(hist[-10:]), statistics.pstdev(hist[-10:]), hist[0]
