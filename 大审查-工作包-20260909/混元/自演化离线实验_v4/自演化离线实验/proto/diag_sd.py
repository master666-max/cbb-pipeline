
import sys, statistics
sys.path.insert(0, "/data/workspace/proto")
import evolve31
from evolve31 import run, BASE

print("逐 seed 分布（非盲评 vs 盲评）")
for corr in (0.3, 0.6, 0.85):
    evolve31.build_world_strong.__defaults__ = (60, 6, corr)
    d = [run(s, dict(BASE, blind=False), gens=25) for s in range(1,9)]
    b = [run(s, dict(BASE, blind=True),  gens=25) for s in range(1,9)]
    diff = [bi - di for bi, di in zip(b, d)]
    print("corr=%.2f  无对策 sd=%.4f  盲评 sd=%.4f  差值sd=%.4f  差值均值=%+.4f"
          % (corr, statistics.pstdev(d), statistics.pstdev(b),
             statistics.pstdev(diff), statistics.mean(diff)))
