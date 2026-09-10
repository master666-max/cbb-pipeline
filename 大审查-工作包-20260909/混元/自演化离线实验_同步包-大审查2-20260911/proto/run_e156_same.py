"""E156 步骤4（关键对照）：离群检测在什么条件下才有效？

上一轮：离群检测 AUC(0.783) < 绝对阈值 AUC(0.796) —— 反而更差。

解释假设：
  减去 peers 均值 = 给 target 加一个随机噪声项。
  只有当【peers 与 target 共享基线】时，减去它才是消除共同噪声，
  否则纯粹是引入噪声。

  本实验里每个 seed 是一个【独立世界】→ peers 均值与 target 无关
  → 减去它 = 加噪声 → AUC 下降。

验证设计：
  对照组  diff-seed : peers 用 s+1000, s+2000...（独立世界）
  实验组  same-seed : peers 用同一 seed、不同随机流（同一世界，
                      共享基线；模拟"同一系统的多次并行测量"）
  测量两组的 AUC。

若 same-seed AUC 显著更高 → 解释成立，且给出离群检测的正确使用条件。
"""
import sys, os, json, random, statistics, math
sys.path.insert(0, '/data/workspace/proto')
from vk_common import mk

OUT = "/data/workspace/res_e156_same.json"
N_SEED = 16
N_PEER = 5


def run(seed, alpha=0.95, gens=20, stream=0):
    """stream 不同 → 同一世界（seed）下的不同随机流"""
    k = mk(seed, scale=2.0, blind=False)
    k.alpha = alpha
    k.margin = k.cfg.margin
    k.rnd = random.Random(seed * 7919 + stream)   # 同世界，不同流
    for g in range(1, gens + 1):
        k._step(g)
    return k.champion.surf_signed()


def auc(pos, neg):
    tot = n = 0
    for p in pos:
        for q in neg:
            tot += 1.0 if p > q else (0.5 if p == q else 0.0); n += 1
    return tot / n if n else 0.5


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    # 需要：每个 seed 的 clean/hack，以及同 seed 不同流
    for lab, alpha in (("clean", 0.95), ("hack", 0.5)):
        got = res.get(lab, [])
        for s in range(len(got) + 1, N_SEED + 1):
            try:
                row = [run(s, alpha=alpha, stream=st) for st in range(N_PEER + 1)]
                got.append(row)
            except Exception as ex:
                print("ERR", lab, s, repr(ex)[:60]); break
            res[lab] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {lab}: {len(res[lab])}/{N_SEED}", flush=True)

    if not all(len(res.get(l, [])) >= N_SEED for l in ("clean", "hack")):
        print("未完成，续跑"); return

    print("\n" + "=" * 72)
    print(f"E156 关键对照（n_seed={N_SEED}, n_peer={N_PEER}）")
    print("=" * 72)

    # A) 绝对阈值
    pos_a = [r[0] for r in res["hack"][:N_SEED]]
    neg_a = [r[0] for r in res["clean"][:N_SEED]]
    print("A) 绝对阈值                  AUC = %.3f" % auc(pos_a, neg_a))

    # B) 离群 - 不同 seed（独立世界）
    rnd = random.Random(4242)
    pos_b, neg_b = [], []
    for _ in range(1500):
        ps = [res["clean"][rnd.randrange(N_SEED)][rnd.randrange(N_PEER)]
              for _ in range(N_PEER)]
        m = statistics.mean(ps)
        pos_b.append(res["hack"][rnd.randrange(N_SEED)][rnd.randrange(N_PEER)] - m)
        neg_b.append(res["clean"][rnd.randrange(N_SEED)][rnd.randrange(N_PEER)] - m)
    a_b = auc(pos_b[:300], neg_b[:300])
    print("B) 离群 · peers 独立世界      AUC = %.3f" % a_b)

    # C) 离群 - 同 seed（共享基线）
    pos_c, neg_c = [], []
    for _ in range(1500):
        s = rnd.randrange(N_SEED)
        # peers 与 target 来自同一 seed 的【不同流】→ 共享世界基线
        pos_c.append(res["hack"][s][0] -
                     statistics.mean(res["clean"][s][1:N_PEER + 1]))
        neg_c.append(res["clean"][s][0] -
                     statistics.mean(res["clean"][s][1:N_PEER + 1]))
    a_c = auc(pos_c[:300], neg_c[:300])
    print("C) 离群 · peers 共享基线      AUC = %.3f" % a_c)
    print("=" * 72)
    print()
    if a_c > a_b + 0.03:
        print("✅ 解释成立：共享基线时离群检测才有价值")
        print("   （%.3f vs %.3f）" % (a_c, a_b))
    else:
        print("❌ 解释不成立：共享基线也未改善")
    print()
    print("组内方差 vs 组间方差：")
    within = statistics.mean([statistics.pstdev(r[1:N_PEER + 1])
                              for r in res["clean"][:N_SEED]])
    between = statistics.pstdev([statistics.mean(r[1:N_PEER + 1])
                                 for r in res["clean"][:N_SEED]])
    print("  clean 组内 sd（同世界不同流）= %.3f" % within)
    print("  clean 组间 sd（不同世界）   = %.3f" % between)
    print("  ★ 若 组内 << 组间 → 共享基线能消除大部分噪声")


if __name__ == "__main__":
    main()
