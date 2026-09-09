# -*- coding: utf-8 -*-
"""probe_r7_d7_forgetting_econ.py — D7: 遗忘经济学(retention 预算内交易)
dup+stale 世界; 每条保留条目计成本 1, 预算 cap R。策略:
  unlimited(全保留) / TTL(按失效时间先 retire) / value(按 measured 采纳率 retire 最低值)。
度量: 预算内真值 recall(T_fixed 固定金标) 与保留规模。
"""
import sys, os, json, time, pathlib, statistics, random
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
import world_gen as wg
import engine_gate as eg

OUT = HERE / "out_r5_d7"
OUT.mkdir(parents=True, exist_ok=True)


def value_of(entries, cfg, seed=3, sess=40):
    rng = random.Random(seed)
    shown = {e["id"]: 0 for e in entries}
    adpt = {e["id"]: 0 for e in entries}
    topics = sorted({e["topic"] for e in entries})
    for _ in range(sess):
        t = rng.choice(topics)
        top = eg.retrieve_top(entries, t, cfg)
        gold = set(eg.gold_ids_at(entries, {"topic": t}, 999, "rv"))
        for fid, _s, _e in top:
            shown[fid] += 1
            if fid in gold:
                adpt[fid] += 1
    return {e["id"]: (adpt[e["id"]] / shown[e["id"]]) if shown[e["id"]] else 0.0 for e in entries}


def run(w, policy, seed, cap=70, gens=16):
    entries = list(w["entries"])
    orig = list(w["entries"])
    audq = w["audit"]
    gold0 = [set(eg.gold_ids_at(orig, q, 0, "rv")) for q in audq]
    cfg = dict(eg.V3_DEFAULT)

    def Tfixed():
        tot = 0.0
        for q, g0 in zip(audq, gold0):
            top = eg.retrieve_top(entries, q["topic"], cfg)
            ids = [fid for fid, _s, _e in top]
            tot += sum(1 for i in ids if i in g0) / min(eg.K_GOLD, eg.K_TOPK)
        return tot / len(audq)

    removed = []
    if policy != "unlimited":
        rng = random.Random(seed * 3 + 1)
        for g in range(gens):
            if len(entries) <= cap:
                break
            if policy == "ttl":
                cands = sorted(entries, key=lambda e: -e.get("age_days", 0))
            else:
                val = value_of(entries, cfg, seed * 5 + g)
                cands = sorted(entries, key=lambda e: val.get(e["id"], 0))
            over = len(entries) - cap
            drop = cands[:over]
            entries = [e for e in entries if e not in drop]
            removed += [e["id"] for e in drop]
    return {"policy": policy, "T_fixed": round(Tfixed(), 4), "remain": len(entries),
            "removed": len(removed), "cap": cap}


rows = []
for seed in range(1, 7):
    w = wg.build_world("dup-drift", seed)
    # 叠 stale 噪声: 随机 15% 置 obsolete 但保留在库(模拟无人清理)
    rng = random.Random(seed + 99)
    for e in w["entries"]:
        if rng.random() < 0.15:
            e["obsolete_gen"] = 1
    for policy in ["unlimited", "ttl", "value"]:
        r = run(w, policy, seed)
        r.update({"seed": seed})
        rows.append(r)
(OUT / "rows_d7.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("%-10s %9s %8s %8s" % ("policy", "T_fixed", "remain", "removed"))
for policy in ["unlimited", "ttl", "value"]:
    rs = [r for r in rows if r["policy"] == policy]
    print("%-10s %9.4f %8d %8.1f" % (policy, statistics.mean(r["T_fixed"] for r in rs),
          int(statistics.mean(r["remain"] for r in rs)), statistics.mean(r["removed"] for r in rs)))
print("[D7] out_r5_d7 done");
