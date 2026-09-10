
"""E130 - 信号强度扫描：结论如何随 corr 变化

真实系统的信号强度未知。若结论依赖 corr，则不可外推。
扫描 corr = 0.3 / 0.6 / 0.85，看：
  (a) surf 占比
  (b) 盲评收益
  (c) 配对效应（幅度2.0下审计收益）
"""
import sys, statistics
sys.path.insert(0, "/data/workspace/proto")
import evolve31
from evolve31 import run, BASE
import random
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, surf_mag

def signal_sd(corr, seed=0):
    E = evolve31.build_world_strong(seed, corr=corr)
    audit = build_tasks(E, random.Random(7777), 40, offset=5)
    base = _m(evolve31.tscore(E, t, Cfg2()) for t in audit)
    rnd = random.Random(0); zs = []
    for _ in range(60):
        c = Cfg2(w_kw=rnd.uniform(0,6), w_content=rnd.uniform(0,3),
                 w_imp=rnd.uniform(-1,3), w_age=rnd.uniform(-1,1))
        zs.append(_m(evolve31.tscore(E, t, c) for t in audit) - base)
    return statistics.pstdev(zs)

if __name__ == "__main__":
    seeds = range(1, 9)
    print("信号强度扫描（8种子，25代，非盲评）")
    print("%-6s %8s %10s %12s %12s %12s" % ("corr", "信号sd", "surf占比", "无对策", "+盲评", "盲评收益"))
    for corr in (0.3, 0.6, 0.85):
        evolve31.build_world_strong.__defaults__ = (60, 6, corr)
        sd = signal_sd(corr)
        danger = [run(s, dict(BASE, blind=False), gens=25, collect=True) for s in seeds]
        blind  = [run(s, dict(BASE, blind=True),  gens=25, collect=True) for s in seeds]
        print("%-6.2f %8.4f %9.1f%% %+12.4f %+12.4f %+12.4f" % (
            corr, sd,
            statistics.mean(r[1]["frac"] for r in danger) * 100,
            statistics.mean(r[0] for r in danger),
            statistics.mean(r[0] for r in blind),
            statistics.mean(r[0] for r in blind) - statistics.mean(r[0] for r in danger)))
