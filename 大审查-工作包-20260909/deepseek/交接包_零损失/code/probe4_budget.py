# -*- coding: utf-8 -*-
"""probe4_budget.py — H8 预算曲线(E64) + H6b 能力式边界
用法: py -3 probe4_budget.py"""
import sys, os, json, glob, statistics, pathlib, time, shutil
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import world_gen as wg
import engine_gate as eg
import lib_bridge as lb

OUT = HERE / "out_v4_budget"
OUT.mkdir(exist_ok=True)

# ---------- H8: 预算曲线 ----------
SCENE = "clean"
SEEDS = list(range(1, 9))
GENS = 12
BUDGETS = [1, 2, 4, 6, 10, 16, 24, 64]
rows = []
for seed in SEEDS:
    w = wg.build_world(SCENE, seed)
    # static baseline
    sr = eg.run_arm(w, "static", seed, GENS)
    rows.append({"seed": seed, "budget": 0, "u_audit": sr["u_audit"], "adopts": 0,
                 "used": 0, "audit_dips": 0, "rollbacks": 0})
    for b in BUDGETS:
        t0 = time.time()
        r = eg.run_arm_budget(w, seed, GENS, b)
        rows.append({"seed": seed, "budget": b, "u_audit": r["u_audit"],
                     "adopts": r["adopts"], "used": r["used"],
                     "audit_dips": r["audit_dips"], "rollbacks": r["rollbacks"],
                     "sec": round(time.time() - t0, 2)})

(OUT / "rows_budget.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

print("===== H8 budget curve (scene=%s, gens=%d, seeds=%d) =====" % (SCENE, GENS, len(SEEDS)))
print("%-10s %10s %9s %9s %8s %8s" % ("budget", "u_audit", "u_static", "Delta", "pos/8", "adopt"))
static_mean = statistics.mean(r["u_audit"] for r in rows if r["budget"] == 0)
per_b = {}
for b in [0] + BUDGETS:
    rs = [r for r in rows if r["budget"] == b]
    if not rs:
        continue
    mu = statistics.mean(r["u_audit"] for r in rs)
    per_b[b] = mu
    if b == 0:
        print("%-10d %10.4f %9.4f %9s %8s %8s" % (b, mu, static_mean, "-", "-", 0))
        continue
    deltas = [r["u_audit"] - s0 for r, s0 in
              zip(rs, [x["u_audit"] for x in rows if x["budget"] == 0])]
    pos = sum(1 for d in deltas if d > 0)
    print("%-10d %10.4f %9.4f %+9.4f %5d/8 %8.1f" % (b, mu, static_mean, mu - static_mean, pos,
                                                       statistics.mean(r["adopts"] for r in rs)))

# crossing points: minimal budget where mean Delta > 0.05
thr05 = [b for b in BUDGETS if per_b.get(b, 0) - static_mean > 0.05]
print()
print("Delta>0.05 起于 budget=", thr05[0] if thr05 else None, "| 全预算最低档(1) Delta=", round(per_b.get(1, 0) - static_mean, 4))

# ---------- H6b: 能力式边界 ----------
print()
print("===== H6b: 能力式边界 =====")
cap_rows = []
for seed in range(1, 6):
    w = wg.build_world("clean", seed)
    lib = OUT / "tmp_h6b" / ("lib%d" % seed)
    lb.materialize_lib(lib, w["entries"])
    # (a) 引擎层能力: b3 append 同 id 必须拒绝(不覆盖)
    sample = None
    for p in (lib / "memory").rglob("*.json"):
        if "attic" not in str(p):
            sample = json.loads(p.read_text(encoding="utf-8"))
            break
    sample["content"] = sample["content"] + " TAMPERED"
    import io, contextlib
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            lb.b3.cmd_engine("append", str(lib), json.dumps(sample, ensure_ascii=False), 5)
        append_refused = False
    except SystemExit:
        append_refused = True
    # (b) 若绕过引擎直接 in-place 改文件 -> 一致性/梅克尔能否检出
    integ_before = lb.check_integrity(lib)
    pfile = next(p for p in (lib / "memory").rglob("*.json") if "attic" not in str(p))
    raw = json.loads(pfile.read_text(encoding="utf-8"))
    raw["importance"] = float(raw["importance"]) + 3.7   # in-place 篡改(违规操作)
    pfile.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
    integ_after = lb.check_integrity(lib)
    detected = (integ_after["merkle_ok"] is False) or (integ_after["chain_bad"] > integ_before["chain_bad"])
    cap_rows.append({"seed": seed, "append_same_id_refused": append_refused,
                     "inplace_detected": detected,
                     "merkle_before": integ_before["merkle_ok"],
                     "merkle_after": integ_after["merkle_ok"]})
    shutil.rmtree(OUT / "tmp_h6b" / ("lib%d" % seed), ignore_errors=True)
(OUT / "rows_h6b.json").write_text(json.dumps(cap_rows, ensure_ascii=False, indent=1), encoding="utf-8")
for c in cap_rows:
    print(c)
print("[probe4] out_v4_budget done");
