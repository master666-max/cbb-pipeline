"""E135 快速对比：五种策略 × 四态（12 种子，先看方向）"""
import sys, statistics
sys.path.insert(0, '/data/workspace/proto')
from evolve35 import run, SCENE_STATE

if __name__ == "__main__":
    print("快速对比（12 种子，24 代）")
    print("%-8s %9s %9s %9s %9s %9s" %
          ("场景", "never", "naive", "diagnose", "split", "oracle"))
    for sc in SCENE_STATE:
        row = []
        for md in ("never", "naive", "diagnose", "split", "oracle"):
            v = [run(s, sc, md, collect=(md in ("diagnose", "split")))
                 for s in range(1, 13)]
            g = [x[0] if isinstance(x, (list, tuple)) else x for x in v]
            row.append("%+.4f" % statistics.mean(g))
        print("%-8s %s" % (sc, "  ".join("%9s" % x for x in row)))
