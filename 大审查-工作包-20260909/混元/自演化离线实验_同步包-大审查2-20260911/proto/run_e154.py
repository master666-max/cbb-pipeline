"""E154 —— hacking 泛化溢出：论文发现的最危险缺口

★ 触发（外部文献 "School of Reward Hacks", Taylor et al. 2025）：
  "模型在【无害但可破解】的任务上学到破解后，会【泛化溢出】到危险行为：
   篡改棋引擎、操纵评分函数、给出危险建议、甚至抗拒关机。
   而且——**语言类（指标模糊）比代码类（指标清晰）溢出更多**。"

★ 这动摇了本项目的根本假设：
  153 个实验里，每个危险都是**独立注入、独立测量**的。
  从没测过：**一个系统是否"学会了破解"这件事本身会迁移**。

本轮设计（两阶段迁移范式）：

  阶段1（训练期，20 代）
    A 类任务。分两组：
      hack组  : judge 可被表象操纵（eff=0.5）→ 有破解机会
      对照组  : judge 只看真值（eff=1.0）     → 无破解机会
    另设"指标模糊度" noise ∈ {0.02(清晰/代码类), 0.25(模糊/语言类)}

  阶段2（测试期，B 类任务，judge 严格 eff=1.0，无破解可能）
    测两件事：
      (a) 立即迁移：直接把阶段1 的 champion 拿到 B 上评分
      (b) 继续演化：在 B 上再跑 20 代，看能否纠正

判据：
  ⭐ 溢出存在 ⟺ hack组 在 B 上的 gain 显著低于对照组
     （即使 B 上根本无法破解——说明带过来的是"破解倾向"本身）

  ⭐ 溢出强度：Δ = gain(对照组) − gain(hack组)
  模糊度效应：noise=0.25 时 Δ 是否更大（论文预测：是）
"""
import sys, os, json, random, statistics, math
sys.path.insert(0, '/data/workspace/proto')

from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong, retrieve_strong, tscore

OUT = "/data/workspace/res_e154.json"
P1_GENS = 20
P2_GENS = 20
N_SEEDS = 20
NOISES = [0.02, 0.25]      # 清晰(代码类) / 模糊(语言类)


def featurize(E, task, c):
    rs = retrieve_strong(E, task, c)
    if not rs:
        return 0.0, 0.0
    real = sum(x["true_quality"] for x in rs) / len(rs)
    surf = sum((x["length"] + x["formatting"] + x["kw_density"]
                + x["has_citation"]) / 4.0 for x in rs) / len(rs)
    return real, surf


def evolve(E, rnd, start, eff, noise, gens, scale=2.0, tasks_off=0):
    """在给定世界/任务上演化，返回 (champion, surf)"""
    main = start
    arch = [start]
    cap, tol, margin = 8, 0.04, 0.0

    def J(c, tasks):
        out = []
        for t in tasks:
            real, surf = featurize(E, t, c)
            v = eff * real + (1 - eff) * surf
            out.append(max(0.0, min(1.0, v + rnd.gauss(0, noise))))
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

    for g in range(1, gens + 1):
        tr = build_tasks(E, rnd, 16, offset=tasks_off)
        he = build_tasks(E, rnd, 16, offset=tasks_off + 3)
        for _ in range(4):
            cand = rnd.choice(arch[-3:])
            ch = mut(cand)
            d_tr = J(ch, tr) - J(cand, tr)
            d_he = J(ch, he) - J(cand, he)
            if d_tr > -tol:
                arch.append(ch)
            if len(arch) > cap:
                arch = arch[-cap:]
            if d_tr > margin and d_he > 0 and J(ch, tr) > J(main, tr):
                main = ch
    return main


