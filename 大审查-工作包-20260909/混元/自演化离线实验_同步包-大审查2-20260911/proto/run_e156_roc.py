"""E156 步骤3：ROC / AUC —— 离群检测到底有没有比绝对阈值更好？

上一轮反直觉结果：并行实例越多，检出率越【低】。
解释：判据 target > mean(peers)+k·sd(peers) 随 n 增大收敛到
      一个【固定绝对阈值】1.202 + k·2.868。
      即：离群检测 ≈ 绝对阈值，n 只影响阈值稳定性。

本轮用 AUC 做无阈值比较——这才是公平的。
计算：
  A_abs   = AUC(单个残留值区分 clean/hack)      ← 绝对阈值的理论上界
  A_out   = AUC(离群分数 target - mean(peers))  ← 离群检测的能
若 A_out ≈ A_abs → 离群检测没有带来新信息（只是换了个阈值）
"""
import sys, json, random, statistics, math
sys.path.insert(0, '/data/workspace/proto')

dist = json.load(open("/data/workspace/res_e156_dist.json"))
clean, hack = dist["clean"], dist["hack"]
rnd = random.Random(31337)
N = 6000


def auc(pos, neg):
    """pos = hack 分数, neg = clean 分数"""
    n = 0
    tot = 0.0
    for p in pos:
        for q in neg:
            tot += 1.0 if p > q else (0.5 if p == q else 0.0)
            n += 1
    return tot / n if n else 0.5


# ── A: 绝对阈值（单值）──
# 用 bootstrap 抽样多个 score 集合，降低 small-sample 偏差
A_abs_list = []
for _ in range(20):
    p = [rnd.choice(hack) for _ in range(60)]
    q = [rnd.choice(clean) for _ in range(60)]
    A_abs_list.append(auc(p, q))
A_abs = statistics.mean(A_abs_list)

print("=" * 70)
print("E156 ROC / AUC 对比（无阈值比较）")
print("=" * 70)
print("理论参考：Cohen's d = %.3f → 正态最优 AUC ≈ %.3f"
      % (0.901, 0.5 + 0.5 * math.erf(0.901 / 2)))
print()
print("A) 绝对阈值（单个残留值）        AUC = %.3f" % A_abs)
print()

# ── B: 离群分数 target − mean(peers) ──
print("B) 离群分数 = target − mean(peers)")
print("%8s | %10s | %s" % ("n_peer", "AUC", "vs 绝对阈值"))
for n_peer in (3, 5, 10, 20):
    scores_pos, scores_neg = [], []
    for _ in range(N):
        peers = [rnd.choice(clean) for _ in range(n_peer)]
        m = statistics.mean(peers)
        scores_pos.append(rnd.choice(hack) - m)
        scores_neg.append(rnd.choice(clean) - m)
    a = auc(scores_pos[:400], scores_neg[:400])
    print("%8d | %10.3f | %+.3f" % (n_peer, a, a - A_abs))

print()
print("=" * 70)
print("判读：")
print("  若 B ≈ A → 离群检测【没有新信息】，只是换了个阈值")
print("  若 B >> A → 离群检测有效")
print("=" * 70)
