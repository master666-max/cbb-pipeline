"""E140 —— 元判断 III：机制的价值是否依赖【数据量】？

E139 发现：世界 A（强信号）下 tol=0.1、cap=8 最优，但差异都很小
  (tol: 0.133 / 0.199 / 0.203 / 0.200；cap: 0.178/0.182/0.199/0.182)
  → 参数在"平台区"内不敏感，标定无意义。

E3 世界没有 tol/cap 参数，但有更贴合元判断的维度：**n_train（训练任务数）**。
E17 已证明 n=10 时假阳性率 42%，E64 证明预算<150 终局为负。

本轮问：门的净收益是否随数据量变化？若"数据少时门无效"，
则 E3「门必需」的结论也有适用范围。

设计：E3 世界，n_train ∈ {6, 12, 20, 40}，配对比较 有门 vs 无门，n=30。
"""
import sys, os, json, statistics, math
sys.path.insert(0, '/data/workspace/proto')
from evolve3 import evolve

OUT = "/data/workspace/res_e140.json"
N_SEEDS = 30
N_TRAINS = (6, 12, 20, 40)


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for nt in N_TRAINS:
        for tag, gated in (("gated", True), ("ungated", False)):
            k = f"{nt}_{tag}"
            got = res.get(k, [])
            for s in range(len(got) + 1, N_SEEDS + 1):
                try:
                    r = evolve(s, gated=gated, margin=0.0, n_train=nt)
                    got.append([r["best_he"] - r["root_he"], 1 if r["cheated"] else 0])
                except Exception as ex:
                    print("ERR", k, s, ex)
                    break
                res[k] = got
                json.dump(res, open(OUT, "w"))
            print(f"  {k}: {len(res.get(k, []))}/{N_SEEDS}")

    if not all(len(res.get(f"{nt}_{t}", [])) >= N_SEEDS
               for nt in N_TRAINS for t in ("gated", "ungated")):
        print("未完成，续跑")
        return

    print("\n" + "=" * 70)
    print(f"E140 门的净收益是否依赖数据量（E3 世界，配对 n={N_SEEDS}）")
    print("%-8s %10s %10s %12s %10s" % ("n_train", "有门", "无门", "门的净收益", "无门作弊率"))
    for nt in N_TRAINS:
        g = [x[0] for x in res[f"{nt}_gated"][:N_SEEDS]]
        u = [x[0] for x in res[f"{nt}_ungated"][:N_SEEDS]]
        cheat = sum(x[1] for x in res[f"{nt}_ungated"][:N_SEEDS]) / N_SEEDS
        d = [a - b for a, b in zip(g, u)]
        se = statistics.pstdev(d) / math.sqrt(len(d))
        print("%-8d %+10.4f %+10.4f %+8.4f±%.4f(t=%.2f) %9.0f%%"
              % (nt, statistics.mean(g), statistics.mean(u),
                 statistics.mean(d), se, statistics.mean(d) / se if se else 0,
                 cheat * 100))
    print("=" * 70)


if __name__ == "__main__":
    main()
