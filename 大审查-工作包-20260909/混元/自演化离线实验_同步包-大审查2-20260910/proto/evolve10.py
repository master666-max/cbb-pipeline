"""自演化推演 v10 —— 第八轮：把第七轮的悬案做实

E34 锚定审计误报率：无漂移时多常误报？阈值怎么定才划算（第七轮提出）
E35 E31 重做：大任务池 + 配对设计，留出集膨胀是否真实存在
E36 bootstrap vs margin：配对设计 + 24 种子（第七轮方差过大）
E37 审计总账：误报成本 vs 漏报损失，什么条件下审计净收益为正
"""
import random, math, statistics
from dataclasses import dataclass, asdict
import sys
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import (Cfg, build_world, build_tasks, retrieve, feats, U, W0,
                     mutate, rand_cfg, boot_lower, pareto_front, K, TOPICS)
from evolve9 import _WORLD, _FC

# 更大的任务池（E35）
def big_pool(seed, n=400):
    E = build_world(seed)
    out = []
    for i in range(n):
        rnd = random.Random(seed * 1000 + i)
        out += build_tasks(E, rnd, 1)
    return E, out


# ═══════════ E34 锚定审计误报率 ═══════════
def e34(seed, thresh, n_anchor=30, gens=30, drift=0.0, eval_every=3):
    """drift=0 → 纯误报率；drift>0 → 检出率
    返回 (误报/检出次数, 首次代数)"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    w = list(W0)
    anchors = []
    for _ in range(n_anchor):
        a, b = rand_cfg(rnd), rand_cfg(rnd)
        anchors.append((a, b, 1.0 if U(E, tr, a) > U(E, tr, b) else -1.0))
    root = Cfg(); arch = [root]; main = root
    fired = 0; first = None
    for g in range(1, gens + 1):
        for _ in range(4):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch, w) - U(E, tr, cand, w)
            d_he = U(E, he, ch, w) - U(E, he, cand, w)
            if d_tr > -0.06: arch.append(ch)
            if d_tr > 0.01 and d_he > 0.01 and U(E, tr, ch, w) > U(E, tr, main, w): main = ch
        arch = pareto_front(arch, E, tr) or arch[-1:]
        if drift > 0:
            f = feats(E, tr, main); fn = math.sqrt(sum(x * x for x in f)) or 1.0
            tgt = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
            w = [(1 - drift) * wi + drift * ti for wi, ti in zip(w, tgt)]
        if g % eval_every == 0:
            acc = sum(1 for a, b, y in anchors
                      if (U(E, tr, a, w) - U(E, tr, b, w)) * y > 0) / len(anchors)
            if acc < thresh:
                fired += 1
                if first is None: first = g
    return fired, first


# ═══════════ E35 留出集膨胀（大池重做）═══════════
def e35(seed, schedule, gens=200, kids=4, held_n=12):
    """任务池 400 条（互不重叠）；held 从池中取，fresh 是未用过的一段
    schedule: 'never' / int(每N代轮换)。返回 (自报提升, 真实提升, 换过几次)"""
    E, pool = big_pool(seed, 400)
    rnd = random.Random(seed * 17)
    tr = pool[:20]
    fresh = pool[300:340]
    base_fresh = U(E, fresh, Cfg())
    N = schedule if isinstance(schedule, int) else 10 ** 9
    ptr = 20
    def take():
        nonlocal ptr
        seg = pool[ptr:ptr + held_n]; ptr += held_n
        if ptr > 280: ptr = 20
        return seg
    held = take()
    root = Cfg(); arch = [root]; main = root
    used = 0; swaps = 0
    for g in range(gens):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch) - U(E, tr, cand)
            d_he = U(E, held, ch) - U(E, held, cand)
            if d_tr > -0.06: arch.append(ch)
            if d_tr > 0.01 and d_he > 0.01 and U(E, tr, ch) > U(E, tr, main): main = ch
        arch = arch[-25:]
        used += 1
        if used >= N:
            held = take(); used = 0; swaps += 1
    return (U(E, held, main) - U(E, held, root),
            U(E, fresh, main) - base_fresh, swaps)


# ═══════════ E36 bootstrap vs margin（配对 + 多种子）══════════
def e36(seed, gate, margin=0.01, noise=0.05, gens=25, kids=4):
    """配对设计：同一 seed 下两种门控共享同一世界与初始档案"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg(); arch = [root]; main = root
    for g in range(gens):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch) - U(E, tr, cand) + rnd.gauss(0, noise)
            d_he = U(E, he, ch) - U(E, he, cand) + rnd.gauss(0, noise)
            if gate == "boot":
                dts = [U(E, [t], ch) - U(E, [t], cand) for t in tr]
                dhs = [U(E, [t], ch) - U(E, [t], cand) for t in he]
                ok = boot_lower(dts, rnd) > 0 and boot_lower(dhs, rnd) > 0
            else:
                ok = d_tr > margin and d_he > margin
            if d_tr > -0.06: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if ok and U(E, tr, ch) > U(E, tr, main): main = ch
    return U(E, fresh, main) - U(E, fresh, root)


# ═══════════ E37 审计总账 ═══════════
def e37(seed, thresh, c_audit=3.0, c_arb=10.0, c_drift_per_gen=0.02,
        drift=0.0, gens=30, eval_every=3):
    """drift=0：只有误报成本（净收益为负）
       drift>0：漏报一代损失 c_drift_per_gen
    返回净收益 = 避免的漂移损失 − 审计成本 − 裁决成本"""
    fired, first = e34(seed, thresh, gens=gens, drift=drift, eval_every=eval_every)
    n_audits = gens // eval_every
    cost = n_audits * 0 + fired * c_arb          # 每次触发都要人工裁决
    if drift == 0:
        return -cost, fired
    # 有漂移：从第 1 代起就在损失，检出后停止
    lost_gens = first if first else gens
    avoided = (gens - lost_gens) * c_drift_per_gen
    return avoided - cost, fired
