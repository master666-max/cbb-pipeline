# -*- coding: utf-8 -*-
"""probe_r2_n2_correlated_noise.py — N2: 3危险 + 相关噪声真值(E57 式共享偏差)
引擎看到的'真值'金标 rv_corr = 0.5*rv0 + 0.5*nominal(spur 名义 7+ -> 被共同污染);
终局诚实审计用独立 rv0。检验: 相关噪声是否击穿双门/审计(双门挡不住相关噪声), E80 触发。
"""
import sys, os, json, time, pathlib, statistics, random
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
import world_gen as wg
import engine_gate as eg

OUT = HERE / "out_r2_n2"
OUT.mkdir(parents=True, exist_ok=True)


def corr_world(scene, seed, corr):
    w = wg.build_world(scene, seed)
    for e in w["entries"]:
        e["rv0"] = e["rv"]
        imp = min(1.0, e["importance"] / 7.0) if e["importance"] > 1 else e["importance"]
        e["rv"] = round((1.0 - corr) * e["rv0"] + corr * imp, 4)  # 共享偏差剂量 corr
    return w


def run(w, arm, seed, gens):
    entries = w["entries"]
    rng = random.Random(seed * 331 + 9)
    tA = w.get("trainA") or w.get("train")
    tB = w.get("trainB")
    hold = w["hold"]
    audit = w["audit"]
    ga = w.get("switch_ga") or max(2, int(gens * 2 / 3))

    def tn(g):
        return tA if (tB is None or g < ga) else tB

    def Tf(cfg):  # 独立真值(未被共享偏差污染): 临时把 rv 换回 rv0 再量
        clean = []
        for e in entries:
            ee = dict(e)
            ee["rv"] = ee.get("rv0", ee["rv"])
            clean.append(ee)
        return eg.measure(clean, audit, cfg, gens - 1, "rv")

    if arm == "static":
        c0 = dict(eg.V3_DEFAULT)
        return {"mode": arm, "T0_final": round(Tf(c0), 4), "adopts": 0, "dips": 0, "rollbacks": 0}
    cfg = dict(eg.V3_DEFAULT)
    margin = eg.MARGIN0
    arch = [dict(cfg)]
    adopts = dips = rollbacks = 0
    last = None
    for g in range(gens):
        t = tn(g)
        tr0 = eg.measure(entries, t, cfg, g, "imp")
        ho0 = eg.measure(entries, hold, cfg, g, "rv")   # 晋升门=被污染真值(共享偏差)
        best, bd = None, 0.0
        for _ in range(4):
            c = eg.mutate(rng, cfg)
            dt = eg.measure(entries, t, c, g, "imp") - tr0
            dh = eg.measure(entries, hold, c, g, "rv") - ho0
            if arm == "bare":
                ok = dt > 0
            else:
                ok = dt > margin and dh > margin
            if ok and dt > bd:
                best, bd = c, dt
        if best is not None:
            cfg = dict(best)
            adopts += 1
        if arm != "bare" and arm != "noAudit" and (g % 3 == 0 or g == gens - 1):
            ua = eg.measure(entries, audit, cfg, g, "rv")   # 审计也用污染金标(E57 场景: 无独立通道)
            if last is not None and ua < last[1] - eg.REVERT_THR:
                dips += 1
                if last[0] is not None:
                    cfg = dict(last[0])
                    rollbacks += 1
                margin = max(0.005, margin * 0.7)
            last = (dict(cfg), ua)
    return {"mode": arm, "T0_final": round(Tf(cfg), 4), "adopts": adopts,
            "dips": dips, "rollbacks": rollbacks}


rows = []
for corr in [0.0, 0.5, 1.0]:
    for seed in range(1, 7):
        w = corr_world("composite", seed, corr)
        for arm in ["static", "bare", "gated"]:
            t0 = time.time()
            r = run(w, arm, seed, 30)
            r.update({"seed": seed, "sec": round(time.time() - t0, 2), "corr": corr})
            rows.append(r)

(OUT / "rows_n2.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("%-5s %-8s %10s %9s %7s" % ("corr", "arm", "T0独立真值", "Δvsstatic", "adopt"))
for corr in [0.0, 0.5, 1.0]:
    sm = {r["seed"]: r["T0_final"] for r in rows if r["mode"] == "static" and r["corr"] == corr}
    for arm in ["static", "bare", "gated"]:
        rs = [r for r in rows if r["mode"] == arm and r["corr"] == corr]
        if not rs:
            continue
        T = statistics.mean(r["T0_final"] for r in rs)
        ds = [r["T0_final"] - sm[r["seed"]] for r in rs]
        print("%-5.1f %-8s %10.4f %+9.4f %7.1f  (pos %d/%d)" % (
            corr, arm, T, statistics.mean(ds), statistics.mean(r["adopts"] for r in rs),
            sum(1 for d in ds if d > 0), len(ds)))
print("[N2] out_r2_n2 done");
