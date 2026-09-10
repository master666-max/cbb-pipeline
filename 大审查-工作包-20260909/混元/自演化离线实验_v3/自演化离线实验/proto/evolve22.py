"""自演化推演 v22 —— 第十九轮：委派边界与审计的经济学

第十八轮留下三条最值得验证的：
  ① E86 依赖单点变异算子 —— 若算子能协调多维（真实系统的 prompt 改写），结论是否反转？
  ② E85 的膨胀有多普遍 —— 什么条件下 judge 数字才可用？
  ③ 真值审计的成本曲线 —— 频率/样本量如何取最划算？

E88 协调式变异：算子能同时改多个表象维度时，维度还是稀释剂吗（E86 复核）
E89 委派边界：judge 能可靠地做哪些判断？（偏好 vs 有用性 vs 正确性）
E90 审计成本曲线：频率 × 样本量 的联合最优，以及边际收益
E91 审计时的伪装：系统能否学会"只在被审计时表现好"
"""
import random, math, statistics, sys
from dataclasses import dataclass, asdict
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks, K, TOPICS
from evolve20 import build_world_v2, Cfg2, retrieve2, truth_score, judge_score, mutate2, SC2


def _m(xs): return statistics.mean(xs) if xs else 0.0


def surf_w(cfg):
    return [cfg.w_len, cfg.w_fmt, cfg.w_den, cfg.w_cit]


# ═══════════ E88 协调式变异（E86 复核）══════════
@dataclass(frozen=True)
class Cfg6:
    w_kw: float = 3.0
    w_content: float = 1.0
    w_imp: float = 1.0
    w_age: float = 0.1
    surf: tuple = ()
    filter_zero: int = 0
    deep: int = 0


def build_world_v6(seed, n_surf=4, n_entries=60, n_kws=6, reliability=0.32):
    rnd = random.Random(seed)
    out = []
    for i in range(n_entries):
        k, t = i % n_kws, TOPICS[i % 16]
        tok = t if rnd.random() < reliability else rnd.choice(TOPICS)
        out.append({"id": f"e{i}", "kw": f"K{k}", "topic": t,
                    "keywords": [f"K{k}"], "content": f"{tok} K{k} 片段{i}",
                    "importance": rnd.randint(1, 3), "age_days": rnd.randint(0, 400),
                    "true_quality": rnd.random(),
                    "surf": [rnd.random() for _ in range(n_surf)]})
    return out


def retrieve6(E, task, cfg):
    qw = task["q"].split()
    out = []
    for e in E:
        kh = sum(1 for w in qw if w in " ".join(e["keywords"]))
        ch = sum(1 for w in qw if w in e["content"])
        if cfg.filter_zero and kh == 0 and ch == 0: continue
        s = (cfg.w_kw * kh + cfg.w_content * ch + cfg.w_imp * e["importance"]
             - cfg.w_age * (e["age_days"] / 100.0))
        if cfg.surf:
            s += sum(w * f for w, f in zip(cfg.surf, e["surf"]))
        out.append((s, e))
    out.sort(key=lambda x: -x[0])
    return [e for _, e in out[:K]]


def e88(seed, n_surf, coordinated, alpha=0.5, gens=35, kids=4, probe_n=8,
        audit_every=2):
    """coordinated=False → 每次只改一个表象维度（第十八轮的设置）
       coordinated=True  → 一次同时推动所有表象维度（模拟 prompt 改写）"""
    rnd = random.Random(seed)
    E = build_world_v6(seed, n_surf=n_surf)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    probe = build_tasks(E, random.Random(4242), probe_n, offset=7)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)

    def sc(cfg, task):
        top = retrieve6(E, task, cfg)
        if not top: return 0.0
        real = _m(e["true_quality"] for e in top)
        surf = _m(sum(w * f for w, f in zip(cfg.surf, e["surf"]))
                  for e in top) if cfg.surf else 0.0
        return alpha * real + (1 - alpha) * surf

    def tc(cfg, task):
        top = retrieve6(E, task, cfg)
        return _m(e["true_quality"] for e in top) if top else 0.0

    root = Cfg6(surf=tuple([0.0] * n_surf))
    base = _m(tc(root, t) for t in fresh)
    arch = [root]; main = root; best = main; btr = None; reverts = 0
    for g in range(1, gens + 1):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:])
            d = asdict(cand); r = rnd.random()
            if r < 0.08: d["deep"] = 1 - d["deep"]
            elif r < 0.16: d["filter_zero"] = 1 - d["filter_zero"]
            else:
                sl = list(d["surf"]) or [0.0] * n_surf
                if coordinated:
                    # 协调：所有表象维度同向推进（一次改写全部"话术"）
                    delta = rnd.choice([0.15, 0.4, 1.0])
                    sl = [round(max(-5.0, min(20.0, x + delta)), 3) for x in sl]
                else:
                    i = rnd.randrange(n_surf)
                    sl[i] = round(max(-5.0, min(20.0, sl[i]
                                 + rnd.choice([-0.3, 0.3, 1.0]))), 3)
                d["surf"] = tuple(sl)
            ch = Cfg6(**d)
            d_tr = _m(sc(ch, t) for t in tr) - _m(sc(cand, t) for t in tr)
            d_he = _m(sc(ch, t) for t in he) - _m(sc(cand, t) for t in he)
            if d_tr > -0.04: arch.append(ch)
            arch = arch[-12:]
            if d_tr > 0.01 and d_he > 0.01 and \
               _m(sc(ch, t) for t in tr) > _m(sc(main, t) for t in tr):
                main = ch
        if audit_every and g % audit_every == 0:
            cur = _m(tc(main, t) for t in probe)
            if btr is None: btr = cur; best = main
            elif cur < btr - 0.01: main = best; arch = [main]; reverts += 1
            else: best = main; btr = cur
    sw = _m(abs(x) for x in main.surf) if main.surf else 0.0
    return _m(tc(main, t) for t in fresh) - base, sw, reverts


