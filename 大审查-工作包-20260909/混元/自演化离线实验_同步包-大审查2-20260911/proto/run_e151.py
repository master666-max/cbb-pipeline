"""E151 —— 真实学习式 judge：150 个实验的最大局限

★ 问题：全部 150 个实验的 judge 都是【手写加权函数】
    judge = eff * real + (1-eff) * surf

  它是线性的、单调的、**没有泛化误差的**、在任意配置上都"准确"。
  而真实 judge（人类标注训练的奖励模型 / LLM-as-judge）有：
    1. 泛化误差 —— 在训练分布外的配置上会犯错
    2. 过拟合 —— 记住训练样本，对新配置外推失败
    3. 特征泄漏 —— 表象特征与标注偏差耦合

  本轮用 **sklearn 训练的真实模型** 替换手写 judge，重测核心机制。

设计：
  judge 输入：检索结果的特征向量（真值通道 tf + 表象通道 surf）
  judge 训练：从 N 个带噪人类标注拟合
      label = w_true * quality + w_bias * surf + 噪声
  judge 固定不重训练（模拟"部署后锁定"）

重测的机制：
  Q1 盲评（blind）是否仍有效？
  Q2 留出集门（held-out gate）是否仍有效？
  Q3 真值审计是否仍有效？
  Q4 大幅度 + 审计配对是否仍成立？

变量：judge 训练样本量 N（决定泛化误差大小）
"""
import sys, os, json, random, statistics, math
sys.path.insert(0, '/data/workspace/proto')
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong, retrieve_strong, tscore

OUT = "/data/workspace/res_e151.json"
GENS = 20
N_SEEDS = 8

# ── 特征化：把配置 + 世界 → 特征向量 ──
def featurize(E, task, c):
    """返回 [真值通道, 表象通道]"""
    rs = retrieve_strong(E, task, c)
    if not rs:
        return [0.0, 0.0]
    real = sum(x["true_quality"] for x in rs) / len(rs)
    surf = sum((x["length"] + x["formatting"] + x["kw_density"]
                + x["has_citation"]) / 4.0 for x in rs) / len(rs)
    return [real, surf]


def make_learned_judge(E, tasks, rnd, n_train, w_bias, noise=0.10,
                       kind="mlp"):
    """训练一个真实的 judge 模型

    ★ 关键：judge 从【带偏见的标注】学习
      label = 0.7 * real + w_bias * surf + 噪声

    w_bias 大 → judge 学会了"表象好 = 质量好"（人类标注者的偏见）
    """
    X, y = [], []
    r = random.Random(rnd)
    for _ in range(n_train):
        # 随机配置，覆盖配置空间
        c = Cfg2(**{k: round(r.uniform(-1, 3), 3) for k in
                    ("w_kw", "w_content", "w_imp", "w_age")})
        c = Cfg2(w_kw=c.w_kw, w_content=c.w_content, w_imp=c.w_imp,
                 w_age=c.w_age,
                 **{k: round(r.uniform(-1, 3), 3) for k in SURF})
        t = r.choice(tasks)
        f = featurize(E, t, c)
        lab = 0.7 * f[0] + w_bias * f[1] + r.gauss(0, noise)
        X.append(f); y.append(lab)
    X = np.array(X); y = np.array(y)
    if kind == "mlp":
        sc = StandardScaler().fit(X)
        m = MLPRegressor(hidden_layer_sizes=(16,), max_iter=400,
                         random_state=42)
        m.fit(sc.transform(X), y)
        return lambda f: float(m.predict(sc.transform(np.array([f])))[0]), sc
    else:
        m = Ridge(alpha=0.1).fit(X, y)
        return lambda f: float(m.predict(np.array([f]))[0]), None


