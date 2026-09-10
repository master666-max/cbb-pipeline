"""E111 分片运行器：结果增量落盘，中断后可续跑"""
import sys, os, json, statistics
sys.path.insert(0, '/data/workspace/proto')
from evolve27 import e111

OUT = "/data/workspace/res_e111.json"
GENS = 25
SEEDS = list(range(1, 13))
SCALES = (0.5, 1.0, 2.0, 3.0)
CORRUPTS = (0.0, 0.3, 0.6, 1.0)

res = json.load(open(OUT)) if os.path.exists(OUT) else {}

for cp in CORRUPTS:
    for sc in SCALES:
        key = f"{cp}_{sc}"
        if key in res and len(res[key]) >= len(SEEDS):
            continue
        got = res.get(key, [])
        for s in SEEDS[len(got):]:
            try:
                got.append(e111(s, sc, cp, gens=GENS))
            except Exception as ex:
                print("ERR", key, s, ex)
                break
            res[key] = got
            json.dump(res, open(OUT, "w"))      # 每片立刻落盘

print("=== E111 审计污染 × 变异幅度 ===")
print(f"{'污染':>6s} " + " ".join(f"{sc:>8.1f}" for sc in SCALES))
for cp in CORRUPTS:
    row = []
    for sc in SCALES:
        k = f"{cp}_{sc}"
        row.append(statistics.mean(res[k]) if res.get(k) else float('nan'))
    best = SCALES[max(range(len(row)), key=lambda i: row[i])]
    print(f"{cp:>6.1f} " + " ".join(f"{x:>+8.4f}" for x in row) + f"   最优={best}")
print("样本数:", {k: len(v) for k, v in res.items()})
