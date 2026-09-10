"""E139 —— 检测层比武：文献序贯变化检测 vs 现行一步落差判据（预注册判据，勿反改）

流：复用 evolve35.run 演化循环（never 语义，无动作），逐代审计 champion 真值读数。
场景：none / drift(第8代35%重洗) / driftg(第10/15/20代各10%重洗) / corrupt(第8代换差champion)
标定：种子 1001-1020 干净流选档（不参与测试）；测试：种子 1-44 × 4 场景。
分片落盘可续跑。OUT 到本目录，不触碰任何既有目录。
"""
import sys, os, json, random, statistics, math

HERE = r"D:\临时工作区\大审查-工作包-20260909\混元\第31轮-学术接入-20260910"
SYNC = r"D:\临时工作区\大审查-工作包-20260909\混元\自演化离线实验_同步包-大审查2-20260910\proto"
sys.path.insert(0, SYNC)
sys.path.insert(0, HERE)

from evolve9 import build_tasks          # noqa: E402
from evolve20 import Cfg2                # noqa: E402
from evolve24 import _m, SURF            # noqa: E402
from evolve31 import build_world_strong, tscore, jscore  # noqa: E402
import cdetectors                        # noqa: E402

OUT = os.path.join(HERE, "res_e139_streams.json")
OUT_EVAL = os.path.join(HERE, "res_e139_eval.json")
GENS = 24
KIDS = 4
SCENES = ("none", "drift", "driftg", "corrupt")
EVENT_AT = {"none": 8, "drift": 8, "driftg": 10, "corrupt": 8}
N_TEST = 44
N_CAL = 20
CAL_SEEDS = list(range(1001, 1001 + N_CAL))

GRIDS = {
    "ph": [dict(alpha=a, lambd=l) for a in (0.0, 0.005)
           for l in (0.02, 0.05, 0.1, 0.2, 0.3, 0.5)],
    "cusum": [dict(k=k, h=h) for k in (0.0025, 0.005, 0.01)
              for h in (0.05, 0.1, 0.2, 0.3, 0.5, 0.8)],
    "adwin": [dict(delta=d) for d in (0.002, 0.01, 0.05, 0.1)],
    "baseline": [dict(thr=0.01)],
}


# ────────────────── 流采集（演化循环逐字复刻自 evolve35.run，动作全关） ──────────────────
def gen_stream(seed, scene):
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    eff = 0.95
    arch, main = [root], root
    m, tol, cap = 0.02, 0.04, 8
    probe = build_tasks(E, random.Random(4242), 4, offset=7)
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
                d[p] * (1 + rnd.choice([-0.4, -0.15, 0.2, 0.6]) * scale)
                + rnd.choice([0, 0, 0.5, -0.5]) * scale)), 4)
        return Cfg2(**d)

    scale = 2.0

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

        cur = _m(tscore(E, t, main) for t in probe)
        stream.append([g, round(cur, 6)])

    gain = _m(tscore(E, t, main) for t in audit_set) - base
    return {"gain": round(gain, 6), "stream": stream}


# ────────────────── 检测评估 ──────────────────
def run_detector(det, stream):
    """返回首次报警的 gen（无则 None）。报警后不再更新（first-fire 语义）。"""
    for g, x in stream:
        if det.update(x):
            return g
    return None


def first_fire_all(cfgdict, streams):
    return [run_detector(cdetectors.make(cfgdict["name"], **cfgdict["params"]), s)
            for s in streams]


def summarize(fires, scene):
    e0 = EVENT_AT[scene]
    none_scene = (scene == "none")
    tp = fp = 0
    lats = []
    for f in fires:
        if none_scene:
            if f is not None:
                fp += 1
        else:
            if f is not None and f >= e0:
                tp += 1
                lats.append(f - e0)
            elif f is not None:
                fp += 1
    n = len(fires)
    return {"tpr": tp / n, "fpr": fp / n,
            "lat_mean": statistics.mean(lats) if lats else None,
            "lat_n": len(lats), "n": n, "fires": fires}


