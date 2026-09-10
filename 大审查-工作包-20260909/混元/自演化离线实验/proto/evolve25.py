"""自演化推演 v25 —— 第二十二轮：审计之外还有什么

二十一轮证明：真值审计收益 (+0.059) >> 盲评极致化 (+0.023)，margin 标定 ≈ 0。
本轮问：审计之后，下一个 +0.05 从哪来？

E101 检索结构演化：不只调权重，还能改"检索方式"（是否过滤/是否扩展/是否重排）
E102 元层判断集更新：人定期补充判断样本（而不只是审计一次性的"有没有用"）
E103 双通道互检：judge(A) 与 judge(B) 相互校验，能否替代真值审计
E104 演化自身参数（学习率式）：变异幅度、档案采样温度
E105 人类注意力的最优分配：把固定预算分给 (盲评工程 / 真值审计 / 判断集) 三处
"""
import random, math, statistics, sys
from dataclasses import dataclass, asdict
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks, K, TOPICS
from evolve20 import build_world_v2, Cfg2, retrieve2, truth_score, judge_score
from evolve24 import (mutate_coord, pareto_clean, surf_mag, _m, V4A, run as run24,
                      SURF)


# ═══════════ E101 检索结构演化 ═══════════
@dataclass(frozen=True)
class CfgS:
    w_kw: float = 3.0
    w_content: float = 1.0
    w_imp: float = 1.0
    w_age: float = 0.1
    w_len: float = 0.0
    w_fmt: float = 0.0
    w_den: float = 0.0
    w_cit: float = 0.0
    filter_zero: int = 0
    deep: int = 0
    expand: int = 0        # 结构基因：是否扩展查询（同 kw 的相邻条目）
    rerank: int = 0        # 结构基因：是否对 top-K 二次重排
    dedup: int = 0         # 结构基因：是否去重（同 content 只保留一条）


def to_c2s(c):
    return Cfg2(w_kw=c.w_kw, w_content=c.w_content, w_imp=c.w_imp, w_age=c.w_age,
                w_len=c.w_len, w_fmt=c.w_fmt, w_den=c.w_den, w_cit=c.w_cit,
                filter_zero=c.filter_zero, deep=c.deep)


def retrieve_s(E, task, c):
    top = retrieve2(E, task, to_c2s(c))
    if c.expand:
        kw = task.get("kw")
        extra = [e for e in E if e["kw"] == kw and e not in top]
        top = top + extra[:2]
    if c.dedup:
        seen = set(); out = []
        for e in top:
            k = e["content"][:12]
            if k in seen: continue
            seen.add(k); out.append(e)
        top = out
    if c.rerank:
        top = sorted(top, key=lambda e: -e["true_quality"] * 0.0 - e["importance"])
    return top[:K]


def e101(seed, allow_struct, alpha=0.5, gens=35, kids=4, blind=True,
         audit=True, probe_n=4, audit_every=5):
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    probe = build_tasks(E, random.Random(4242), probe_n, offset=7)
    root = CfgS()
    base = _m(truth_score(E, t, root) for t in fresh)
    eff = 0.95 if blind else alpha

    def jsc(c, tasks):
        return _m(judge_score(E, t, c, eff) for t in tasks)

    def tc(c, tasks):
        return _m(truth_score(E, t, c) for t in tasks)

    def mut(c):
        d = asdict(c); r = rnd.random()
        if allow_struct and r < 0.12:
            d[rnd.choice(["expand", "rerank", "dedup"])] = rnd.randint(0, 1)
        elif r < 0.20:
            d["deep"] = 1 - d["deep"]
        elif r < 0.28:
            d["filter_zero"] = 1 - d["filter_zero"]
        else:
            p = rnd.choice(["w_kw", "w_content", "w_imp", "w_age"] + list(SURF))
            d[p] = round(max(-5.0, min(20.0, d[p] * rnd.choice([0.6, 0.85, 1.2, 1.6])
                                       + rnd.choice([0, 0, 0.5, -0.5]))), 4)
        return CfgS(**d)

    arch = [root]; main = root; best = main; btr = None
    for g in range(1, gens + 1):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mut(cand)
            d_tr = jsc(ch, tr) - jsc(cand, tr) + rnd.gauss(0, 0.05)
            d_he = jsc(ch, he) - jsc(cand, he) + rnd.gauss(0, 0.05)
            if d_tr > -0.04: arch.append(ch)
            arch = arch[-8:]
            if d_tr > 0.02 and d_he > 0.02 and jsc(ch, tr) > jsc(main, tr): main = ch
        if audit and g % audit_every == 0:
            cur = tc(main, probe)
            if btr is None: btr = cur; best = main
            elif cur < btr - 0.01: main = best; arch = [main]
            else: best = main; btr = cur
    return tc(main, fresh) - base


