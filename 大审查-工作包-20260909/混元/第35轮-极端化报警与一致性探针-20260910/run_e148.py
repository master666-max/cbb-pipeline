"""E148 —— judge 一致性探针（预注册 §三，勿反改）

judge 加每调用噪声 N(0, 0.10)（独立流）。世界 none。探针：每 4 代取 3 个存档
(golden, main) 各重评 2 次，平均分歧 > τ=0.06 → 冻结采纳；此后每 4 代复测，一致才解冻。
臂：noisy / noisy_probe；对照复用 E146 base（同世界无噪声无探针）。
"""
import sys, os, json, statistics, math, random

HERE = r"D:\临时工作区\大审查-工作包-20260909\混元\第35轮-极端化报警与一致性探针-20260910"
R34 = r"D:\临时工作区\大审查-工作包-20260909\混元\第34轮-正交组合与通道缠绕-20260910"
SYNC = r"D:\临时工作区\大审查-工作包-20260909\混元\自演化离线实验_同步包-大审查2-20260910\proto"
sys.path.insert(0, SYNC)
sys.path.insert(0, HERE)

from evolve9 import build_tasks          # noqa: E402
from evolve20 import Cfg2                # noqa: E402
from evolve24 import _m, SURF            # noqa: E402
from evolve31 import build_world_strong, tscore, jscore  # noqa: E402

OUT = os.path.join(HERE, "res_e148.json")
N = 44
ARMS = ("noisy", "noisy_probe")
SIGMA = 0.10
TAU = 0.06


def run(seed, arm):
    rnd = random.Random(seed)
    rj = random.Random(seed * 7 + 1)      # judge 噪声独立流
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    eff = 0.5
    probe = build_tasks(E, random.Random(4242), 4, offset=7)

    def jsc(c, tasks):
        if arm == "noisy_probe":
            # 探针模式：演化路径上同样有噪声（公平），探针另用 rj
            return _m(jscore(E, t, c, eff) + rj.gauss(0, SIGMA) for t in tasks)
        return _m(jscore(E, t, c, eff) + rj.gauss(0, SIGMA) for t in tasks)

    arch, main = [root], root
    m, tol, cap = 0.02, 0.04, 8
    frozen = False
    probes = 0
    trigger_gens = 0

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

    def pareto_strong(a, tr, he):
        pts = [((_m(jscore(E, t, c, eff) for t in tr),
                 _m(jscore(E, t, c, eff) for t in he)), c) for c in a]
        front = []
        for (A, ca) in pts:
            if not any(B[0] >= A[0] and B[1] >= A[1] and (B[0] > A[0] or B[1] > A[1])
                       for (B, _cb) in pts):
                front.append(ca)
        return front or a[-1:]

    for g in range(1, 25):
        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
        adopting = not frozen
        for _ in range(4):
            cand = rnd.choice(arch[-3:])
            ch = mut(cand)
            d_tr = jsc(ch, tr) - jsc(cand, tr) + rnd.gauss(0, 0.05)
            d_he = jsc(ch, he) - jsc(cand, he) + rnd.gauss(0, 0.05)
            if d_tr > -tol:
                arch.append(ch)
            arch = pareto_strong(arch, tr, he)
            if len(arch) > cap:
                arch = rnd.sample(arch, cap)
            if adopting and d_tr > m and d_he > m and jsc(ch, tr) > jsc(main, tr):
                main = ch

        # 一致性探针（每 4 代）：3 个 (golden, main) 对各重评 2 次
        if arm == "noisy_probe" and g % 4 == 0:
            probes += 1
            dis = []
            for t in probe[:3]:
                s1 = jscore(E, t, main, eff) + rj.gauss(0, SIGMA)
                s2 = jscore(E, t, main, eff) + rj.gauss(0, SIGMA)
                dis.append(abs(s1 - s2))
            mean_dis = statistics.mean(dis)
            if mean_dis > TAU:
                frozen = True
                trigger_gens += 1
            else:
                frozen = False

    gain = _m(tscore(E, t, main) for t in audit_set) - base
    surf = sum(abs(getattr(main, w)) for w in SURF)
    return [round(gain, 6), round(surf, 4), probes, trigger_gens]


def main():
    res = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    for arm in ARMS:
        got = res.get(arm, [])
        for s in range(len(got) + 1, N + 1):
            try:
                got.append(run(s, arm))
            except Exception as ex:
                print("ERR", arm, s, ex)
                break
            res[arm] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {arm}: {len(got)}/{N}")
    if not all(len(res.get(a, [])) >= N for a in ARMS):
        print("未完成，重跑续传")
        return

    e146 = json.load(open(os.path.join(
        R34, "res_e146.json"), encoding="utf-8"))
    print("\n" + "=" * 92)
    print(f"E148 · judge 一致性探针（配对 n={N}，σ={SIGMA}，τ={TAU}）")
    print("%-16s %12s %14s %10s %10s" % ("臂", "真值增益", "表象幅度", "探针次数", "冻结代"))
    rows = {}
    for arm, src in (("base", e146["base"]), ("noisy", res["noisy"]),
                     ("noisy_probe", res["noisy_probe"])):
        v = [x[0] for x in src]
        sf = statistics.mean(x[1] for x in src)
        pz = statistics.mean(x[2] for x in src) if arm != "base" else 0.0
        fz = statistics.mean(x[3] for x in src) if arm != "base" else 0.0
        rows[arm] = v
        print("%-16s %+12.4f %14.3f %10.1f %10.1f" % (arm, statistics.mean(v), sf, pz, fz))
    diff = [y - x[0] for x, y in zip(e146["base"], rows["noisy"])]
    m_ = statistics.mean(diff)
    se = statistics.pstdev(diff) / math.sqrt(len(diff))
    print("  noisy − base: %+0.4f ± %.4f (t=%+.2f)" % (m_, se, m_ / se if se else 0))
    diff = [y - x for x, y in zip(rows["noisy"], rows["noisy_probe"])]
    m_ = statistics.mean(diff)
    se = statistics.pstdev(diff) / math.sqrt(len(diff))
    print("  noisy_probe − noisy: %+0.4f ± %.4f (t=%+.2f)" % (m_, se, m_ / se if se else 0))
    print("=" * 92)


if __name__ == "__main__":
    main()