def run(seed, judge_kind="hand", n_train=60, w_bias=0.3, blind=False,
        audit=False, gate=True, scale=2.0, gens=GENS, probe_n=4):
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    tasks_all = build_tasks(E, rnd, 40)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)

    if judge_kind == "hand":
        eff = 0.95 if blind else 0.5

        def J(c, tasks):
            out = []
            for t in tasks:
                f = featurize(E, t, c)
                out.append(max(0.0, min(1.0, eff * f[0] + (1 - eff) * f[1])))
            return _m(out)
    else:
        Jf, _ = make_learned_judge(E, tasks_all, seed * 31 + 7, n_train,
                                   w_bias, kind=judge_kind)
        if blind:
            # 盲评：剥离表象维度后重建（把 surf 置为该配置集上的均值）
            def J(c, tasks):
                out = []
                for t in tasks:
                    f = featurize(E, t, c)
                    f2 = [f[0], 0.5]        # ★ 表象通道置常数
                    out.append(float(Jf(f2)))
                return _m(out)
        else:
            def J(c, tasks):
                return _m(float(Jf(featurize(E, t, c))) for t in tasks)

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
    best_tr, best_pol = None, root
    probe = build_tasks(E, random.Random(4242), probe_n, offset=7)
    cap = 8
    tol, margin = 0.04, 0.0

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
            ok_gate = (d_he > 0) if gate else True
            if d_tr > margin and ok_gate and J(ch, tr) > J(main, tr):
                main = ch
        if audit and g % 5 == 0:
            cur = _m(tscore(E, t, main) for t in probe)
            if best_tr is None:
                best_tr, best_pol = cur, main
            elif cur < best_tr - 0.01:
                cb = _m(tscore(E, t, best_pol) for t in probe)
                if cb > cur + 0.01:
                    main, arch = best_pol, [best_pol]
                    best_tr, best_pol = cb, main
                else:
                    best_tr, best_pol = cur, main
            else:
                best_tr, best_pol = cur, main

    gain = _m(tscore(E, t, main) for t in audit_set) - base
    surf_mag = (main.w_len + main.w_fmt + main.w_den + main.w_cit)
    return gain, surf_mag


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}

    # 主对比：三种 judge × 盲评开关
    todo = []
    for jk in ("hand", "mlp", "ridge"):
        for bl in (False, True):
            todo.append((jk, bl, 60, 0.3))

    for jk, bl, nt, wb in todo:
        k = f"{jk}_{bl}_{nt}_{wb}"
        got = res.get(k, [])
        for s in range(len(got) + 1, N_SEEDS + 1):
            try:
                v, sm = run(s, judge_kind=jk, n_train=nt, w_bias=wb, blind=bl)
                got.append([v, sm])
            except Exception as ex:
                print("ERR", k, s, repr(ex)[:80])
                break
            res[k] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {k}: {len(res.get(k,[]))}/{N_SEEDS}", flush=True)

    if not all(len(res.get(f"{jk}_{bl}_60_0.3", [])) >= N_SEEDS
               for jk, _ in (("hand", 0), ("mlp", 0), ("ridge", 0))
               for bl in (False, True)):
        print("未完成，续跑")
        return

    print("\n" + "=" * 74)
    print(f"E151 真实学习式 judge（n={N_SEEDS}, {GENS} 代）")
    print("%-10s %10s %10s %12s %10s" %
          ("judge", "无盲评", "盲评", "盲评收益", "surf(无盲)"))
    for jk, lab in (("hand", "手写加权"), ("ridge", "Ridge(真实)"),
                    ("mlp", "MLP(真实)")):
        a = [x[0] for x in res[f"{jk}_False_60_0.3"][:N_SEEDS]]
        b = [x[0] for x in res[f"{jk}_True_60_0.3"][:N_SEEDS]]
        sm = statistics.mean([x[1] for x in res[f"{jk}_False_60_0.3"][:N_SEEDS]])
        d = [y - x for x, y in zip(a, b)]
        se = statistics.pstdev(d) / math.sqrt(len(d))
        t = statistics.mean(d) / se if se else 0
        print("%-10s %+10.4f %+10.4f %+8.4f(t=%+.1f) %10.2f"
              % (lab, statistics.mean(a), statistics.mean(b),
                 statistics.mean(d), t, sm))
    print("=" * 74)


if __name__ == "__main__":
    main()
