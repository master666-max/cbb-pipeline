"""E153 —— 选择式 vs 演化式：质疑"演化"这个范式本身

★ 破坏性假设：
  40 轮都在问"怎么让自演化安全"。
  但如果 Skalse 定理成立——任何非平凡可优化目标都必然可破解——
  那么"让演化安全"可能是在错的问题上努力。

  替代方案：**不做演化，只做选择**
    - 预生成 N 个配置（一次性，可穷举验证）
    - 系统只能从中选，不能创造新的
    - "变坏"的空间 = N 个候选中挑错，而 N 是可枚举、可预先验证的

  这把"无限搜索空间的安全"变成"有限选择集的安全"。

对比（3 种）：
  evolve    变异产生新配置（现状）
  select_N  从预生成 N 个配置中选（N=20 / N=100）
  hybrid    选择 + 只在通过门控时才允许变异

在三种环境下测：
  clean     干净世界
  surf      表象污染（judge 看表象）
  drift     世界漂移

★ 关键判据：
  如果 select 在污染/漂移下明显更安全，而 clean 下性能损失小
  → 那么"自演化"本身可能不是必需的，选择就够了
"""
import sys, os, json, random, statistics, math
sys.path.insert(0, '/data/workspace/proto')

from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong, retrieve_strong, tscore

OUT = "/data/workspace/res_e153.json"
GENS = 20
N_SEEDS = 8


def featurize(E, task, c):
    rs = retrieve_strong(E, task, c)
    if not rs:
        return 0.0, 0.0
    real = sum(x["true_quality"] for x in rs) / len(rs)
    surf = sum((x["length"] + x["formatting"] + x["kw_density"]
                + x["has_citation"]) / 4.0 for x in rs) / len(rs)
    return real, surf


def gen_pool(rnd, n):
    """一次性生成候选池（可预先穷举验证）"""
    out = [Cfg2()]
    for _ in range(n - 1):
        d = {}
        for k in ("w_kw", "w_content", "w_imp", "w_age"):
            d[k] = round(rnd.uniform(0.0, 3.0), 3)
        for k in SURF:
            d[k] = round(rnd.uniform(-0.5, 1.5), 3)
        out.append(Cfg2(**d))
    return out


def run(seed, mode="evolve", env="clean", n_pool=20, gens=GENS):
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    # ★ 修正（第 22 次实验设计失败）：原实现里 env="surf" 什么都没做，
    #   导致 surf 与 clean 两列逐位相同。surf 环境必须【真正改变 judge】。
    eff = 0.2 if env == "surf" else 0.5   # surf: judge 主要看表象

    def J(c, tasks):
        out = []
        for t in tasks:
            real, surf = featurize(E, t, c)
            out.append(max(0.0, min(1.0, eff * real + (1 - eff) * surf)))
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
                d[p] * (1 + rnd.choice([-0.4, -0.15, 0.2, 0.6]) * 2.0)
                + rnd.choice([0, 0, 0.5, -0.5]) * 2.0)), 4)
        return Cfg2(**d)

    pool = gen_pool(random.Random(seed * 17 + 3), n_pool) if mode != "evolve" else None
    if pool:
        pool = [root] + pool[:n_pool - 1]
    main = root
    best_seen = J(root, build_tasks(E, rnd, 16))
    cap, tol, margin = 8, 0.04, 0.0
    arch = [root]

    for g in range(1, gens + 1):
        if env == "drift" and g == gens // 3:
            r = random.Random(seed + 999)
            for e in E:
                if r.random() < 0.35:
                    e["true_quality"] = r.random() * 0.3
        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)

        if mode == "evolve":
            cands = [mut(rnd.choice(arch[-3:])) for _ in range(4)]
        else:
            # 选择式：从池中采样（模拟"只能选"）
            cands = [rnd.choice(pool) for _ in range(4)]

        for ch in cands:
            cand = main
            d_tr = J(ch, tr) - J(cand, tr) + rnd.gauss(0, 0.05)
            d_he = J(ch, he) - J(cand, he) + rnd.gauss(0, 0.05)
            if mode == "hybrid":
                # 只在门控通过时允许变异（否则只从池选）
                ok = (d_he > 0)
                if not ok:
                    continue
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
    todo = []
    for mode, np_ in (("evolve", 0), ("select", 20), ("select", 100),
                      ("hybrid", 20)):
        for env in ("clean", "surf", "drift"):
            todo.append((mode, np_, env))

    for mode, np_, env in todo:
        k = f"{mode}_{np_}_{env}"
        got = res.get(k, [])
        for i in range(len(got) + 1, N_SEEDS + 1):
            try:
                g, sm = run(i, mode=mode, env=env, n_pool=(np_ or 20))
                got.append([g, sm])
            except Exception as ex:
                print("ERR", k, i, repr(ex)[:70]); break
            res[k] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {k}: {len(res.get(k,[]))}/{N_SEEDS}", flush=True)

    if not all(len(res.get(f"{m}_{n}_{e}", [])) >= N_SEEDS
               for m, n, _ in todo for e in ("clean", "surf", "drift")):
        print("未完成，续跑"); return

    print("\n" + "=" * 80)
    print(f"E153 选择式 vs 演化式（n={N_SEEDS}, {GENS} 代，无盲评）")
    print("%-14s | %10s %8s | %10s %8s | %10s %8s"
          % ("模式", "clean", "hack", "surf污染", "hack", "drift", "hack"))
    for mode, np_, lab in (("evolve", 0, "演化（现状）"),
                           ("select", 20, "选择 N=20"),
                           ("select", 100, "选择 N=100"),
                           ("hybrid", 20, "混合（门控变异）")):
        cells = []
        for env in ("clean", "surf", "drift"):
            v = [x[0] for x in res[f"{mode}_{np_}_{env}"][:N_SEEDS]]
            h = [x[1] for x in res[f"{mode}_{np_}_{env}"][:N_SEEDS]]
            cells.append((statistics.mean(v), statistics.mean(h)))
        print("%-14s | %+10.4f %8.2f | %+10.4f %8.2f | %+10.4f %8.2f"
              % (lab, cells[0][0], cells[0][1], cells[1][0], cells[1][1],
                 cells[2][0], cells[2][1]))
    print("=" * 80)


if __name__ == "__main__":
    main()
