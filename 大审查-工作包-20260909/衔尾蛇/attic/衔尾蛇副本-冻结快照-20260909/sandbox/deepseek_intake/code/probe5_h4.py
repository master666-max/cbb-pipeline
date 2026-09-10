# -*- coding: utf-8 -*-
"""probe5_h4.py — H4: importance 实测化(EV-14/E32 同构)
用法: py -3 probe5_h4.py"""
import sys, os, json, random, statistics, pathlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import world_gen as wg
import engine_gate as eg

OUT = HERE / "out_v5_h4"
OUT.mkdir(exist_ok=True)

SCENES = ["clean", "spur-surface"]
SEEDS = list(range(1, 6))
SESSIONS = 900


def sessions_for(world, seed, n=SESSIONS):
    """代理使用轨迹: 随机主题查询 -> 检索 top-5(shown); 采纳=shown 且在该主题真值金标(rv top3)内"""
    rng = random.Random(seed * 1009 + 5)
    entries = wg.actives_at(world["entries"], 999)   # 全量活跃
    topics = sorted({e["topic"] for e in entries})
    shown_cnt = {e["id"]: 0 for e in entries}
    adopt_cnt = {e["id"]: 0 for e in entries}
    sem = wg.SEM_TOK
    cfg_pool = [dict(eg.V3_DEFAULT),
                dict(eg.V3_DEFAULT, w_age=0.02),
                dict(eg.V3_DEFAULT, w_age=0.0, w_imp=2.0)]
    for _ in range(n):
        cfg = rng.choice(cfg_pool)
        t = rng.choice(topics)
        roll = rng.random()
        if roll < 0.4:
            qt = t                                   # 主题查询(规范)
        elif roll < 0.7:
            qt = t + " " + rng.choice(sem[t])        # 主题+语义词
        else:
            qt = t + " " + rng.choice(wg.NOISE)      # 主题+上下文噪声词(任意片段)
        top = eg.retrieve_top(entries, qt, cfg, eg.K_TOPK)
        shown = [fid for fid, _s, _e in top]
        gold = set(eg.gold_ids_at(entries, {"topic": t}, 999, "rv"))
        for fid in shown:
            shown_cnt[fid] += 1
            if fid in gold:
                adopt_cnt[fid] += 1
    measured = {}
    for e in entries:
        s = shown_cnt[e["id"]]
        measured[e["id"]] = (adopt_cnt[e["id"]] / s) if s > 0 else 0.0   # 悲观初始化(EV-14/E46)
    return entries, shown_cnt, measured


def topn_quality(entries, ranking_ids, n=10):
    byid = {e["id"]: e for e in entries}
    ids = ranking_ids[:n]
    ids = [i for i in ids if i in byid][:n]
    return statistics.mean(byid[i]["rv"] for i in ids) if ids else 0.0


def util_with_imp(entries, qs, imp_map):
    """用给定 importance 源跑检索 util(真值金标)"""
    mod = []
    for e in entries:
        ee = dict(e)
        ee["importance"] = imp_map[e["id"]]
        mod.append(ee)
    cfg = dict(eg.V3_DEFAULT)
    return eg.measure(mod, qs, cfg, 999, "rv")


rows = []
for sc in SCENES:
    print("===== scene", sc, "=====")
    for seed in SEEDS:
        world = wg.build_world(sc, seed)
        entries, shown_cnt, measured = sessions_for(world, seed)
        # 公平比较: 两个排序都在"已观测(shown>=1)"条目池上取 top-10(消除覆盖混杂)
        obs = [e for e in entries if shown_cnt[e["id"]] > 0]
        claimed_ids_l = [e["id"] for e in sorted(obs, key=lambda e: (-e["importance"], e["id"]))]
        meas_ids_l = [e["id"] for e in sorted(obs, key=lambda e: (-measured[e["id"]], e["id"]))]
        Qc = topn_quality(entries, claimed_ids_l)
        Qm = topn_quality(entries, meas_ids_l)
        util_c = util_with_imp(entries, world["audit"], {e["id"]: e["importance"] for e in entries})
        util_m = util_with_imp(entries, world["audit"], measured)
        cov = len(obs) / len(entries)
        rows.append({"scene": sc, "seed": seed, "Q_claimed": round(Qc, 4),
                     "Q_measured": round(Qm, 4),
                     "ratio": round(Qm / Qc, 4) if Qc else None,
                     "util_claimed": round(util_c, 4), "util_measured": round(util_m, 4),
                     "coverage_shown": round(cov, 3)})
        print("seed %d  Q_claimed=%.3f Q_measured=%.3f ratio=%.2f | util_claimed=%.3f util_measured=%.3f coverage=%.2f" % (
            seed, Qc, Qm, (Qm / Qc) if Qc else float("nan"), util_c, util_m, cov))

(OUT / "rows_h4.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print()
print("按场景汇总(5 seeds):")
for sc in SCENES:
    rs = [r for r in rows if r["scene"] == sc]
    ratios = [r["ratio"] for r in rs if r["ratio"]]
    print("  %-12s Q_claimed=%.4f Q_measured=%.4f  ratio_mean=%.3f | util_claimed=%.4f util_measured=%.4f (Δ=%.4f) | coverage=%.3f" % (
        sc,
        statistics.mean(r["Q_claimed"] for r in rs),
        statistics.mean(r["Q_measured"] for r in rs),
        statistics.mean(ratios),
        statistics.mean(r["util_claimed"] for r in rs),
        statistics.mean(r["util_measured"] for r in rs),
        statistics.mean(r["util_measured"] - r["util_claimed"] for r in rs),
        statistics.mean(r["coverage_shown"] for r in rs)))
print("[probe5] out_v5_h4 done");