# ═══════════ E102 判断集定期更新 ═══════════
def e102(seed, refresh_every, n_new=20, gens=35, alpha=0.5, blind=True,
         audit=True, probe_n=4, audit_every=5):
    """人定期补充判断样本 → 重新拟合效用函数 → 更新 judge 的"真值权重"
    这里简化为：每次刷新把 judge 的 eff 提升（逼近真值），但会逐渐衰减"""
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    probe = build_tasks(E, random.Random(4242), probe_n, offset=7)
    root = Cfg2()
    base = _m(truth_score(E, t, root) for t in fresh)
    eff = 0.95 if blind else alpha
    eff0 = eff
    arch = [root]; main = root; best = main; btr = None
    for g in range(1, gens + 1):
        # 判断集刷新：eff 短暂提升，然后衰减（模拟"人补充了样本，但世界在变"）
        if refresh_every and g % refresh_every == 0:
            eff = min(1.0, eff0 + 0.04)
        else:
            eff = max(alpha, eff - 0.004)
        for _ in range(4):
            cand = rnd.choice(arch[-3:]); ch = mutate_coord(cand, rnd, True)
            d_tr = (_m(judge_score(E, t, ch, eff) for t in tr)
                    - _m(judge_score(E, t, cand, eff) for t in tr) + rnd.gauss(0, 0.05))
            d_he = (_m(judge_score(E, t, ch, eff) for t in he)
                    - _m(judge_score(E, t, cand, eff) for t in he) + rnd.gauss(0, 0.05))
            if d_tr > -0.04: arch.append(ch)
            arch = pareto_clean(arch, E, tr, he, eff) or arch[-1:]
            if len(arch) > 8: arch = rnd.sample(arch, 8)
            if d_tr > 0.02 and d_he > 0.02 and \
               _m(judge_score(E, t, ch, eff) for t in tr) > \
               _m(judge_score(E, t, main, eff) for t in tr): main = ch
        if audit and g % audit_every == 0:
            cur = _m(truth_score(E, t, main) for t in probe)
            if btr is None: btr = cur; best = main
            elif cur < btr - 0.01: main = best; arch = [main]
            else: best = main; btr = cur
    return _m(truth_score(E, t, main) for t in fresh) - base


# ═══════════ E103 双通道互检 ═══════════
def e103(seed, mode, gens=35, alpha=0.5, blind=True, probe_n=4, audit_every=5):
    """mode: truth   —— 真值审计（人直接判断）
             dual    —— 两个独立 judge 互检（都是 LLM，但有不同偏差）
             none    —— 不审计
    问：双通道互检能否替代真值审计？"""
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    probe = build_tasks(E, random.Random(4242), probe_n, offset=7)
    root = Cfg2()
    base = _m(truth_score(E, t, root) for t in fresh)
    eff = 0.95 if blind else alpha
    # judge B：与 judge A 独立的表象偏差（不同随机权重）
    wb = [rnd.gauss(0, 1) for _ in range(4)]

    def jscB(c, tasks):
        """judge B：独立偏差"""
        tops = [retrieve2(E, t, c) for t in tasks]; tops = [x for x in tops if x]
        if not tops: return 0.0
        real = _m(e["true_quality"] for x in tops for e in x)
        surf = _m(wb[0] * e["length"] + wb[1] * e["formatting"]
                  + wb[2] * e["kw_density"] + wb[3] * e["has_citation"]
                  for x in tops for e in x)
        return eff * real + (1 - eff) * surf

    arch = [root]; main = root; best = main; btr = None; reverts = 0
    for g in range(1, gens + 1):
        for _ in range(4):
            cand = rnd.choice(arch[-3:]); ch = mutate_coord(cand, rnd, True)
            d_tr = (_m(judge_score(E, t, ch, eff) for t in tr)
                    - _m(judge_score(E, t, cand, eff) for t in tr) + rnd.gauss(0, 0.05))
            d_he = (_m(judge_score(E, t, ch, eff) for t in he)
                    - _m(judge_score(E, t, cand, eff) for t in he) + rnd.gauss(0, 0.05))
            if d_tr > -0.04: arch.append(ch)
            arch = pareto_clean(arch, E, tr, he, eff) or arch[-1:]
            if len(arch) > 8: arch = rnd.sample(arch, 8)
            if d_tr > 0.02 and d_he > 0.02 and \
               _m(judge_score(E, t, ch, eff) for t in tr) > \
               _m(judge_score(E, t, main, eff) for t in tr): main = ch
        if mode != "none" and g % audit_every == 0:
            if mode == "truth":
                cur = _m(truth_score(E, t, main) for t in probe)
            else:  # dual：judge B 评估，但 B 也有偏差
                cur = jscB(main, probe)
            if btr is None: btr = cur; best = main
            elif cur < btr - 0.01: main = best; arch = [main]; reverts += 1
            else: best = main; btr = cur
    return _m(truth_score(E, t, main) for t in fresh) - base, reverts


