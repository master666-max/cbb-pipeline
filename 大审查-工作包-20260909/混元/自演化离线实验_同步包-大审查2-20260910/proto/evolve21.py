"""自演化推演 v21 —— 第十八轮：自我美化的对抗与边界

A 轮（E81）发现：judge 只看表象时，系统学会自我美化，而锚定审计【零触发】。
E81c 证明周期性真值抽样有效（每2代 +0.090）。
本轮攻这个解法的边界：

E84 探针集污染：真值探针集若被系统影响（来自近期使用分布），审计还有效吗？
E85 直接通道操纵：若系统能直接给 judge 加分（prompt注入级），真值审计能否拦住？
E86 表象维度爆炸：表象维度 4 → 64，自我美化会放大到什么程度？
E87 对策对比：真值审计 / 展示权重上界 / 盲评 / 组合，哪个最划算？
"""
import random, math, statistics, sys
from dataclasses import dataclass, asdict, field
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks, U, Cfg, K, TOPICS
from evolve20 import (build_world_v2, Cfg2, retrieve2, truth_score,
                      judge_score, mutate2, SC2)


# ═══════════ 通用：带表象世界的演化 ═══════════
def _mk_cfg2(rnd, surf_scale=1.0):
    return Cfg2(w_kw=round(rnd.uniform(0, 8), 2),
                w_content=round(rnd.uniform(0, 4), 2),
                w_imp=round(rnd.uniform(-1, 3), 2),
                w_age=round(rnd.uniform(0, 0.5), 3),
                w_len=round(rnd.uniform(-1, 1) * surf_scale, 2),
                w_fmt=round(rnd.uniform(-1, 1) * surf_scale, 2),
                w_den=round(rnd.uniform(-1, 1) * surf_scale, 2),
                w_cit=round(rnd.uniform(-1, 1) * surf_scale, 2),
                filter_zero=rnd.randint(0, 1), deep=rnd.randint(0, 1))


def surf_w(cfg):
    return [cfg.w_len, cfg.w_fmt, cfg.w_den, cfg.w_cit]


def _mean(xs): return statistics.mean(xs) if xs else 0.0


