"""R28-E18b · P2 重测：跨库迁移为负（-0.083）在 16 种子下是否站得住？

背景（第二十七轮 6.2 行动项 P2）：
  E18 原结论"跨库迁移比从零演化还差"，效应量 0.083 勉强过旧检出限，判"勉强可靠"。
  升级到 16 种子配对复核。

预注册设计：
  载体：evolve6.evolve_transfer（原实现原样调用）
  三臂（同 dst_seed 配对，src 库独立取 seed 101..116）：
    from_scratch（目标库从零演化，基线）
    direct（源库配置直接搬）
    finetune（搬后微调 10 代）
  样本：16 dst 种子 × 25 代
  判据：direct/finetune - from_scratch 的配对差 ±se、t、n

输出：res_r28_e18b.json
"""
import sys, statistics, math, json, os
sys.path.insert(0, '/data/workspace/proto')
from evolve6 import evolve_transfer

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'res_r28_e18b.json')

DST_SEEDS = list(range(1, 17))    # 16 个目标库
MODES = ("from_scratch", "direct", "finetune")


def load():
    if os.path.exists(RES):
        with open(RES, encoding='utf-8') as f:
            return json.load(f)
    return {}


def main():
    res = load()
    for i, dst in enumerate(DST_SEEDS):
        src = 100 + dst             # 独立源库
        for mode in MODES:
            res.setdefault(mode, {})
            if str(dst) in res[mode]:
                continue
            res[mode][str(dst)] = evolve_transfer(src, dst, mode)
            with open(RES, 'w', encoding='utf-8') as f:
                json.dump(res, f, ensure_ascii=False, indent=1)

    print("R28-E18b · 跨库迁移 16 dst 种子配对（25 代）")
    base = [res["from_scratch"][str(d)] for d in DST_SEEDS]
    print("  from_scratch 增益 %+0.4f (sd %.4f)"
          % (statistics.mean(base), statistics.pstdev(base)))
    for mode in MODES[1:]:
        a = [res[mode][str(d)] for d in DST_SEEDS]
        diff = [x - y for x, y in zip(a, base)]
        n = len(diff)
        m_ = statistics.mean(diff); sd_ = statistics.pstdev(diff)
        se_ = sd_ / math.sqrt(n)
        t_ = m_ / se_ if se_ else float('nan')
        lo, hi = m_ - 1.96 * se_, m_ + 1.96 * se_
        print("  %-12s 增益 %+0.4f  差 %+0.4f ± %.4f (sd %.4f, t=%.2f, n=%d)  95CI[%+.4f, %+.4f]"
              % (mode, statistics.mean(a), m_, se_, sd_, t_, n, lo, hi))


if __name__ == "__main__":
    main()
