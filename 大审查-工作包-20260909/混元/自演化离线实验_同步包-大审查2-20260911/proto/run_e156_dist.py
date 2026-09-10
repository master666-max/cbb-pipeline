"""E156 步骤1：实测残留分布（为离群检测的功效分析提供真实参数）

上一轮结论：单 seed 判不准（sd≈2.85，均值差仅 1.94）。
本轮问：多运行离群检测能不能救？答案是功效问题——
  检出偏移 δ=1.94 相对 sd=2.85，需要 n 使 δ/(sd/√n) > 2.8
  → n > (2.8*2.85/1.94)² ≈ 17

先测准分布参数（30 seed），再做蒙特卡洛验证。
"""
import sys, os, json, random, statistics, math
sys.path.insert(0, '/data/workspace/proto')
from vk_common import mk

OUT = "/data/workspace/res_e156_dist.json"
N = 30


def run(seed, alpha=0.95, blind=False, gens=20):
    k = mk(seed, scale=2.0, blind=blind)
    k.alpha = alpha
    k.margin = k.cfg.margin
    for g in range(1, gens + 1):
        k._step(g)
    return k.champion.surf_signed()


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for lab, alpha, bl in (("clean", 0.95, False), ("hack", 0.5, False)):
        got = res.get(lab, [])
        for s in range(len(got) + 1, N + 1):
            try:
                got.append(run(s, alpha=alpha, blind=bl))
            except Exception as ex:
                print("ERR", lab, s, repr(ex)[:60]); break
            res[lab] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {lab}: {len(res[lab])}/{N}", flush=True)

    if not all(len(res.get(l, [])) >= N for l in ("clean", "hack")):
        print("未完成，续跑"); return

    c, h = res["clean"][:N], res["hack"][:N]
    print("\n" + "=" * 66)
    print(f"残留分布实测（n={N}，20 代）")
    print("%-8s %8s %8s %8s %8s %8s" % ("组", "均值", "sd", "中位", "min", "max"))
    for lab, v in (("clean", c), ("hack", h)):
        print("%-8s %+8.3f %8.3f %+8.3f %+8.3f %+8.3f"
              % (lab, statistics.mean(v), statistics.pstdev(v),
                 statistics.median(v), min(v), max(v)))
    delta = statistics.mean(h) - statistics.mean(c)
    # 合并 sd（假设两组方差相近，用于功效估算）
    sd_p = math.sqrt((statistics.pvariance(c) + statistics.pvariance(h)) / 2)
    print(f"\n效应量 δ = {delta:+.3f}   合并 sd = {sd_p:.3f}")
    print(f"Cohen's d = {delta/sd_p:.3f}")
    print(f"单实例 z = {delta/sd_p:.3f}  ← 远低于 2.8，故单 seed 判不准")
    for n in (5, 10, 17, 25, 40, 60):
        z = delta / (sd_p / math.sqrt(n))
        print("  并行 n=%2d → z=%.2f %s" % (n, z, "✅可检出" if abs(z) > 2.8 else ""))
    print("=" * 66)


if __name__ == "__main__":
    main()
