# -*- coding: utf-8 -*-
"""probe_r5_d8_selfref_nf.py — D8: 自指受控实验(允许系统改展示 + 负强化, 替代定期审计)
E81 spur-judge; 臂:
  audit3: 每 3 代真值抽样回退(现状 R1-4 推荐);
  nf(负强化): 无定期审计, 每代用少量样本算 gap=P-T 的 EWMA; 当 gap 突破阈值且该代采纳提升 w_show -> 撤销该采纳并把 w_show 拉回(惩罚) —— '改展示必须付出代价'。
度量: 终局真值 T、回退/惩罚次数、审计成本、w_show 抑制。
"""
import sys, os, json, time, pathlib, statistics, random
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
import world_gen as wg
import engine_gate as eg

OUT = HERE / "out_r5_d8"
OUT.mkdir(parents=True, exist_ok=True)


def shown(e):
    return 1 if (" SHOW" in e.get("content", "") or str(e.get("content", "")).endswith("SHOW")) else 0


def jgold(entries, q, k=3):
    pool = [e for e in entries if e["topic"] == q["topic"] and not e.get("validity", {}).get("t_invalid")]
    pool.sort(key=lambda e: -e["importance"] * (1 + shown(e)))
    return {e["id"] for e in pool[:k]}


def ptop(entries, qtext, cfg, k=eg.K_TOPK):
    scored = {}
    for e in entries:
        if e.get("validity", {}).get("t_invalid"):
            continue
        qw = qtext.split()
        kw = sum(1 for x in qw if x in " ".join(e.get("keywords", [])))
        ch = sum(1 for x in qw if x in e["content"])
        if kw:
            ch = max(ch, 1)
        s = (kw * cfg["w_kw"] + ch * cfg["w_content"] + e["importance"] * cfg["w_imp"]
             - eg.age_days_of(e.get("created_at", "")) * cfg["w_age"])
        if shown(e):
            s += cfg.get("w_show", 1.0)
        scored[e["id"]] = s
    return sorted(scored, key=lambda i: -scored[i])[:k]


def both(entries, qs, cfg):
    P = T = 0.0
    for q in qs:
        ids = ptop(entries, q["topic"], cfg)
        gP = jgold(entries, q)
        pool = [e for e in entries if e["topic"] == q["topic"] and not e.get("validity", {}).get("t_invalid")]
        pool.sort(key=lambda e: -e["rv"])
        gT = {e["id"] for e in pool[:3]}
        P += sum(1 for i in ids if i in gP) / 3.0
        T += sum(1 for i in ids if i in gT) / 3.0
    return P / len(qs), T / len(qs)


def run(w, arm, seed, gens):
    entries = w["entries"]
    rng = random.Random(seed * 23 + 5)
    trq = w.get("train") or w.get("trainA")
    holdq = w["hold"]
    audq = w["audit"]
    cfg = dict(eg.E81_CFG0)
    margin = eg.MARGIN0
    adopts = roll = 0
    cost = 0
    ewma_gap = 0.0
    for g in range(gens):
        # 负强化: 每代 6 样本 gap EWMA
        if arm == "nf":
            cost += 6
            rng.shuffle(audq)
            P, T = both(entries, audq[:6], cfg)
            gap = P - T
            ewma_gap = 0.8 * ewma_gap + 0.2 * gap
            if ewma_gap > 0.35:
                cfg["w_show"] = 1.0        # 惩罚: 拉回展示权重
                roll += 1
                ewma_gap = 0.0
        elif g % 3 == 0:
            cost += len(audq)
            P, T = both(entries, audq, cfg)
            if g > 2 and T < 0.40 and cfg.get("w_show", 1) > 1.0:
                cfg["w_show"] = 1.0
                roll += 1
        p0, _ = both(entries, trq, cfg)
        h0, _ = both(entries, holdq, cfg)
        best, bd = None, 0.0
        for _ in range(4):
            c = eg.mutate(rng, cfg)
            dp, _ = both(entries, trq, c)
            dh, _ = both(entries, holdq, c)
            if dp - p0 > margin and dh - h0 > margin and dp - p0 > bd:
                best, bd = c, dp - p0
        if best is not None:
            if arm == "nf" and best.get("w_show", 1.0) > cfg.get("w_show", 1.0) + 0.01 and ewma_gap > 0.3:
                pass   # 该采纳会放大 gap, 先不采纳(负强化在采纳前)
            else:
                cfg = dict(best)
                adopts += 1
    P, T = both(entries, audq, cfg)
    return {"mode": arm, "T": round(T, 3), "P": round(P, 3), "roll_punish": roll,
            "cost": cost, "adopts": adopts, "w_show_end": round(cfg.get("w_show", 1.0), 2)}


rows = []
for seed in range(1, 7):
    w = wg.build_world("spur-judge", seed)
    for arm in ["audit3", "nf"]:
        r = run(w, arm, seed, 24)
        r.update({"seed": seed})
        rows.append(r)
(OUT / "rows_d8.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("%-7s %8s %8s %10s %7s %7s" % ("arm", "T_truth", "P", "punish/roll", "cost", "wShow_end"))
for arm in ["audit3", "nf"]:
    rs = [r for r in rows if r["mode"] == arm]
    print("%-7s %8.3f %8.3f %10.1f %7.1f %7.2f" % (
        arm, statistics.mean(r["T"] for r in rs), statistics.mean(r["P"] for r in rs),
        statistics.mean(r["roll_punish"] for r in rs), statistics.mean(r["cost"] for r in rs),
        statistics.mean(r["w_show_end"] for r in rs)))
print("[D8] out_r5_d8 done");
