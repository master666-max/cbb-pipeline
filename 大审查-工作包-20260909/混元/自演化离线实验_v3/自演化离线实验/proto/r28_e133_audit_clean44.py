"""R28-E133 · P1 重测：「审计在干净（无漂移）世界的收益」到底是不是负/零？

背景（第二十七轮 6.2 行动项 P1）：
  既有结论"审计在干净世界负收益 −0.005"系小样本（diag_audit 16 种子 / E129 10 种子）。
  E129 强信号世界 10 种子：scale1.0 −0.0198 / scale2.0 +0.0032 / scale3.0 +0.0135，
  方向对但均低于 10 种子检出限 0.062，不可下结论。

预注册设计：
  载体：evolve31 强信号世界（corr=0.85），非盲评（危险场景），无漂移（干净世界）
  配对：audit=True vs audit=False，同种子配对
  样本：44 种子 × 25 代 × 两档幅度（scale 1.0 与 2.0）
  判据：audit - noaudit 配对差 ±se、t、n（第二十七轮新格式）
  预注册预期：若真实效应 |Δ|<0.03，44 对仍可能检不出（检出限≈0.028）；
  那就如实登记"仍未与噪声区分"，不得宣称"确认无效"。

输出：res_r28_e133.json（逐 seed 落盘，可续跑）
"""
import sys, statistics, math, json, os
sys.path.insert(0, '/data/workspace/proto')
from evolve31 import run, BASE

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'res_r28_e133.json')

GENS = 25
SEEDS = list(range(1, 45))   # 44 种子（第二十七轮清单要求 44+）
SCALES = (1.0, 2.0)


def load():
    if os.path.exists(RES):
        with open(RES, encoding='utf-8') as f:
            return json.load(f)
    return {}


def main():
    res = load()
    for sc in SCALES:
        for arm, cfg in (("audit", dict(BASE, blind=False, scale=sc)),
                         ("noaudit", dict(BASE, blind=False, scale=sc, audit=False))):
            res.setdefault("s%.1f" % sc, {}).setdefault(arm, {})
            bucket = res["s%.1f" % sc][arm]
            for s in SEEDS:
                if str(s) in bucket:
                    continue
                bucket[str(s)] = run(s, cfg, gens=GENS)
                with open(RES, 'w', encoding='utf-8') as f:
                    json.dump(res, f, ensure_ascii=False, indent=1)

    print("R28-E133 · 干净世界审计收益 44 种子配对（强信号+非盲评，%d 代）" % GENS)
    for sc in SCALES:
        a = [res["s%.1f" % sc]["audit"][str(s)] for s in SEEDS]
        b = [res["s%.1f" % sc]["noaudit"][str(s)] for s in SEEDS]
        diff = [x - y for x, y in zip(a, b)]
        n = len(diff)
        m_ = statistics.mean(diff); sd_ = statistics.pstdev(diff)
        se_ = sd_ / math.sqrt(n)
        t_ = m_ / se_ if se_ else float('nan')
        print("  scale=%.1f: 审计 %+0.4f  无审计 %+0.4f  差 %+0.4f ± %.4f (sd %.4f, t=%.2f, n=%d)"
              % (sc, statistics.mean(a), statistics.mean(b), m_, se_, sd_, t_, n))


if __name__ == "__main__":
    main()
