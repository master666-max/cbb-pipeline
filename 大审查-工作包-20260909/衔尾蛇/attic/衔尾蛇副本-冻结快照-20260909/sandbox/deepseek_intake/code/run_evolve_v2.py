# -*- coding: utf-8 -*-
"""run_evolve_v2.py — V2 主驱动

用法:
  py -3 run_evolve_v2.py --stage parity
  py -3 run_evolve_v2.py --scene all --arms static,bare,gated --seeds 6 --gens 12 --out out_v2
"""
import sys, os, json, time, argparse, pathlib, statistics

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import world_gen as wg
import engine_gate as eg
import lib_bridge as lb

SCENES = ["clean", "spur-surface", "switch", "stale", "dup-drift"]
ARMS = ["static", "bare", "single", "gated", "gated-noAudit", "gated-noPareto",
        "gated-marginHigh", "gated-cap", "gated-row",
        "e81-static", "e81-bare", "e81-anchor", "e81-truth"]

ARM_FLAGS = {
    "static": {},
    "bare": {"audit_on": False, "pareto_on": False, "margin_override": 0.0},
    "gated": {"audit_on": True, "pareto_on": True},
    "gated-noAudit": {"audit_on": False, "pareto_on": True},
    "gated-noPareto": {"audit_on": True, "pareto_on": False},
    "gated-marginHigh": {"audit_on": True, "pareto_on": True, "margin_override": 0.15},
    "single": {"audit_on": True, "pareto_on": False},
    "gated-cap": {"audit_on": True, "pareto_on": True, "pareto_mode": "cap"},
    "gated-row": {"audit_on": True, "pareto_on": True},
}


