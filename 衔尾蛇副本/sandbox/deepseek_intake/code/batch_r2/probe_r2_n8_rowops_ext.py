# -*- coding: utf-8 -*-
"""probe_r2_n8_rowops_ext.py (v2) — N8: 行层算子扩展 + 语义组冗余度量(修 M9)
臂: gated / gated-row(副本 retire) / gated-row2(+usage-based 低价值 retire)。
度量: T(随活跃集金标) 与 T_fixed(移除前固定 rv-top 金标, 移除=miss) —— 防机械虚高。
"""
import sys, os, json, time, pathlib, statistics, random
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
import world_gen as wg
import engine_gate as eg

OUT = HERE / "out_r2_n8"
OUT.mkdir(parents=True, exist_ok=True)


def cluster_map(entries):
    alive = {e["id"] for e in entries}
    parent = {e["id"]: e["id"] for e in entries}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    for e in entries:
        for lk in e.get("links", []):
            lid = str(lk).strip("[]")
            if lid in alive:
                union(e["id"], lid)
    return {e["id"]: find(e["id"]) for e in entries}


def group_redundancy(entries, qs, cfg, gen, k=eg.K_TOPK):
    mp = cluster_map(entries)
    tot = cnt = 0.0
    for q in qs:
        top = eg.retrieve_top(entries, q["topic"], cfg, k)
        ids = [fid for fid, _s, _e in top]
        if len(ids) < 2:
            continue
        same = pairs = 0
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                pairs += 1
                if mp.get(ids[i]) == mp.get(ids[j]):
                    same += 1
        if pairs:
            tot += same / pairs
            cnt += 1
    return tot / cnt if cnt else 0.0


def usage_low_ids(entries, cfg, seed):
    rng = random.Random(seed)
    shown = {e["id"]: 0 for e in entries}
    adpt = {e["id"]: 0 for e in entries}
    topics = sorted({e["topic"] for e in entries})
    for _ in range(50):
        t = rng.choice(topics)
        top = eg.retrieve_top(entries, t, cfg)
        gold = set(eg.gold_ids_at(entries, {"topic": t}, 999, "rv"))
        for fid, _s, _e in top:
            shown[fid] += 1
            if fid in gold:
                adpt[fid] += 1
    return [e["id"] for e in entries if shown[e["id"]] >= 2 and adpt[e["id"]] == 0]


def run(w, arm, seed, gens):
    entries = list(w["entries"])
    orig = list(w["entries"])
    audit_q = w["audit"]
    gold0 = [set(eg.gold_ids_at(orig, q, 0, "rv")) for q in audit_q]

    def Tfixed(cfg):
        tot = 0.0
        for q, g0 in zip(audit_q, gold0):
            top = eg.retrieve_top(entries, q["topic"], cfg)
            ids = [fid for fid, _s, _e in top]
            tot += sum(1 for i in ids if i in g0) / min(eg.K_GOLD, eg.K_TOPK)
        return tot / len(audit_q)

    rng = random.Random(seed * 229 + 7)
    train_q = w.get("train") or w.get("trainA")
    hold_q = w["hold"]
    cfg = dict(eg.V3_DEFAULT)
    margin = eg.MARGIN0
    adopts = removed = 0
    for g in range(gens):
        if arm in ("gated-row", "gated-row2") and g % 3 == 0:
            clus = eg.detect_redundant(entries)
            retire = sorted({m for ms in clus.values() for m in ms})
            if arm == "gated-row2":
                low = [i for i in usage_low_ids(entries, cfg, seed * 10 + g) if i not in retire]
                retire += low
            if retire:
                cand = [e for e in entries if e["id"] not in retire]
                ok = (eg.measure(cand, train_q, cfg, g, "imp")
                      >= eg.measure(entries, train_q, cfg, g, "imp") - eg.TOL_ARCH
                      and eg.measure(cand, hold_q, cfg, g, "rv")
                      >= eg.measure(entries, hold_q, cfg, g, "rv") - eg.TOL_ARCH)
                if ok:
                    entries = cand
                    removed += len(retire)
        tr0 = eg.measure(entries, train_q, cfg, g, "imp")
        ho0 = eg.measure(entries, hold_q, cfg, g, "rv")
        best, bd = None, 0.0
        for _ in range(4):
            c = eg.mutate(rng, cfg)
            dt = eg.measure(entries, train_q, c, g, "imp") - tr0
            dh = eg.measure(entries, hold_q, c, g, "rv") - ho0
            if dt > margin and dh > margin and dt > bd:
                best, bd = c, dt
        if best is not None:
            cfg = dict(best)
            adopts += 1
    gf = gens - 1
    return {"mode": arm, "T": round(eg.measure(entries, audit_q, cfg, gf, "rv"), 4),
            "T_fixed": round(Tfixed(cfg), 4),
            "grp_redun": round(group_redundancy(entries, hold_q, cfg, gf), 4),
            "n_remain": len(entries), "adopts": adopts, "removed": removed}


rows = []
for seed in range(1, 7):
    w = wg.build_world("dup-drift", seed)
    for arm in ["gated", "gated-row", "gated-row2"]:
        t0 = time.time()
        r = run(w, arm, seed, 24)
        r.update({"seed": seed, "sec": round(time.time() - t0, 2)})
        rows.append(r)

(OUT / "rows_n8.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("%-12s %8s %8s %9s %8s %7s %8s" % ("arm", "T", "T_fixed", "grp_redun", "remain", "adopt", "removed"))
for arm in ["gated", "gated-row", "gated-row2"]:
    rs = [r for r in rows if r["mode"] == arm]
    if rs:
        print("%-12s %8.4f %8.4f %9.4f %8d %7.1f %8.1f" % (
            arm, statistics.mean(r["T"] for r in rs), statistics.mean(r["T_fixed"] for r in rs),
            statistics.mean(r["grp_redun"] for r in rs), int(statistics.mean(r["n_remain"] for r in rs)),
            statistics.mean(r["adopts"] for r in rs), statistics.mean(r["removed"] for r in rs)))
print("[N8] out_r2_n8 done");
