"""自演化推演 v17 —— 第十五轮：修正上一轮的已知缺陷

E67 失败模式覆盖重做（E65 有严重实现缺陷）：每个失败模式单独实现"护栏关闭"
E68 参数联合标定（E66 阶段5 为负）：在目标场景上联合搜索，对比独立最优
E69 外部性衰减：锚定集是唯一外部参照，它老化后系统还能维持吗
E70 元层签名的最小频率：多久需要人签一次名，低于此频率会怎样
"""
import random, math, statistics, sys, itertools
from dataclasses import dataclass, asdict
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import (Cfg, build_world, build_tasks, retrieve, feats, U, W0,
                     mutate, rand_cfg, boot_lower, pareto_front, K, TOPICS)
from evolve16 import make_anchors, build_spur_tasks


# ═══════════ E67 失败模式覆盖（重做）═══════════
def e67(seed, failure, guard=True, gens=35):
    """每个失败模式【单独】实现护栏开关。guard=True 表示该护栏开启。
    failure -> 对应护栏:
      drift          -> audit(锚定审计+重锚)
      spur           -> holdout(留出集门)
      deceptive      -> archive(Pareto, 而非单一最优)
      switch         -> archive
      noisy_gold     -> holdout(部分)
      margin_large   -> monitor(停摆监控)
      accept_cheap   -> cheap_reject_only
      no_holdout     -> holdout
      single_archive -> archive
    """
    rnd = random.Random(seed)
    E = build_world(seed)
    if failure == "spur":
        tr = build_spur_tasks(E, rnd, 16, 1); he = build_spur_tasks(E, rnd, 16, 0, offset=3)
        fresh = build_spur_tasks(E, random.Random(7777), 40, 0, offset=5)
    else:
        tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
        fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    if failure == "noisy_gold":
        for t in tr + he:
            if rnd.random() < 0.3: t["golden"] = rnd.choice(E)["id"]
    base = U(E, fresh, Cfg())

    # 默认全开；guard=False 时【只关对应那一条】
    audit = holdout = archive = monitor = cheap_ok = True
    if not guard:
        if failure in ("drift",): audit = False
        elif failure in ("spur", "no_holdout", "noisy_gold"): holdout = False
        elif failure in ("deceptive", "switch", "single_archive"): archive = False
        elif failure == "margin_large": monitor = False
        elif failure == "accept_cheap": cheap_ok = False

    anchors = make_anchors(E, tr, 30, random.Random(seed + 999))
    root = Cfg(); arch = [root]; main = root
    m = 0.15 if failure == "margin_large" else 0.02
    tol, cap = 0.04, 12
    w = list(W0); stall = 0
    for g in range(1, gens + 1):
        if failure == "drift" and g >= gens // 3:
            f = feats(E, tr, main); fn = math.sqrt(sum(x * x for x in f)) or 1.0
            tgt = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
            w = [(1 - 0.15) * wi + 0.15 * ti for wi, ti in zip(w, tgt)]
        def obj(c):
            if failure == "deceptive":
                return U(E, tr, c, w) + (0.40 if (c.deep and c.filter_zero)
                                         else (-0.10 if (c.deep or c.filter_zero) else 0.0))
            if failure == "switch" and g >= gens // 2:
                return -(feats(E, tr, c)[1] + feats(E, tr, c)[2])
            return U(E, tr, c, w)
        adopts = 0
        for _ in range(4):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = obj(ch) - obj(cand) + rnd.gauss(0, 0.05)
            d_he = U(E, he, ch, w) - U(E, he, cand, w) + rnd.gauss(0, 0.05)
            if not cheap_ok and failure == "accept_cheap":
                # 违规：廉价评估直接用于采纳
                if d_tr + rnd.gauss(0, 0.25) > 0.01:
                    main = ch; adopts += 1
                    if d_tr > -tol: arch.append(ch)
                if archive:
                    arch = pareto_front(arch, E, tr) or arch[-1:]
                    if len(arch) > cap: arch = rnd.sample(arch, cap)
                else:
                    arch = [max(arch, key=obj)]
                continue
            if d_tr > -tol: arch.append(ch)
            if archive:
                arch = pareto_front(arch, E, tr) or arch[-1:]
                if len(arch) > cap: arch = rnd.sample(arch, cap)
            else:
                arch = [max(arch, key=obj)]
            ok = (d_tr > m and d_he > m) if holdout else (d_tr > m)
            if ok and obj(ch) > obj(main): main = ch; adopts += 1
        if monitor:
            stall = 0 if adopts else stall + 1
            if stall >= 5: m = max(0.005, m * 0.5); stall = 0
        if audit and g % 3 == 0 and anchors:
            acc = sum(1 for a, b, y in anchors
                      if (U(E, tr, a, w) - U(E, tr, b, w)) * y > 0) / len(anchors)
            if acc < 0.85:
                w = list(W0)
                anchors = make_anchors(E, tr, 30, random.Random(seed + 1000 + g))
    return U(E, fresh, main) - base


