import sys, random; sys.path.insert(0,'/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong, retrieve_strong, tscore

def count_audit(seed, gens=20):
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    root = Cfg2()
    main, best, btr = root, root, None
    probe = build_tasks(E, random.Random(4242), 4, offset=7)
    trig = 0
    for g in range(1, gens+1):
        if g == gens//3:
            r = random.Random(seed+999)
            for e in E:
                if r.random() < 0.30: e["true_quality"] = r.random()*0.3
        if g % 5 == 0:
            cur = _m(tscore(E, t, main) for t in probe)
            if btr is None:
                btr, best = cur, main
            elif cur < btr - 0.01:
                trig += 1
                btr, best = cur, main
            else:
                btr, best = cur, main
    return trig

v = [count_audit(s) for s in range(1, 11)]
print("drift 下审计触发次数（20代，每5代一次=最多4次）:", v, "均值", sum(v)/len(v))
