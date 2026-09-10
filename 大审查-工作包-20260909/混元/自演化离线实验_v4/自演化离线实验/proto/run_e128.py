"""E128 - 弱信号世界 2x2 补全：剥离 surf 后的真值

已有（diag_blindsurf）：
  弱x盲评    +0.1386  surf占比 81.5%
  弱x非盲评  +0.0460  surf占比 92.1%

关键问题：弱信号世界的高 surf 占比是否真的有害？
判据：把 champion 的 surf 权重归零后重测真值。
  剥离后约等于不剥离 -> 无害的中性漂移
  剥离后显著更高     -> 有害，P0 成立
"""
import sys, random, statistics
sys.path.insert(0, "/data/workspace/proto")
from evolve9 import build_tasks
from evolve20 import build_world_v2, Cfg2, truth_score, judge_score
from evolve24 import _m, surf_mag, pareto_clean, SURF


def frac(c):
    tot = abs(c.w_kw) + abs(c.w_content) + abs(c.w_imp) + abs(c.w_age) + surf_mag(c)
    return surf_mag(c) / tot if tot > 0 else 0.0


def strip(c):
    return Cfg2(w_kw=c.w_kw, w_content=c.w_content, w_imp=c.w_imp, w_age=c.w_age,
                w_len=0.0, w_fmt=0.0, w_den=0.0, w_cit=0.0,
                filter_zero=c.filter_zero, deep=c.deep)


def run(seed, blind, scale=2.0, gens=30, kids=4, alpha=0.5):
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    audit = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(truth_score(E, t, root) for t in audit)
    eff = 0.95 if blind else alpha
    arch, main = [root], root
    m, tol, cap = 0.02, 0.04, 8

    def jsc(c, tasks):
        return _m(judge_score(E, t, c, eff) for t in tasks)

    def mut(c):
        d = dict(w_kw=c.w_kw, w_content=c.w_content, w_imp=c.w_imp, w_age=c.w_age,
                 w_len=c.w_len, w_fmt=c.w_fmt, w_den=c.w_den, w_cit=c.w_cit,
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
    gain_strip = _m(truth_score(E, t, strip(main)) for t in audit) - base
    return gain, gain_strip, surf_mag(main), frac(main)


if __name__ == "__main__":
    print("弱信号世界（原世界）· 2x2 补全：剥离 surf 后重测（10种子，30代）")
    print("%-12s %10s %11s %9s %10s" % ("配置", "真值增益", "剥离后增益", "surf占比", "剥离损失"))
    for lab, blind in (("盲评", True), ("非盲评a=0.5", False)):
        rs = [run(s, blind) for s in range(1, 11)]
        g = statistics.mean(r[0] for r in rs)
        gs = statistics.mean(r[1] for r in rs)
        print("%-12s %+10.4f %+11.4f %8.1f%% %+10.4f" % (
            lab, g, gs, statistics.mean(r[3] for r in rs) * 100, gs - g))
