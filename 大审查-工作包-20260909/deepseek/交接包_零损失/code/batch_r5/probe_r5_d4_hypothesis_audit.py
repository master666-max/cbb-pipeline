# -*- coding: utf-8 -*-
"""probe_r5_d4_hypothesis_audit.py — D4: 声明式假设审计(审'系统相信什么'而非'结果')
E81 spur-judge: 引擎演化 w_show(展示漂移)。两种审计:
  result-audit: 每 3 代真值 util 跌 >thr 回退(现状);
  hypothesis-audit: 每代用少量样本(k=6)测 '引擎自报 quality(imp) 与 真值(rv) 的秩相关 τ', τ<0.5 即警(漂移先于效用损失发生)。
度量: 检出代数(注入漂移后)、回退数、终局真值 T、审计成本(每代样本)。种子内固定漂移注入时刻(人为把 w_show 涨到 3 并允许剥削)。
"""
import sys, os, json, time, pathlib, statistics, random
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
import world_gen as wg
import engine_gate as eg

OUT = HERE / "out_r5_d4"
OUT.mkdir(parents=True, exist_ok=True)


def ktau(xs, ys):
    n = len(xs)
    c = d = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx, dy = xs[i] - xs[j], ys[i] - ys[j]
            if dx * dy > 0:
                c += 1
            elif dx * dy < 0:
                d += 1
    den = c + d or 1
    return (c - d) / den


def shown(e):
    return 1 if (" SHOW" in e.get("content", "") or str(e.get("content", "")).endswith("SHOW")) else 0


def judge_gold(entries, q, wJ, k=3):
    pool = [e for e in entries if e["topic"] == q["topic"] and not e.get("validity", {}).get("t_invalid")]
    pool.sort(key=lambda e: -(e["importance"] * (1 + wJ * shown(e))))
    return [e["id"] for e in pool[:k]]


def present_top(entries, qtext, cfg, k=eg.K_TOPK):
    scored = {}
    for e in entries:
        if e.get("validity", {}).get("t_invalid"):
            continue
        qw = qtext.split()
        kw = sum(1 for x in qw if x in " ".join(e.get("keywords", [])))
        ch = sum(1 for x in qw if x in e["content"])
        if kw:
            ch = max(ch, 1)
        s = (kw * cfg["w_kw"] + ch * cfg["w_content"]
             + e.get("importance", 0) * cfg["w_imp"]
             - eg.age_days_of(e.get("created_at", "")) * cfg["w_age"])
        if shown(e):
            s += cfg.get("w_show", 1.0)
        scored[e["id"]] = s
    return sorted(scored, key=lambda i: -scored[i])[:k]


def util_both(entries, qs, cfg, wJ):
    pt = t = 0.0
    for q in qs:
        ids = present_top(entries, q["topic"], cfg)
        gP = set(judge_gold(entries, q, wJ))
        pool = [e for e in entries if e["topic"] == q["topic"] and not e.get("validity", {}).get("t_invalid")]
        pool.sort(key=lambda e: -e["rv"])
        gT = set(e["id"] for e in pool[:3])
        pt += sum(1 for i in ids if i in gP) / 3.0
        t += sum(1 for i in ids if i in gT) / 3.0
    return pt / len(qs), t / len(qs)


def run(w, arm, seed, gens, drift_gen=12, thr=0.5):
    entries = w["entries"]
    rng = random.Random(seed * 17 + 3)
    trq = w.get("train") or w.get("trainA")
    holdq = w["hold"]
    audq = w["audit"]
    wJ = 1.0
    cfg = dict(eg.E81_CFG0)
    margin = eg.MARGIN0
    adopts = det = roll = 0
    sample_cost = 0
    detect_gen = None
    for g in range(gens):
        if g == drift_gen:
            wJ = 3.0   # 漂移注入(judge 突然更信 SHOW)
        # 假设审计(只读 belief 与 truth 的相关, 每代少量样本)
        if arm == "hypothesis":
            rng.shuffle(audq)
            sub = audq[:6]
            sample_cost += 6
            xs, ys = [], []
            for q in sub:
                pool = [e for e in entries if e["topic"] == q["topic"] and not e.get("validity", {}).get("t_invalid")]
                for e in pool[:8]:
                    xs.append(e["importance"] * (1 + wJ * shown(e)))
                    ys.append(e["rv"])
            if len(xs) > 3 and ktau(xs, ys) < thr:
                det += 1
                if detect_gen is None:
                    detect_gen = g
                wJ = 1.0  # 冻结/重锚 belief
        if arm == "result":
            if g % 3 == 0:
                sample_cost += len(audq)
                _, t = util_both(entries, audq, cfg, wJ)
                if g >= drift_gen and detect_gen is None and t < 0.42:
                    det += 1
                    detect_gen = g
                    wJ = 1.0
        p0, _ = util_both(entries, trq, cfg, wJ)
        h0, _ = util_both(entries, holdq, cfg, wJ)
        best, bd = None, 0.0
        for _ in range(4):
            c = eg.mutate(rng, cfg)
            dp, _ = util_both(entries, trq, c, wJ)
            dh, _ = util_both(entries, holdq, c, wJ)
            if dp - p0 > margin and dh - h0 > margin and dp - p0 > bd:
                best, bd = c, dp - p0
        if best is not None:
            cfg = dict(best)
            adopts += 1
    _, T = util_both(entries, audq, cfg, wJ)
    return {"mode": arm, "T": round(T, 3), "detect_gen": detect_gen, "dets": det,
            "cost": sample_cost, "adopts": adopts, "wJ_end": round(wJ, 2)}


rows = []
for seed in range(1, 7):
    w = wg.build_world("spur-judge", seed)
    for arm in ["result", "hypothesis"]:
        r = run(w, arm, seed, 24)
        r.update({"seed": seed})
        rows.append(r)
(OUT / "rows_d4.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("%-11s %8s %9s %8s %8s" % ("arm", "T_truth", "detect_gen", "cost", "wJ_end"))
for arm in ["result", "hypothesis"]:
    rs = [r for r in rows if r["mode"] == arm]
    dg = [r["detect_gen"] for r in rs if r["detect_gen"] is not None]
    print("%-11s %8.3f %9s %8.1f %8.2f  (检出 %d/6, 平均代数 %s)" % (
        arm, statistics.mean(r["T"] for r in rs),
        (round(statistics.mean(dg), 1) if dg else "-"),
        statistics.mean(r["cost"] for r in rs),
        statistics.mean(r["wJ_end"] for r in rs),
        len(dg), (round(statistics.mean(dg), 1) if dg else "-")))
print("[D4] out_r5_d4 done");
