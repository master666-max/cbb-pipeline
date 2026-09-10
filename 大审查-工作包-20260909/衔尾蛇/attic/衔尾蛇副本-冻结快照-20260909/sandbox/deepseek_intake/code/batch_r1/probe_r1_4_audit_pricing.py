# -*- coding: utf-8 -*-
"""probe_r1_4_audit_pricing.py — R1-4: 真值抽样审计成本-检出面(E81 环境定价)
网格: freq {1,2,3,5,10} x sample {4,8} x thr {0.03,0.05}; 4 seeds x 20 代
度量: T_final(真值保护), P_final, dips/rollbacks, 审计代价=每检查点样本量之和(近似注意力单位)。
"""
import sys, os, json, time, pathlib, statistics, random
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import world_gen as wg
import engine_gate as eg

OUT = HERE / "out_r1_4"
OUT.mkdir(parents=True, exist_ok=True)


def run(world, seed, gens, freq, sample, thr):
    entries = list(world["entries"])
    rng = random.Random(seed * 171 + 3)
    train_q = world.get("train") or world.get("trainA")
    hold_q = world["hold"]
    audit_q = world["audit"]
    mainline = dict(eg.E81_CFG0)
    margin = eg.MARGIN0
    adopts = dips = rollbacks = 0
    last = None
    cost = 0
    for g in range(gens):
        p0 = eg.measure_presented(entries, train_q, mainline, g, "imp")
        h0 = eg.measure_presented(entries, hold_q, mainline, g, "imp")
        best, bd = None, 0.0
        for _ in range(4):
            c = eg.mutate(rng, mainline)
            dp = eg.measure_presented(entries, train_q, c, g, "imp") - p0
            dh = eg.measure_presented(entries, hold_q, c, g, "imp") - h0
            if dp > margin and dh > margin and dp > bd:
                best, bd = c, dp
        if best is not None:
            mainline = dict(best)
            adopts += 1
        if g % freq == 0 or g == gens - 1:
            rng.shuffle(audit_q)
            sub = audit_q[:sample]
            ua = eg.measure_presented(entries, sub, mainline, g, "rv")
            cost += sample
            if last is not None and ua < last[1] - thr:
                dips += 1
                if last[0] is not None:
                    mainline = dict(last[0])
                    rollbacks += 1
                margin = max(0.005, margin * 0.7)
            last = (dict(mainline), ua)
    gf = gens - 1
    return {"T": round(eg.measure_presented(entries, audit_q, mainline, gf, "rv"), 4),
            "P": round(eg.measure_presented(entries, audit_q, mainline, gf, "imp"), 4),
            "adopts": adopts, "dips": dips, "rollbacks": rollbacks, "cost": cost}


rows = []
grid = []
for freq in [1, 2, 3, 5, 10]:
    for sample in [4, 8]:
        for thr in [0.03, 0.05]:
            grid.append((freq, sample, thr))
for seed in range(1, 5):
    w = wg.build_world("spur-judge", seed)
    for (freq, sample, thr) in grid:
        t0 = time.time()
        r = run(w, seed, 20, freq, sample, thr)
        r.update({"seed": seed, "freq": freq, "sample": sample, "thr": thr,
                  "sec": round(time.time() - t0, 2)})
        rows.append(r)

(OUT / "rows_r1_4.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
# static reference per seed
refs = {}
for seed in range(1, 5):
    w = wg.build_world("spur-judge", seed)
    refs[seed] = eg.measure_presented(w["entries"], w["audit"], dict(eg.E81_CFG0), 19, "rv")
print("%-4s %-5s %-5s %8s %8s %6s %6s %6s" % ("freq","smp","thr","T","T-Tref","dips","roll","cost"))
summ = {}
for (freq, sample, thr) in grid:
    rs = [r for r in rows if (r["freq"], r["sample"], r["thr"]) == (freq, sample, thr)]
    T = statistics.mean(r["T"] for r in rs)
    Ts = statistics.mean([r["T"] - refs[r["seed"]] for r in rs])
    cost = statistics.mean(r["cost"] for r in rs)
    dips = statistics.mean(r["dips"] for r in rs)
    summ[(freq, sample, thr)] = (round(T, 3), round(Ts, 3), int(cost), round(dips, 1), round(statistics.mean(r["rollbacks"] for r in rs), 1))
    print("%-4d %-5d %-5.2f %8.3f %8.3f %6.1f %6.1f %6d" % (freq, sample, thr, T, Ts, dips, summ[(freq, sample, thr)][4], cost))
print()
print("静态参考 T_ref(seed均值)=", round(statistics.mean(refs.values()), 4))
print("[R1-4] out_r1_4 done");
