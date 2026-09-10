import sys, random as _r2; sys.path.insert(0,'/data/workspace/proto')
import kernel as K
from vk_common import mk
from kernel import truth, Policy

def run(seed, dead, gens=16):
    kk = mk(seed, scale=2.0, activity=True)
    kk.margin = kk.cfg.margin
    if dead:
        orig = K.mutate
        K.mutate = lambda p, r, s: p
    try:
        for g in range(1, gens+1):
            kk._step(g)
    finally:
        if dead:
            K.mutate = orig
    adopts = sum(r.adopts for r in kk.reports)
    return adopts, sum(kk._activity_hist), kk.activity_alerts

for lab, dead in (("正常", False), ("mutate_dead", True)):
    a, c, al = run(1, dead)
    print("%-12s 总采纳=%2d  总变化=%2d  活跃度告警=%2d" % (lab, a, c, al))
