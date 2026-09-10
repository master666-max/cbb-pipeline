# -*- coding: utf-8 -*-
"""probe_r3_d2_stat_immunity.py — D2: 统计免疫(不枚举规则的离群检测) + gap 统计抓 E81 型未知失败
正常基线: clean 引擎 runs 的多代指标分布(u_train,u_hold,u_audit,adopts,margin,gap=P-T)。
监测器: 每代 z²(马氏单变量聚合, 指标独立 z) 超阈 -> 告警(不预定义失败规则)。
注入失败类: F1 已知(自报通胀: u_train 悄悄 +0.2) F2 未知A(审计 util 骤降 -0.15 一瞬) F3 未知B(E81 展示漂移: w_show↑ 而 T 不变, 单看 T 无信号 -> 用 gap 统计) F4 干净(无失败, 测误报)。
度量: 检出率/误报率; 观察 gap 统计对 F3 的必要性。
"""
import sys, os, json, time, pathlib, statistics, random, math
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
import world_gen as wg
import engine_gate as eg

OUT = HERE / "out_r3_d2"
OUT.mkdir(parents=True, exist_ok=True)


def run_gen_metrics(seed, gens=12, inject=None):
    """返回每代指标 dict 列表; inject=(kind, gen)"""
    w = wg.build_world("clean", seed)
    rows = eg.run_arm(w, "gated", seed, gens)
    traj = rows["traj"]
    out = []
    for g in range(gens):
        ua = traj[g]["u_audit"] if g < len(traj) else 0.0
        ut = traj[g]["u_train"] if g < len(traj) else 0.0
        uh = traj[g]["u_hold"] if g < len(traj) else 0.0
        gap = ut - ua
        m = {"gen": g, "u_train": ut, "u_hold": uh, "u_audit": ua,
             "adopts": traj[g]["adopts"], "margin": traj[g]["margin"], "gap": gap}
        if inject and inject[1] == g:
            kind = inject[0]
            if kind == "F1":
                m["u_train"] += 0.2
            elif kind == "F2":
                m["u_audit"] -= 0.15
            elif kind == "F3":
                m["gap"] += 0.25   # 展示漂移: 自报涨真值不变(仅 gap 有信号)
        out.append(m)
    return out


def fit_baseline(seeds=6, gens=12):
    seqs = [run_gen_metrics(s, gens) for s in range(1, seeds + 1)]
    keys = ["u_train", "u_hold", "u_audit", "adopts", "margin", "gap"]
    stat = {}
    for k in keys:
        per = {g: [seq[g][k] for seq in seqs] for g in range(gens)}
        stat[k] = {g: (statistics.mean(per[g]), statistics.pstdev(per[g]) or 1e-6) for g in range(gens)}
    return stat, keys


def detect(seq, stat, keys, thr=2.5):
    alerts = []
    for g, m in enumerate(seq):
        zs = {}
        for k in keys:
            mu, sd = stat[k][g]
            zs[k] = abs(m[k] - mu) / sd
        zmax = max(zs.values())
        if zmax > thr:
            alerts.append((g, zmax, max(zs, key=zs.get)))
    return alerts


GENS = 12
stat, keys = fit_baseline(seeds=6, gens=GENS)
trials = {}
for kind in ["clean", "F1", "F2", "F3"]:
    hits = 0
    fp = 0
    tot_inject = 0
    for seed in range(1, 9):
        inject = None if kind == "clean" else (kind, 6)
        seq = run_gen_metrics(seed, GENS, inject)
        al = detect(seq, stat, keys)
        if kind == "clean":
            fp += 1 if al else 0
        else:
            hit = any(g == 6 for g, _, _ in al)
            hits += 1 if hit else 0
            tot_inject += 1
    trials[kind] = {"detected": hits, "n": tot_inject, "false_positive": fp}
print("基线: 每代 6 指标独立 z>%.1f 告警" % 2.5)
print("%-6s %12s %10s %12s" % ("class", "检出/注入", "或误报/8", "说明"))
for kind in ["clean", "F1", "F2", "F3"]:
    t = trials[kind]
    note = {"clean": "干净(无失败)", "F1": "自报通胀(已知)", "F2": "审计骤降(未知A)", "F3": "展示漂移,仅gap有信号(未知B)"}[kind]
    print("%-6s %5d/%-4d %10s %14s" % (kind, t["detected"], t["n"], t["false_positive"], note))
# gap-only detector for F3
print()
print("仅 gap 统计(>2.5z)对 F3 的检出:")
h = 0
for seed in range(1, 9):
    seq = run_gen_metrics(seed, GENS, ("F3", 6))
    al = detect(seq, stat, ["gap"])
    h += 1 if any(g == 6 for g, _, _ in al) else 0
print("F3 检出 %d/8；干净误报 %d/8" % (h, sum(1 for s in range(1, 9) if detect(run_gen_metrics(s, GENS, None), stat, ["gap"]) and False) or 0))
# clean FP for gap-only
fp = sum(1 for s in range(1, 9) if detect(run_gen_metrics(s, GENS), stat, ["gap"]))
print("(gap-only 干净误报 %d/8)" % fp)
json.dump({"stat_keys": keys, "trials": trials}, open(OUT / "d2_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("[D2] out_r3_d2 done");
