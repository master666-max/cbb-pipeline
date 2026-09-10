
import sys, statistics, math
sys.path.insert(0, "/data/workspace/proto")
import evolve31
from evolve31 import run, BASE
evolve31.build_world_strong.__defaults__ = (60, 6, 0.85)
n = 20
d = [run(s, dict(BASE, blind=False), gens=25) for s in range(1, n+1)]
b = [run(s, dict(BASE, blind=True),  gens=25) for s in range(1, n+1)]
diff = [bi - di for bi, di in zip(b, d)]
m = statistics.mean(diff); sd = statistics.pstdev(diff); se = sd / math.sqrt(n)
print("corr=0.85, %d 种子配对" % n)
print("  无对策 %+.4f   盲评 %+.4f" % (statistics.mean(d), statistics.mean(b)))
print("  差值均值 %+.4f  sd %.4f  标准误 %.4f  t=%.2f" % (m, sd, se, m/se))
