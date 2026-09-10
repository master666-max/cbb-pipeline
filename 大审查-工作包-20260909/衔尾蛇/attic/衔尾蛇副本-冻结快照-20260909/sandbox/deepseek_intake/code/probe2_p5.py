# -*- coding: utf-8 -*-
"""probe2_p5.py — 探针2 真实路径验证: gated-row 移除的冗余副本经真实 b3 retire -> attic
用法: py -3 probe2_p5.py (读 out_v2_rowops/rows_dup-drift.json 的 seed1 gated-row)"""
import sys, os, json, pathlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import world_gen as wg
import lib_bridge as lb

rows = json.load(open(HERE / "out_v2_rowops2" / "rows_dup-drift.json", encoding="utf-8"))
target = None
for r in rows:
    if r["mode"] == "gated-row" and r["seed"] == 1:
        target = r
        break
if target is None:
    sys.exit("no gated-row seed1 row found")
removed = target.get("removed_ids", [])
world = wg.build_world("dup-drift", 1)
removed_set = set(removed)
active = [e for e in world["entries"] if e["id"] not in removed_set]
retired = [e for e in world["entries"] if e["id"] in removed_set]
print("active=%d retired_candidates=%d (n_removed recorded=%d)" % (
    len(active), len(retired), target.get("n_removed", -1)))
out_dir = HERE / "out_v2_rowops2" / "integrity_real"
lib = out_dir / "dup-drift_seed1_gatedrow"
wres = lb.materialize_lib(lib, active, extra_expired=retired)
doc_b = lb.real_doctor(lib)
int_b = lb.check_integrity(lib)
ret_out = lb.real_retire(lib)
doc_a = lb.real_doctor(lib)
int_a = lb.check_integrity(lib)
# leakage: retired ids must not appear in retrieve for their topic
leak = 0
for e in retired[:10]:
    ids = lb.real_retrieve_ids(lib, e["topic"], 5)
    if any(i == e["id"] or i == e["id"] + "_exp" for i in ids):
        leak += 1
res = {"active": len(active), "retired_injected": len(retired),
       "doctor_before": doc_b.splitlines(), "doctor_after": doc_a.splitlines(),
       "retire": ret_out, "integrity_before": int_b, "integrity_after": int_a,
       "leak": leak}
(out_dir / "dup-drift_seed1_gatedrow.json").write_text(
    json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1))
print("[probe2_p5] ->", out_dir / "dup-drift_seed1_gatedrow.json")
