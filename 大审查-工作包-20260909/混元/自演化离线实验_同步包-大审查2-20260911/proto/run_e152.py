"""E152 —— Skalse 不可能性的定量权衡曲线

★ 理论基础（Skalse et al. 2022, 搜索所得）：
  "两个奖励函数只有在其中一个是常数时，才能互相 unhackable"
  → 奖励破解是【数学上不可避免】的，不是工程问题

  这比我自己总结的"三个不可能性"更根本：
  它说的是——**任何非平凡的可优化目标，必然存在破解路径**。

本轮要测量的不是"能不能防住 hack"，而是：
  **"改进能力" 与 "不可破解性" 之间的兑换率是多少？**

设计：
  引入 judge 敏感度 σ ∈ [0, 1]
      judge(config) = σ · f(real, surf) + (1-σ) · c₀
  - σ=1  完全响应系统行为（现状：可改进，也可 hack）
  - σ→0  趋向常数（Skalse 意义下"不可破解"，但也不可改进）

测量（每个 σ）：
  gain  = 真实质量增益（可改进性）
  hack  = 表象权重膨胀（破解程度）
  ratio = gain / hack   —— 每单位"破解空间"换来的改进

预期：单调权衡。关键问题是**曲线形状**：
  - 线性 → 兑换率恒定，无免费午餐
  - 凸（先陡后平）→ 存在甜点区，小幅牺牲可换大幅安全
  - 凹（先平后陡）→ 早期几乎免费，值得激进降 σ

同时测：盲评是否移动这条曲线（即改变兑换率而非沿曲线滑动）
"""
import sys, os, json, random, statistics, math
sys.path.insert(0, '/data/workspace/proto')

from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong, retrieve_strong, tscore

OUT = "/data/workspace/res_e152.json"
GENS = 20
N_SEEDS = 8
SIGMAS = [1.0, 0.8, 0.6, 0.4, 0.2, 0.1, 0.0]


def featurize(E, task, c):
    rs = retrieve_strong(E, task, c)
    if not rs:
        return 0.0, 0.0
    real = sum(x["true_quality"] for x in rs) / len(rs)
    surf = sum((x["length"] + x["formatting"] + x["kw_density"]
                + x["has_citation"]) / 4.0 for x in rs) / len(rs)
    return real, surf


def run(seed, sigma, blind=False, gens=GENS, scale=2.0):
    """sigma = judge 对系统行为的敏感度"""
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)

    C0 = 0.5          # 常数部分（judge 的"锚"）
    eff = 0.95 if blind else 0.5

    def J(c, tasks):
        out = []
        for t in tasks:
            real, surf = featurize(E, t, c)
            v = eff * real + (1 - eff) * surf
            out.append(max(0.0, min(1.0, sigma * v + (1 - sigma) * C0)))
        return _m(out)

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

    arch, main = [root], root
    cap, tol, margin = 8, 0.04, 0.0
    for g in range(1, gens + 1):
        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
        for _ in range(4):
            cand = rnd.choice(arch[-3:])
            ch = mut(cand)
            d_tr = J(ch, tr) - J(cand, tr) + rnd.gauss(0, 0.05)
            d_he = J(ch, he) - J(cand, he) + rnd.gauss(0, 0.05)
            if d_tr > -tol:
                arch.append(ch)
            if len(arch) > cap:
                arch = arch[-cap:]
            if d_tr > margin and d_he > 0 and J(ch, tr) > J(main, tr):
                main = ch

    gain = _m(tscore(E, t, main) for t in audit_set) - base
    surf_mag = main.w_len + main.w_fmt + main.w_den + main.w_cit
    return gain, surf_mag


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    todo = [(s, b) for s in SIGMAS for b in (False, True)]
    for sg, bl in todo:
        k = f"{sg}_{bl}"
        got = res.get(k, [])
        for i in range(len(got) + 1, N_SEEDS + 1):
            try:
                g, sm = run(i, sg, blind=bl)
                got.append([g, sm])
            except Exception as ex:
                print("ERR", k, i, repr(ex)[:70]); break
            res[k] = got
            json.dump(res, open(OUT, "w"))
        print(f"  σ={sg} blind={bl}: {len(res.get(k,[]))}/{N_SEEDS}", flush=True)

    if not all(len(res.get(f"{s}_{b}", [])) >= N_SEEDS
               for s in SIGMAS for b in (False, True)):
        print("未完成，续跑"); return

    print("\n" + "=" * 76)
    print(f"E152 Skalse 权衡曲线（n={N_SEEDS}, {GENS} 代）")
    print("%6s | %10s %8s | %10s %8s | %10s"
          % ("σ", "gain(裸)", "hack(裸)", "gain(盲)", "hack(盲)", "盲评Δgain"))
    rows = []
    for sg in SIGMAS:
        a = [x[0] for x in res[f"{sg}_False"][:N_SEEDS]]
        ah = [x[1] for x in res[f"{sg}_False"][:N_SEEDS]]
        b = [x[0] for x in res[f"{sg}_True"][:N_SEEDS]]
        bh = [x[1] for x in res[f"{sg}_True"][:N_SEEDS]]
        d = [y - x for x, y in zip(a, b)]
        se = statistics.pstdev(d) / math.sqrt(len(d))
        t = statistics.mean(d) / se if se else 0
        rows.append((sg, statistics.mean(a), statistics.mean(ah),
                     statistics.mean(b), statistics.mean(bh),
                     statistics.mean(d), t))
        print("%6.1f | %+10.4f %8.2f | %+10.4f %8.2f | %+8.4f(t=%+.1f)"
              % (sg, statistics.mean(a), statistics.mean(ah),
                 statistics.mean(b), statistics.mean(bh),
                 statistics.mean(d), t))
    print("=" * 76)

    # 曲线形状诊断
    gains = [r[1] for r in rows]
    print("\n曲线形状（裸 judge，gain 随 σ 降低的变化）：")
    for i in range(1, len(rows)):
        ds = rows[i-1][0] - rows[i][0]
        dg = rows[i][1] - rows[i-1][1]
        dh = rows[i-1][2] - rows[i][2]      # hack 减少量（正=改善）
        print("  σ %.1f→%.1f: gain %+.4f, hack %+.2f, 兑换率=%.4f"
              % (rows[i-1][0], rows[i][0], dg, dh,
                 dg / dh if abs(dh) > 1e-6 else float('nan')))


if __name__ == "__main__":
    main()
