"""R28-E27b · P0-2 重测：漂移下「回滚到历史配置」与「继续演化」真的几乎无差吗？

背景（第二十七轮 6.2 行动项 P0-2）：
  E27 原结论"回滚 +0.024 vs 继续演化 +0.022，几乎无差"效应量仅 0.002，
  远低于检出限 0.062 —— 不可信，需 44+ 种子重测。

预注册设计：
  载体：evolve8.exp27（原实现原样调用，不改一行）——锚定漂移世界（alpha=0.15, 30 代）
  三臂：continue（继续演化）/ rollback（检出后回滚并停止）/ rollback_then_evolve（回滚后继续）
  样本：44 种子配对（同 seed 共享世界与漂移流）
  判据：各臂 - continue 的配对差 ±se、t、n；并报告 95% CI
  预注册预期：若 44 对后 |t|<1.96，不再说"几乎无差"，改判
  「配对差 X±Y，与零不可区分但 [下界,上界] 之外的更大效应被排除（或未排除）」
  ——把"无差"从断言降级为区间陈述。

输出：res_r28_e27b.json
"""
import sys, statistics, math, json, os
sys.path.insert(0, '/data/workspace/proto')
from evolve8 import exp27

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'res_r28_e27b.json')

SEEDS = list(range(1, 45))   # 44 种子
MODES = ("continue", "rollback", "rollback_then_evolve")


def load():
    if os.path.exists(RES):
        with open(RES, encoding='utf-8') as f:
            return json.load(f)
    return {}


def main():
    res = load()
    for mode in MODES:
        res.setdefault(mode, {})
        bucket = res[mode]
        for s in SEEDS:
            if str(s) in bucket:
                continue
            u, u0 = exp27(s, mode)
            bucket[str(s)] = u - u0
            with open(RES, 'w', encoding='utf-8') as f:
                json.dump(res, f, ensure_ascii=False, indent=1)

    print("R28-E27b · 回滚 vs 继续演化（44 种子配对，锚定漂移世界，30 代）")
    cont = [res["continue"][str(s)] for s in SEEDS]
    print("  continue      增益 %+0.4f (sd %.4f)" % (statistics.mean(cont), statistics.pstdev(cont)))
    for mode in MODES[1:]:
        a = [res[mode][str(s)] for s in SEEDS]
        diff = [x - y for x, y in zip(a, cont)]
        n = len(diff)
        m_ = statistics.mean(diff); sd_ = statistics.pstdev(diff)
        se_ = sd_ / math.sqrt(n)
        t_ = m_ / se_ if se_ else float('nan')
        lo, hi = m_ - 1.96 * se_, m_ + 1.96 * se_
        print("  %-20s 增益 %+0.4f  差 %+0.4f ± %.4f (sd %.4f, t=%.2f, n=%d)  95CI[%+.4f, %+.4f]"
              % (mode, statistics.mean(a), m_, se_, sd_, t_, n, lo, hi))


if __name__ == "__main__":
    main()