def run_matrix(scenes, arms, seeds, gens, out_dir, quick=False):
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"script": "run_evolve_v2.py", "python": sys.version.split()[0],
                "bootstrap_v3": lb.b3.VERSION, "seeds": seeds, "gens": gens,
                "quick": quick, "arms": arms, "scenes": {}, "ts": time.strftime("%F %T")}
    for sc in scenes:
        rows = []
        for seed in seeds:
            world = wg.build_world(sc, seed)
            for arm in arms:
                t0 = time.time()
                if arm.startswith("e81-"):
                    r = eg.run_arm_e81(world, arm, seed, gens)
                    r["u_audit"] = r.get("T_final", 0.0)   # 对齐通用列: 真值 util
                    r["u_trainA"] = r.get("P_final", 0.0)  # 对齐通用列: judge 感知 util
                    r["u_hold"] = r.get("P_final", 0.0)
                else:
                    flags = ARM_FLAGS.get(arm, {})
                    r = eg.run_arm(world, arm, seed, gens, quick=quick, **flags)
                r["seed"] = seed
                r["scene"] = sc
                r["sec"] = round(time.time() - t0, 3)
                rows.append(r)
        agg = {}
        for arm in arms:
            rs = [r for r in rows if r["mode"] == arm]
            if not rs:
                continue
            agg[arm] = {
                "u_audit_mean": round(statistics.mean(x["u_audit"] for x in rs), 4),
                "u_audit_std": round(statistics.pstdev(x["u_audit"] for x in rs), 4),
                "u_hold_mean": round(statistics.mean(x["u_hold"] for x in rs), 4),
                "adopts_mean": round(statistics.mean(x["adopts"] for x in rs), 2),
                "dips_mean": round(statistics.mean(x["audit_dips"] for x in rs), 2),
                "rollbacks_mean": round(statistics.mean(x["rollbacks"] for x in rs), 2),
                "sec_mean": round(statistics.mean(x["sec"] for x in rs), 3),
                "seeds": len(rs),
            }
        manifest["scenes"][sc] = {"by_mode": agg}
        (out_dir / ("rows_" + sc + ".json")).write_text(
            json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print_table(sc, rows, agg)
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print("[manifest] ->", out_dir / "manifest.json")
    return manifest


def print_table(scene, rows, agg):
    print()
    print("===== scene", scene, "| seeds=", len(set(r["seed"] for r in rows)), "=====")
    hdr = "%-16s %9s %7s %9s %8s %6s %6s %6s" % (
        "arm", "auditU", "std", "holdU", "adopt", "dips", "rbk", "sec")
    print(hdr)
    for arm, v in agg.items():
        print("%-16s %9.4f %7.4f %9.4f %8.2f %6.2f %6.2f %6.2f" % (
            arm, v["u_audit_mean"], v["u_audit_std"], v["u_hold_mean"],
            v["adopts_mean"], v["dips_mean"], v["rollbacks_mean"], v["sec_mean"]))


def p5_spot_check(world, seed, out_dir, final_gen):
    sc = world["scene"]
    active = [e for e in world["entries"] if e["birth_gen"] <= final_gen
              and (e.get("obsolete_gen") is None or e["obsolete_gen"] > final_gen)]
    expired = [e for e in world["entries"] if e.get("obsolete_gen") is not None
               and e["obsolete_gen"] <= final_gen]
    lib_dir = out_dir / "libs_snapshot" / (sc + "_seed%d_gated" % seed)
    wres = lb.materialize_lib(lib_dir, active, extra_expired=expired[:4])
    doc_before = lb.real_doctor(lib_dir)
    int_before = lb.check_integrity(lib_dir)
    retire_out = lb.real_retire(lib_dir)
    doc_after = lb.real_doctor(lib_dir)
    int_after = lb.check_integrity(lib_dir)
    leak = 0
    leak_check = {}
    if world.get("decay_topics"):
        for t in world["decay_topics"]:
            ids = lb.real_retrieve_ids(lib_dir, t, 5)
            exp_hits = [i for i in ids if i.endswith("_exp")]
            leak += len(exp_hits)
            leak_check[t] = ids
    res = {"scene": sc, "seed": seed, "arm": "gated",
           "written": wres["entries_written"], "append_ms": wres["append_ms"],
           "doctor_before": doc_before.splitlines()[:2],
           "integrity_before": int_before,
           "retire": retire_out,
           "doctor_after": doc_after.splitlines()[:2],
           "integrity_after": int_after,
           "leak_exp_in_top5": leak, "leak_topids": leak_check,
           "n_expired_injected": min(4, len(expired))}
    target = out_dir / "integrity_real" / (sc + "_seed1_gated.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="matrix", choices=["matrix", "parity"])
    ap.add_argument("--scene", default="all")
    ap.add_argument("--arms", default="static,bare,gated")
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--gens", type=int, default=12)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--zeroout", type=float, default=0.0,
                    help="变异罕见置零概率(越过阶跃阈值; 0=关闭)")
    ap.add_argument("--out", default="out_v2")
    a = ap.parse_args()
    if a.zeroout > 0:
        eg.MUTATE_ZERO = a.zeroout

    out_dir = pathlib.Path(HERE) / a.out
    out_dir.mkdir(parents=True, exist_ok=True)

    if a.stage == "parity":
        res = lb.parity_check(seed_count=5, queries_per_lib=20)
        (out_dir / "parity.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print("[parity]", res)
        sys.exit(0)

    scenes = SCENES if a.scene == "all" else [s.strip() for s in a.scene.split(",")]
    arms = [s.strip() for s in a.arms.split(",")]
    for arm in arms:
        if arm not in ARM_FLAGS and not arm.startswith("e81-"):
            sys.exit("未知 arm: %s (可选 %s)" % (arm, ARMS))
    seeds = list(range(1, a.seeds + 1))
    run_matrix(scenes, arms, seeds, a.gens, out_dir, quick=a.quick)

    (out_dir / "integrity_real").mkdir(parents=True, exist_ok=True)
    p5 = {}
    for sc in scenes:
        world = wg.build_world(sc, 1)
        try:
            p5[sc] = p5_spot_check(world, 1, out_dir, final_gen=a.gens - 1)
        except Exception as ex:
            p5[sc] = {"error": str(ex)[:300]}
    (out_dir / "p5_real_spot.json").write_text(
        json.dumps(p5, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print("[P5 real spot] ->", out_dir / "p5_real_spot.json")


if __name__ == "__main__":
    main()
