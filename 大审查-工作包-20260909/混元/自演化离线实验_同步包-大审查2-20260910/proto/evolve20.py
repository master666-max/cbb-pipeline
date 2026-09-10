"""自演化推演 v20 —— A 轮：升级实验世界

十七轮的实验世界太干净：judge 只看特征向量，任务集外部给定，伪特征是独立位。
本轮引入三个真实世界特性：

E81 judge 只看【表象】：LLM-as-judge 看到的是文本，不是真值。
     系统能否通过选择"展示什么"来自我美化？锚定集能否挡住？
E82 任务集自生成：eval 任务由系统自己生成时，外部性消失
E83 语义伪特征：伪特征与真信号相关（而非独立位），更接近真实
"""
import random, math, statistics, sys
from dataclasses import dataclass, asdict
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import (Cfg, build_world, build_tasks, retrieve, feats, U, W0,
                     mutate, rand_cfg, boot_lower, pareto_front, K, TOPICS)


# ═══════════ 世界：条目同时有真值与表象 ═══════════
def build_world_v2(seed, n_entries=60, n_kws=6, reliability=0.32):
    """条目增加表象特征（系统可优化，对真值零贡献）：
       length / formatting / keyword_density / has_citation"""
    rnd = random.Random(seed)
    entries = []
    for i in range(n_entries):
        k, t = i % n_kws, TOPICS[i % 16]
        tok = t if rnd.random() < reliability else rnd.choice(TOPICS)
        tq = rnd.random()                                  # 真值：系统不可见
        entries.append({
            "id": f"e{i}", "kw": f"K{k}", "topic": t,
            "keywords": [f"K{k}"], "content": f"{tok} K{k} 片段{i}",
            "importance": rnd.randint(1, 3),
            "age_days": rnd.randint(0, 400),
            "true_quality": tq,
            # 表象：与真值【无关】，但 judge 能看到
            "length": rnd.random(),
            "formatting": rnd.random(),
            "kw_density": rnd.random(),
            "has_citation": 1.0 if rnd.random() < 0.5 else 0.0,
        })
    return entries


def present(e, w):
    """表象分：judge 实际'看到'的东西（系统可通过 w 调节展示）"""
    return (w[0] * e["length"] + w[1] * e["formatting"] +
            w[2] * e["kw_density"] + w[3] * e["has_citation"])


@dataclass(frozen=True)
class Cfg2:
    w_kw: float = 3.0
    w_content: float = 1.0
    w_imp: float = 1.0
    w_age: float = 0.1
    w_len: float = 0.0        # 展示权重：长度偏好
    w_fmt: float = 0.0        # 展示权重：格式偏好
    w_den: float = 0.0        # 展示权重：关键词密度偏好
    w_cit: float = 0.0        # 展示权重：引用偏好
    filter_zero: int = 0
    deep: int = 0

SC2 = ["w_kw", "w_content", "w_imp", "w_age", "w_len", "w_fmt", "w_den", "w_cit"]


def retrieve2(entries, task, cfg):
    qw = task["q"].split()
    out = []
    for e in entries:
        kw_hit = sum(1 for w in qw if w in " ".join(e["keywords"]))
        c_hit = sum(1 for w in qw if w in e["content"])
        if cfg.filter_zero and kw_hit == 0 and c_hit == 0: continue
        s = (cfg.w_kw * kw_hit + cfg.w_content * c_hit + cfg.w_imp * e["importance"]
             - cfg.w_age * (e["age_days"] / 100.0)
             + present(e, [cfg.w_len, cfg.w_fmt, cfg.w_den, cfg.w_cit]))
        out.append((s, e))
    out.sort(key=lambda x: -x[0])
    return [e for _, e in out[:K]]


def judge_score(entries, task, cfg, alpha):
    """alpha = judge 看真值的比例；1-alpha = 看表象的比例
    alpha=1 → 完美 judge；alpha<1 → judge 被表象影响（真实情况）"""
    top = retrieve2(entries, task, cfg)
    if not top: return 0.0
    # judge 对 top-K 的整体评分
    real = statistics.mean(e["true_quality"] for e in top)
    surf = statistics.mean(present(e, [cfg.w_len, cfg.w_fmt, cfg.w_den, cfg.w_cit])
                           for e in top)
    return alpha * real + (1 - alpha) * surf


def truth_score(entries, task, cfg):
    top = retrieve2(entries, task, cfg)
    return statistics.mean(e["true_quality"] for e in top) if top else 0.0


