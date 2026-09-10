"""自演化推演 v28 —— 第二十五轮：打开静态世界假设

【俯瞰发现】115 个实验全部在【静态世界】里：
    build_world 一次性生成 60 条目，演化过程中世界【永不改变】。
    而真实系统的核心恰恰是：系统自己写入记忆条目 → 世界随演化而变
    → 下一代评估的数据集被上一代改变（真正的自指）。

本轮打开这个假设：

E116 自写入世界：系统的输出成为自己未来的输入。会出现什么？
E117 内容坍缩：系统是否会把世界推向"自己擅长的形态"（模式坍缩）？
E118 世界增长 vs 收益：条目累积是资产还是负担？
E119 自写入 + 审计：审计能否抓住"世界被污染"？
E120 遗忘/整理机制：能否缓解坍缩？
"""
import random, math, statistics, sys
from dataclasses import asdict
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks, K, TOPICS
from evolve20 import build_world_v2, Cfg2, retrieve2, truth_score, judge_score
from evolve24 import pareto_clean, surf_mag, _m, SURF


def write_entry(E, rnd, cfg, topic_hint=None, quality=None):
    """系统写入一条新条目。
    关键：条目的形态受当前配置影响——系统会写"容易被自己检索到"的条目。
    true_quality 由 quality 参数指定（用于测试不同情形）。"""
    i = len(E)
    k = f"K{rnd.randrange(6)}"
    t = topic_hint if topic_hint else rnd.choice(TOPICS)
    tok = t if rnd.random() < 0.5 else rnd.choice(TOPICS)
    q = quality if quality is not None else rnd.random()
    e = {
        "id": f"n{i}", "kw": k, "topic": t,
        "keywords": [k],
        "content": f"{tok} {k} 自写入{i}",
        "importance": rnd.randint(1, 3),
        "age_days": 0,
        "true_quality": q,
        "length": rnd.random(),
        "formatting": rnd.random(),
        "kw_density": rnd.random(),
        "has_citation": 1.0 if rnd.random() < 0.5 else 0.0,
        "self_written": True,
    }
    # 若配置偏好表象，新条目会【迎合】：表象特征更高
    bias = (cfg.w_len + cfg.w_fmt + cfg.w_den + cfg.w_cit) / 4.0
    if bias > 0:
        e["length"] = min(1.0, e["length"] + 0.1 * min(3.0, bias))
        e["formatting"] = min(1.0, e["formatting"] + 0.1 * min(3.0, bias))
        e["kw_density"] = min(1.0, e["kw_density"] + 0.1 * min(3.0, bias))
    E.append(e)
    return e


