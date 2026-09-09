# -*- coding: utf-8 -*-
"""probe_r1_1_switch_reward.py — R1-1: reward-form 切换(E16 同构) → Pareto 保留判别
阶段 A 奖励 = rv 真值 recall(旧好, 需 w_age 低); 阶段 B 奖励 = 新鲜度 recall(最年轻 3 条, 需 w_age 高)。
同一域(所有条目: 旧高名义/新低名义) → 单主线在形式切换后丢弃 A 方向; Pareto(双能力轴 rv 与 fresh)保留。
"""
import sys, os, json, random, time, pathlib, statistics
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import engine_gate as eg
import world_gen as wg

OUT = HERE / "out_r1_1"
OUT.mkdir(parents=True, exist_ok=True)


def build_domain(seed):
    """t0..t3 每主题 12 条: rv 随 age 升(旧好), 名义=rv+eps(旧=高名义); 用于双形式同域"""
    rng = random.Random(seed * 37 + 1)
    entries = []
    for ti, t in enumerate(["t0", "t1", "t2", "t3"]):
        for j in range(12):
            age = rng.uniform(5, 80)
            rv = 0.15 + 0.80 * min(1.0, age / 80.0)
            nominal = min(1.0, rv + 0.05 * rng.random())
            sem = ["x", "y", "z"]
            e = {"id": "e%03d" % len(entries), "topic": t, "rv": round(rv, 4),
                 "importance": round(nominal, 4), "age_days": round(age, 2),
                 "content": " ".join([t] + [t + "a", t + "b"] + [rng.choice(sem), rng.choice(["n1", "n2"])]),
                 "keywords": [t], "links": [], "source_event_id": "genesis",
                 "confidence": 1.0, "validity": {}, "birth_gen": 0,
                 "created_at": wg.ts_days_ago(age), "updated_at": wg.ts_days_ago(age)}
            entries.append(e)
    return entries


def age_d(e):
    return e["age_days"]


def gold_ids(entries, by, k=eg.K_GOLD):
    act = [e for e in entries if not e.get("validity", {}).get("t_invalid")]
    if by == "rv":
        act.sort(key=lambda e: -e["rv"])
    else:  # fresh: 最年轻
        act.sort(key=lambda e: e["age_days"])
    return [e["id"] for e in act[:k]]


def util(entries, cfg, by):
    tot = 0.0
    qs = sorted({e["topic"] for e in entries})
    for t in qs:
        top = eg.retrieve_top(entries, t, cfg)
        ids = [fid for fid, _s, _e in top]
        g = set(gold_ids([e for e in entries if e["topic"] == t], by))
        tot += sum(1 for i in ids if i in g) / min(eg.K_GOLD, eg.K_TOPK)
    return tot / len(qs)


def run(seed, gens, ga, mode):
    entries = build_domain(seed)
    rng = random.Random(seed * 613 + 31)
    cfg = dict(eg.V3_DEFAULT)
    margin = eg.MARGIN0
    archive = [dict(cfg)]
    seen = []
    adopts = 0
    for g in range(gens):
        by = "rv" if g < ga else "fresh"
        u0 = util(entries, cfg, by)
        best, du = None, 0.0
        for _ in range(4):
            c = eg.mutate(rng, cfg)
            if rng.random() < 0.05:
                c["w_age"] = 0.0
            if c["w_age"] <= 1e-9 and rng.random() < 0.25:
                c["w_age"] = rng.uniform(0.02, 0.15)   # 逃逸: 置零后允许重新激活该基因
            duu = util(entries, c, by) - u0
            if duu > margin and duu > du:
                best, du = c, duu
        if best is not None:
            cfg = dict(best)
            adopts += 1
            if mode == "pareto":
                seen.append(dict(best))
    g_f = gens - 1
    if mode == "pareto":
        # 档案 = 历史主线集合(保有所见过的权衡方向); 终局在历史∪当前上取 (rv,fresh) Pareto 前沿
        cands = seen + [dict(cfg)]
        pts = [(c, util(entries, c, "rv"), util(entries, c, "fresh")) for c in cands]
        keep = []
        for i in range(len(pts)):
            dom = False
            for j in range(len(pts)):
                if i != j and pts[j][1] > pts[i][1] and pts[j][2] > pts[i][2]:
                    dom = True
                    break
            if not dom:
                keep.append(pts[i][0])
        pool = keep or [dict(cfg)]
    else:
        pool = [cfg]
    return {"mode": mode, "uA_mainline": round(util(entries, cfg, "rv"), 4),
            "bestA": round(max(util(entries, c, "rv") for c in pool), 4),
            "uF_mainline": round(util(entries, cfg, "fresh"), 4),
            "adopts": adopts, "final_cfg": dict(cfg)}


rows = []
for seed in range(1, 7):
    for mode in ["static", "single", "pareto"]:
        t0 = time.time()
        if mode == "static":
            cfg0 = dict(eg.V3_DEFAULT)
            rows.append({"seed": seed, "mode": mode,
                         "uA_mainline": round(util(build_domain(seed), cfg0, "rv"), 4),
                         "bestA": round(util(build_domain(seed), cfg0, "rv"), 4),
                         "uF_mainline": round(util(build_domain(seed), cfg0, "fresh"), 4),
                         "adopts": 0, "sec": round(time.time() - t0, 2)})
        else:
            r = run(seed, 60, 30, mode)
            r.update({"seed": seed, "sec": round(time.time() - t0, 2)})
            rows.append(r)

(OUT / "rows_r1_1.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("%-8s %10s %9s %9s %7s" % ("mode", "uA_main", "bestA", "uF_main", "adopt"))
for m in ["static", "single", "pareto"]:
    rs = [r for r in rows if r["mode"] == m]
    if rs:
        print("%-8s %10.4f %9.4f %9.4f %7.1f" % (m,
              statistics.mean(r["uA_mainline"] for r in rs),
              statistics.mean(r["bestA"] for r in rs),
              statistics.mean(r["uF_mainline"] for r in rs),
              statistics.mean(r["adopts"] for r in rs)))
# paired bestA single vs pareto
print()
print("配对 bestA(保留 A 能力):")
for seed in range(1, 7):
    s = next(r for r in rows if r["seed"] == seed and r["mode"] == "single")
    p = next(r for r in rows if r["seed"] == seed and r["mode"] == "pareto")
    st = next(r for r in rows if r["seed"] == seed and r["mode"] == "static")
    print("seed %d  single uA=%.3f bestA=%.3f | pareto bestA=%.3f | static uA=%.3f | single遗忘量=%.3f" % (
        seed, s["uA_mainline"], s["bestA"], p["bestA"], st["uA_mainline"], st["uA_mainline"] - s["uA_mainline"]))
print("[R1-1] out_r1_1 done");
