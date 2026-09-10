# -*- coding: utf-8 -*-
"""probe_r2_n4_anchor_refresh.py — N4/E69: judge 漂移 + 锚定集刷新协议
E14 型: judge 对 SHOW 的信任 wJ 每代向系统输出漂移(wJ←(1-α)wJ+α·w_show_current);
锚定审计: 固定 wJ0=1 的排序 vs 当前 wJ 排序一致性<0.85 -> 检出漂移。
臂: noAudit(漂移自由跑) / freeze(检出即停采纳, 不重置) / reanchor(检出即重置 wJ=1 并继续, E69 解药)。
真值=rv(与 SHOW 无关)。
"""
import sys, os, json, time, pathlib, statistics, random
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
import world_gen as wg
import engine_gate as eg

OUT = HERE / "out_r2_n4"
OUT.mkdir(parents=True, exist_ok=True)

ALPHA = 0.05


def shown(e):
    return 1 if (" SHOW" in e.get("content", "") or str(e.get("content", "")).endswith("SHOW")) else 0


def judge_gold(entries, q, gen, wJ, k=eg.K_GOLD):
    pool = [e for e in entries if e["topic"] == q["topic"] and not e.get("validity", {}).get("t_invalid")]
    pool.sort(key=lambda e: -(e["importance"] * (1 + wJ * shown(e))))
    return [e["id"] for e in pool[:k]]


def present_top(entries, qtext, cfg, k=eg.K_TOPK):
    """呈交 top-K(带 w_show 对 SHOW 的加成, 引擎可演化)"""
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
             + e.get("importance", 0.0) * cfg["w_imp"]
             - eg.age_days_of(e.get("created_at", "")) * cfg["w_age"])
        if shown(e):
            s += cfg.get("w_show", 1.0)
        scored[e["id"]] = s
    return sorted(scored, key=lambda i: -scored[i])[:k]


def jutil(entries, qs, cfg, gen, wJ):
    tot = 0.0
    for q in qs:
        ids = present_top(entries, q["topic"], cfg)
        g = set(judge_gold(entries, q, gen, wJ))
        tot += sum(1 for i in ids if i in g) / min(eg.K_GOLD, eg.K_TOPK)
    return tot / len(qs)


def tutil(entries, qs, cfg, gen):
    return eg.measure(entries, qs, cfg, gen, "rv")


def run(w, arm, seed, gens):
    entries = w["entries"]
    rng = random.Random(seed * 41 + 3)
    train_q = w.get("train") or w.get("trainA")
    hold_q = w["hold"]
    audit_q = w["audit"]
    wJ = 1.0
    cfg = dict(eg.E81_CFG0)
    margin = eg.MARGIN0
    adopts = detections = resets = 0
    frozen_until = -1
    traj = []
    for g in range(gens):
        # judge 漂移: 向系统当前展示偏好靠拢
        wJ = min(5.0, (1 - ALPHA) * wJ + ALPHA * max(1.0, cfg.get("w_show", 1.0)))
        if arm == "noAudit":
            pass
        else:
            # 锚定审计: 一致性 = 当前 wJ 排序 与 锚定(wJ0=1)排序 在审计查询上的同序率
            agree = 0.0
            nq = 0
            for q in audit_q:
                cur = set(judge_gold(entries, q, g, wJ, 3))
                anc = set(judge_gold(entries, q, g, 1.0, 3))
                agree += len(cur & anc) / 3.0
                nq += 1
            acc = agree / nq if nq else 1.0
            if acc < 0.85:
                detections += 1
                if arm == "reanchor":
                    wJ = 1.0
                    resets += 1
                elif arm == "freeze":
                    frozen_until = g + 10
        if g < frozen_until:
            continue
        # 演化(judge 通道 train/hold)
        p0 = jutil(entries, train_q, cfg, g, wJ)
        h0 = jutil(entries, hold_q, cfg, g, wJ)
        best, bd = None, 0.0
        for _ in range(4):
            c = eg.mutate(rng, cfg)
            dp = jutil(entries, train_q, c, g, wJ) - p0
            dh = jutil(entries, hold_q, c, g, wJ) - h0
            if dp > margin and dh > margin and dp > bd:
                best, bd = c, dp
        if best is not None:
            cfg = dict(best)
            adopts += 1
        traj.append((g, round(wJ, 3), round(tutil(entries, audit_q, cfg, g), 3)))
    return {"mode": arm, "T_final": round(tutil(entries, audit_q, cfg, gens - 1), 4),
            "P_final": round(jutil(entries, audit_q, cfg, gens - 1, wJ), 4),
            "wJ_end": round(wJ, 3), "adopts": adopts,
            "detections": detections, "resets": resets, "traj": traj[:4] + traj[-2:]}


rows = []
for seed in range(1, 7):
    w = wg.build_world("spur-judge", seed)
    for arm in ["static", "noAudit", "freeze", "reanchor"]:
        t0 = time.time()
        if arm == "static":
            cfg0 = dict(eg.E81_CFG0)
            r = {"mode": arm, "T_final": round(tutil(w["entries"], w["audit"], cfg0, 39), 4),
                 "P_final": round(jutil(w["entries"], w["audit"], cfg0, 39, 1.0), 4),
                 "wJ_end": 1.0, "adopts": 0, "detections": 0, "resets": 0}
        else:
            r = run(w, arm, seed, 40)
        r.update({"seed": seed, "sec": round(time.time() - t0, 2)})
        rows.append(r)

(OUT / "rows_n4.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("%-9s %9s %9s %7s %8s %7s %7s" % ("arm", "T_truth", "P_judge", "adopt", "wJ_end", "detect", "reset"))
for arm in ["static", "noAudit", "freeze", "reanchor"]:
    rs = [r for r in rows if r["mode"] == arm]
    if rs:
        print("%-9s %9.4f %9.4f %7.1f %8.3f %7.1f %7.1f" % (
            arm, statistics.mean(r["T_final"] for r in rs),
            statistics.mean(r["P_final"] for r in rs),
            statistics.mean(r["adopts"] for r in rs),
            statistics.mean(r["wJ_end"] for r in rs),
            statistics.mean(r["detections"] for r in rs),
            statistics.mean(r["resets"] for r in rs)))
print("[N4] out_r2_n4 done");
