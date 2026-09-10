# -*- coding: utf-8 -*-
"""probe_r2_n5_h4_closed.py — N5: importance 实测化闭环进引擎计分(EV-14)
检索计分用 measured importance(adopted/shown, 每5代从使用轨迹更新, 未观测悲观0);
judge 训练金标仍用自称(judge 信 claims)。对比 gated-claimed vs gated-measured 的真值 util 与 top 内容。
场景: spur-surface(自称不可信域, 期望实测臂少受 spur 误导而真值更高/或同)。
"""
import sys, os, json, time, pathlib, statistics, random
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
import world_gen as wg
import engine_gate as eg

OUT = HERE / "out_r2_n5"
OUT.mkdir(parents=True, exist_ok=True)


def imp_map_from_traces(entries, cfg, sessions=60, seed=7):
    """按当前检索产生的使用轨迹算 measured importance(悲观初始化 0)"""
    rng = random.Random(seed)
    shown = {e["id"]: 0 for e in entries}
    adpt = {e["id"]: 0 for e in entries}
    topics = sorted({e["topic"] for e in entries})
    for _ in range(sessions):
        t = rng.choice(topics)
        top = eg.retrieve_top(entries, t, cfg)
        gold = set(eg.gold_ids_at(entries, {"topic": t}, 999, "rv"))
        for fid, _s, _e in top:
            shown[fid] += 1
            if fid in gold:
                adpt[fid] += 1
    return {e["id"]: (adpt[e["id"]] / shown[e["id"]]) if shown[e["id"]] else 0.0 for e in entries}


def scoring_entries(entries, impmap):
    out = []
    for e in entries:
        ee = dict(e)
        ee["importance"] = impmap.get(e["id"], ee["importance"])
        out.append(ee)
    return out


def run(w, arm, seed, gens):
    entries = list(w["entries"])
    rng = random.Random(seed * 821 + 1)
    train_q = w.get("train") or w.get("trainA")
    hold_q = w["hold"]
    audit_q = w["audit"]
    measured = None
    impmap = {e["id"]: e["importance"] for e in entries}
    work = entries   # scoring source list (claimed by default)
    cfg = dict(eg.V3_DEFAULT)
    margin = eg.MARGIN0
    adopts = 0
    for g in range(gens):
        if arm == "measured" and (g % 5 == 0):
            impmap = imp_map_from_traces(entries, cfg, 60, seed * 10 + g)
            work = scoring_entries(entries, impmap) if arm == "measured" else entries
        tr0 = eg.measure(work, train_q, cfg, g, "imp")   # judge 通道(自称金标)
        ho0 = eg.measure(work, hold_q, cfg, g, "rv")     # 真值晋升门
        best, bd = None, 0.0
        for _ in range(4):
            c = eg.mutate(rng, cfg)
            # 候选用与主线相同的 importance 源
            dt = eg.measure(work, train_q, c, g, "imp") - tr0
            dh = eg.measure(work, hold_q, c, g, "rv") - ho0
            if dt > margin and dh > margin and dt > bd:
                best, bd = c, dt
        if best is not None:
            cfg = dict(best)
            adopts += 1
    gf = gens - 1
    # 终局真值 util(用原始 claimed 检索? 不: 用各自 importance 源——同一把尺子各臂不同源)
    T = eg.measure(work, audit_q, cfg, gf, "rv")
    # 参考: 用独立"真实条目质量"直接量(不含 importance 影响)做不到, 故 T 口径=各臂自己的 importance 源;
    # 另给 claimed-source 的真值(公平同尺): 
    T_claimed = eg.measure(entries, audit_q, cfg, gf, "rv")
    return {"mode": arm, "T_self": round(T, 4), "T_claimedSource": round(T_claimed, 4),
            "adopts": adopts, "final_cfg": cfg}


rows = []
for seed in range(1, 7):
    w = wg.build_world("spur-surface", seed)
    for arm in ["static", "claimed", "measured"]:
        t0 = time.time()
        if arm == "static":
            cfg0 = dict(eg.V3_DEFAULT)
            r = {"mode": arm, "T_self": round(eg.measure(w["entries"], w["audit"], cfg0, 29, "rv"), 4),
                 "T_claimedSource": round(eg.measure(w["entries"], w["audit"], cfg0, 29, "rv"), 4),
                 "adopts": 0}
        else:
            r = run(w, arm, seed, 30)
        r.update({"seed": seed, "sec": round(time.time() - t0, 2)})
        rows.append(r)

(OUT / "rows_n5.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("%-9s %9s %9s %7s" % ("arm", "T_self", "T_claimedSrc", "adopt"))
for arm in ["static", "claimed", "measured"]:
    rs = [r for r in rows if r["mode"] == arm]
    if rs:
        print("%-9s %9.4f %9.4f %7.1f" % (arm,
              statistics.mean(r["T_self"] for r in rs),
              statistics.mean(r["T_claimedSource"] for r in rs),
              statistics.mean(r["adopts"] for r in rs)))
# paired measured vs claimed on T_claimedSource(同尺)
print()
sm = {r["seed"]: r["T_claimedSource"] for r in rows if r["mode"] == "claimed"}
for arm in ["measured"]:
    rs = [r for r in rows if r["mode"] == arm]
    ds = [r["T_claimedSource"] - sm[r["seed"]] for r in rs]
    print("measured vs claimed (同 claimedSource 尺): mean Δ %+.4f pos %d/%d" % (
        statistics.mean(ds), sum(1 for d in ds if d > 0), len(ds)))
print("[N5] out_r2_n5 done");
