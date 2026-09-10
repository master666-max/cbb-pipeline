import sys, time
sys.path.insert(0,'/data/workspace/proto')
import verify_kernel as V
from kernel import truth, Policy
import random as _rnd
t = time.time()
kk = V.mk(1, scale=3.0, audit=True, reanchor_after=2, diagnose_delta=0.01)
kk.margin = kk.cfg.margin
base = truth(kk.entries, kk.tasks_train + kk.tasks_held, Policy())
for g in range(1, 25):
    if g == 8:
        r = _rnd.Random(1000)
        for e in kk.entries:
            if r.random() < 0.35:
                e.quality = r.random() * 0.3
    kk._step(g)
g = truth(kk.entries, kk.tasks_train + kk.tasks_held, kk.champion) - base
print("耗时 %.1fs  增益 %.4f" % (time.time() - t, g))