def mutate2(cfg, rnd):
    d = asdict(cfg)
    r = rnd.random()
    if r < 0.08: d["deep"] = 1 - d["deep"]
    elif r < 0.16: d["filter_zero"] = 1 - d["filter_zero"]
    else:
        p = rnd.choice(SC2)
        d[p] = round(max(-5.0, min(20.0, d[p] * rnd.choice([0.5, 0.7, 0.85, 1.2, 1.5, 2.0])
                                 + rnd.choice([0, 0, 0.5, -0.5]))), 4)
    return Cfg2(**d)


def pareto2(arch, E, tr, alpha):
    pts = [(judge_score(E, t, c, alpha), c) for c in arch for t in []]
    # 简化：以任务集均值作为目标
    vals = []
    for c in arch:
        v = statistics.mean(judge_score(E, t, c, alpha) for t in tr)
        vals.append((v, c))
    return [c for _, c in vals]


# ═══════════ E81 judge 只看表象 ═══════════
def e81(seed, alpha, use_anchor=True, gens=35, kids=4):
    """系统演化检索参数（含展示权重）。judge 打分中被表象影响的比例 = 1-alpha。
    测：终局【真值】 vs judge【自报】。锚定集能否挡住？"""
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base_truth = statistics.mean(truth_score(E, t, root) for t in fresh)
    base_judge = statistics.mean(judge_score(E, t, root, alpha) for t in fresh)
    # 锚定集：启用前由【同一个 judge】给出（关键：judge 本身也被表象影响）
    anchors = []
    for _ in range(30):
        def rnd_cfg2():
            return Cfg2(w_kw=round(rnd.uniform(0, 8), 2),
                        w_content=round(rnd.uniform(0, 4), 2),
                        w_imp=round(rnd.uniform(-1, 3), 2),
                        w_age=round(rnd.uniform(0, 0.5), 3),
                        w_len=round(rnd.uniform(-1, 1), 2),
                        w_fmt=round(rnd.uniform(-1, 1), 2),
                        w_den=round(rnd.uniform(-1, 1), 2),
                        w_cit=round(rnd.uniform(-1, 1), 2),
                        filter_zero=rnd.randint(0, 1), deep=rnd.randint(0, 1))
        a2, b2 = rnd_cfg2(), rnd_cfg2()
        ja = statistics.mean(judge_score(E, t, a2, alpha) for t in tr)
        jb = statistics.mean(judge_score(E, t, b2, alpha) for t in tr)
        if abs(ja - jb) < 1e-9: continue
        anchors.append((a2, b2, 1.0 if ja > jb else -1.0))
    arch = [root]; main = root
    fired = 0
    for g in range(gens):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate2(cand, rnd)
            d_tr = (statistics.mean(judge_score(E, t, ch, alpha) for t in tr)
                    - statistics.mean(judge_score(E, t, cand, alpha) for t in tr))
            d_he = (statistics.mean(judge_score(E, t, ch, alpha) for t in he)
                    - statistics.mean(judge_score(E, t, cand, alpha) for t in he))
            if d_tr > -0.04: arch.append(ch)
            arch = arch[-12:]
            if d_tr > 0.01 and d_he > 0.01 and \
               statistics.mean(judge_score(E, t, ch, alpha) for t in tr) > \
               statistics.mean(judge_score(E, t, main, alpha) for t in tr):
                main = ch
        if use_anchor and g % 3 == 0 and anchors:
            acc = sum(1 for a, b, y in anchors
                      if (statistics.mean(judge_score(E, t, a, alpha) for t in tr) -
                          statistics.mean(judge_score(E, t, b, alpha) for t in tr)) * y > 0) / len(anchors)
            if acc < 0.85: fired += 1
    end_truth = statistics.mean(truth_score(E, t, main) for t in fresh)
    end_judge = statistics.mean(judge_score(E, t, main, alpha) for t in fresh)
    surf = [main.w_len, main.w_fmt, main.w_den, main.w_cit]
    return (end_truth - base_truth, end_judge - base_judge,
            statistics.mean(abs(x) for x in surf), fired)


