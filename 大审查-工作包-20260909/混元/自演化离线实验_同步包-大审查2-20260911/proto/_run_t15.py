import sys, json, os
sys.path.insert(0,'/data/workspace/proto')
C = "/data/workspace/res_t15.json"
# 只借用 mk/truth/Policy：直接内联避免执行整个 verify
from kernel import Kernel, KernelConfig, Meta, Policy, truth
def mk(seed=0, **cfgkw):
    import verify_kernel as V
    return V.mk(seed, **cfgkw)

import random as _rnd

def run_drift(seed, audit, gens=24, drift=0.35, diag=0.01):
    key = f"{seed}_{audit}_{gens}_{drift}_{diag}"
    cache = json.load(open(C)) if os.path.exists(C) else {}
    if key in cache:
        return cache[key]
    kk = mk(seed, scale=3.0, audit=audit, reanchor_after=2, diagnose_delta=diag)
    kk.margin = kk.cfg.margin
    base = truth(kk.entries, kk.tasks_train + kk.tasks_held, Policy())
    for g in range(1, gens + 1):
        if g == gens // 3:
            r = _rnd.Random(seed + 999)
            for e in kk.entries:
                if r.random() < drift:
                    e.quality = r.random() * 0.3
        kk._step(g)
    val = truth(kk.entries, kk.tasks_train + kk.tasks_held, kk.champion) - base
    cache[key] = val
    json.dump(cache, open(C, "w"))
    return val

if __name__ == "__main__":
    want = sys.argv[1] if len(sys.argv) > 1 else "all"
    todo = []
    for s in range(1, 13):
        todo.append((s, True, -999.0))   # naive
        todo.append((s, True, 0.01))     # diagnose
        todo.append((s, False, 0.01))    # no audit
    cache = json.load(open(C)) if os.path.exists(C) else {}
    n = 0
    for s, au, dg in todo:
        k = f"{s}_{au}_24_0.35_{dg}"
        if k not in cache:
            run_drift(s, au, diag=dg)
            n += 1
    cache = json.load(open(C)) if os.path.exists(C) else {}
    print(f"已缓存 {len(cache)}/{len(todo)}（本次新增 {n}）")
