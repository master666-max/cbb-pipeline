
"""E129 - 强信号世界重测 E110 配对效应（大幅度 x 审计）

弱世界信噪比 1:1，E110 的 +0.162 可能不可信。
在强信号世界（tf 相关 0.85）重测。
"""
import sys, statistics
sys.path.insert(0, "/data/workspace/proto")
from evolve31 import run, BASE

D = dict(BASE, blind=False)   # 非盲评危险场景

if __name__ == "__main__":
    seeds = range(1, 11)
    print("强信号世界 + 非盲评 · E110 配对效应重测（10种子，25代）")
    print("%-8s %12s %12s %12s" % ("幅度", "有审计", "无审计", "审计收益"))
    for sc in (1.0, 2.0, 3.0):
        a = statistics.mean([run(s, dict(D, scale=sc), gens=25) for s in seeds])
        b = statistics.mean([run(s, dict(D, scale=sc, audit=False), gens=25) for s in seeds])
        print("%-8.1f %+12.4f %+12.4f %+12.4f" % (sc, a, b, a - b))
