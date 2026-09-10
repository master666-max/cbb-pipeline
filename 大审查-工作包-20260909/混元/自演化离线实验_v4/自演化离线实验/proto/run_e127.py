"""E127 - P0 决定性验证：强信号世界 + 非盲评"""
import sys, statistics
sys.path.insert(0, "/data/workspace/proto")
from evolve31 import run, BASE

DANGER = dict(BASE, blind=False)

CFGS = {
    "danger":        dict(DANGER),
    "+blind":        dict(DANGER, blind=True),
    "+strict":       dict(DANGER, audit_mode="strict"),
    "+strip":        dict(DANGER, strip=True),
    "+cap5":         dict(DANGER, surf_cap=5.0),
    "+blind+strict": dict(DANGER, blind=True, audit_mode="strict"),
    "+all":          dict(DANGER, blind=True, audit_mode="strict", strip=True, surf_cap=5.0),
}

if __name__ == "__main__":
    gens = 25
    print("强信号世界 + 非盲评(a=0.5) - P0 对策对比(10种子, 25代)")
    print("%-16s %10s %11s %9s %8s" % ("配置", "真值增益", "剥离后增益", "surf占比", "回退"))
    for nm, cfg in CFGS.items():
        rs = [run(s, cfg, gens=gens, collect=True) for s in range(1, 11)]
        print("%-16s %+10.4f %+11.4f %8.1f%% %8.1f" % (
            nm,
            statistics.mean(r[0] for r in rs),
            statistics.mean(r[1]["gain_strip"] for r in rs),
            statistics.mean(r[1]["frac"] for r in rs) * 100,
            statistics.mean(r[1]["reverts"] for r in rs)))
