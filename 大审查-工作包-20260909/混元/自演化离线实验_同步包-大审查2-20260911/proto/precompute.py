"""预计算 verify_kernel 中的重型测试（分片落盘，可中断续跑）

★ 为什么要独立出来：
  verify_kernel.py 是平铺脚本，import 它就会跑全部测试。
  沙盒不稳时"从中间续跑"做不到，所以把重活拆到这里预先填缓存。

用法：
    python3 proto/precompute.py           # 只补缺失项
    python3 proto/precompute.py t15       # 只做 T15
    python3 proto/precompute.py t17       # T17/T18/T20
"""
import sys, random as _rnd, statistics
sys.path.insert(0, '/data/workspace/proto')
from vk_common import mk, cached
from kernel import truth, Policy

GENS = 24


def _drifted(seed, gens, drift, at, entries):
    if not drift:
        return
    r = _rnd.Random(seed + 999)
    for e in entries:
        if r.random() < drift:
            e.quality = r.random() * 0.3


def run_drift(seed, audit, gens=GENS, drift=0.35, diag=0.01):
    """T15: 返回增益。diag=-999 → 退化为 naive 无条件回退"""
    key = f"drift_{seed}_{audit}_2_{gens}_{drift}_{diag}"

    def _f():
        kk = mk(seed, scale=3.0, audit=audit, reanchor_after=2,
                diagnose_delta=diag)
        kk.margin = kk.cfg.margin
        base = truth(kk.entries, kk.tasks_train + kk.tasks_held, Policy())
        for g in range(1, gens + 1):
            if g == gens // 3:
                _drifted(seed, gens, drift, g, kk.entries)
            kk._step(g)
        return truth(kk.entries, kk.tasks_train + kk.tasks_held,
                     kk.champion) - base
    return cached(key, _f)


def run_det(seed, do_drift=True, gens=GENS):
    """T17: 返回 [检出代(-1=未检出), 注入代, 增益]"""
    key = f"det_{seed}_{do_drift}_{gens}_[]"

    def _f():
        kk = mk(seed, scale=2.0)
        kk.margin = kk.cfg.margin
        base = truth(kk.entries, kk.tasks_train + kk.tasks_held, Policy())
        at = gens // 3
        for g in range(1, gens + 1):
            if do_drift and g == at:
                _drifted(seed, gens, 0.35, g, kk.entries)
            kk._step(g)
        gain = truth(kk.entries, kk.tasks_train + kk.tasks_held,
                     kk.champion) - base
        return [kk._drift_detected_at if kk._drift_detected_at is not None else -1,
                at, gain]
    return cached(key, _f)


def run_boost(seed, boost, gens=GENS, seeds_n=6):
    """T18: drift 后 boost vs 不 boost"""
    key = f"boost_{seed}_{boost}_{gens}_{seeds_n}"

    def _f():
        tot = []
        for sd in range(seed, seed + seeds_n):
            kk = mk(sd, scale=2.0, blind=True,
                    boost_on_drift=(4 if boost else None))
            kk.margin = kk.cfg.margin
            base = truth(kk.entries, kk.tasks_train + kk.tasks_held, Policy())
            for g in range(1, gens + 1):
                if g == gens // 3:
                    _drifted(sd, gens, 0.35, g, kk.entries)
                kk._step(g)
            tot.append(truth(kk.entries, kk.tasks_train + kk.tasks_held,
                             kk.champion) - base)
        return statistics.mean(tot)
    return cached(key, _f)


def run_nodrift(seed, anchor, gens=18):
    """T20: 锚定探针零副作用"""
    key = f"nodrift_{seed}_{anchor}_{gens}"

    def _f():
        kk = mk(seed, scale=2.0, anchor=anchor)
        kk.margin = kk.cfg.margin
        base = truth(kk.entries, kk.tasks_train + kk.tasks_held, Policy())
        for g in range(1, gens + 1):
            kk._step(g)
        return truth(kk.entries, kk.tasks_train + kk.tasks_held,
                     kk.champion) - base
    return cached(key, _f)


def gains(scale, audit, seeds=8):
    key = f"gains_{scale}_{audit}_{seeds}"

    def _f():
        out = []
        for sd in range(seeds):
            kk = mk(sd, scale=scale, audit=audit)
            base = truth(kk.entries, kk.tasks_train + kk.tasks_held, Policy())
            kk.run(20)
            out.append(truth(kk.entries, kk.tasks_train + kk.tasks_held, kk.champion) - base)
        return statistics.mean(out)
    return cached(key, _f)


def gains_blind(blind, seeds=8):
    key = f"gblind_{blind}_{seeds}"

    def _f():
        out = []
        for sd in range(seeds):
            kk = mk(sd, scale=3.0, audit=False, blind=blind)
            base = truth(kk.entries, kk.tasks_train + kk.tasks_held, Policy())
            kk.run(20)
            out.append(truth(kk.entries, kk.tasks_train + kk.tasks_held, kk.champion) - base)
        return statistics.mean(out)
    return cached(key, _f)


def gains_prune(prune_by, seeds=8):
    key = f"gprune_{prune_by}_{seeds}"

    def _f():
        out = []
        for sd in range(seeds):
            kk = mk(sd, scale=1.0, write_every=2, write_n=3, prune_by=prune_by)
            base = truth(kk.entries, kk.tasks_train + kk.tasks_held, Policy())
            kk.run(20)
            out.append(truth(kk.entries, kk.tasks_train + kk.tasks_held, kk.champion) - base)
        return statistics.mean(out)
    return cached(key, _f)


TASKS = {
    "gains": lambda: [gains(2.0, False), gains(2.0, True), gains(1.0, True)],
    "gblind": lambda: [gains_blind(True), gains_blind(False)],
    "gprune": lambda: [gains_prune(None), gains_prune("truth")],
    "t15": lambda: [run_drift(s, au, diag=dg)
                    for s in range(1, 9)
                    for au, dg in ((True, -999.0), (True, 0.01), (False, 0.01))],
    "t17": lambda: ([run_det(s, True) for s in range(1, 7)]
                    + [run_det(s, False) for s in range(1, 7)]),
    "t18": lambda: [run_boost(1, False), run_boost(1, True)],
    "t20": lambda: ([run_nodrift(s, True) for s in range(1, 7)]
                    + [run_nodrift(s, False) for s in range(1, 7)]),
}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else None
    for name, fn in TASKS.items():
        if which and name != which:
            continue
        vals = fn()
        print(f"  {name}: {len(vals)} 项完成", flush=True)
    print("预计算完成")
