# -*- coding: utf-8 -*-
"""aggregate_adversarial.py — 汇总对抗挑战 → 裁决摘要清单（按严重度排序）"""
import json, os, glob

OUTDIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "结果", "adversarial")

rows = []
for p in sorted(glob.glob(os.path.join(OUTDIR, "excerpt*_R*.json"))):
    d = json.load(open(p, encoding="utf-8"))
    base = os.path.basename(p).replace(".json", "")
    gname, rnd = base.rsplit("_R", 1)
    for c in d.get("challenges", []):
        rows.append({"gold": gname, "round": int(rnd),
                     "sev": c.get("severity", "?"), "type": c.get("type", "?"),
                     "target": (c.get("target") or "")[:40],
                     "claim": (c.get("claim") or "")[:90],
                     "evidence": (c.get("evidence") or "")[:70],
                     "fix": (c.get("proposed_fix") or "")[:70]})

sev_order = {"high": 0, "medium": 1, "low": 2, "?": 3}
rows.sort(key=lambda r: (r["gold"], sev_order.get(r["sev"], 9), r["round"]))

stats = {}
for r in rows:
    stats[(r["gold"], r["sev"])] = stats.get((r["gold"], r["sev"]), 0) + 1
print("=== 统计 (gold × severity) ===")
for k in sorted(stats):
    print(k, stats[k])
print("total:", len(rows))

out = os.path.join(OUTDIR, "_digest.md")
with open(out, "w", encoding="utf-8") as f:
    f.write(f"# 对抗挑战摘要（{len(rows)} 条，按 gold+严重度排序）\n\n")
    cur = None
    for i, r in enumerate(rows):
        if r["gold"] != cur:
            cur = r["gold"]
            f.write(f"\n## {cur}\n")
        f.write(f"- [{i}] R{r['round']} [{r['sev']}/{r['type']}] 目标:`{r['target']}` → {r['claim']} | 证:{r['evidence']} | 修:{r['fix']}\n")
print("written:", out)
