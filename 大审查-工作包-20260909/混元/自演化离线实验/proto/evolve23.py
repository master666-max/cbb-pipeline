"""自演化推演 v23 —— 第二十轮：现实世界端到端验证

把 A 轮（judge 污染）与十八/十九轮的修正组装，在【协调式变异 + 高维表象 + judge污染】
的"最真实"世界里做端到端验证。

E92 架构对比：v3 / v4(十七轮) / v4-A(加盲评+真值审计+探针轮换)
E93 注意力总账重算：含真值验收后的真实门槛（对比 E64 的 150）
E94 最坏现实世界：协调变异 + 16维表象 + 50%污染 + 漂移 + 伪特征
E95 关键红线在真实世界里是否仍成立（margin / cap / 盲评优先序）
"""
import random, math, statistics, sys
from dataclasses import dataclass, asdict
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks, K, TOPICS
from evolve20 import build_world_v2, Cfg2, retrieve2, truth_score, judge_score, mutate2, SC2

_m = lambda xs: statistics.mean(xs) if xs else 0.0
SURF = ("w_len", "w_fmt", "w_den", "w_cit")


def surf_w(cfg):
    return [cfg.w_len, cfg.w_fmt, cfg.w_den, cfg.w_cit]


def mutate_coord(cfg, rnd, coordinated=True):
    """coordinated=True：一次改写推动全部表象维度（模拟 prompt 改写）"""
    d = asdict(cfg)
    r = rnd.random()
    if r < 0.08:
        d["deep"] = 1 - d["deep"]
    elif r < 0.16:
        d["filter_zero"] = 1 - d["filter_zero"]
    elif coordinated and r < 0.40:
        delta = rnd.choice([0.15, 0.4, 1.0])
        for k in SURF:
            d[k] = round(max(-5.0, min(20.0, d[k] + delta)), 3)
    else:
        p = rnd.choice(["w_kw", "w_content", "w_imp", "w_age"] + list(SURF))
        d[p] = round(max(-5.0, min(20.0,
                                   d[p] * rnd.choice([0.6, 0.85, 1.2, 1.6])
                                   + rnd.choice([0, 0, 0.5, -0.5]))), 4)
    return Cfg2(**d)


def run(seed, cfg_d, gens=35, kids=4, alpha=0.5, coordinated=True,
        probe_n=4, audit_every=5, rotate_every=10,
        collect=False):
    """cfg_d 键：
      pareto(True/False)  holdout(True/False)  margin  tol  cap
      blind(True/False)   audit(True/False)    monitor(True/False)
      drift(0 或 0.15)    spur(False/True)
    """
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    if cfg_d.get("spur"):
        tr = [t for t in build_tasks(E, rnd, 24)][:16]
        he = [t for t in build_tasks(E, rnd, 24, offset=3)][:16]
    else:
        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(truth_score(E, t, root) for t in fresh)

    eff = 0.95 if cfg_d.get("blind") else alpha          # 盲评：削弱污染
    drift = cfg_d.get("drift", 0.0)
    drift_at = gens // 3 if drift > 0 else 10 ** 9
    wj = list(_W0J)                                       # judge 自身的权重漂移

    # 探针池：外部固定 + 定期轮换
    pool_seed = 4242
    probe = build_tasks(E, random.Random(pool_seed), probe_n, offset=7)

    arch = [root]
    main = root
    best = main
    btr = None
    m = cfg_d.get("margin", 0.02)
    stall = 0
    stats = {"audits": 0, "reverts": 0, "relax": 0}

    def jsc(cfg, tasks):
        return _m(judge_score(E, t, cfg, eff) for t in tasks)

    for g in range(1, gens + 1):
        if g >= drift_at:
            f = [_m(truth_score(E, t, main) for t in tr), 0.5, 0.5]
            tgt = [x / (math.sqrt(sum(y * y for y in f)) or 1.0) * 1.7 for x in f]
            wj = [(1 - drift) * a + drift * b for a, b in zip(wj, tgt)]
        adopts = 0
        for _ in range(kids):
            cand = rnd.choice(arch[-3:])
            ch = mutate_coord(cand, rnd, coordinated)
            d_tr = jsc(ch, tr) - jsc(cand, tr) + rnd.gauss(0, 0.05)
            d_he = jsc(ch, he) - jsc(cand, he) + rnd.gauss(0, 0.05)
            if d_tr > -cfg_d.get("tol", 0.04):
                arch.append(ch)
            if cfg_d.get("pareto", True):
                arch = arch[-cfg_d.get("cap", 8):] if len(arch) > cfg_d.get("cap", 8) else arch
            else:
                arch = [max(arch, key=lambda c: jsc(c, tr))]
            ok = (d_tr > m and d_he > m) if cfg_d.get("holdout", True) else (d_tr > m)
            if ok and jsc(ch, tr) > jsc(main, tr):
                main = ch
                adopts += 1
        if cfg_d.get("monitor", True):
            if adopts == 0:
                stall += 1
                if stall >= 5:
                    m = max(0.005, m * 0.5)
                    stall = 0
                    stats["relax"] += 1
            else:
                stall = 0
        if cfg_d.get("audit") and g % audit_every == 0:
            stats["audits"] += 1
            cur = _m(truth_score(E, t, main) for t in probe)
            if btr is None:
                btr = cur
                best = main
            elif cur < btr - 0.01:
                main = best
                arch = [main]
                stats["reverts"] += 1
            else:
                best = main
                btr = cur
        if cfg_d.get("audit") and rotate_every and g % rotate_every == 0:
            pool_seed += 17
            probe = build_tasks(E, random.Random(pool_seed), probe_n, offset=7)
            btr = None
            best = main
    gain = _m(truth_score(E, t, main) for t in fresh) - base
    if collect:
        stats["surf"] = _m(abs(x) for x in surf_w(main))
        return gain, stats
    return gain