# ═══════════ E84 探针集污染 ═══════════
def e84(seed, alpha=0.5, contaminated=False, audit_every=2,
        gens=35, kids=4, probe_n=8):
    """真值探针集来源：
       clean        —— 外部固定（随机种子 4242）
       contaminated —— 来自近期使用分布，而系统能影响使用分布（挑擅长类型）"""
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _mean(truth_score(E, t, root) for t in fresh)
    arch = [root]; main = root
    best = main
    best_truth = None
    reverts = 0

    def probe_set():
        if not contaminated:
            return build_tasks(E, random.Random(4242), probe_n, offset=7)
        # 污染：探针抽自"近期使用"，而近期使用由系统偏好决定
        # （系统倾向展示自己擅长的 query 类型）
        ws = []
        for k in [f"K{i}" for i in range(6)]:
            sub = [t for t in build_tasks(E, rnd, 8) if t["kw"] == k]
            s = _mean(truth_score(E, t, main) for t in sub) if sub else 0.0
            ws.append((s, k))
        ws.sort(key=lambda x: -x[0])
        pick = [k for _, k in ws[:3]]
        out = []
        for k in pick:
            sub = [t for t in build_tasks(E, rnd, 6) if t["kw"] == k]
            out += sub[:max(1, probe_n // 3)]
        return out[:probe_n]

    for g in range(1, gens + 1):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate2(cand, rnd)
            d_tr = (_mean(judge_score(E, t, ch, alpha) for t in tr)
                    - _mean(judge_score(E, t, cand, alpha) for t in tr))
            d_he = (_mean(judge_score(E, t, ch, alpha) for t in he)
                    - _mean(judge_score(E, t, cand, alpha) for t in he))
            if d_tr > -0.04: arch.append(ch)
            arch = arch[-12:]
            if d_tr > 0.01 and d_he > 0.01 and \
               _mean(judge_score(E, t, ch, alpha) for t in tr) > \
               _mean(judge_score(E, t, main, alpha) for t in tr):
                main = ch
        if audit_every and g % audit_every == 0:
            pr = probe_set()
            cur = _mean(truth_score(E, t, main) for t in pr)
            if best_truth is None:
                best_truth = cur; best = main
            elif cur < best_truth - 0.01:
                main = best; arch = [main]; reverts += 1
            else:
                best = main; best_truth = cur
    return _mean(truth_score(E, t, main) for t in fresh) - base, reverts


# ═══════════ E85 直接通道操纵（prompt 注入级）═══════════
@dataclass(frozen=True)
class Cfg4:
    w_kw: float = 3.0
    w_content: float = 1.0
    w_imp: float = 1.0
    w_age: float = 0.1
    w_len: float = 0.0
    w_fmt: float = 0.0
    w_den: float = 0.0
    w_cit: float = 0.0
    persuade: float = 0.0      # 直接给 judge 加分，对真值零贡献
    filter_zero: int = 0
    deep: int = 0


def judge4(E, task, cfg, alpha):
    """judge 分数 = alpha*真值 + (1-alpha)*表象 + persuade（直接通道加分）"""
    base = judge_score(E, task, Cfg2(**{k: v for k, v in asdict(cfg).items()
                                        if k != "persuade"}), alpha)
    return base + cfg.persuade


def mutate4(cfg, rnd, allow_persuade=True):
    d = asdict(cfg)
    r = rnd.random()
    if allow_persuade and r < 0.15:
        d["persuade"] = round(min(20.0, d["persuade"] + rnd.choice([0.2, 0.5, 1.0])), 3)
    elif r < 0.23:
        d["deep"] = 1 - d["deep"]
    elif r < 0.31:
        d["filter_zero"] = 1 - d["filter_zero"]
    else:
        p = rnd.choice(SC2)
        d[p] = round(max(-5.0, min(20.0, d[p] * rnd.choice([0.5, 0.7, 0.85, 1.2, 1.5, 2.0])
                                 + rnd.choice([0, 0, 0.5, -0.5]))), 4)
    return Cfg4(**d)


def e85(seed, alpha=0.5, audit_every=0, gens=35, kids=4, probe_n=8):
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    probe = build_tasks(E, random.Random(4242), probe_n, offset=7)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg4()
    base = _mean(truth_score(E, t, root) for t in fresh)
    arch = [root]; main = root; best = main; best_truth = None; reverts = 0
    for g in range(1, gens + 1):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate4(cand, rnd)
            d_tr = (_mean(judge4(E, t, ch, alpha) for t in tr)
                    - _mean(judge4(E, t, cand, alpha) for t in tr))
            d_he = (_mean(judge4(E, t, ch, alpha) for t in he)
                    - _mean(judge4(E, t, cand, alpha) for t in he))
            if d_tr > -0.04: arch.append(ch)
            arch = arch[-12:]
            if d_tr > 0.01 and d_he > 0.01 and \
               _mean(judge4(E, t, ch, alpha) for t in tr) > \
               _mean(judge4(E, t, main, alpha) for t in tr):
                main = ch
        if audit_every and g % audit_every == 0:
            cur = _mean(truth_score(E, t, main) for t in probe)
            if best_truth is None:
                best_truth = cur; best = main
            elif cur < best_truth - 0.01:
                main = best; arch = [main]; reverts += 1
            else:
                best = main; best_truth = cur
    return (_mean(truth_score(E, t, main) for t in fresh) - base,
            main.persuade, reverts)


# ═══════════ E86 表象维度爆炸 ═══════════
def build_world_v5(seed, n_surf=4, n_entries=60, n_kws=6, reliability=0.32):
    rnd = random.Random(seed)
    entries = []
    for i in range(n_entries):
        k, t = i % n_kws, TOPICS[i % 16]
        tok = t if rnd.random() < reliability else rnd.choice(TOPICS)
        e = {"id": f"e{i}", "kw": f"K{k}", "topic": t,
             "keywords": [f"K{k}"], "content": f"{tok} K{k} 片段{i}",
             "importance": rnd.randint(1, 3), "age_days": rnd.randint(0, 400),
             "true_quality": rnd.random(),
             "surf": [rnd.random() for _ in range(n_surf)]}
        entries.append(e)
    return entries


@dataclass(frozen=True)
class Cfg5:
    w_kw: float = 3.0
    w_content: float = 1.0
    w_imp: float = 1.0
    w_age: float = 0.1
    surf: tuple = ()
    filter_zero: int = 0
    deep: int = 0


def retrieve5(E, task, cfg, n_surf):
    qw = task["q"].split()
    out = []
    for e in E:
        kw_hit = sum(1 for w in qw if w in " ".join(e["keywords"]))
        c_hit = sum(1 for w in qw if w in e["content"])
        if cfg.filter_zero and kw_hit == 0 and c_hit == 0: continue
        s = (cfg.w_kw * kw_hit + cfg.w_content * c_hit
             + cfg.w_imp * e["importance"] - cfg.w_age * (e["age_days"] / 100.0))
        if cfg.surf:
            s += sum(w * f for w, f in zip(cfg.surf, e["surf"]))
        out.append((s, e))
    out.sort(key=lambda x: -x[0])
    return [e for _, e in out[:K]]


def e86(seed, n_surf, alpha=0.5, audit_every=0, gens=35, kids=4, probe_n=8):
    rnd = random.Random(seed)
    E = build_world_v5(seed, n_surf=n_surf)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    probe = build_tasks(E, random.Random(4242), probe_n, offset=7)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)

    def sc(cfg, task):
        top = retrieve5(E, task, cfg, n_surf)
        if not top: return 0.0
        real = _mean(e["true_quality"] for e in top)
        surf = _mean(sum(w * f for w, f in zip(cfg.surf, e["surf"]))
                     for e in top) if cfg.surf else 0.0
        return alpha * real + (1 - alpha) * surf

    def tc(cfg, task):
        top = retrieve5(E, task, cfg, n_surf)
        return _mean(e["true_quality"] for e in top) if top else 0.0

    root = Cfg5(surf=tuple([0.0] * n_surf))
    base = _mean(tc(root, t) for t in fresh)
    arch = [root]; main = root; best = main; best_truth = None; reverts = 0
    for g in range(1, gens + 1):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:])
            d = asdict(cand); r = rnd.random()
            if r < 0.08: d["deep"] = 1 - d["deep"]
            elif r < 0.16: d["filter_zero"] = 1 - d["filter_zero"]
            else:
                sl = list(d["surf"])
                if not sl: sl = [0.0] * n_surf
                i = rnd.randrange(n_surf)
                sl[i] = round(max(-5.0, min(20.0, sl[i] + rnd.choice([-0.3, 0.3, 1.0]))), 3)
                d["surf"] = tuple(sl)
            ch = Cfg5(**d)
            d_tr = _mean(sc(ch, t) for t in tr) - _mean(sc(cand, t) for t in tr)
            d_he = _mean(sc(ch, t) for t in he) - _mean(sc(cand, t) for t in he)
            if d_tr > -0.04: arch.append(ch)
            arch = arch[-12:]
            if d_tr > 0.01 and d_he > 0.01 and \
               _mean(sc(ch, t) for t in tr) > _mean(sc(main, t) for t in tr):
                main = ch
        if audit_every and g % audit_every == 0:
            cur = _mean(tc(main, t) for t in probe)
            if best_truth is None:
                best_truth = cur; best = main
            elif cur < best_truth - 0.01:
                main = best; arch = [main]; reverts += 1
            else:
                best = main; best_truth = cur
    sw = _mean(abs(x) for x in main.surf) if main.surf else 0.0
    return _mean(tc(main, t) for t in fresh) - base, sw, reverts


