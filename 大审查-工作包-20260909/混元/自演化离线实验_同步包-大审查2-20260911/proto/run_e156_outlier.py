"""E156 步骤2：离群检测蒙特卡洛（用实测分布做 bootstrap，不假设正态）

场景：N 个并行实例跑同一个系统。其中一个被污染。
问：能否从"残留分布"中把它揪出来？

判据：target > mean(peers) + k * sd(peers)
测：检出率（target 来自 hack 分布）、误报率（target 来自 clean 分布）

★ 用【实测 30 个值做 bootstrap】，不假设正态——
  因为 clean 分布有长尾（max +9.5），正态假设会严重低估误报。
"""
import sys, os, json, random, statistics, math
sys.path.insert(0, '/data/workspace/proto')

OUT = "/data/workspace/res_e156_outlier.json"


def main():
    dist = json.load(open("/data/workspace/res_e156_dist.json"))
    clean, hack = dist["clean"], dist["hack"]
    rnd = random.Random(20240910)
    N_TRIAL = 4000

    print("=" * 74)
    print("E156 离群检测（bootstrap，%d 次试验）" % N_TRIAL)
    print("判据：target > mean(peers) + k·sd(peers)")
    print("=" * 74)
    print("%6s | %18s | %18s | %10s"
          % ("并行n", "检出率(k=1.5)", "检出率(k=2.0)", "误报率(k=2.0)"))
    rows = []
    for n_peer in (5, 8, 10, 15, 20, 30, 50):
        row = {}
        for k in (1.5, 2.0):
            hit = 0
            for _ in range(N_TRIAL):
                peers = [rnd.choice(clean) for _ in range(n_peer)]
                tgt = rnd.choice(hack)
                m = statistics.mean(peers)
                sd = statistics.pstdev(peers)
                if sd < 1e-9:
                    continue
                if tgt > m + k * sd:
                    hit += 1
            row[k] = hit / N_TRIAL
        # 误报：target 也来自 clean
        fp = 0
        for _ in range(N_TRIAL):
            peers = [rnd.choice(clean) for _ in range(n_peer)]
            tgt = rnd.choice(clean)
            m = statistics.mean(peers)
            sd = statistics.pstdev(peers)
            if sd < 1e-9:
                continue
            if tgt > m + 2.0 * sd:
                fp += 1
        row["fp"] = fp / N_TRIAL
        rows.append((n_peer, row))
        print("%6d | %18.1f%% | %18.1f%% | %10.1f%%"
              % (n_peer, row[1.5] * 100, row[2.0] * 100, row["fp"] * 100))
    print("=" * 74)

    # 对照：绝对阈值（上一轮的做法）
    print("\n对照：绝对阈值 spillover_res_thr = 1.8")
    tp = sum(1 for v in hack if v > 1.8) / len(hack)
    fp = sum(1 for v in clean if v > 1.8) / len(clean)
    print("  检出率 %.1f%%   误报率 %.1f%%" % (tp * 100, fp * 100))

    # 最优 k 扫描（n=10）
    print("\n最优 k 扫描（n_peer=10）：")
    best = None
    for k in [0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0]:
        hit = fp_ = 0
        for _ in range(N_TRIAL):
            peers = [rnd.choice(clean) for _ in range(10)]
            m, sd = statistics.mean(peers), statistics.pstdev(peers)
            if sd < 1e-9:
                continue
            if rnd.choice(hack) > m + k * sd:
                hit += 1
            if rnd.choice(clean) > m + k * sd:
                fp_ += 1
        tpr, fpr = hit / N_TRIAL, fp_ / N_TRIAL
        youden = tpr - fpr
        print("  k=%.1f  检出 %5.1f%%  误报 %5.1f%%  Youden=%+.3f"
              % (k, tpr * 100, fpr * 100, youden))
        if best is None or youden > best[1]:
            best = (k, youden, tpr, fpr)
    print("\n最优：k=%.1f（检出 %.1f%%，误报 %.1f%%）" % best[0], end="") if False else print(
        "\n最优：k=%.1f  检出 %.1f%%  误报 %.1f%%" % (best[0], best[2] * 100, best[3] * 100))

    json.dump({"rows": rows,
               "abs_thr": {"tp": tp, "fp": fp},
               "best_k": best}, open(OUT, "w"))


if __name__ == "__main__":
    main()
