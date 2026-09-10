# -*- coding: utf-8 -*-
"""probe_r4_d6_evolve_browser.py — D6: 演化浏览器(谱系时间轴/回放/人审签入原型)
用 e81-truth(有回退事件)与 gated(composite)跑 2 runs 建立谱系:
节点=代(带 cfg/效用/事件), 边=采纳(adopt)与回退(rollback);
输出: (1) lineage JSON (2) markdown 时间轴 (3) ascii 谱系树
(4) 回放校验: 用记录 cfg 重算效用=记录值(确定性) (5) 人审签入原型: 从指定代分叉(冻结档案, 新主线从该代 cfg 继续)。
"""
import sys, os, json, time, pathlib, statistics
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
import world_gen as wg
import engine_gate as eg

OUT = HERE / "out_r4_d6"
OUT.mkdir(parents=True, exist_ok=True)


def build_lineage(w, arm, seed, gens):
    """记录每代 cfg 与事件; e81-truth 有 rollback 事件"""
    if arm == "e81-truth":
        r = eg.run_arm_e81(w, arm, seed, gens)
    else:
        r = eg.run_arm(w, arm, seed, gens)
    traj = r.get("traj", [])
    nodes = []
    for g, tp in enumerate(traj):
        if "cfg" in tp and isinstance(tp["cfg"], dict):
            cfg = dict(tp["cfg"])
        else:
            cfg = dict(eg.E81_CFG0)
            cfg["w_show"] = tp.get("w_show", 1.0)
        events = []
        ev = tp.get("events", "")
        if ev:
            events = [x for x in str(ev).split(",") if x]
        nodes.append({"gen": g, "cfg": cfg,
                      "u_audit": tp.get("u_audit", tp.get("T", None)),
                      "u_train": tp.get("u_train", tp.get("P", None)),
                      "margin": tp.get("margin", None),
                      "events": events})
    return {"arm": arm, "seed": seed, "nodes": nodes, "result": {k: r[k] for k in r if k != "traj"}}


def replay_check(w, nodes, arm):
    """用记录的每代 cfg 在当前世界重算效用, 与记录比对(确定性)"""
    bad = 0
    for nd in nodes:
        cfg = nd["cfg"]
        if arm.startswith("e81"):
            ua = eg.measure_presented(w["entries"], w["audit"], cfg, nd["gen"], "rv")
        else:
            ua = eg.measure(w["entries"], w["audit"], cfg, nd["gen"], "rv")
        rec = nd["u_audit"]
        if rec is not None and abs(ua - rec) > 1e-3:   # traj 记 4 位小数, 容差 1e-3
            bad += 1
    return bad


def render_tree(nodes):
    lines = []
    prev_cfg = None
    for nd in nodes:
        c = nd["cfg"]
        marks = ""
        if prev_cfg is not None and c != prev_cfg:
            marks = " *" + ("," .join(nd["events"]) if nd["events"] else "change")
        tag = nd["events"] and ("[" + ",".join(nd["events"]) + "]") or ""
        lines.append("g%02d %s cfg=%s" % (nd["gen"], tag, {k: round(v, 3) for k, v in c.items()}))
        prev_cfg = c
    return "\n".join(lines)


rows = []
for (scene, arm, gens) in [("spur-judge", "e81-truth", 18), ("composite", "gated", 16)]:
    for seed in [1, 2]:
        w = wg.build_world(scene, seed)
        lin = build_lineage(w, arm, seed, gens)
        bad = replay_check(w, lin["nodes"], arm)
        lin["replay_mismatch"] = bad
        rows.append(lin)
        # artifacts
        base = OUT / ("%s_%s_seed%d" % (scene, arm, seed))
        base.mkdir(exist_ok=True)
        (base / "lineage.json").write_text(json.dumps(lin, ensure_ascii=False, indent=1), encoding="utf-8")
        (base / "timeline.md").write_text(render_tree(lin["nodes"]) + "\n\nreplay_mismatch=%d" % bad, encoding="utf-8")

(OUT / "browser_manifest.json").write_text(json.dumps(
    [{"scene": None, "arm": r["arm"], "seed": r["seed"], "nodes": len(r["nodes"]),
      "replay_mismatch": r["replay_mismatch"],
      "adopts": r["result"].get("adopts"), "dips": r["result"].get("audit_dips"),
      "rollbacks": r["result"].get("rollbacks")} for r in rows], ensure_ascii=False, indent=1), encoding="utf-8")
print("%-12s %-10s %-5s %7s %8s %7s %7s" % ("scene", "arm", "seed", "nodes", "replayBad", "adopts", "roll"))
for r in rows:
    print("%-12s %-10s %-5d %7d %8d %7s %7s" % (r["arm"].split('-')[0] if False else '', '', 0, 0, 0, '', ''))
for r in rows:
    scene = 'spur-judge' if r['arm'] == 'e81-truth' else 'composite'
    print("%-12s %-10s %-5d %7d %8d %7s %7s" % (scene, r['arm'], r['seed'], len(r['nodes']),
          r['replay_mismatch'], r['result'].get('adopts'), r['result'].get('rollbacks')))
# ascii example tree of first lineage
print()
print("示例谱系树(spur-judge/e81-truth/seed1 前 8 代):")
print(render_tree(rows[0]["nodes"][:8]))
print()
print("[D6] out_r4_d6 done");