# ═══════════ E87 对策对比 ═══════════
def e87(seed, mode, alpha=0.5, gens=35, kids=4, probe_n=8,
        cap=0.5, audit_every=2):
    """mode: none / audit / cap / blind / audit+cap"""
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    probe = build_tasks(E, random.Random(4242), probe_n, offset=7)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _mean(truth_score(E, t, root) for t in fresh)
    # blind：judge 被剥离表象影响（effective alpha 提升）
    eff = 0.95 if mode == "blind" else alpha
    arch = [root]; main = root; best = main; best_truth = None; reverts = 0
    for g in range(1, gens + 1):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate2(cand, rnd)
            if "cap" in mode:
                d = asdict(ch)
                for k in ("w_len", "w_fmt", "w_den", "w_cit"):
                    d[k] = round(max(-cap, min(cap, d[k])), 3)
                ch = Cfg2(**d)
            d_tr = (_mean(judge_score(E, t, ch, eff) for t in tr)
                    - _mean(judge_score(E, t, cand, eff) for t in tr))
            d_he = (_mean(judge_score(E, t, ch, eff) for t in he)
                    - _mean(judge_score(E, t, cand, eff) for t in he))
            if d_tr > -0.04: arch.append(ch)
            arch = arch[-12:]
            if d_tr > 0.01 and d_he > 0.01 and \
               _mean(judge_score(E, t, ch, eff) for t in tr) > \
               _mean(judge_score(E, t, main, eff) for t in tr):
                main = ch
        if "audit" in mode and g % audit_every == 0:
            cur = _mean(truth_score(E, t, main) for t in probe)
            if best_truth is None:
                best_truth = cur; best = main
            elif cur < best_truth - 0.01:
                main = best; arch = [main]; reverts += 1
            else:
                best = main; best_truth = cur
    sw = _mean(abs(x) for x in surf_w(main))
    return _mean(truth_score(E, t, main) for t in fresh) - base, sw, reverts
