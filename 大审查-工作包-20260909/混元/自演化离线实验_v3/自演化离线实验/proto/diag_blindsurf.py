"""诊断3（决定性）：盲评下 surf 占比是否还上升？

- 盲评 blind=True  → judge 只有 5% 看表象 → 选择压力应被消除
- 非盲评 blind=False(α=0.5) → 50% 看表象 → 系统应推高 surf 占比

随机配置基线：surf 占比 ≈ 60%（4个surf权重 vs 4个真值权重）
若演化后占比 ≈ 60%  → 中性漂移，无害
若演化后占比 >> 60% → 确实在自我美化
"""
import sys, random, statistics
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import build_world_v2, Cfg2, truth_score, judge_score
from evolve24 import _m, surf_mag, pareto_clean, SURF


def frac(c):
    tot = abs(c.w_kw) + abs(c.w_content) + abs(c.w_imp) + abs(c.w_age) + surf_mag(c)
    return surf_mag(c) / tot if tot > 0 else 0.0


def run(seed, blind, scale=2.0, gens=30, kids=4, alpha=0.5):
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    audit = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(truth_score(E, t, root) for t in audit)
    eff = 0.95 if blind else alpha
    arch = [root]
    main = root
    m, tol, cap = 0.02, 0.04, 8

    def jsc(c, tasks):
        return _m(judge_score(E, t, c, eff) for t in tasks)

    def mut(c):
        d = dict(w_kw=c.w_kw, w_content=c.w_content, w_imp=c.w_imp,
                 w_age=c.w_age, w_len=c.w_len, w_fmt=c.w_fmt,
                 w_den=c.w_den, w_cit=c.w_cit,
                 filter_zero=c.filter_zero, deep=c.deep)
        r = rnd.random()
        if r < 0.08:
            d["deep"] = 1 - d["deep"]
        elif r < 0.16:
            d["filter_zero"] = 1 - d["filter_zero"]
        else:
            p = rnd.choice(["w_kw", "w_content", "w_imp", "w_age"] + list(SURF))
            d[p] = round(max(-5.0, min(20.0,
                d[p] * (1 + rnd.choice([-0.4, -0.15, 0.2, 0.6]) * scale)
                + rnd.choice([0, 0, 0.5, -0.5]) * scale)), 4)
        return Cfg2(**d)

    for g in range(gens):
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
    gain = _m(truth_score(E, t, main) for t in audit) - base
    return gain, surf_mag(main), frac(main)


if __name__ == "__main__":
    print("盲评 vs 非盲评：演化终局 champion 的 surf 指标")
    print("随机基线占比 ≈ 60%（诊断2 实测）\n")
    print("%-14s %10s %12s %10s" % ("配置", "真值增益", "surf绝对值", "surf占比"))
    for lab, blind in (("盲评", True), ("非盲评α=0.5", False)):
        rs = [run(s, blind) for s in range(1, 11)]
        print("%-14s %+10.4f %12.2f %9.1f%%" % (
            lab,
            statistics.mean(r[0] for r in rs),
            statistics.mean(r[1] for r in rs),
            statistics.mean(r[2] for r in rs) * 100))
