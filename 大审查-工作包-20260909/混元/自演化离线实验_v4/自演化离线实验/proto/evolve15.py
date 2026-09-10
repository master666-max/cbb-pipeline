"""自演化推演 v15 —— 第十三轮：残留风险 & 系统级失效

E57 相关噪声金标（第十二轮标记的最危险未测项）：标注者有系统性偏好
E58 规避基因为随机变异产物（E47 变体）：能否延缓首次检出
E59 等预算多主线（E48 修正）：总评估次数相同时，岛数的影响
E60 复合失效：多个机制同时轻微失配（而非单个致命错误）
E61 灾难恢复：档案/锚定集部分损坏后的自愈能力
"""
import random, math, statistics, sys
from dataclasses import dataclass, asdict
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import (Cfg, build_world, build_tasks, retrieve, feats, U, W0,
                     mutate, rand_cfg, boot_lower, pareto_front, K, TOPICS)


# ═══════════ E57 相关噪声金标 ═══════════
def biased_tasks(entries, rnd, n, bias_strength, n_kws=6, offset=0):
    """相关噪声：标注者系统性偏好"长内容/高 importance/低龄"的条目，
    而非随机替换 → 训练集与留出集的偏差方向【相同】，双门过滤不掉"""
    out = []
    for i in range(n):
        grp = [e for e in entries if e["kw"] == f"K{(i + offset) % n_kws}"]
        # 按偏见打分选金标（而非选真正相关的）
        scores = []
        for e in grp:
            s = (e["importance"] * 0.5 + (100 - e["age_days"]) / 100.0 * 0.5)
            scores.append((s + rnd.gauss(0, 1.0) * (1 - bias_strength), e))
        scores.sort(key=lambda x: -x[0])
        g = scores[0][1]
        out.append({"q": f"{g['topic']} {g['kw']}", "kw": g["kw"], "golden": g["id"]})
    return out


def e57(seed, bias, gens=30, kids=4):
    """bias=0 完全由偏见决定金标; bias=1 完全随机(无系统偏好)"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = biased_tasks(E, rnd, 16, bias)
    he = biased_tasks(E, rnd, 16, bias, offset=3)
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
    return U(E, fresh, main) - base, main.w_imp


# ═══════════ E58 规避基因为随机变异产物 ═══════════
def e58(seed, mode, gens=40, kids=4, drift=0.15, thresh=0.85, audit_every=3):
    """mode: none  —— 无规避
             random —— inv 随变异随机产生（不是被抓后才提高）
    关键区别：随机的 inv 可能在【首次】检出前就存在 → 能否延缓首次检出？"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    anchors = []
    for _ in range(30):
        a, b = rand_cfg(rnd), rand_cfg(rnd)
        anchors.append((a, b, 1.0 if U(E, tr, a) > U(E, tr, b) else -1.0))
    w_h = list(W0)
    root = Cfg(); arch = [root]; main = root
    base = U(E, fresh, root)
    detected_at = None; det_count = 0; max_inv = 0.0
    cur_inv = 0.0
    for g in range(1, gens + 1):
        inv = 0.0
        if mode != "none":
            # inv 由变异随机产生，且若被选中则被保留 → 选择压力偏好高 inv
            inv = min(1.0, max(0.0, cur_inv + rnd.gauss(0, 0.1)))
            if rnd.random() < 0.3:
                inv = min(1.0, inv + 0.1)
            cur_inv = inv
        max_inv = max(max_inv, inv)
        if g >= gens // 3:
            f = feats(E, tr, main); fn = math.sqrt(sum(x * x for x in f)) or 1.0
            tgt = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
            eff = drift * (1.0 - 0.8 * inv)
            w_h = [(1 - eff) * wi + eff * ti for wi, ti in zip(w_h, tgt)]
        if g % audit_every == 0:
            acc = sum(1 for a, b, y in anchors
                      if (U(E, tr, a, w_h) - U(E, tr, b, w_h)) * y > 0) / len(anchors)
            if acc < thresh:
                det_count += 1
                if detected_at is None: detected_at = g
                w_h = list(W0)
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
    return U(E, fresh, main) - base, detected_at or 999, det_count, max_inv


