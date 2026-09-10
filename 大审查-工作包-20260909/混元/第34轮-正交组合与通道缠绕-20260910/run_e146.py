"""E146 —— 通道缠绕偏见：盲评的前提检验（预注册 §三，勿反改）

judge 加性偏置：jscore_kb = jscore + κ_g × c.w_kw，κ_g 挂在 40% 条目的 golden 上
（Random(seed+555)，值 N(0.15,0.03)，其余为 0），对系统不可见、跨代持久。
w_kw 是本世界的【真信号通道】——盲评（eff 0.5→0.95）只压表象混合，动不到它。
臂：base（无偏见无盲评）/ bias（偏见无盲评）/ bias_blind（偏见+盲评）× n=44。
指标：真值增益、表象权重幅度 Σ|w|(SURF)、终局 w_kw。
"""
import sys, os, json, statistics, math, random

HERE = r"D:\临时工作区\大审查-工作包-20260909\混元\第34轮-正交组合与通道缠绕-20260910"
SYNC = r"D:\临时工作区\大审查-工作包-20260909\混元\自演化离线实验_同步包-大审查2-20260910\proto"
sys.path.insert(0, SYNC)
sys.path.insert(0, HERE)

from evolve9 import build_tasks          # noqa: E402
from evolve20 import Cfg2                # noqa: E402
from evolve24 import _m, SURF            # noqa: E402
from evolve31 import build_world_strong, tscore, jscore  # noqa: E402

OUT = os.path.join(HERE, "res_e146.json")
N = 44
ARMS = ("base", "bias", "bias_blind")


def run(seed, arm):
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    bias = arm in ("bias", "bias_blind")
    eff = 0.95 if arm == "bias_blind" else 0.5
    kappa = {}
    if bias:
        kr = random.Random(seed + 555)
        for e in E:
            if kr.random() < 0.40:
                kappa[e["id"]] = max(0.0, kr.gauss(0.15, 0.03))

    def jsc(c, tasks):
        if not bias:
            return _m(jscore(E, t, c, eff) for t in tasks)
        return _m(jscore(E, t, c, eff) + kappa.get(t["golden"], 0.0) * c.w_kw
                  for t in tasks)

    arch, main = [root], root
    m, tol, cap = 0.02, 0.04, 8

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
            if d_tr > m and d_he > m and jsc(ch, tr) > jsc(main, tr):
                main = ch

    gain = _m(tscore(E, t, main) for t in audit_set) - base
    surf = sum(abs(getattr(main, w)) for w in SURF)
    return [round(gain, 6), round(surf, 4), main.w_kw]


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

    print("\n" + "=" * 88)
    print(f"E146 · 通道缠绕偏见（配对 n={N}，偏见=κ_g×w_kw，κ_g~N(0.15,0.03)@40%条目）")
    print("%-12s %12s %16s %10s" % ("臂", "真值增益", "表象权重幅度", "终局w_kw"))
    bv = None
    for arm in ARMS:
        v = [x[0] for x in res[arm][:N]]
        sf = statistics.mean(x[1] for x in res[arm][:N])
        kw = statistics.mean(x[2] for x in res[arm][:N])
        print("%-12s %+12.4f %16.3f %10.3f" % (arm, statistics.mean(v), sf, kw))
        if arm == "base":
            bv = v
        else:
            diff = [b - a for a, b in zip(bv, v)]
            m_ = statistics.mean(diff)
            se = statistics.pstdev(diff) / math.sqrt(len(diff))
            print("             vs base: %+0.4f ± %.4f (t=%+.2f)" %
                  (m_, se, m_ / se if se else 0))
    print("=" * 88)


if __name__ == "__main__":
    main()