# ═══════════ E68 参数联合标定 ═══════════
def e68(seed, params, scenario="mixed", gens=35):
    """params = (margin, tol, cap)"""
    m, tol, cap = params
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base = U(E, fresh, Cfg())
    anchors = make_anchors(E, tr, 30, random.Random(seed + 999))
    root = Cfg(); arch = [root]; main = root; w = list(W0); stall = 0
    for g in range(1, gens + 1):
        if scenario == "mixed" and g >= gens // 3:
            f = feats(E, tr, main); fn = math.sqrt(sum(x * x for x in f)) or 1.0
            tgt = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
            w = [(1 - 0.12) * wi + 0.12 * ti for wi, ti in zip(w, tgt)]
        adopts = 0
        for _ in range(4):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch, w) - U(E, tr, cand, w) + rnd.gauss(0, 0.05)
            d_he = U(E, he, ch, w) - U(E, he, cand, w) + rnd.gauss(0, 0.05)
            if d_tr > -tol: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > cap: arch = rnd.sample(arch, cap)
            if d_tr > m and d_he > m and U(E, tr, ch, w) > U(E, tr, main, w):
                main = ch; adopts += 1
        stall = 0 if adopts else stall + 1
        if stall >= 5: m = max(0.005, m * 0.5); stall = 0
        if g % 3 == 0 and anchors:
            acc = sum(1 for a, b, y in anchors
                      if (U(E, tr, a, w) - U(E, tr, b, w)) * y > 0) / len(anchors)
            if acc < 0.85:
                w = list(W0)
                anchors = make_anchors(E, tr, 30, random.Random(seed + 1000 + g))
    return U(E, fresh, main) - base


# ═══════════ E69 锚定集老化 ═══════════
def e69(seed, refresh, gens=60, drift=0.10):
    """refresh: never / every_N / adaptive(检出漂移后重采)
    锚定集是唯一外部参照。若它老化（与新世界脱节），系统还能维持吗？"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base = U(E, fresh, Cfg())
    anchors = make_anchors(E, tr, 30, random.Random(seed + 999))
    root = Cfg(); arch = [root]; main = root; w = list(W0)
    N = refresh if isinstance(refresh, int) else 10 ** 9
    reanchor_n = 0
    for g in range(1, gens + 1):
        f = feats(E, tr, main); fn = math.sqrt(sum(x * x for x in f)) or 1.0
        tgt = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
        w = [(1 - drift) * wi + drift * ti for wi, ti in zip(w, tgt)]
        if g % 3 == 0:
            acc = sum(1 for a, b, y in anchors
                      if (U(E, tr, a, w) - U(E, tr, b, w)) * y > 0) / len(anchors)
            if acc < 0.85:
                if refresh != "never":
                    w = list(W0); reanchor_n += 1
                    if refresh == "adaptive":
                        anchors = make_anchors(E, tr, 30, random.Random(seed + 1000 + g))
        elif isinstance(refresh, int) and g % N == 0:
            anchors = make_anchors(E, tr, 30, random.Random(seed + 1000 + g))
            reanchor_n += 1
        for _ in range(4):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch, w) - U(E, tr, cand, w) + rnd.gauss(0, 0.05)
            d_he = U(E, he, ch, w) - U(E, he, cand, w) + rnd.gauss(0, 0.05)
            if d_tr > -0.04: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > 12: arch = rnd.sample(arch, 12)
            if d_tr > 0.02 and d_he > 0.02 and U(E, tr, ch, w) > U(E, tr, main, w):
                main = ch
    return U(E, fresh, main) - base, reanchor_n


# ═══════════ E70 元层签名最小频率 ═══════════
def e70(seed, sign_every, gens=60, drift=0.10, sign_cost=10):
    """元层（效用函数）每 sign_every 代由人重新签名一次（= 重置为 W0 并通知系统）
    低于某频率 → 漂移积累。返回 (终局效用, 总签名成本)"""
    rnd = random.Random(seed)
    E = build_world(seed)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base = U(E, fresh, Cfg())
    anchors = make_anchors(E, tr, 30, random.Random(seed + 999))
    root = Cfg(); arch = [root]; main = root; w = list(W0)
    signs = 0
    N = sign_every if isinstance(sign_every, int) else 10 ** 9
    for g in range(1, gens + 1):
        f = feats(E, tr, main); fn = math.sqrt(sum(x * x for x in f)) or 1.0
        tgt = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
        w = [(1 - drift) * wi + drift * ti for wi, ti in zip(w, tgt)]
        if g % N == 0:                      # 人重新签名：效用函数重置为初心
            w = list(W0); signs += 1
        if g % 3 == 0 and anchors:
            acc = sum(1 for a, b, y in anchors
                      if (U(E, tr, a, w) - U(E, tr, b, w)) * y > 0) / len(anchors)
            if acc < 0.85:
                w = list(W0)
                anchors = make_anchors(E, tr, 30, random.Random(seed + 1000 + g))
        for _ in range(4):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch, w) - U(E, tr, cand, w) + rnd.gauss(0, 0.05)
            d_he = U(E, he, ch, w) - U(E, he, cand, w) + rnd.gauss(0, 0.05)
            if d_tr > -0.04: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > 12: arch = rnd.sample(arch, 12)
            if d_tr > 0.02 and d_he > 0.02 and U(E, tr, ch, w) > U(E, tr, main, w):
                main = ch
    return U(E, fresh, main) - base, signs * sign_cost
