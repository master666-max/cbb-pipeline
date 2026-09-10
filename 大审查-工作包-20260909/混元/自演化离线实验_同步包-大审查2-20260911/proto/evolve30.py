"""自演化推演 v30 —— P0 专项：展示权重爆炸（E112）

【问题】E112 实测：真值增益随幅度上升（0.5→+0.022，3.0→+0.200），
        但展示权重同步爆炸到 0.66 → 7.17 → 12.9 → 26.9（40 倍），
        而审计回退次数始终只有 0.7–1.5 —— 审计【几乎没拦住】。
        E87 已证明"展示权重上界"是无效对策（比不做还差）。

【假说 H1】温水煮青蛙：审计基线 best_truth 在每次未触发回退时
        都被更新为当前读数（btr = cur），导致阈值只约束【单步】下降，
        不约束【累积】下降。真值每次降 0.009，30 代后可降 0.27 而永不触发。

【假说 H2】审计通道被表象污染：审计读数用含高展示权重的配置，
        该权重扰乱排序 → 真值读数偏低，但"偏低"是渐进的，被 H1 掩盖。

【对策候选】
  C0 baseline    现状（btr 滚动更新）
  C1 strict      best 只增不减（累积下降超阈值即回退）
  C2 strip       审计读数时剥离表象权重（w_len/fmt/den/cit 置 0）
  C3 strict+strip 组合
  C4 cap         展示权重上界（E87 已证明无效，作为对照）
  C5 probe_n     增加探针样本量（降噪声）

实验：
  E125 复现 + 真值轨迹诊断（温水煮青蛙是否成立）
  E126 best 更新策略：rolling vs strict
  E127 阈值敏感性（strict 下）
  E128 审计剥离表象（strip）
  E129 综合对策对比
"""
import random, math, statistics, sys
from dataclasses import asdict, replace
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks, K
from evolve20 import build_world_v2, Cfg2, truth_score, judge_score
from evolve24 import pareto_clean, surf_mag, _m, SURF


def strip_surf(c: Cfg2) -> Cfg2:
    """剥离表象权重：只保留真值相关权重。用于审计读数。"""
    return Cfg2(w_kw=c.w_kw, w_content=c.w_content, w_imp=c.w_imp, w_age=c.w_age,
                w_len=0.0, w_fmt=0.0, w_den=0.0, w_cit=0.0,
                filter_zero=c.filter_zero, deep=c.deep)


def run(seed, d, gens=30, kids=4, alpha=0.5, collect=False):
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    for e in E:
        e.setdefault("self_written", False)
    E0 = [dict(e) for e in E]
    # 外部固定的审计集（不随演化变）
    audit_set = build_tasks(E0, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(truth_score(E0, t, root) for t in audit_set)

    eff = 0.95 if d.get("blind", True) else alpha
    scale = d.get("scale", 2.0)
    cap = d.get("cap", 8)
    m = d.get("margin", 0.02)
    tol = d.get("tol", 0.04)
    thr = d.get("audit_thr", 0.01)
    mode = d.get("audit_mode", "rolling")      # rolling / strict
    do_strip = d.get("strip", False)
    probe_n = d.get("probe_n", 4)
    surf_cap = d.get("surf_cap", None)
    probe = build_tasks(E0, random.Random(4242), probe_n, offset=7)

    arch = [root]
    main = root
    best = main
    btr = None
    st = {"reverts": 0, "audits": 0, "surf": 0.0}
    traj = []
    adopt_hist = []

    def jsc(c, tasks):
        return _m(judge_score(E, t, c, eff) for t in tasks)

    def read_truth(c):
        """审计读数。strip=True 时剥离表象后再读。"""
        cc = strip_surf(c) if do_strip else c
        return _m(truth_score(E, t, cc) for t in probe)

    def mut(c):
        dd = asdict(c)
        r = rnd.random()
        if r < 0.08: dd["deep"] = 1 - dd["deep"]
        elif r < 0.16: dd["filter_zero"] = 1 - dd["filter_zero"]
        else:
            p = rnd.choice(["w_kw", "w_content", "w_imp", "w_age"] + list(SURF))
            dd[p] = round(max(-5.0, min(20.0,
                dd[p] * (1 + rnd.choice([-0.4, -0.15, 0.2, 0.6]) * scale)
                + rnd.choice([0, 0, 0.5, -0.5]) * scale)), 4)
        nc = Cfg2(**dd)
        if surf_cap is not None and surf_mag(nc) > surf_cap:
            return c            # 超上界则放弃该变异
        return nc

    for g in range(1, gens + 1):
        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
        adopts = 0
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
                adopts += 1
        adopt_hist.append(adopts)
        if d.get("monitor", True):
            if adopts == 0:
                st.setdefault("stall", 0)
                st["stall"] += 1
                if st["stall"] >= 5:
                    m = max(0.005, m * 0.5)
                    st["stall"] = 0
            else:
                st["stall"] = 0
        if d.get("audit", True) and g % d.get("audit_every", 5) == 0:
            st["audits"] += 1
            cur = read_truth(main)
            if btr is None:
                btr = cur
                best = main
            elif cur < btr - thr:
                main = best
                arch = [main]
                st["reverts"] += 1
                # strict: 基线不因回退而降低；rolling: 接受当前
                if mode == "rolling":
                    btr = cur
                    best = main
            else:
                if mode == "strict":
                    if cur > btr:          # ★ 只增不减
                        btr = cur
                        best = main
                else:                       # rolling：接受当前（允许渐进下降）
                    btr = cur
                    best = main
        if collect:
            traj.append(_m(truth_score(E, t, main) for t in audit_set) - base)

    gain = _m(truth_score(E, t, main) for t in audit_set) - base
    if collect:
        st["surf"] = surf_mag(main)
        st["traj"] = traj
        st["adopt_hist"] = adopt_hist
        return gain, st
    return gain


BASE = dict(blind=True, audit=True, audit_every=5, scale=2.0,
            pareto=True, cap=8, tol=0.04, margin=0.02, monitor=True)


def e125(seed, scale, gens=30):
    """复现：真值轨迹 + 展示权重 + 回退次数"""
    return run(seed, dict(BASE, scale=scale), gens=gens, collect=True)


def e126(seed, mode, gens=30):
    return run(seed, dict(BASE, audit_mode=mode), gens=gens, collect=True)


def e127(seed, thr, gens=30):
    return run(seed, dict(BASE, audit_mode="strict", audit_thr=thr),
               gens=gens, collect=True)


def e128(seed, strip, gens=30):
    return run(seed, dict(BASE, audit_mode="strict", strip=strip),
               gens=gens, collect=True)


def e129(seed, cfg_name, gens=30):
    cfgs = {
        "baseline":  dict(BASE),
        "strict":    dict(BASE, audit_mode="strict"),
        "strip":     dict(BASE, strip=True),
        "strict+strip": dict(BASE, audit_mode="strict", strip=True),
        "cap5":      dict(BASE, surf_cap=5.0),
        "probe16":   dict(BASE, probe_n=16),
        "noaudit":   dict(BASE, audit=False),
    }
    return run(seed, cfgs[cfg_name], gens=gens, collect=True)
