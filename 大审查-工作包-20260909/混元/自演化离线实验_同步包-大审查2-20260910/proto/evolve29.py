"""自演化推演 v29 —— 第二十六轮：系统能否控制自己的写入质量

上一轮标记的关键问题：E119 的写入质量是【外部指定】的参数。
真实系统里，写入质量是【内生的】——系统自己决定往条目里投什么。

本轮把写入质量变成可演化的基因：

writalloc ∈ [0,1]：写入时把预算投给【真实质量】的比例
  1.0 = 全投真实质量（内容扎实，表象朴素）
  0.0 = 全投表象（格式漂亮、长、有引用，但内容空）

若 judge 被表象污染，系统应演化出 writalloc → 0，世界被垃圾占满。

E121 内生写入质量：系统会演化向"认真写"还是"迎合写"？
E122 整理标准：用 judge 整理（会被污染）vs 用真值整理（太贵）vs 混合
E123 写入 × 审计 × 整理 三元交互
E124 空世界冷启动：无初始条目，自写入能否建立可用世界
"""
import random, math, statistics, sys
from dataclasses import dataclass, asdict
from collections import Counter
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks, K, TOPICS
from evolve20 import build_world_v2, Cfg2, retrieve2, truth_score, judge_score
from evolve24 import pareto_clean, surf_mag, _m, SURF
from evolve28 import write_entry


@dataclass(frozen=True)
class CfgW:
    """带写入策略的配置"""
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
    writalloc: float = 0.5      # ★ 内生写入质量：投给真实质量的比例


def to_c2(c):
    return Cfg2(w_kw=c.w_kw, w_content=c.w_content, w_imp=c.w_imp, w_age=c.w_age,
                w_len=c.w_len, w_fmt=c.w_fmt, w_den=c.w_den, w_cit=c.w_cit,
                filter_zero=c.filter_zero, deep=c.deep)


def write_with_alloc(E, rnd, cfg, alloc, topic_hint=None):
    """按 alloc 分配预算：alloc=1 全投真实质量；alloc=0 全投表象"""
    i = len(E)
    k = f"K{rnd.randrange(6)}"
    t = topic_hint or rnd.choice(TOPICS)
    tok = t if rnd.random() < 0.5 else rnd.choice(TOPICS)
    E.append({
        "id": f"n{i}", "kw": k, "topic": t, "keywords": [k],
        "content": f"{tok} {k} 自写入{i}",
        "importance": rnd.randint(1, 3), "age_days": 0,
        "true_quality": rnd.random() * alloc,          # 真实质量 ∝ alloc
        "length": rnd.random() * (1 - alloc) + 0.5 * alloc,
        "formatting": rnd.random() * (1 - alloc) + 0.5 * alloc,
        "kw_density": rnd.random() * (1 - alloc) + 0.5 * alloc,
        "has_citation": 1.0 if rnd.random() < (1 - alloc) else 0.5,
        "self_written": True,
    })


