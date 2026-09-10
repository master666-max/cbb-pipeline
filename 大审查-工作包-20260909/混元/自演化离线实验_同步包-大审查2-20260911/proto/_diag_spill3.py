import sys, random, statistics, math; sys.path.insert(0,'/data/workspace/proto')
from vk_common import mk
import kernel as K

def run(seed, alpha, blind, gens=20):
    k = mk(seed, scale=2.0, blind=blind)
    k.alpha = alpha
    k.margin = k.cfg.margin
    for g in range(1, gens+1):
        k._step(g)
    c = k.champion
    return c.w_len + c.w_fmt + c.w_den + c.w_cit

for alpha, blind, lab in ((0.95, False, "judge≈真值(无机会)"),
                          (0.5, False, "judge看表象(有机会)"),
                          (0.5, True,  "judge看表象+盲评")):
    v = [run(s, alpha, blind) for s in range(1, 13)]
    se = statistics.pstdev(v)/math.sqrt(len(v))
    print("%-22s 有符号surf %+7.3f  sd %.3f  se %.3f" % (lab, statistics.mean(v), statistics.pstdev(v), se))