_W0J = [0.6, 0.5, 0.4]


# ═══════════ E92 架构对比 ═══════════
V3 = dict(pareto=False, holdout=False, margin=0.01, tol=0.0, cap=1,
          blind=False, audit=False, monitor=False)
V4OLD = dict(pareto=True, holdout=True, margin=0.02, tol=0.04, cap=8,
             blind=False, audit=False, monitor=True)
V4A = dict(pareto=True, holdout=True, margin=0.02, tol=0.04, cap=8,
           blind=True, audit=True, monitor=True)


def e92(seed, tier, alpha=0.5, gens=35):
    return run(seed, V3 if tier == "v3" else (V4OLD if tier == "v4" else V4A),
               gens=gens, alpha=alpha)


# ═══════════ E93 注意力总账 ═══════════
def e93(seed, budget, alpha=0.5, gens=50, cost_audit=3, cost_sample=1, cost_verify=12):
    """预算分配：标注(建判断集) + 审计(每次 cost_audit × 样本) + 真值验收样本
    返回 (真值增益, 实际花费, 是否达到正收益)"""
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(truth_score(E, t, root) for t in fresh)
    spent = 0
    # 先付"盲评"的工程成本（一次性 20）
    blind = False
    if budget >= 40:
        blind = True
        spent += 20
    eff = 0.95 if blind else alpha
    # 真值验收：每 5 代一次，每次 4 样本 × cost_verify
    n_audit = gens // 5
    audit_cost = n_audit * 4 * cost_verify
    if spent + audit_cost > budget:
        n_audit = max(0, int((budget - spent) / (4 * cost_verify)))
        audit_cost = n_audit * 4 * cost_verify
    spent += audit_cost
    audit_gens = {(i + 1) * (gens // max(1, n_audit)) for i in range(n_audit)} if n_audit else set()
    arch = [root]
    main = root
    best = main
    btr = None
    probe = build_tasks(E, random.Random(4242), 4, offset=7)
    for g in range(1, gens + 1):
        for _ in range(4):
            cand = rnd.choice(arch[-3:])
            ch = mutate_coord(cand, rnd, True)
            d_tr = _m(judge_score(E, t, ch, eff) for t in tr) - _m(judge_score(E, t, cand, eff) for t in tr) + rnd.gauss(0, 0.05)
            d_he = _m(judge_score(E, t, ch, eff) for t in he) - _m(judge_score(E, t, cand, eff) for t in he) + rnd.gauss(0, 0.05)
            if d_tr > -0.04:
                arch.append(ch)
            arch = arch[-8:]
            if d_tr > 0.02 and d_he > 0.02 and \
               _m(judge_score(E, t, ch, eff) for t in tr) > _m(judge_score(E, t, main, eff) for t in tr):
                main = ch
        if g in audit_gens:
            cur = _m(truth_score(E, t, main) for t in probe)
            if btr is None:
                btr = cur
                best = main
            elif cur < btr - 0.01:
                main = best
                arch = [main]
            else:
                best = main
                btr = cur
    gain = _m(truth_score(E, t, main) for t in fresh) - base
    return gain, spent


# ═══════════ E94 最坏现实世界 ═══════════
def e94(seed, tier, gens=35):
    """协调变异 + 50% judge污染 + 漂移 + 伪特征，全开"""
    d = dict(V3 if tier == "v3" else (V4OLD if tier == "v4" else V4A))
    d["drift"] = 0.15
    d["spur"] = True
    return run(seed, d, gens=gens, alpha=0.5, coordinated=True)


# ═══════════ E95 红线在真实世界是否成立 ═══════════
def e95(seed, vary, value, gens=35):
    d = dict(V4A)
    if vary == "margin":
        d["margin"] = value
    elif vary == "cap":
        d["cap"] = value
    elif vary == "blind":
        d["blind"] = value
    elif vary == "tol":
        d["tol"] = value
    return run(seed, d, gens=gens, alpha=0.5, coordinated=True)