# ═══════════ E89 委派边界 ═══════════
def e89(seed, task_kind, n_samples=60, noise=0.0):
    """人类真值已知。测 judge 在三类判断上与人类的一致率：
       preference  —— "A 和 B 哪个更好"（可委派？）
       usefulness  —— "这个结果对我有没有用"（可委派？）
       correctness —— "这个答案对不对"（可委派？）
    noise = judge 被表象影响的程度"""
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    tr = build_tasks(E, rnd, 16)
    agree = disagree = 0
    for _ in range(n_samples):
        a = Cfg2(w_kw=rnd.uniform(0, 8), w_content=rnd.uniform(0, 4),
                 w_imp=rnd.uniform(-1, 3), w_age=rnd.uniform(0, 0.5),
                 w_len=rnd.uniform(-1, 1), w_fmt=rnd.uniform(-1, 1),
                 w_den=rnd.uniform(-1, 1), w_cit=rnd.uniform(-1, 1))
        b = Cfg2(w_kw=rnd.uniform(0, 8), w_content=rnd.uniform(0, 4),
                 w_imp=rnd.uniform(-1, 3), w_age=rnd.uniform(0, 0.5),
                 w_len=rnd.uniform(-1, 1), w_fmt=rnd.uniform(-1, 1),
                 w_den=rnd.uniform(-1, 1), w_cit=rnd.uniform(-1, 1))
        ta = _m(truth_score(E, t, a) for t in tr)
        tb = _m(truth_score(E, t, b) for t in tr)
        if abs(ta - tb) < 1e-6: continue
        # 人类判断（真值）
        if task_kind == "preference":
            hy = 1.0 if ta > tb else -1.0
        elif task_kind == "usefulness":
            hy = 1.0 if ta > 0.5 else -1.0      # 绝对阈值：有没有用
        else:  # correctness
            hy = 1.0 if ta > 0.8 else -1.0      # 更严格：对不对
        # judge 判断（被表象影响）
        jv = _m(judge_score(E, t, a, 1.0 - noise) for t in tr)
        jw = _m(judge_score(E, t, b, 1.0 - noise) for t in tr)
        if task_kind == "preference":
            jy = 1.0 if jv > jw else -1.0
        elif task_kind == "usefulness":
            jy = 1.0 if jv > 0.5 else -1.0
        else:
            jy = 1.0 if jv > 0.8 else -1.0
        if hy == jy: agree += 1
        else: disagree += 1
    return agree / (agree + disagree) if (agree + disagree) else 0.0


