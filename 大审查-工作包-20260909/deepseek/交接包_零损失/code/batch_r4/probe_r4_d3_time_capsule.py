# -*- coding: utf-8 -*-
"""probe_r4_d3_time_capsule.py — D3: 记忆时间胶囊(attic 可查询档案 / 回忆视角)
世界: stale(t0/t1 半数条目 EVENT_GEN=6 失效+纠错); 历史测验: 重访 gen3(事件前)有效的事实。
模式: current(默认排除失效, 现状检索) vs capsule(显式"回忆 @t"检索: 只含 birth<=t 且 (无失效或失效>t) 的条目)。
度量: 现状 recall(当前视图) 与 历史 recall(重访旧事实, 金标=事件前 rv-top)。
"""
import sys, os, json, time, pathlib, statistics
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
import world_gen as wg
import engine_gate as eg

OUT = HERE / "out_r4_d3"
OUT.mkdir(parents=True, exist_ok=True)
EVENT = wg.EVENT_GEN


def active_at(entries, t):
    out = []
    for e in entries:
        if e["birth_gen"] > t:
            continue
        if e.get("obsolete_gen") is not None and e["obsolete_gen"] <= t:
            continue
        out.append(e)
    return out


def recall(entries, qs, cfg, t, mode, gen):
    pool = entries if mode == "capsule" else [e for e in entries if not (e.get("obsolete_gen") is not None and e["obsolete_gen"] <= gen)]
    act = active_at(pool, t)
    tot = 0.0
    for q in qs:
        top = eg.retrieve_top(act, q["topic"], cfg)
        ids = [fid for fid, _s, _e in top]
        sub = active_at(act, t)
        gold = set(eg.gold_ids_at(sub, q, t, "rv"))
        tot += sum(1 for i in ids if i in gold) / min(eg.K_GOLD, eg.K_TOPK)
    return tot / len(qs)


rows = []
for seed in range(1, 9):
    w = wg.build_world("stale", seed)
    # 历史测验: 事件前(t=3) t0/t1 的查询; 现状测验: 当前(gen=29)
    decay = w["decay_topics"]
    hist_q = [{"topic": t} for t in decay for _ in range(6)]
    now_q = [{"topic": t} for t in decay for _ in range(6)]
    cfg = dict(eg.V3_DEFAULT)
    cfg_recall = dict(eg.V3_DEFAULT, w_age=0.0)   # 回忆模式: 按内容检索、无视时效
    # 无胶囊: current 模式查历史(应≈0 因条目已失效且被排除)
    cur_hist = recall(w["entries"], hist_q, cfg, 3, "current", 29)
    # 有胶囊: 回忆 @3(用回忆检索配置)
    cap_hist = recall(w["entries"], hist_q, cfg_recall, 3, "capsule", 29)
    # 现状 recall(现在是否仍能服务当下)
    cur_now = recall(w["entries"], now_q, cfg, 29, "current", 29)
    cap_now = recall(w["entries"], now_q, cfg_recall, 29, "capsule", 29)
    rows.append({"seed": seed, "cur_hist": round(cur_hist, 3), "cap_hist": round(cap_hist, 3),
                 "cur_now": round(cur_now, 3), "cap_now": round(cap_now, 3)})

(OUT / "rows_d3.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("%-6s %9s %9s %9s %9s" % ("seed", "cur_hist", "cap_hist", "cur_now", "cap_now"))
for r in rows:
    print("%-6d %9.3f %9.3f %9.3f %9.3f" % (r["seed"], r["cur_hist"], r["cap_hist"], r["cur_now"], r["cap_now"]))
print()
print("均值: 历史 recall  current=%.3f  capsule=%.3f | 现状 recall current=%.3f capsule=%.3f" % (
    statistics.mean(r["cur_hist"] for r in rows), statistics.mean(r["cap_hist"] for r in rows),
    statistics.mean(r["cur_now"] for r in rows), statistics.mean(r["cap_now"] for r in rows)))
print("[D3] out_r4_d3 done");