def main():
    bad = cdetectors.selftest()
    if bad:
        print("自测未过，禁止采集：", bad)
        raise SystemExit(1)
    print("✓ 检测器自测通过")

    res = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}

    # 1) 流采集：测试种子 1-44 × 4 场景 + 标定干净流
    jobs = [(f"{sc}_{s}", sc, s) for sc in SCENES for s in range(1, N_TEST + 1)]
    jobs += [(f"cal_none_{s}", "none", s) for s in CAL_SEEDS]
    for key, sc, s in jobs:
        if key in res:
            continue
        try:
            res[key] = gen_stream(s, sc)
        except Exception as ex:
            print("ERR", key, ex)
            break
        json.dump(res, open(OUT, "w"))
        print(f"  {key}: gain={res[key]['gain']:+.4f}")

    need = set(j[0] for j in jobs)
    if not need <= set(res):
        print("未完成，重跑续传")
        return

    # 2) 标定：每个检测器在干净标定流上选档（FPR≤10% 前提下最敏感）
    cal_streams = [res[f"cal_none_{s}"]["stream"] for s in CAL_SEEDS]
    chosen = {}
    for name, grid in GRIDS.items():
        best = None
        for params in grid:
            fires = first_fire_all({"name": name, "params": params}, cal_streams)
            fpr = sum(1 for f in fires if f is not None) / len(fires)
            if fpr <= 0.10:
                # 最敏感 = PH/CUSUM 取最小阈值档（网格序即从敏感到保守），adwin 取最大 δ
                best = (params, fpr)
                if name != "adwin":
                    break
        if best is None:   # 无档满足 → 取 FPR 最小档，如实报告
            wors = None
            for params in grid:
                fires = first_fire_all({"name": name, "params": params}, cal_streams)
                fpr = sum(1 for f in fires if f is not None) / len(fires)
                if wors is None or fpr < wors[1]:
                    wors = (params, fpr)
            best = wors
            chosen[name] = {"params": best[0], "cal_fpr": best[1], "calibrated": False}
            continue
        chosen[name] = {"params": best[0], "cal_fpr": best[1], "calibrated": True}
    json.dump(chosen, open(OUT_EVAL, "w"), ensure_ascii=False, indent=1)
    print("\n标定结果：")
    for name, c in chosen.items():
        tag = "" if c["calibrated"] else "  ⚠️ 无档满足FPR≤10%，取FPR最小档"
        print(f"  {name:9s} {c['params']}  标定集FPR={c['cal_fpr']:.2f}{tag}")

    # 3) 测试评估（种子 1-44 × 4 场景）
    print("\n" + "=" * 88)
    print("E139 检测层比武（测试 n=44 / 场景；none 的 FPR 为全域任一报警）")
    hdr = ("检测器", "场景", "TPR", "FPR", "延迟均值±se", "t")
    for name in ("baseline", "ph", "cusum", "adwin"):
        params = chosen[name]["params"]
        for sc in SCENES:
            streams = [res[f"{sc}_{s}"]["stream"] for s in range(1, N_TEST + 1)]
            fires = first_fire_all({"name": name, "params": params}, streams)
            st = summarize(fires, sc)
            if st["lat_n"]:
                m_ = st["lat_mean"]
                lats = [f - EVENT_AT[sc] for f in st["fires"] if f is not None and f >= EVENT_AT[sc]]
                se = statistics.pstdev(lats) / math.sqrt(len(lats)) if len(lats) > 1 else 0.0
                lat = f"{m_:.1f}±{se:.1f}(n={st['lat_n']})"
            else:
                lat = "—"
            print("%-9s %-8s TPR=%5.2f FPR=%5.2f  延迟=%s" %
                  (name, sc, st["tpr"], st["fpr"], lat))
    print("=" * 88)
    json.dump({"chosen": chosen}, open(OUT_EVAL, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
