# -*- coding: utf-8 -*-
"""probe_r1_2_composite_judge.py — R1-2: 复合危险 x judge 污染晋升门
composite 世界(switch+spur+过时); 晋升门金标 = judge 名义('imp', 被 spur 污染);
审计臂: anchor(judge 自洽, 预期 0 触发) vs truth(rv, 预期检出回退)。
检验: E80 负交互触发条件 + EV-19/20 真值抽样在复合+污染下的兑付。
"""
import sys, os, json, time, pathlib, statistics, random
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import world_gen as wg
import engine_gate as eg

OUT = HERE / "out_r1_2"
OUT.mkdir(parents=True, exist_ok=True)


def run_lite(world, arm, seed, gens, audit_by):
    entries = list(world["entries"])
    rng = random.Random(seed * 911 + 7)
    trainA = world.get("trainA") or world.get("train")
    trainB = world.get("trainB")
    hold_q = world["hold"]
    audit_q = world["audit"]
    ga = world.get("switch_ga") or max(2, int(gens * 2 / 3))

    def tn(g):
        return trainA if (trainB is None or g < ga) else trainB

    def met(cfg):
        return {"T": eg.measure(entries, audit_q, cfg, gens - 1, "rv"),
                "P": eg.measure(entries, audit_q, cfg, gens - 1, "imp")}

    if arm == "static":
        cfg = dict(eg.V3_DEFAULT)
        m = met(cfg)
        return {"mode": arm, "adopts": 0, "dips": 0, "rollbacks": 0, "T_final": round(m["T"], 4),
                "P_final": round(m["P"], 4), "final_cfg": cfg}

    cfg = dict(eg.V3_DEFAULT)
    margin = eg.MARGIN0
    archive = [dict(cfg)]
    adopts = dips = rollbacks = 0
    last = None
    for g in range(gens):
        t = tn(g)
        p0 = eg.measure(entries, t, cfg, g, "imp")
        h0 = eg.measure(entries, hold_q, cfg, g, "imp")   # 晋升门 = judge(污染)
        best, bd = None, 0.0
        for _ in range(4):
            c = eg.mutate(rng, cfg)
            dp = eg.measure(entries, t, c, g, "imp") - p0
            dh = eg.measure(entries, hold_q, c, g, "imp") - h0
            if arm == "bareJ":
                ok = dp > 0
            else:
                ok = dp > margin and dh > margin
            if ok and dp > bd:
                best, bd = c, dp
        if best is not None:
            cfg = dict(best)
            adopts += 1
            archive.append(dict(best))
        if audit_by in ("imp", "rv") and (g % eg.AUDIT_EVERY == 0 or g == gens - 1):
            ua = eg.measure(entries, audit_q, cfg, g, audit_by)
            if last is not None and ua < last[1] - eg.REVERT_THR:
                dips += 1
                if last[0] is not None:
                    cfg = dict(last[0])
                    rollbacks += 1
                margin = max(0.005, margin * 0.7)
            last = (dict(cfg), ua)
    m = met(cfg)
    return {"mode": arm, "adopts": adopts, "dips": dips, "rollbacks": rollbacks,
            "T_final": round(m["T"], 4), "P_final": round(m["P"], 4), "final_cfg": cfg}


ARMS = [("static", None), ("bareJ", "none"), ("gatedJ-noAudit", "none"),
        ("gatedJ-anchor", "imp"), ("gatedJ-truth", "rv")]
rows = []
for seed in range(1, 9):
    w = wg.build_world("composite", seed)
    for arm, ab in ARMS:
        t0 = time.time()
        r = run_lite(w, arm, seed, 40, ab)
        r.update({"seed": seed, "sec": round(time.time() - t0, 2)})
        rows.append(r)

(OUT / "rows_r1_2.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("%-16s %8s %8s %8s %7s %6s %6s" % ("arm", "T_truth", "P_judge", "P-T", "adopt", "dips", "roll"))
for arm, _ in ARMS:
    rs = [r for r in rows if r["mode"] == arm]
    if rs:
        T = statistics.mean(r["T_final"] for r in rs)
        P = statistics.mean(r["P_final"] for r in rs)
        print("%-16s %8.4f %8.4f %8.4f %7.1f %6.1f %6.1f" % (arm, T, P, P - T,
              statistics.mean(r["adopts"] for r in rs),
              statistics.mean(r["dips"] for r in rs),
              statistics.mean(r["rollbacks"] for r in rs)))
print()
sm = {r["seed"]: r["T_final"] for r in rows if r["mode"] == "static"}
print("配对 T vs static:")
for arm, _ in ARMS:
    if arm == "static":
        continue
    rs = [r for r in rows if r["mode"] == arm]
    ds = [r["T_final"] - sm[r["seed"]] for r in rs]
    pos = sum(1 for d in ds if d > 0)
    print("%-16s mean Δ= %+.4f  pos %d/%d" % (arm, statistics.mean(ds), pos, len(ds)))
print("[R1-2] out_r1_2 done");
