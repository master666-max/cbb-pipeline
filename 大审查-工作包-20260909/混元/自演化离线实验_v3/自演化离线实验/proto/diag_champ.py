
import sys, random, statistics
sys.path.insert(0, "/data/workspace/proto")
from evolve9 import build_tasks
from evolve20 import build_world_v2, Cfg2, truth_score, judge_score
from evolve24 import _m, surf_mag, pareto_clean, SURF

def run(seed, blind, scale=2.0, gens=30, kids=4, alpha=0.5):
    rnd = random.Random(seed)
    E = build_world_v2(seed)
    audit = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2(); base = _m(truth_score(E, t, root) for t in audit)
    eff = 0.95 if blind else alpha
    arch, main = [root], root
    m, tol, cap = 0.02, 0.04, 8
    def jsc(c, tasks): return _m(judge_score(E, t, c, eff) for t in tasks)
    def mut(c):
        d = dict(w_kw=c.w_kw, w_content=c.w_content, w_imp=c.w_imp, w_age=c.w_age,
                 w_len=c.w_len, w_fmt=c.w_fmt, w_den=c.w_den, w_cit=c.w_cit,
                 filter_zero=c.filter_zero, deep=c.deep)
        r = rnd.random()
        if r < 0.08: d["deep"] = 1 - d["deep"]
        elif r < 0.16: d["filter_zero"] = 1 - d["filter_zero"]
        else:
            p = rnd.choice(["w_kw","w_content","w_imp","w_age"] + list(SURF))
            d[p] = round(max(-5.0, min(20.0, d[p]*(1+rnd.choice([-0.4,-0.15,0.2,0.6])*scale)+rnd.choice([0,0,0.5,-0.5])*scale)),4)
        return Cfg2(**d)
    for g in range(gens):
        tr = build_tasks(E, rnd, 16); he = build_tasks(E, rnd, 16, offset=3)
        for _ in range(kids):
            cand = rnd.choice(arch[-3:]); ch = mut(cand)
            d_tr = jsc(ch,tr)-jsc(cand,tr)+rnd.gauss(0,0.05)
            d_he = jsc(ch,he)-jsc(cand,he)+rnd.gauss(0,0.05)
            if d_tr > -tol: arch.append(ch)
            arch = pareto_clean(arch, E, tr, he, eff) or arch[-1:]
            if len(arch) > cap: arch = rnd.sample(arch, cap)
            if d_tr > m and d_he > m and jsc(ch,tr) > jsc(main,tr): main = ch
    return main, E, audit, base

print("champion 权重诊断（弱信号世界，盲评）")
for s in range(1,4):
    c, E, audit, base = run(s, True)
    gain = _m(truth_score(E,t,c) for t in audit) - base
    print("  seed%d: w_kw=%.1f w_content=%.1f w_imp=%.1f | surf: len=%.1f fmt=%.1f den=%.1f cit=%.1f | surf_mag=%.1f gain=%+.4f"
          % (s, c.w_kw, c.w_content, c.w_imp, c.w_len, c.w_fmt, c.w_den, c.w_cit, surf_mag(c), gain))
