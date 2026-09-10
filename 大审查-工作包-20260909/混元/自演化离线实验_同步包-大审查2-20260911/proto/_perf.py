import sys, time
sys.path.insert(0,'/data/workspace/proto')
import verify_kernel as V
from kernel import truth, Policy
t0 = time.time()
kk = V.mk(1, scale=3.0, audit=True)
kk.margin = kk.cfg.margin
print("mk %.2fs  配置 anchor=%s boost=%s kids=%d" %
      (time.time()-t0, kk.cfg.anchor, kk.cfg.boost_on_drift, kk.cfg.kids))
for g in range(1, 6):
    t = time.time()
    kk._step(g)
    print("  gen %d: %.2fs  kids_now=%d  drift_at=%s" %
          (g, time.time()-t, kk._cur_kids(g), kk._drift_detected_at), flush=True)