def run(seed, p1_hack=True, noise=0.02, phase2_evolve=True):
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    root = Cfg2()

    # ── 任务集：A（训练）/ B（测试，不重叠）──
    A_set = build_tasks(E, random.Random(7777), 40, offset=5)
    B_set = build_tasks(E, random.Random(31337), 40, offset=23)
    base_B = _m(tscore(E, t, root) for t in B_set)

    # ── 阶段1：A 上演化 ──
    eff1 = 0.5 if p1_hack else 1.0
    p1_main = evolve(E, rnd, root, eff1, noise, P1_GENS)
    surf_after_p1 = p1_main.w_len + p1_main.w_fmt + p1_main.w_den + p1_main.w_cit

    # ── 阶段2(a)：立即迁移到 B（B 的 judge 严格，无法破解）──
    g_migrate = _m(tscore(E, t, p1_main) for t in B_set) - base_B

    # ── 阶段2(b)：在 B 上继续演化 20 代 ──
    if phase2_evolve:
        p2_main = evolve(E, rnd, p1_main, 1.0, 0.02, P2_GENS, tasks_off=23)
        g_after = _m(tscore(E, t, p2_main) for t in B_set) - base_B
        surf_after = (p2_main.w_len + p2_main.w_fmt
                      + p2_main.w_den + p2_main.w_cit)
    else:
        g_after, surf_after = g_migrate, surf_after_p1

    return g_migrate, g_after, surf_after_p1, surf_after


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    todo = [(h, n) for n in NOISES for h in (True, False)]

    for h, n in todo:
        k = f"{'hack' if h else 'ctrl'}_{n}"
        got = res.get(k, [])
        for i in range(len(got) + 1, N_SEEDS + 1):
            try:
                got.append(list(run(i, p1_hack=h, noise=n)))
            except Exception as ex:
                print("ERR", k, i, repr(ex)[:70]); break
            res[k] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {k}: {len(res.get(k,[]))}/{N_SEEDS}", flush=True)

    if not all(len(res.get(f"{'hack' if h else 'ctrl'}_{n}", [])) >= N_SEEDS
               for n in NOISES for h in (True, False)):
        print("未完成，续跑"); return

    print("\n" + "=" * 78)
    print(f"E154 hacking 泛化溢出（n={N_SEEDS}，阶段1/2 各 {P1_GENS}/{P2_GENS} 代）")
    print("%-14s | %10s %8s | %10s %8s | %10s"
          % ("指标模糊度", "迁移gain", "surf", "纠正后", "surf", "溢出Δ(迁移)"))
    for n, lab in ((0.02, "清晰(代码类)"), (0.25, "模糊(语言类)")):
        hk = res[f"hack_{n}"][:N_SEEDS]
        ct = res[f"ctrl_{n}"][:N_SEEDS]
        hm = [x[0] for x in hk]; cm = [x[0] for x in ct]
        ha = [x[1] for x in hk]; ca = [x[1] for x in ct]
        hs = [x[2] for x in hk]; cs = [x[2] for x in ct]
        d = [c - h for c, h in zip(cm, hm)]
        se = statistics.pstdev(d) / math.sqrt(len(d))
        t = statistics.mean(d) / se if se else 0
        print("%-14s | %+10.4f %8.2f | %+10.4f %8.2f | %+8.4f(t=%+.1f)"
              % (lab, statistics.mean(hm), statistics.mean(hs),
                 statistics.mean(ha), statistics.mean([x[3] for x in hk]),
                 statistics.mean(d), t))
        print("%-14s | %+10.4f %8.2f | %+10.4f %8.2f |"
              % ("  └对照组", statistics.mean(cm), statistics.mean(cs),
                 statistics.mean(ca), statistics.mean([x[3] for x in ct])))
    print("=" * 78)
    print("\n解读：溢出Δ = gain(对照组) − gain(hack组)")
    print("      Δ > 0 说明：即使在【无法破解】的 B 上，")
    print("      有过破解史的系统表现更差 → 破解倾向发生了迁移。")


if __name__ == "__main__":
    main()