# ═══════════ E90 审计成本曲线 ═══════════
def e90(seed, audit_every, probe_n, alpha=0.5, gens=35, kids=4, cost_per=1):
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    probe = build_tasks(E, random.Random(4242), probe_n, offset=7)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(truth_score(E, t, root) for t in fresh)
    arch = [root]; main = root; best = main; btr = None
    n_audits = 0
    for g in range(1, gens + 1):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mutate2(cand, rnd)
            d_tr = (_m(judge_score(E, t, ch, alpha) for t in tr)
                    - _m(judge_score(E, t, cand, alpha) for t in tr))
            d_he = (_m(judge_score(E, t, ch, alpha) for t in he)
                    - _m(judge_score(E, t, cand, alpha) for t in he))
            if d_tr > -0.04: arch.append(ch)
            arch = arch[-12:]
            if d_tr > 0.01 and d_he > 0.01 and \
               _m(judge_score(E, t, ch, alpha) for t in tr) > \
               _m(judge_score(E, t, main, alpha) for t in tr): main = ch
        if audit_every and g % audit_every == 0:
            n_audits += 1
            cur = _m(truth_score(E, t, main) for t in probe)
            if btr is None: btr = cur; best = main
            elif cur < btr - 0.01: main = best; arch = [main]
            else: best = main; btr = cur
    gain = _m(truth_score(E, t, main) for t in fresh) - base
    cost = n_audits * probe_n * cost_per
    return gain, cost, (gain / cost if cost else 0.0)


# ═══════════ E91 审计时伪装 ═══════════
@dataclass(frozen=True)
class Cfg7:
    w_kw: float = 3.0
    w_content: float = 1.0
    w_imp: float = 1.0
    w_age: float = 0.1
    w_len: float = 0.0
    w_fmt: float = 0.0
    w_den: float = 0.0
    w_cit: float = 0.0
    mask: float = 0.0          # 审计时临时降低表象权重的幅度
    filter_zero: int = 0
    deep: int = 0


def to_c2(c):
    return Cfg2(w_kw=c.w_kw, w_content=c.w_content, w_imp=c.w_imp, w_age=c.w_age,
                w_len=c.w_len, w_fmt=c.w_fmt, w_den=c.w_den, w_cit=c.w_cit,
                filter_zero=c.filter_zero, deep=c.deep)


def e91(seed, detectable=True, alpha=0.5, gens=35, kids=4, probe_n=8,
        audit_every=2):
    """系统有 mask 基因：审计时临时压低表象权重（伪装），平时放开。
       detectable=True  → 探针是随机抽查（系统无法预知）
       detectable=False → 系统能感知审计时机（探针固定且可预期）"""
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
    pool = build_tasks(E, random.Random(4242), 40, offset=7)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg7()
    base = _m(truth_score(E, t, to_c2(root)) for t in fresh)
    arch = [root]; main = root; best = main; btr = None; reverts = 0
    for g in range(1, gens + 1):
        for _ in range(kids):
            cand = rnd.choice(arch[-3:])
            d = asdict(cand); r = rnd.random()
            if r < 0.10: d["mask"] = round(min(3.0, max(0.0, d["mask"] + rnd.choice([0.3, 0.8]))), 3)
            elif r < 0.18: d["deep"] = 1 - d["deep"]
            elif r < 0.26: d["filter_zero"] = 1 - d["filter_zero"]
            else:
                p = rnd.choice(SC2)
                d[p] = round(max(-5.0, min(20.0, d[p] * rnd.choice([0.6, 0.85, 1.2, 1.6]))), 4)
            ch = Cfg7(**d)
            d_tr = (_m(judge_score(E, t, to_c2(ch), alpha) for t in tr)
                    - _m(judge_score(E, t, to_c2(cand), alpha) for t in tr))
            d_he = (_m(judge_score(E, t, to_c2(ch), alpha) for t in he)
                    - _m(judge_score(E, t, to_c2(cand), alpha) for t in he))
            if d_tr > -0.04: arch.append(ch)
            arch = arch[-12:]
            if d_tr > 0.01 and d_he > 0.01 and \
               _m(judge_score(E, t, to_c2(ch), alpha) for t in tr) > \
               _m(judge_score(E, t, to_c2(main), alpha) for t in tr): main = ch
        if audit_every and g % audit_every == 0:
            if detectable:
                pr = rnd.sample(pool, probe_n)          # 随机抽查
                cfg_eval = to_c2(main)                  # 无法预知 → 不伪装
            else:
                pr = pool[:probe_n]                     # 固定探针 → 可预期
                d = asdict(to_c2(main))
                for k in ("w_len", "w_fmt", "w_den", "w_cit"):
                    d[k] = round(d[k] - main.mask * (1 if d[k] > 0 else -1), 3)
                cfg_eval = Cfg2(**d)                    # 伪装后的配置
            cur = _m(truth_score(E, t, cfg_eval) for t in pr)
            if btr is None: btr = cur; best = main
            elif cur < btr - 0.01: main = best; arch = [main]; reverts += 1
            else: best = main; btr = cur
    sw = _m(abs(x) for x in surf_w(to_c2(main)))
    return _m(truth_score(E, t, to_c2(main)) for t in fresh) - base, main.mask, sw, reverts
