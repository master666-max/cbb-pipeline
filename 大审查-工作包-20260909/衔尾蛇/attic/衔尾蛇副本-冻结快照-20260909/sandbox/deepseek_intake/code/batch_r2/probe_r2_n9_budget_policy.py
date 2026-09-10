# -*- coding: utf-8 -*-
"""probe_r2_n9_budget_policy.py — N9: 预算账本策略化(EV-16 落地)
clean x 12 代 x 8 seeds; 每代预算 b。策略: policy-off= b<b_min 时关演化(省注意力, 效用=static);
always= 预算不足也硬跑(浪费注意力无收益)。对照 b=1(低于 b*=2) 与 b=6(饱和)。
"""
import sys, os, json, time, pathlib, statistics
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
import world_gen as wg
import engine_gate as eg

OUT = HERE / "out_r2_n9"
OUT.mkdir(parents=True, exist_ok=True)
GENS = 12
B_MIN = 2


def static_u(w):
    return eg.measure(w["entries"], w["audit"], dict(eg.V3_DEFAULT), GENS - 1, "rv")


rows = []
for seed in range(1, 9):
    w = wg.build_world("clean", seed)
    su = static_u(w)
    for b in [1, 6]:
        # always: 每代花光 b
        ra = eg.run_arm_budget(w, seed, GENS, b)
        # policy: b>=B_MIN 才演化, 否则完全静止(0 注意力)
        if b >= B_MIN:
            rp = eg.run_arm_budget(w, seed, GENS, b)
        else:
            rp = {"u_audit": su, "used": 0, "adopts": 0}
        rows.append({"seed": seed, "b": b, "always_u": ra["u_audit"],
                     "always_used": ra["used"], "policy_u": rp["u_audit"],
                     "policy_used": rp["used"], "static": su})

(OUT / "rows_n9.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("%-4s %9s %9s %9s %9s %10s" % ("b", "static", "always_u", "policy_u", "always_used", "policy_used"))
for b in [1, 6]:
    rs = [r for r in rows if r["b"] == b]
    print("%-4d %9.4f %9.4f %9.4f %9.1f %10.1f  (alwaysΔ %+.4f / policyΔ %+.4f)" % (
        b, statistics.mean(r["static"] for r in rs),
        statistics.mean(r["always_u"] for r in rs),
        statistics.mean(r["policy_u"] for r in rs),
        statistics.mean(r["always_used"] for r in rs),
        statistics.mean(r["policy_used"] for r in rs),
        statistics.mean(r["always_u"] - r["static"] for r in rs),
        statistics.mean(r["policy_u"] - r["static"] for r in rs)))
print("[N9] out_r2_n9 done");
