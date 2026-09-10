"""E144 —— 修复延迟是否重开 corrupt 边界（预注册 §二，勿反改）

strict_slow = strict 但回退要求 streak>=3（退化持续 3 审计才修复）；
strict_slow_cd = strict_slow + CUSUM（E139 冻结，报警后重置）。
对照 strict 取自 E141 存档（同种子/世界/节拍/固定探针）。
记录每个 seed 的 CD 首报代与首次修复代。
"""
import sys, os, json, statistics, math, random

HERE = r"D:\临时工作区\大审查-工作包-20260909\混元\第33轮-同框与节拍-20260910"
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

OUT = os.path.join(HERE, "res_e144.json")
N = 44
SCENES = ("corrupt", "drift", "none")
ARMS = ("strict_slow", "strict_slow_cd")
CD_PARAMS = ("cusum", dict(k=0.0025, h=0.05))
STREAK_REQ = 3


def run(seed, scene, mode):
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    eff = 0.95
    arch, main, best, btr = [root], root, root, None
    m, tol, cap = 0.02, 0.04, 8
    probe = build_tasks(E, random.Random(4242), 4, offset=7)   # 固定探针
    reverts = reanchors = cd_restarts = 0
    streak = 0
    cd = cdetectors.make(CD_PARAMS[0], **CD_PARAMS[1]) if mode.endswith("_cd") else None
    cd_fire_gen = None
    repair_gen = None

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
                if cd_fire_gen is None:
                    cd_fire_gen = g
                btr, best = cur, main
                streak = 0
                cd.reset()
                continue
            if btr is None:
                btr, best = cur, main
                continue
            if cur < btr - 0.01:
                streak += 1
                if streak >= STREAK_REQ:
                    main, arch = best, [best]
                    reverts += 1
                    if repair_gen is None:
                        repair_gen = g
            else:
                streak = 0
                if cur > btr:
                    btr, best = cur, main

    gain = _m(tscore(E, t, main) for t in audit_set) - base
    return [round(gain, 6), reverts, cd_restarts,
            cd_fire_gen if cd_fire_gen else -1, repair_gen if repair_gen else -1]


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

    # 对照 strict（E141 存档，同种子/世界/节拍/固定探针）
    e141p = r"D:\临时工作区\大审查-工作包-20260909\混元\第32轮-遗忘与轮换-20260910\res_e141.json"
    e141 = json.load(open(e141p, encoding="utf-8"))

    print("\n" + "=" * 96)
    print(f"E144 · 修复延迟（streak>={STREAK_REQ}）是否重开 corrupt 边界（配对 n={N}）")
    for sc in SCENES:
        print(f"--- {sc} ---")
        rows = []
        for arm in ("strict",) + ARMS:
            if arm == "strict":
                src = e141[f"{sc}_strict"]
                v = [x[0] for x in src]
                rv = statistics.mean(x[1] for x in src)
                cd_ = 0.0
                fires = [-1] * N
                repairs = [x[1] for x in src]
            else:
                src = res[f"{sc}_{arm}"]
                v = [x[0] for x in src]
                rv = statistics.mean(x[1] for x in src)
                cd_ = statistics.mean(x[2] for x in src)
                fires = [x[3] for x in src]
                repairs = [x[4] for x in src]
            print("%-15s 增益=%+.4f  回退=%4.1f CD重启=%4.1f" %
                  (arm, statistics.mean(v), rv, cd_))
            rows.append((arm, v))
        a = rows[0][1]      # strict (E141)
        b = rows[1][1]      # strict_slow
        c = rows[2][1]      # strict_slow_cd
        for name, other in (("strict_slow", b), ("strict_slow_cd", c)):
            diff = [y - x for x, y in zip(a, other)]
            m_ = statistics.mean(diff)
            se = statistics.pstdev(diff) / math.sqrt(len(diff))
            print("  %s vs strict: %+0.4f ± %.4f (t=%+.2f)" %
                  (name, m_, se, m_ / se if se else 0))
        diff = [y - x for x, y in zip(b, c)]
        m_ = statistics.mean(diff)
        se = statistics.pstdev(diff) / math.sqrt(len(diff))
        print("  strict_slow_cd vs strict_slow: %+0.4f ± %.4f (t=%+.2f)" %
              (m_, se, m_ / se if se else 0))
        # 赛跑观测（仅 corrupt 的 strict_slow_cd）
        if sc == "corrupt":
            fire_first = sum(1 for f in fires if f > 0)
            before_repair = sum(1 for f, rp in zip(fires, repairs)
                                if f > 0 and (rp < 0 or f < rp))
            fired = [f for f in fires if f > 0]
            rep = [rp for rp in repairs if rp > 0]
            print("  corrupt 赛跑：CD曾报警 %d/44；报警先于修复 %d；"
                  "首报代均值=%s；首修复代均值=%s" %
                  (fire_first, before_repair,
                   "%.1f" % statistics.mean(fired) if fired else "—",
                   "%.1f" % statistics.mean(rep) if rep else "—"))
    print("=" * 96)


if __name__ == "__main__":
    main()