# ═══════════ E82 任务集自生成 ═══════════
def e82(seed, selfgen, gens=35, kids=4):
    """selfgen: 系统能影响 eval 任务分布（选择生成哪些 query）
    真实场景：agent 自己写 eval case → 会挑自己擅长的"""
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    all_kws = [f"K{i}" for i in range(6)]
    root = Cfg2(); arch = [root]; main = root
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base_truth = statistics.mean(truth_score(E, t, root) for t in fresh)
    # 系统对各类 query 的"偏好权重"（自生成时会偏向高分的类型）
    pref = {k: 1.0 for k in all_kws}
    for g in range(gens):
        def mk_tr():
            if not selfgen:
                return build_tasks(E, rnd, 16)
            # 自生成：按当前偏好抽取（偏好 = 当前配置在该类上的表现）
            ws = []
            for k in all_kws:
                sub = [t for t in build_tasks(E, random.Random(hash(k) % 9999), 8)
                       if t["kw"] == k]
                s = statistics.mean(truth_score(E, t, main) for t in sub) if sub else 0.0
                ws.append((s, k))
            ws.sort(key=lambda x: -x[0])
            pick = [k for _, k in ws[:3]]                 # 只生成自己擅长的 3 类
            out = []
            for k in pick:
                sub = [t for t in build_tasks(E, rnd, 6) if t["kw"] == k]
                out += sub[:6]
            return out
        tr = mk_tr()
        he = mk_tr()
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate2(cand, rnd)
            d_tr = (statistics.mean(judge_score(E, t, ch, 1.0) for t in tr)
                    - statistics.mean(judge_score(E, t, cand, 1.0) for t in tr))
            d_he = (statistics.mean(judge_score(E, t, ch, 1.0) for t in he)
                    - statistics.mean(judge_score(E, t, cand, 1.0) for t in he))
            if d_tr > -0.04: arch.append(ch)
            arch = arch[-12:]
            if d_tr > 0.01 and d_he > 0.01 and \
               statistics.mean(judge_score(E, t, ch, 1.0) for t in tr) > \
               statistics.mean(judge_score(E, t, main, 1.0) for t in tr):
                main = ch
    end_truth = statistics.mean(truth_score(E, t, main) for t in fresh)
    return end_truth - base_truth


# ═══════════ E83 语义伪特征 ═══════════
def build_world_v3(seed, n_entries=60, n_kws=6, corr=0.6):
    """伪特征与真信号【相关】（corr>0），而非独立的 spur 位。更接近真实"""
    rnd = random.Random(seed)
    entries = []
    for i in range(n_entries):
        k, t = i % n_kws, TOPICS[i % 16]
        tok = t if rnd.random() < 0.32 else rnd.choice(TOPICS)
        real = 1.0 if tok == t else 0.0            # 真信号
        # 伪特征：与真信号相关（corr），但在留出集上方向相反
        spur = 1 if (rnd.random() < corr * real + (1 - corr) * 0.5) else 0
        entries.append({"id": f"e{i}", "kw": f"K{k}", "topic": t,
                        "keywords": [f"K{k}"], "content": f"{tok} K{k} 片段{i}",
                        "importance": rnd.randint(1, 3),
                        "age_days": rnd.randint(0, 400),
                        "spur": spur, "true_quality": rnd.random()})
    return entries


def e83(seed, corr, use_holdout=True, gens=35, kids=4):
    rnd = random.Random(seed)
    E = build_world_v3(seed, corr=corr)
    def mk(want_spur, n, off=0):
        out = []
        for i in range(n):
            grp = [e for e in E if e["kw"] == f"K{(i + off) % 6}"]
            c = [e for e in grp if e["spur"] == want_spur] or grp
            g = rnd.choice(c)
            out.append({"q": f"{g['topic']} {g['kw']}", "kw": g["kw"], "golden": g["id"]})
        return out
    tr = mk(1, 16); he = mk(0, 16, 3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    base = U(E, fresh, Cfg())
    root = Cfg(); arch = [root]; main = root
    for g in range(gens):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate(cand, rnd)
            d_tr = U(E, tr, ch) - U(E, tr, cand)
            d_he = U(E, he, ch) - U(E, he, cand)
            if d_tr > -0.04: arch.append(ch)
            arch = pareto_front(arch, E, tr) or arch[-1:]
            if len(arch) > 8: arch = rnd.sample(arch, 8)
            ok = (d_tr > 0.02 and d_he > 0.02) if use_holdout else (d_tr > 0.02)
            if ok and U(E, tr, ch) > U(E, tr, main): main = ch
    return U(E, fresh, main) - base, main.w_spur
