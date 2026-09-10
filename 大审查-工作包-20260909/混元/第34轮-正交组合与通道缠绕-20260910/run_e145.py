"""E145 —— CD 门控二态判别（预注册 §二，勿反改）

strict_cd2s：strict + CUSUM（E139 冻结）逐审计喂流；
  CD 报警 → 重启基线（同 E141，清 streak）；
  退化审计：CD 自上次基线更新以来已报警 → 免测 cur_best 直接重锚（省探针）；
           否则 streak>=2 → 测 cur_best 二态判别；streak==1 → 回退。
新增计数：cur_best 测量次数。臂：strict/strict_2s/strict_cd/strict_cd2s ×
世界 drift/corrupt/none × n=44（固定探针，audit 每 2 代，同 E141 节拍）。
"""
import sys, os, json, statistics, math, random

HERE = r"D:\临时工作区\大审查-工作包-20260909\混元\第34轮-正交组合与通道缠绕-20260910"
SYNC = r"D:\临时工作区\大审查-工作包-20260909\混元\自演化离线实验_同步包-大审查2-20260910\proto"
R31 = r"D:\临时工作区\大审查-工作包-20260909\混元\第31轮-学术接入-20260910"
sys.path.insert(0, SYNC)
sys.path.insert(0, HERE)
sys.path.insert(0, R31)

from evolve9 import build_tasks          # noqa: E402
from evolve20 import Cfg2                # noqa: E402
from evolve24 import _m, SURF            # noqa: E402
from evolve31 import build_world_strong, tscore, jscore  # noqa: E402
import cdetectors                        # noqa: E402

OUT = os.path.join(HERE, "res_e145.json")
N = 44
SCENES = ("drift", "corrupt", "none")
ARMS = ("strict", "strict_2s", "strict_cd", "strict_cd2s")
CD_PARAMS = ("cusum", dict(k=0.0025, h=0.05))


def run(seed, scene, mode):
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    eff = 0.95
    arch, main, best, btr = [root], root, root, None
    m, tol, cap = 0.02, 0.04, 8
    probe = build_tasks(E, random.Random(4242), 4, offset=7)
    reverts = reanchors = cd_restarts = measures = 0
    streak = 0
    cd_fired = False
    cd = cdetectors.make(CD_PARAMS[0], **CD_PARAMS[1]) \
        if mode in ("strict_cd", "strict_cd2s") else None

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
        if g == 8:
            if scene == "drift":
                r = random.Random(seed + 999)
                for e in E:
                    if r.random() < 0.35:
                        e["true_quality"] = r.random() * 0.3
            elif scene == "corrupt":
                main = Cfg2(w_kw=-2.0, w_content=-1.0, w_imp=-1.0, w_age=1.0,
                            w_len=6.0, w_fmt=6.0, w_den=6.0, w_cit=6.0)
                arch = [main]

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

        if g % 2 == 0:
            cur = _m(tscore(E, t, main) for t in probe)
            if cd is not None and cd.update(cur):
                cd_restarts += 1
                btr, best = cur, main
                streak = 0
                cd_fired = True           # 证据保持：直到基线被真实更新才清零
                cd.reset()
                continue
            if btr is None:
                btr, best = cur, main
                continue
            if cur < btr - 0.01:
                streak += 1
                if mode == "strict_cd2s" and cd_fired:
                    btr, best = cur, main   # 免测 cur_best 直接重锚
                    reanchors += 1
                    streak = 0
                    cd_fired = False
                elif mode == "strict_2s" and streak >= 2 or \
                        (mode == "strict_cd2s" and streak >= 2):
                    cur_best = _m(tscore(E, t, best) for t in probe)
                    measures += 1
                    if cur_best > cur + 0.01:
                        main, arch = best, [best]     # 回退，基线不动
                    else:
                        btr, best = cur, main         # 世界变了 → 重置
                        reanchors += 1
                        streak = 0
                        cd_fired = False
                else:
                    main, arch = best, [best]         # streak==1（及 strict 全部退化）
                    reverts += 1
                    if mode == "strict_cd":
                        pass
            else:
                streak = 0
                if mode == "reanchor" or cur > btr:
                    pass
                if mode in ("strict", "strict_2s", "strict_cd", "strict_cd2s"):
                    if cur > btr:
                        btr, best = cur, main
                        cd_fired = False

    gain = _m(tscore(E, t, main) for t in audit_set) - base
    return [round(gain, 6), reverts, reanchors, cd_restarts, measures]


def main():
    bad = cdetectors.selftest()
    if bad:
        print("自测未过：", bad)
        raise SystemExit(1)
    res = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    for sc in SCENES:
        for arm in ARMS:
            k = f"{sc}_{arm}"
            got = res.get(k, [])
            for s in range(len(got) + 1, N + 1):
                try:
                    got.append(run(s, sc, arm))
                except Exception as ex:
                    print("ERR", k, s, ex)
                    break
                res[k] = got
                json.dump(res, open(OUT, "w"))
            print(f"  {k}: {len(got)}/{N}")
    if not all(len(res.get(f"{sc}_{a}", [])) >= N for sc in SCENES for a in ARMS):
        print("未完成，重跑续传")
        return

    print("\n" + "=" * 100)
    print(f"E145 · CD 门控二态判别（配对 n={N}）")
    for sc in SCENES:
        print(f"--- {sc} ---")
        base_v = None
        for arm in ARMS:
            v = [x[0] for x in res[f"{sc}_{arm}"][:N]]
            rv = statistics.mean(x[1] for x in res[f"{sc}_{arm}"][:N])
            ra = statistics.mean(x[2] for x in res[f"{sc}_{arm}"][:N])
            cd_ = statistics.mean(x[3] for x in res[f"{sc}_{arm}"][:N])
            ms = statistics.mean(x[4] for x in res[f"{sc}_{arm}"][:N])
            print("%-12s 增益=%+.4f  回退=%4.1f 重锚=%4.1f CD=%4.1f cur_best测量=%4.1f"
                  % (arm, statistics.mean(v), rv, ra, cd_, ms))
            if arm == "strict":
                base_v = v
            else:
                diff = [b - a for a, b in zip(base_v, v)]
                m_ = statistics.mean(diff)
                se = statistics.pstdev(diff) / math.sqrt(len(diff))
                print("             vs strict: %+0.4f ± %.4f (t=%+.2f)"
                      % (m_, se, m_ / se if se else 0))
    print("=" * 100)


if __name__ == "__main__":
    main()