def run(seed, d, gens=30, kids=4, alpha=0.5, collect=False):
    rnd = random.Random(seed)
    E = build_world_v2(seed) if d.get("init_world", True) else []
    for e in E:
        e.setdefault("self_written", False)
    # 冷启动：世界空时，先播种 seed_n 条，把该状态作为基准世界 E0
    if not E and d.get("init_world", True) is False:
        _seed_cfg = CfgW()
        _n = d.get("seed_n", 30)
        for _i in range(_n):
            _e_kw = f"K{_i % 6}"          # 均匀铺开 6 类
            _r = random.Random(seed * 1000 + _i)
            E.append({
                "id": f"s{_i}", "kw": _e_kw, "topic": TOPICS[_i % 16],
                "keywords": [_e_kw],
                "content": f"{TOPICS[_i % 16]} {_e_kw} 播种{_i}",
                "importance": _r.randint(1, 3), "age_days": 0,
                "true_quality": _r.random() * d.get("init_alloc", 0.5),
                "length": _r.random(), "formatting": _r.random(),
                "kw_density": _r.random(),
                "has_citation": 1.0 if _r.random() < 0.5 else 0.0,
                "self_written": True,
            })
    E0 = [dict(e) for e in E]
    audit_set = build_tasks(E0, random.Random(7777), 40, offset=5) if E0 else []
    root = CfgW()
    base = _m(truth_score(E0, t, to_c2(root)) for t in audit_set) if audit_set else 0.0

    eff = 0.95 if d.get("blind") else alpha
    scale = d.get("scale", 1.0)
    cap = d.get("cap", 8)
    m = d.get("margin", 0.02)
    tol = d.get("tol", 0.04)
    write_every = d.get("write_every", 2)
    write_n = d.get("write_n", 3)
    prune_by = d.get("prune_by", None)      # None / "judge" / "truth" / "mixed"
    prune_every = d.get("prune_every", 2)
    probe = build_tasks(E0, random.Random(4242), 4, offset=7) if E0 else []

    arch = [root]
    main = root
    best = main
    btr = None
    st = {"reverts": 0, "audits": 0, "n_self": 0, "writalloc": 0.0}

    def jsc(c, tasks):
        return _m(judge_score(E, t, to_c2(c), eff) for t in tasks)

    def mut(c):
        dd = asdict(c)
        r = rnd.random()
        if d.get("evolve_alloc", True) and r < 0.15:
            dd["writalloc"] = round(max(0.0, min(1.0,
                dd["writalloc"] + rnd.choice([-0.3, -0.15, 0.15, 0.3]))), 3)
        elif r < 0.23:
            dd["deep"] = 1 - dd["deep"]
        elif r < 0.31:
            dd["filter_zero"] = 1 - dd["filter_zero"]
        else:
            p = rnd.choice(["w_kw", "w_content", "w_imp", "w_age"] + list(SURF))
            dd[p] = round(max(-5.0, min(20.0,
                                        dd[p] * (1 + rnd.choice([-0.4, -0.15, 0.2, 0.6]) * scale)
                                        + rnd.choice([0, 0, 0.5, -0.5]) * scale)), 4)
        return CfgW(**dd)

    for g in range(1, gens + 1):
        if not E:
            # 冷启动：世界空，必须先写
            for _ in range(write_n * 2):
                write_with_alloc(E, rnd, main, main.writalloc)
                st["n_self"] += 1
        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
        for _ in range(kids):
            cand = rnd.choice(arch[-3:])
            ch = mut(cand)
            d_tr = jsc(ch, tr) - jsc(cand, tr) + rnd.gauss(0, 0.05)
            d_he = jsc(ch, he) - jsc(cand, he) + rnd.gauss(0, 0.05)
            if d_tr > -tol:
                arch.append(ch)
            arch = pareto_clean(arch, E, tr, he, eff) or arch[-1:]
            if len(arch) > cap:
                arch = rnd.sample(arch, cap)
            if d_tr > m and d_he > m and jsc(ch, tr) > jsc(main, tr):
                main = ch
        if write_every and g % write_every == 0:
            tops = []
            for t in tr:
                tops += retrieve2(E, t, to_c2(main))
            for _ in range(write_n):
                hint = rnd.choice(tops)["topic"] if tops else None
                write_with_alloc(E, rnd, main, main.writalloc, topic_hint=hint)
                st["n_self"] += 1
        if prune_by and g % prune_every == 0:
            mine = [e for e in E if e.get("self_written")]
            if len(mine) > 8:
                if prune_by == "judge":
                    mine.sort(key=lambda e: -judge_score(E, {"q": e["topic"]},
                                                         to_c2(main), eff))
                elif prune_by == "truth":
                    mine.sort(key=lambda e: e["true_quality"])
                else:  # mixed：一半按 judge 保留，一半按真值淘汰
                    mine.sort(key=lambda e: e["true_quality"])
                    half = len(mine) // 2
                    keep = mine[:half] + sorted(mine[half:],
                                                key=lambda e: -e["true_quality"])[:half]
                    mine = [e for e in mine if e not in keep] or mine
                n_rm = max(1, len(mine) // 4)
                for e in mine[:n_rm]:
                    if e in E:
                        E.remove(e)
        if d.get("audit") and audit_set and g % d.get("audit_every", 5) == 0:
            st["audits"] += 1
            cur = _m(truth_score(E, t, to_c2(main)) for t in probe)
            if btr is None:
                btr = cur
                best = main
            elif cur < btr - 0.01:
                main = best
                arch = [main]
                st["reverts"] += 1
            else:
                best = main
                btr = cur

    if audit_set:
        gain = _m(truth_score(E, t, to_c2(main)) for t in audit_set) - base
    else:
        gain = 0.0
    if collect:
        st["writalloc"] = main.writalloc
        st["final_size"] = len(E)
        st["self_frac"] = (sum(1 for e in E if e.get("self_written")) / len(E)) if E else 0
        st["avg_quality"] = statistics.mean([e["true_quality"] for e in E]) if E else 0
        st["surf"] = surf_mag(to_c2(main))
        return gain, st
    return gain


BASE = dict(blind=True, audit=True, audit_every=5, scale=1.0,
            pareto=True, cap=8, tol=0.04, margin=0.02, monitor=True,
            write_every=2, write_n=3, evolve_alloc=True)


def e121(seed, alpha, evolve_alloc=True, gens=30):
    """judge 污染程度不同时，writalloc 会演化向哪。
    ★ 必须 blind=False，否则 eff 被固定为 0.95，alpha 完全失效"""
    return run(seed, dict(BASE, evolve_alloc=evolve_alloc, blind=False),
               gens=gens, alpha=alpha, collect=True)


def e122(seed, prune_by, gens=30):
    return run(seed, dict(BASE, prune_by=prune_by, prune_every=2),
               gens=gens, collect=True)


def e123(seed, audit, prune_by, gens=30):
    return run(seed, dict(BASE, audit=audit, prune_by=prune_by, prune_every=2),
               gens=gens)


def e124(seed, init_world, gens=30):
    """冷启动：空世界（系统自己播种）vs 有初始世界"""
    return run(seed, dict(BASE, init_world=init_world, seed_n=30,
                          init_alloc=0.5), gens=gens, collect=True)


def e121b(seed, gens, gens_write=None):
    """长周期：writalloc 是否会随代数漂移？"""
    return run(seed, dict(BASE, blind=False, write_every=1, write_n=5),
               gens=gens, alpha=0.5, collect=True)