# ═══════════ E104 演化自身参数 ═══════════
def e104(seed, scale, temp, gens=35, alpha=0.5, blind=True, audit=True,
         probe_n=4, audit_every=5):
    """scale = 变异幅度倍率；temp = 档案采样温度（0=只取最好，1=均匀随机）"""
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    probe = build_tasks(E, random.Random(4242), probe_n, offset=7)
    root = Cfg2()
    base = _m(truth_score(E, t, root) for t in fresh)
    eff = 0.95 if blind else alpha

    def mut(c):
        d = asdict(c); r = rnd.random()
        if r < 0.08: d["deep"] = 1 - d["deep"]
        elif r < 0.16: d["filter_zero"] = 1 - d["filter_zero"]
        else:
            p = rnd.choice(["w_kw", "w_content", "w_imp", "w_age"] + list(SURF))
            d[p] = round(max(-5.0, min(20.0,
                                       d[p] * (1 + (rnd.choice([-0.4, -0.15, 0.2, 0.6]) * scale))
                                       + rnd.choice([0, 0, 0.5, -0.5]) * scale)), 4)
        return Cfg2(**d)

    def pick(arch):
        if temp <= 0 or len(arch) == 1:
            return max(arch, key=lambda c: _m(judge_score(E, t, c, eff) for t in tr))
        scores = [_m(judge_score(E, t, c, eff) for t in tr) for c in arch]
        lo, hi = min(scores), max(scores)
        if hi - lo < 1e-9:
            return rnd.choice(arch)
        wts = [math.exp((s - lo) / (hi - lo) / max(0.01, temp)) for s in scores]
        tot = sum(wts)
        r = rnd.random() * tot
        acc = 0
        for c, w in zip(arch, wts):
            acc += w
            if r <= acc: return c
        return arch[-1]

    arch = [root]; main = root; best = main; btr = None
    for g in range(1, gens + 1):
        for _ in range(4):
            cand = pick(arch); ch = mut(cand)
            d_tr = (_m(judge_score(E, t, ch, eff) for t in tr)
                    - _m(judge_score(E, t, cand, eff) for t in tr) + rnd.gauss(0, 0.05))
            d_he = (_m(judge_score(E, t, ch, eff) for t in he)
                    - _m(judge_score(E, t, cand, eff) for t in he) + rnd.gauss(0, 0.05))
            if d_tr > -0.04: arch.append(ch)
            arch = pareto_clean(arch, E, tr, he, eff) or arch[-1:]
            if len(arch) > 8: arch = rnd.sample(arch, 8)
            if d_tr > 0.02 and d_he > 0.02 and \
               _m(judge_score(E, t, ch, eff) for t in tr) > \
               _m(judge_score(E, t, main, eff) for t in tr): main = ch
        if audit and g % audit_every == 0:
            cur = _m(truth_score(E, t, main) for t in probe)
            if btr is None: btr = cur; best = main
            elif cur < btr - 0.01: main = best; arch = [main]
            else: best = main; btr = cur
    return _m(truth_score(E, t, main) for t in fresh) - base


# ═══════════ E105 注意力最优分配 ═══════════
def e105(seed, alloc, total=200, gens=40):
    """alloc = (盲评工程, 真值审计, 判断集刷新) 的预算分配比例
    单价：盲评 20 一次性；审计 12/样本·次；判断集 1/条
    返回 (真值增益, 实际花费)"""
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(truth_score(E, t, root) for t in fresh)
    b_blind, b_audit, b_label = alloc
    blind = b_blind >= 20
    eff0 = 0.95 if blind else 0.5
    n_audit = int(b_audit / (4 * 12)) if b_audit >= 48 else 0
    n_label = int(b_label / 1)
    eff = eff0
    probe = build_tasks(E, random.Random(4242), 4, offset=7)
    audit_gens = {(i + 1) * (gens // (n_audit + 1)) for i in range(n_audit)} if n_audit else set()
    label_gens = set(range(1, gens + 1, max(1, gens // max(1, n_label // 20)))) if n_label >= 20 else set()
    arch = [root]; main = root; best = main; btr = None
    for g in range(1, gens + 1):
        if g in label_gens:
            eff = min(1.0, eff0 + 0.04)
        else:
            eff = max(0.5, eff - 0.004)
        for _ in range(4):
            cand = rnd.choice(arch[-3:]); ch = mutate_coord(cand, rnd, True)
            d_tr = (_m(judge_score(E, t, ch, eff) for t in tr)
                    - _m(judge_score(E, t, cand, eff) for t in tr) + rnd.gauss(0, 0.05))
            d_he = (_m(judge_score(E, t, ch, eff) for t in he)
                    - _m(judge_score(E, t, cand, eff) for t in he) + rnd.gauss(0, 0.05))
            if d_tr > -0.04: arch.append(ch)
            arch = pareto_clean(arch, E, tr, he, eff) or arch[-1:]
            if len(arch) > 8: arch = rnd.sample(arch, 8)
            if d_tr > 0.02 and d_he > 0.02 and \
               _m(judge_score(E, t, ch, eff) for t in tr) > \
               _m(judge_score(E, t, main, eff) for t in tr): main = ch
        if g in audit_gens:
            cur = _m(truth_score(E, t, main) for t in probe)
            if btr is None: btr = cur; best = main
            elif cur < btr - 0.01: main = best; arch = [main]
            else: best = main; btr = cur
    spend = (20 if blind else 0) + n_audit * 4 * 12 + n_label
    return _m(truth_score(E, t, main) for t in fresh) - base, spend