def run(seed, d, gens=30, kids=4, alpha=0.5, collect=False):
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    for e in E:
        e["self_written"] = False
    fresh_seed = 7777
    root = Cfg2()
    # 固定的外部审计集：始终用【初始世界】构建，测真实泛化
    E0 = [dict(e) for e in E]
    audit_set = build_tasks(E0, random.Random(fresh_seed), 40, offset=5)

    base = _m(truth_score(E0, t, root) for t in audit_set)
    eff = 0.95 if d.get("blind") else alpha
    scale = d.get("scale", 1.0)
    cap = d.get("cap", 8)
    m = d.get("margin", 0.02)
    tol = d.get("tol", 0.04)
    write_every = d.get("write_every", 0)      # 每 N 代写入
    write_n = d.get("write_n", 3)
    write_quality = d.get("write_quality", None)  # None=随机；否则固定
    prune = d.get("prune", 0)                    # 每 N 代清理最差的自写入条目
    probe = build_tasks(E0, random.Random(4242), 4, offset=7)

    arch = [root]; main = root; best = main; btr = None
    st = {"reverts": 0, "audits": 0, "n_self": 0, "surf": 0.0}

    def jsc(c, tasks, world=None):
        W = world if world is not None else E
        return _m(judge_score(W, t, c, eff) for t in tasks)

    def mut(c):
        dd = asdict(c); r = rnd.random()
        if r < 0.08: dd["deep"] = 1 - dd["deep"]
        elif r < 0.16: dd["filter_zero"] = 1 - dd["filter_zero"]
        else:
            p = rnd.choice(["w_kw", "w_content", "w_imp", "w_age"] + list(SURF))
            dd[p] = round(max(-5.0, min(20.0,
                                        dd[p] * (1 + rnd.choice([-0.4, -0.15, 0.2, 0.6]) * scale)
                                        + rnd.choice([0, 0, 0.5, -0.5]) * scale)), 4)
        return Cfg2(**dd)

    for g in range(1, gens + 1):
        # 训练集：每次从【当前世界】重建（这是关键：世界变了，训练分布就变了）
        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mut(cand)
            d_tr = jsc(ch, tr) - jsc(cand, tr) + rnd.gauss(0, 0.05)
            d_he = jsc(ch, he) - jsc(cand, he) + rnd.gauss(0, 0.05)
            if d_tr > -tol: arch.append(ch)
            arch = pareto_clean(arch, E, tr, he, eff) or arch[-1:]
            if len(arch) > cap: arch = rnd.sample(arch, cap)
            if d_tr > m and d_he > m and jsc(ch, tr) > jsc(main, tr): main = ch
        # 自写入：把当前 top 结果的主题写回世界
        if write_every and g % write_every == 0:
            tops = []
            for t in tr:
                tops += retrieve2(E, t, main)
            for _ in range(write_n):
                hint = rnd.choice(tops)["topic"] if tops else None
                write_entry(E, rnd, main, topic_hint=hint, quality=write_quality)
                st["n_self"] += 1
        if prune and g % prune == 0:
            mine = [e for e in E if e.get("self_written")]
            if len(mine) > prune * 2:
                mine.sort(key=lambda e: e["true_quality"])
                for e in mine[:max(1, len(mine) // 4)]:
                    E.remove(e)
        if d.get("audit") and g % d.get("audit_every", 5) == 0:
            st["audits"] += 1
            cur = _m(truth_score(E, t, main) for t in probe)
            if btr is None: btr = cur; best = main
            elif cur < btr - 0.01: main = best; arch = [main]; st["reverts"] += 1
            else: best = main; btr = cur

    # 终局评估：用【初始世界】的外部审计集（不随系统污染而变）
    gain = _m(truth_score(E, t, main) for t in audit_set) - base
    if collect:
        st["surf"] = surf_mag(main)
        st["final_size"] = len(E)
        st["self_frac"] = sum(1 for e in E if e.get("self_written")) / len(E)
        # 内容熵：世界是否被推向少数主题
        from collections import Counter
        c = Counter(e["topic"] for e in E)
        tot = sum(c.values())
        st["entropy"] = -sum((v / tot) * math.log(v / tot) for v in c.values()) if tot else 0
        st["max_topic_frac"] = max(c.values()) / tot if tot else 0
        return gain, st
    return gain


# ── 配置 ──
BASE = dict(blind=True, audit=True, audit_every=5, scale=1.0, temp=0.0,
            pareto=True, cap=8, tol=0.04, margin=0.02, monitor=True)


def e116(seed, write_every, gens=30):
    """自写入 vs 静态"""
    return run(seed, dict(BASE, write_every=write_every), gens=gens)


def e117(seed, write_every, gens=30):
    """内容坍缩：世界分布熵"""
    return run(seed, dict(BASE, write_every=write_every), gens=gens, collect=True)


def e118(seed, write_n, gens=30):
    """写入量：条目累积是资产还是负担"""
    return run(seed, dict(BASE, write_every=2, write_n=write_n), gens=gens)


def e119(seed, audit, quality, gens=30):
    """审计能否抓住世界污染（quality 低=系统写入垃圾）"""
    return run(seed, dict(BASE, write_every=2, write_quality=quality,
                          audit=audit), gens=gens)


def e120(seed, prune, gens=30):
    """整理机制能否缓解坍缩"""
    return run(seed, dict(BASE, write_every=2, write_n=3, prune=prune),
               gens=gens, collect=True)