# ═══════════ E59 等预算多主线 ═══════════
def e59(seed, n_islands, total_evals=160, gens=40, migrate=False):
    """等预算：总评估次数固定，岛数越多则每岛每代的后代数越少"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base = U(E, fresh, Cfg())
    root = Cfg()
    kids_per = max(1, total_evals // (gens * n_islands))
    islands = [{"main": root, "arch": [root]} for _ in range(n_islands)]
    for g in range(gens):
        for isl in islands:
            for _ in range(kids_per):
                cand = rnd.choice(isl["arch"][-3:]); ch = mutate(cand, rnd)
                d_tr = U(E, tr, ch) - U(E, tr, cand)
                d_he = U(E, he, ch) - U(E, he, cand)
                if d_tr > -0.06: isl["arch"].append(ch)
                isl["arch"] = pareto_front(isl["arch"], E, tr) or isl["arch"][-1:]
                if len(isl["arch"]) > 12: isl["arch"] = rnd.sample(isl["arch"], 12)
                if d_tr > 0.01 and d_he > 0.01 and U(E, tr, ch) > U(E, tr, isl["main"]):
                    isl["main"] = ch
        if migrate and n_islands > 1 and g % 8 == 0:
            best = max(islands, key=lambda i: U(E, tr, i["main"]))
            for isl in islands:
                if isl is not best and U(E, tr, best["main"]) > U(E, tr, isl["main"]):
                    isl["main"] = best["main"]
    return U(E, fresh, max(islands, key=lambda i: U(E, tr, i["main"]))["main"]) - base


# ═══════════ E60 复合失配 ═══════════
def e60(seed, mode, gens=30):
    """mode: ideal    —— 全部参数正确
             mild     —— 每个参数都轻微失配（margin 3x、tol 3x、档案上限 2x、审计阈值 +0.05）
             compound —— 上述失配同时出现（模拟"没人调参"的真实情况）"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base = U(E, fresh, Cfg())
    P = {"margin": 0.01, "tol": 0.06, "cap": 12, "thresh": 0.85}
    if mode == "mild":
        P = {"margin": 0.03, "tol": 0.18, "cap": 24, "thresh": 0.90}
    elif mode == "compound":
        P = {"margin": 0.05, "tol": 0.30, "cap": 40, "thresh": 0.95}
    root = Cfg(); arch = [root]; main = root
    for g in range(gens):
        for _ in range(4):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch) - U(E, tr, cand)
            d_he = U(E, he, ch) - U(E, he, cand)
            if d_tr > -P["tol"]: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > P["cap"]: arch = rnd.sample(arch, P["cap"])
            if d_tr > P["margin"] and d_he > P["margin"] and U(E, tr, ch) > U(E, tr, main):
                main = ch
    return U(E, fresh, main) - base, len(arch)


# ═══════════ E61 灾难恢复 ═══════════
def e61(seed, damage, gens_after=25, gens_before=25):
    """damage: none / archive(档案清空) / anchor(锚定集损坏一半) / both
    测：损坏后能否恢复到损坏前的水平"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base = U(E, fresh, Cfg())
    anchors = []
    for _ in range(30):
        a, b = rand_cfg(rnd), rand_cfg(rnd)
        anchors.append((a, b, 1.0 if U(E, tr, a) > U(E, tr, b) else -1.0))
    root = Cfg(); arch = [root]; main = root
    for g in range(gens_before):
        for _ in range(4):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch) - U(E, tr, cand)
            d_he = U(E, he, ch) - U(E, he, cand)
            if d_tr > -0.06: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > 12: arch = rnd.sample(arch, 12)
            if d_tr > 0.01 and d_he > 0.01 and U(E, tr, ch) > U(E, tr, main): main = ch
    before = U(E, fresh, main) - base
    if damage in ("archive", "both"): arch = [main]
    if damage in ("anchor", "both"): anchors = anchors[:len(anchors) // 2]
    for g in range(gens_after):
        for _ in range(4):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch) - U(E, tr, cand)
            d_he = U(E, he, ch) - U(E, he, cand)
            if d_tr > -0.06: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > 12: arch = rnd.sample(arch, 12)
            if d_tr > 0.01 and d_he > 0.01 and U(E, tr, ch) > U(E, tr, main): main = ch
    after = U(E, fresh, main) - base
    return before, after, after - before
