"""E145d —— drift 无解的机制确认：是"信号崩塌"还是"应对不对"？

E145c 显示复合危险下 5 种应对全部无效。
E145 诊断显示 drift 后信号 sd 从 0.1036 降到 0.0654（−37%）。

假设：drift 后【可学习的信号变弱】，所以任何应对都无效——
      因为应对只能改变"怎么学"，改变不了"能学到什么"。

验证：若假设成立，则【增大搜索预算】（更多变异/更多代）应当能部分恢复，
      因为弱信号需要更多样本才能学到。

设计：kids ∈ {4, 8, 16} × 策略 {never, fresh}，n=16，复合危险
判据：若 kids↑ 时 drift 场景收益显著上升 → 是信号问题（可缓解）
      若 kids↑ 无帮助 → 是结构问题（无解）
"""
import sys, os, json, statistics, math
sys.path.insert(0, '/data/workspace/proto')
from run_e145b import run

OUT = "/data/workspace/res_e145d.json"
N_SEEDS = 16


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    combos = [(k, md) for k in (4, 8, 16) for md in ("never", "fresh")]
    for k, md in combos:
        key = f"k{k}_{md}"
        got = res.get(key, [])
        for s in range(len(got) + 1, N_SEEDS + 1):
            try:
                got.append(run(s, md, kids=k, write=True, eff=0.5)[0])
            except Exception as ex:
                print("ERR", key, s, ex)
                break
            res[key] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {key}: {len(res.get(key, []))}/{N_SEEDS}")

    if not all(len(res.get(f"k{k}_{md}", [])) >= N_SEEDS for k, md in combos):
        print("未完成，续跑")
        return

    print("\n" + "=" * 68)
    print(f"E145d 搜索预算 × drift（复合危险，n={N_SEEDS}）")
    print("%-6s %10s %10s %14s" % ("kids", "never", "fresh", "fresh−never"))
    for k in (4, 8, 16):
        nv = res[f"k{k}_never"][:N_SEEDS]
        fv = res[f"k{k}_fresh"][:N_SEEDS]
        d = [y - x for x, y in zip(nv, fv)]
        se = statistics.pstdev(d) / math.sqrt(len(d))
        print("%-6d %+10.4f %+10.4f %+10.4f ± %.4f (t=%.2f)"
              % (k, statistics.mean(nv), statistics.mean(fv),
                 statistics.mean(d), se, statistics.mean(d) / se if se else 0))
    print("-" * 68)
    for md in ("never", "fresh"):
        a = res[f"k4_{md}"][:N_SEEDS]
        b = res[f"k16_{md}"][:N_SEEDS]
        d = [y - x for x, y in zip(a, b)]
        se = statistics.pstdev(d) / math.sqrt(len(d))
        print("  kids 4→16 (%s): %+.4f ± %.4f (t=%.2f)"
              % (md, statistics.mean(d), se, statistics.mean(d) / se if se else 0))
    print("=" * 68)


if __name__ == "__main__":
    main()
