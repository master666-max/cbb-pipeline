"""E136 —— 元判断扫描：适配机制的结论是否依赖被适配参数？

★ 核心问题：第二十七轮发现 8-12 种子只能检出 >0.062 的效应。
  而此前关于 margin / tol / cap / 幅度 的"标定"实验，
  用的恰恰是那个样本量。

  若"最优 margin 依赖判定它时用的样本量"，则所有标定结论都不可外推。

设计（2x2 + 扫描）：
  在【同一世界、同一演化】下，用不同 n_eval 评估 margin ∈ {0, 0.02, 0.05, 0.1}：
    n_eval = 8   （旧基线）
    n_eval = 20  （第二十七轮建议）
    n_eval = 40  （检测 0.03 效应）
  看"哪个 margin 最好"是否随 n_eval 改变。
"""
import sys, os, json, statistics, math, random
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong, tscore, jscore

OUT = "/data/workspace/res_e136.json"
MARGINS = (0.0, 0.02, 0.05, 0.10)
N_SEEDS = 40           # 大样本池，用于下采样到不同 n_eval
GENS = 24


def run(seed, margin, gens=GENS, kids=4, blind=True, scale=2.0, tol=0.04):
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit)
    eff = 0.95 if blind else 0.5
    arch, main = [root], root
    m, cap = margin, 8
    m_cur = margin

    def jsc(c, tasks):
        return _m(jscore(E, t, c, eff) for t in tasks)

    def mut(c):
        d = dict(w_kw=c.w_kw, w_content=c.w_content, w_imp=c.w_imp, w_age=c.w_age,
                 w_len=c.w_len, w_fmt=c.w_fmt, w_den=c.w_den, w_cit=c.w_cit,
                 filter_zero=c.filter_zero, deep=c.deep)
        r = rnd.random()
        if r < 0.08:
            d["deep"] = 1 - d["deep"]
        elif r < 0.16:
            d["filter_zero"] = 1 - d["filter_zero"]
        else:
            p = rnd.choice(["w_kw", "w_content", "w_imp", "w_age"] + list(SURF))
            d[p] = round(max(-5.0, min(20.0,
                d[p] * (1 + rnd.choice([-0.4, -0.15, 0.2, 0.6]) * scale)
                + rnd.choice([0, 0, 0.5, -0.5]) * scale)), 4)
        return Cfg2(**d)

    def pareto_strong(a, tr, he):
        pts = [((_m(jscore(E, t, c, eff) for t in tr),
                 _m(jscore(E, t, c, eff) for t in he)), c) for c in a]
        front = []
        for (A, ca) in pts:
            if not any(B[0] >= A[0] and B[1] >= A[1] and (B[0] > A[0] or B[1] > A[1])
                       for (B, _cb) in pts):
                front.append(ca)
        return front or a[-1:]

    for g in range(gens):
        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
        for _ in range(kids):
            cand = rnd.choice(arch[-3:])
            ch = mut(cand)
            d_tr = jsc(ch, tr) - jsc(cand, tr) + rnd.gauss(0, 0.05)
            d_he = jsc(ch, he) - jsc(cand, he) + rnd.gauss(0, 0.05)
            if d_tr > -tol:
                arch.append(ch)
            arch = pareto_strong(arch, tr, he)
            if len(arch) > cap:
                arch = rnd.sample(arch, cap)
            if d_tr > m_cur and d_he > m_cur and jsc(ch, tr) > jsc(main, tr):
                main = ch
    return _m(tscore(E, t, main) for t in audit) - base


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for mg in MARGINS:
        got = res.get(str(mg), [])
        for s in range(len(got) + 1, N_SEEDS + 1):
            try:
                got.append(run(s, mg))
            except Exception as ex:
                print("ERR", mg, s, ex)
                break
            res[str(mg)] = got
            json.dump(res, open(OUT, "w"))
        print(f"  margin={mg}: {len(res.get(str(mg), []))}/{N_SEEDS}")

    if not all(len(res.get(str(mg), [])) >= N_SEEDS for mg in MARGINS):
        print("未完成，续跑")
        return

    print("\n" + "=" * 72)
    print(f"E136 元判断扫描：最优 margin 是否依赖评估样本量（池 n={N_SEEDS}）")
    print("%-8s %10s %10s %10s %10s  %s" %
          ("n_eval", "m=0", "m=0.02", "m=0.05", "m=0.10", "最优 margin"))
    for n_eval in (8, 20, 40):
        row, best_m, best_v = [], None, -1e9
        for mg in MARGINS:
            v = res[str(mg)][:n_eval]
            mu = statistics.mean(v)
            row.append(mu)
            if mu > best_v:
                best_v, best_m = mu, mg
        print("%-8d %10.4f %10.4f %10.4f %10.4f  %s" %
              (n_eval, row[0], row[1], row[2], row[3], f"m={best_m}"))
    print("-" * 72)
    # 稳定性：n_eval=8 下排名前二的 margin，在 n_eval=40 下差异
    for mg in MARGINS:
        v = res[str(mg)]
        print("  margin=%-5s 全池 n=%d 均值=%+.4f  sd=%.4f  se=%.4f"
              % (mg, N_SEEDS, statistics.mean(v),
                 statistics.pstdev(v), statistics.pstdev(v) / math.sqrt(N_SEEDS)))
    print("=" * 72)


if __name__ == "__main__":
    main()
