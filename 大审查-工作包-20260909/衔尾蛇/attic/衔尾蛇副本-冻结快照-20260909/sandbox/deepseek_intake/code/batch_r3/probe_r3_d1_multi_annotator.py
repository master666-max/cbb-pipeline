# -*- coding: utf-8 -*-
"""probe_r3_d1_multi_annotator.py — D1: 异质标注者 / 多源分歧投票(对抗 E57 共享偏差 & 同源失效)
世界: composite corr=1.0(引擎可见真值=纯名义, 单源必然被 spur 带偏)。
三异质源: S1=judge 名义(imp, spur 爱), S2=内容规则(关键词命中密度=内容质量代理, 与 rv0 部分共享),
S3=使用实测(adopted/shown, 独立于声称)。
源输出=每查询 top3 候选 id 集合; 分歧投票: 候选 util 用"至少 2 源一致 + 真值抽样"的同意金标。
臂: 单源(仅 S1, =E57 同化基线) vs 多源一致(S1∩(S2∪S3) 或 2/3 多数) vs 多源+真值抽样。
终局诚实 T0=rv0。
"""
import sys, os, json, time, pathlib, statistics, random
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
import world_gen as wg
import engine_gate as eg

OUT = HERE / "out_r3_d1"
OUT.mkdir(parents=True, exist_ok=True)


def build(seed, corr=1.0):
    w = wg.build_world("composite", seed)
    for e in w["entries"]:
        e["rv0"] = e["rv"]
        impn = min(1.0, e["importance"] / 7.0) if e["importance"] > 1 else e["importance"]
        e["rv"] = round((1 - corr) * e["rv0"] + corr * impn, 4)  # 引擎可见真值(共享偏差 1.0)
    return w


def kw_density(e):
    c = e.get("content", "")
    kw = e.get("keywords", [])
    return sum(1 for k in kw if k in c) / max(1, len(c.split()))


def s2_rank(entries, q, k=3):
    pool = [e for e in entries if e["topic"] == q["topic"] and not e.get("validity", {}).get("t_invalid")]
    pool.sort(key=lambda e: -(kw_density(e) + e["rv0"]))   # 内容规则: 密度+独立真值代理
    return [e["id"] for e in pool[:k]]


def s1_rank(entries, q, k=3):
    pool = [e for e in entries if e["topic"] == q["topic"] and not e.get("validity", {}).get("t_invalid")]
    pool.sort(key=lambda e: -e["importance"])              # judge 声称(被 spur 污染)
    return [e["id"] for e in pool[:k]]


def s3_rank(entries, q, cfg, rng, k=3):
    """使用实测: 基于当轮检索轨迹的采纳率(悲观0); 用缓存近似(重算慢, 简化为 rv0 代理+噪声)"""
    pool = [e for e in entries if e["topic"] == q["topic"] and not e.get("validity", {}).get("t_invalid")]
    pool.sort(key=lambda e: -(e.get("meas", 0.0)))
    return [e["id"] for e in pool[:k]]


def agreed_gold(entries, q, cfg, mode, rng, k=3):
    a = set(s1_rank(entries, q, k))
    if mode == "single":
        return sorted(a)
    b = set(s2_rank(entries, q, k))
    c = set(s3_rank(entries, q, cfg, rng, k))
    if mode == "consensus2of3":
        vote = {}
        for i in list(a) + list(b) + list(c):
            vote[i] = vote.get(i, 0) + 1
        return sorted([i for i, v in vote.items() if v >= 2])[:k]
    if mode == "truthsampled":
        # 独立真值抽样(小样本, 每代重抽不同主题)
        return sorted([i for i in a if i in b] + [i for i in c])[:k]
    return sorted(a)


def util_agree(entries, qs, cfg, mode, rng, gen):
    tot = 0.0
    for q in qs:
        top = eg.retrieve_top(entries, q["topic"], cfg)
        ids = [fid for fid, _s, _e in top]
        g = set(agreed_gold(entries, q, cfg, mode, rng))
        tot += sum(1 for i in ids if i in g) / min(eg.K_GOLD, eg.K_TOPK)
    return tot / len(qs)


def T0(entries, qs, cfg, gen):
    clean = [dict(e, rv=e["rv0"]) for e in entries]
    return eg.measure(clean, qs, cfg, gen, "rv")


def run(w, arm, seed, gens):
    entries = w["entries"]
    # 使用实测: 每代更新 meas 字段(当前检索下 adopted/shown)
    for e in entries:
        e["meas"] = 0.0
    rng = random.Random(seed * 5 + 1)
    trq = w.get("train") or w.get("trainA")
    holdq = w["hold"]
    audq = w["audit"]
    cfg = dict(eg.V3_DEFAULT)
    margin = eg.MARGIN0
    adopts = 0
    for g in range(gens):
        # 更新 S3 实测
        if arm.startswith("multi") or arm == "consensus":
            for e in entries:
                e["meas"] = e["rv0"] * 0.7 + 0.3 * (0.5 if e["importance"] > 1 else 0.2) * rng.random()
        u0 = util_agree(entries, trq, cfg, arm, rng, g)
        h0 = util_agree(entries, holdq, cfg, arm, rng, g)
        best, bd = None, 0.0
        for _ in range(4):
            c = eg.mutate(rng, cfg)
            du = util_agree(entries, trq, c, arm, rng, g) - u0
            dh = util_agree(entries, holdq, c, arm, rng, g) - h0
            if du > margin and dh > margin and du > bd:
                best, bd = c, du
        if best is not None:
            cfg = dict(best)
            adopts += 1
    return {"mode": arm, "T0": round(T0(entries, audq, cfg, gens - 1), 4), "adopts": adopts, "cfg": cfg}


rows = []
for seed in range(1, 7):
    w = build(seed, 1.0)
    for arm in ["single", "consensus", "truthsampled"]:
        t0 = time.time()
        r = run(w, arm, seed, 24)
        r.update({"seed": seed, "sec": round(time.time() - t0, 2)})
        rows.append(r)
    # static
    rows.append({"mode": "static", "T0": round(T0(w["entries"], w["audit"], dict(eg.V3_DEFAULT), 23), 4),
                 "adopts": 0, "seed": seed, "sec": 0.0})

(OUT / "rows_d1.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("%-13s %9s %8s" % ("arm", "T0(独立真值)", "adopt"))
sm = {r["seed"]: r["T0"] for r in rows if r["mode"] == "static"}
for arm in ["static", "single", "consensus", "truthsampled"]:
    rs = [r for r in rows if r["mode"] == arm]
    if rs:
        T = statistics.mean(r["T0"] for r in rs)
        ds = [r["T0"] - sm[r["seed"]] for r in rs]
        print("%-13s %9.4f %8.1f  (Δ %+.4f, pos %d/%d)" % (
            arm, T, statistics.mean(r["adopts"] for r in rs),
            statistics.mean(ds), sum(1 for d in ds if d > 0), len(ds)))
print("[D1] out_r3_d1 done");
