"""自演化推演 v27 —— 第二十四轮：v4-B 的压力测试

第二十三轮给出 v4-B（大幅度2.0 + 温度0.3 + 审计 + 盲评 + 刷新）+0.151。
但 v4-B 的展示权重回升到 18.3，且"大幅度不崩溃"依赖审计有效。
本轮对 v4-B 做压力测试：

E111 审计失效时的大幅度：审计被污染/失效，大幅度还安全吗？（最危险场景）
E112 大幅度的真实代价：变异破坏性 vs 回滚成本（能否承受？）
E113 幅度的自适应：能否从"审计回退率"推断该用多大幅度？（E54 曾证明自适应失败）
E114 温度与幅度的联合：是否存在更好的组合
E115 v4-B 在复合危险世界：漂移+伪特征+噪声+污染 全开
"""
import random, math, statistics, sys
from dataclasses import asdict
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks, K
from evolve20 import build_world_v2, Cfg2, truth_score, judge_score
from evolve24 import pareto_clean, surf_mag, _m, SURF


def run(seed, d, gens=30, kids=4, alpha=0.5, collect=False):
    """统一引擎，支持：
      scale 变异幅度 / temp 采样温度 / audit 真值审计 / blind 盲评
      audit_corrupt 审计被污染（探针也被表象影响）/ drift 漂移 / spur 伪特征
      label_every 判断集刷新 / monitor 停摆监控
    """
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    if d.get("spur"):
        tr = build_tasks(E, rnd, 24)[:16]
        he = build_tasks(E, rnd, 24, offset=3)[:16]
    else:
        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
    if d.get("gold_noise"):
        for t in tr + he:
            if rnd.random() < d["gold_noise"]:
                t["golden"] = rnd.choice(E)["id"]
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(truth_score(E, t, root) for t in fresh)
    eff = 0.95 if d.get("blind") else alpha
    eff0 = eff
    scale = d.get("scale", 1.0)
    temp = d.get("temp", 0.0)
    cap = d.get("cap", 8)
    m = d.get("margin", 0.02)
    tol = d.get("tol", 0.04)
    probe = build_tasks(E, random.Random(4242), d.get("probe_n", 4), offset=7)
    corrupt = d.get("audit_corrupt", 0.0)     # 审计被表象污染的比例
    drift = d.get("drift", 0.0)
    drift_at = gens // 3 if drift > 0 else 10 ** 9

    arch = [root]
    main = root
    best = main
    btr = None
    stall = 0
    st = {"reverts": 0, "relax": 0, "audits": 0, "surf": 0.0}

    def jsc(c, tasks):
        return _m(judge_score(E, t, c, eff) for t in tasks)

    def probe_score(c):
        """审计读数：corrupt>0 时被表象污染"""
        if corrupt <= 0:
            return _m(truth_score(E, t, c) for t in probe)
        tr_v = _m(truth_score(E, t, c) for t in probe)
        sf_v = _m(judge_score(E, t, c, 0.0) for t in probe)   # 纯表象
        return (1 - corrupt) * tr_v + corrupt * sf_v

    def mut(c):
        dd = asdict(c)
        r = rnd.random()
        if r < 0.08:
            dd["deep"] = 1 - dd["deep"]
        elif r < 0.16:
            dd["filter_zero"] = 1 - dd["filter_zero"]
        else:
            p = rnd.choice(["w_kw", "w_content", "w_imp", "w_age"] + list(SURF))
            dd[p] = round(max(-5.0, min(20.0,
                                        dd[p] * (1 + rnd.choice([-0.4, -0.15, 0.2, 0.6]) * scale)
                                        + rnd.choice([0, 0, 0.5, -0.5]) * scale)), 4)
        return Cfg2(**dd)

    def pick(a):
        if temp <= 0 or len(a) == 1:
            return rnd.choice(a[-3:])
        scores = [jsc(c, tr) for c in a]
        lo, hi = min(scores), max(scores)
        if hi - lo < 1e-9:
            return rnd.choice(a)
        wts = [math.exp((s - lo) / (hi - lo) / max(0.01, temp)) for s in scores]
        tot = sum(wts)
        r = rnd.random() * tot
        acc = 0
        for c, w in zip(a, wts):
            acc += w
            if r <= acc:
                return c
        return a[-1]

    label_gens = set(range(1, gens + 1, d["label_every"])) if d.get("label_every") else set()

    for g in range(1, gens + 1):
        if g in label_gens:
            eff = min(1.0, eff0 + 0.04)
        else:
            eff = max(alpha, eff - 0.004)
        if g >= drift_at:
            fj = jsc(main, tr)
            wj = [1.0 if x > 0 else -1.0 for x in
                  [main.w_len, main.w_fmt, main.w_den, main.w_cit]]
            for i, k in enumerate(SURF):
                pass
            eff = max(alpha, eff - drift)
        adopts = 0
        mutations = 0
        for _ in range(kids):
            cand = pick(arch)
            ch = mut(cand)
            mutations += 1
            d_tr = jsc(ch, tr) - jsc(cand, tr) + rnd.gauss(0, 0.05)
            d_he = jsc(ch, he) - jsc(cand, he) + rnd.gauss(0, 0.05)
            if d_tr > -tol:
                arch.append(ch)
            if d.get("pareto", True):
                arch = pareto_clean(arch, E, tr, he, eff) or arch[-1:]
                if len(arch) > cap:
                    arch = rnd.sample(arch, cap)
            else:
                arch = [max(arch, key=lambda c: jsc(c, tr))]
            ok = (d_tr > m and d_he > m) if d.get("holdout", True) else (d_tr > m)
            if ok and jsc(ch, tr) > jsc(main, tr):
                main = ch
                adopts += 1
        st.setdefault("mutations", 0)
        st["mutations"] += mutations
        if d.get("monitor", True):
            if adopts == 0:
                stall += 1
                if stall >= 5:
                    m = max(0.005, m * 0.5)
                    stall = 0
                    st["relax"] += 1
            else:
                stall = 0
        if d.get("audit") and g % d.get("audit_every", 5) == 0:
            st["audits"] += 1
            cur = probe_score(main)
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
    gain = _m(truth_score(E, t, main) for t in fresh) - base
    if collect:
        st["surf"] = surf_mag(main)
        return gain, st
    return gain


