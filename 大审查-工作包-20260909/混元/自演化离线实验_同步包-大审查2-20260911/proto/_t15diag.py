import sys, statistics, math, random as _rnd
sys.path.insert(0,'/data/workspace/proto')
from verify_kernel import mk
from kernel import truth, Policy

def rd(seed, audit, ra_after, gens=24, drift=0.35, **kw):
    kk = mk(seed, scale=3.0, audit=audit, reanchor_after=ra_after, **kw)
    kk.margin = kk.cfg.margin
    base = truth(kk.entries, kk.tasks_train+kk.tasks_held, Policy())
    for g in range(1, gens+1):
        if g == gens//3:
            r=_rnd.Random(seed+999)
            for e in kk.entries:
                if r.random()<drift: e.quality=r.random()*0.3
        kk._step(g)
    return truth(kk.entries, kk.tasks_train+kk.tasks_held, kk.champion)-base

N = int(sys.argv[1]) if len(sys.argv)>1 else 8
for lab,kw in (('默认(含anchor+boost)',{}),
               ('隔离 anchor=False,boost=None',dict(anchor=False,boost_on_drift=None))):
    a=[rd(s,True,2,**kw) for s in range(1,N+1)]
    b=[rd(s,False,2,**kw) for s in range(1,N+1)]
    d=[x-y for x,y in zip(a,b)]
    se=statistics.pstdev(d)/math.sqrt(N)
    print('%-30s 审计=%+.4f 无审计=%+.4f 差=%+.4f (t=%.2f)'%(
        lab,statistics.mean(a),statistics.mean(b),statistics.mean(d),
        statistics.mean(d)/se if se else 0), flush=True)
