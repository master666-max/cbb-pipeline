import sys, random, statistics; sys.path.insert(0,'/data/workspace/proto')
from vk_common import mk
import kernel as K
from kernel import SURF

def run(seed, alpha, gens=20):
    k = mk(seed, scale=2.0)
    k.alpha = alpha
    k.margin = k.cfg.margin
    for g in range(1, gens+1):
        k._step(g)
    c = k.champion
    return (c.w_len + c.w_fmt + c.w_den + c.w_cit), c.surf_magnitude()

for alpha, lab in ((0.95, "judge≈真值(无破解机会)"), (0.5, "judge看表象(有破解机会)")):
    sg = [run(s, alpha)[0] for s in range(1, 13)]
    print("%-24s 有符号surf 均值 %+7.3f  sd %.3f" % (lab, statistics.mean(sg), statistics.pstdev(sg)))