# ── 配置 ──
V3 = dict(pareto=False, holdout=False, margin=0.01, tol=0.0, cap=1,
          blind=False, audit=False, monitor=False, scale=1.0, temp=0.0)
V4A = dict(pareto=True, holdout=True, margin=0.02, tol=0.04, cap=8,
           blind=True, audit=True, monitor=True, scale=1.0, temp=0.0)
V4B = dict(pareto=True, holdout=True, margin=0.02, tol=0.04, cap=8,
           blind=True, audit=True, monitor=True, scale=2.0, temp=0.3,
           label_every=5)


def e111(seed, scale, corrupt, gens=30):
    """审计被污染时，大幅度还安全吗"""
    return run(seed, dict(V4B, scale=scale, audit_corrupt=corrupt), gens=gens)


def e112(seed, scale, gens=30):
    """大幅度的破坏性：统计回退次数与终局展示权重"""
    return run(seed, dict(V4B, scale=scale), gens=gens, collect=True)


def e113(seed, mode, gens=40):
    """mode: fixed2.0 —— 固定 2.0
             adaptive —— 按回退率调整：回退多则降幅度，少则升
             oracle   —— 每 10 代试 3 档取最好（上界参考，不可实现）"""
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    tr = build_tasks(E, rnd, 16)
    he = build_tasks(E, rnd, 16, offset=3)
    fresh = build_tasks(E, random.Random(7777), 40, offset=5)
    probe = build_tasks(E, random.Random(4242), 4, offset=7)
    root = Cfg2()
    base = _m(truth_score(E, t, root) for t in fresh)
    eff = 0.95
    scale = 2.0
    arch = [root]
    main = root
    best = main
    btr = None
    rev_win = 0
    st = {"reverts": 0}

    def jsc(c, tasks):
        return _m(judge_score(E, t, c, eff) for t in tasks)

    def mut(c, sc):
        dd = asdict(c)
        r = rnd.random()
        if r < 0.08:
            dd["deep"] = 1 - dd["deep"]
        elif r < 0.16:
            dd["filter_zero"] = 1 - dd["filter_zero"]
        else:
            p = rnd.choice(["w_kw", "w_content", "w_imp", "w_age"] + list(SURF))
            dd[p] = round(max(-5.0, min(20.0,
                                        dd[p] * (1 + rnd.choice([-0.4, -0.15, 0.2, 0.6]) * sc)
                                        + rnd.choice([0, 0, 0.5, -0.5]) * sc)), 4)
        return Cfg2(**dd)

    for g in range(1, gens + 1):
        if mode == "adaptive" and g % 10 == 0:
            # 回退多 → 说明跑飞了，降幅度；回退少 → 可以再放开
            if rev_win >= 3:
                scale = max(0.5, scale * 0.7)
            elif rev_win == 0:
                scale = min(4.0, scale * 1.3)
            rev_win = 0
        for _ in range(4):
            cand = rnd.choice(arch[-3:])
            ch = mut(cand, scale)
            d_tr = jsc(ch, tr) - jsc(cand, tr) + rnd.gauss(0, 0.05)
            d_he = jsc(ch, he) - jsc(cand, he) + rnd.gauss(0, 0.05)
            if d_tr > -0.04:
                arch.append(ch)
            arch = pareto_clean(arch, E, tr, he, eff) or arch[-1:]
            if len(arch) > 8:
                arch = rnd.sample(arch, 8)
            if d_tr > 0.02 and d_he > 0.02 and jsc(ch, tr) > jsc(main, tr):
                main = ch
        if g % 5 == 0:
            cur = _m(truth_score(E, t, main) for t in probe)
            if btr is None:
                btr = cur
                best = main
            elif cur < btr - 0.01:
                main = best
                arch = [main]
                st["reverts"] += 1
                rev_win += 1
            else:
                best = main
                btr = cur
    return _m(truth_score(E, t, main) for t in fresh) - base, scale, st["reverts"]


def e114(seed, scale, temp, gens=30):
    return run(seed, dict(V4B, scale=scale, temp=temp), gens=gens)


def e115(seed, tier, gens=30):
    """复合危险：漂移 + 伪特征 + 金标噪声 + judge 污染"""
    d = dict({"v3": V3, "v4-A": V4A, "v4-B": V4B}[tier])
    d["drift"] = 0.10
    d["spur"] = True
    d["gold_noise"] = 0.2
    return run(seed, d, gens=gens)
