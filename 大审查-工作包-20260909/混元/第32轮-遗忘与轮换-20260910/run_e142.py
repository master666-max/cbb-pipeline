"""E142 —— 探针轮换 × 检测器（预注册追加栏，勿反改）

与 E139 唯一差异：每次审计轮换探针（Random(4242+g)）。检测器 = E139 冻结参数，不重标定。
产出：四场景 TPR/FPR/延迟 + none 世界相邻读数差（噪声直接读数，固定 vs 轮换）。
"""
import sys, os, json, random, statistics, math

HERE = r"D:\临时工作区\大审查-工作包-20260909\混元\第32轮-遗忘与轮换-20260910"
R31 = r"D:\临时工作区\大审查-工作包-20260909\混元\第31轮-学术接入-20260910"
SYNC = r"D:\临时工作区\大审查-工作包-20260909\混元\自演化离线实验_同步包-大审查2-20260910\proto"
sys.path.insert(0, SYNC)
sys.path.insert(0, HERE)
sys.path.insert(0, R31)

from evolve9 import build_tasks          # noqa: E402
from evolve20 import Cfg2                # noqa: E402
from evolve24 import _m, SURF            # noqa: E402
from evolve31 import build_world_strong, tscore, jscore  # noqa: E402
import cdetectors                        # noqa: E402

OUT = os.path.join(HERE, "res_e142_streams.json")
GENS, KIDS = 24, 4
SCENES = ("none", "drift", "driftg", "corrupt")
EVENT_AT = {"none": 8, "drift": 8, "driftg": 10, "corrupt": 8}
N_TEST, N_CAL = 44, 20
CAL_SEEDS = list(range(1001, 1001 + N_CAL))

FROZEN = {  # E139 冻结
    "baseline": dict(thr=0.01),
    "ph": dict(alpha=0.0, lambd=0.02),
    "cusum": dict(k=0.0025, h=0.05),
    "adwin": dict(delta=0.1),
}


def gen_stream(seed, scene, rotate=True):
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    eff = 0.95
    arch, main = [root], root
    m, tol, cap = 0.02, 0.04, 8
    probe_fixed = build_tasks(E, random.Random(4242), 4, offset=7)
    event_at = GENS // 3

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

    stream = []
    for g in range(1, GENS + 1):
        if g == event_at:
            if scene == "drift":
                r = random.Random(seed + 999)
                for e in E:
                    if r.random() < 0.35:
                        e["true_quality"] = r.random() * 0.3
            elif scene == "corrupt":
                main = Cfg2(w_kw=-2.0, w_content=-1.0, w_imp=-1.0, w_age=1.0,
                            w_len=6.0, w_fmt=6.0, w_den=6.0, w_cit=6.0)
                arch = [main]
        elif scene == "driftg" and g in (10, 15, 20):
            r = random.Random(seed + 1000 + g)
            for e in E:
                if r.random() < 0.10:
                    e["true_quality"] = r.random() * 0.3

        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
        for _ in range(KIDS):
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

        probe = build_tasks(E, random.Random(4242 + g), 4, offset=7) if rotate \
            else probe_fixed
        cur = _m(tscore(E, t, main) for t in probe)
        stream.append([g, round(cur, 6)])

    gain = _m(tscore(E, t, main) for t in audit_set) - base
    return {"gain": round(gain, 6), "stream": stream}


def first_fire(params_name, params, stream):
    d = cdetectors.make(params_name, **params)
    for g, x in stream:
        if d.update(x):
            return g
    return None


def main():
    bad = cdetectors.selftest()
    if bad:
        print("自测未过：", bad)
        raise SystemExit(1)
    res = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    jobs = [(f"{sc}_{s}", sc, s) for sc in SCENES for s in range(1, N_TEST + 1)]
    jobs += [(f"cal_none_{s}", "none", s) for s in CAL_SEEDS]
    for key, sc, s in jobs:
        if key in res:
            continue
        res[key] = gen_stream(s, sc, rotate=True)
        json.dump(res, open(OUT, "w"))
    if not all(k in res for k, _s, _c in jobs):
        print("未完成，重跑续传")
        return
    print("采集完成（轮换探针）")

    # 噪声直接读数：none 世界相邻读数差
    diffs_rot, diffs_fix = [], []
    e139 = json.load(open(os.path.join(
        R31, "res_e139_streams.json"), encoding="utf-8"))
    for s in range(1, N_TEST + 1):
        st_r = res[f"none_{s}"]["stream"]
        st_f = e139[f"none_{s}"]["stream"]
        diffs_rot += [abs(st_r[i][1] - st_r[i - 1][1]) for i in range(1, len(st_r))]
        diffs_fix += [abs(st_f[i][1] - st_f[i - 1][1]) for i in range(1, len(st_f))]
    print("none 世界相邻读数差均值：固定=%.4f  轮换=%.4f  (比值 %.2f×)" %
          (statistics.mean(diffs_fix), statistics.mean(diffs_rot),
           statistics.mean(diffs_rot) / statistics.mean(diffs_fix)))

    print("\n" + "=" * 88)
    print("E142 轮换探针 × 冻结检测器（n=44/场景；括号内为 E139 固定探针参照）")
    ref = {"baseline": {"none": 0.09, "drift": 0.93, "driftg": 0.89, "corrupt": 0.91},
           "ph": {"none": 0.00, "drift": 0.98, "driftg": 0.84, "corrupt": 0.93},
           "cusum": {"none": 0.00, "drift": 0.95, "driftg": 0.70, "corrupt": 0.91},
           "adwin": {"none": 0.00, "drift": 0.00, "driftg": 0.00, "corrupt": 0.00}}
    for name, params in FROZEN.items():
        for sc in SCENES:
            fires = [first_fire(name, params, res[f"{sc}_{s}"]["stream"])
                     for s in range(1, N_TEST + 1)]
            e0 = EVENT_AT[sc]
            none_scene = (sc == "none")
            tp = fp = 0
            lats = []
            for f in fires:
                if none_scene:
                    if f is not None:
                        fp += 1
                elif f is not None and f >= e0:
                    tp += 1
                    lats.append(f - e0)
                elif f is not None:
                    fp += 1
            lat = ("%0.1f±%0.1f" % (statistics.mean(lats),
                   statistics.pstdev(lats) / math.sqrt(len(lats)) if len(lats) > 1 else 0)
                   ) if lats else "—"
            print("%-9s %-8s TPR=%.2f(参照%.2f) FPR=%.2f(参照%.2f) 延迟=%s" %
                  (name, sc, tp / N_TEST, ref[name][sc], fp / N_TEST,
                   ref[name]["none"] if none_scene else ref[name][sc], lat))
    print("=" * 88)


if __name__ == "__main__":
    main()
