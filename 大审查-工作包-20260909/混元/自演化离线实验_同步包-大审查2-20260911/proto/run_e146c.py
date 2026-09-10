"""E146c —— 锚定探针的关键边界：它能区分"世界漂移"和"judge 漂移"吗？

E146a：锚定探针 100%/0%，是本轮最好的检测信号。
E146b：检出后加预算（boost）在两种 drift 下都有效（t=3.53 / 2.93）。

但 E14 揭示过一类更危险的事：**judge 本身会漂移**（评判者被系统输出锚定）。
此时锚定探针（固定配置在固定集上的 judge 得分）**也会漂移**——
它测的是"judge 对世界的评价"，两者都变时它无法区分。

本轮检验这个混淆：
  A world   世界漂移（条目质量重洗）—— 锚定探针应触发，boost 应有效
  B judge   judge 漂移（eff 缓慢下降：越来越看表象）—— 探针【误触发】
  C both    两者同时

关键判据：
  若 B 下探针也触发，且 boost 有害 → "探针触发即加预算"是危险策略
  → 必须先用【盲评】切断 judge 通道，才能安全使用探针

设计：n=20，24 代
"""
import sys, os, json, statistics, math, random
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong, retrieve_strong, tscore

OUT = "/data/workspace/res_e146c.json"
N_SEEDS = 20
GENS = 24
DRIFT_AT = 8


def run(seed, scen, mode="never", gens=GENS, kids=4, scale=2.0,
        tol=0.04, margin=0.0, eff0=0.95, rate=0.03, blind=False):
    """scen: world / judge / both ; mode: never / boost"""
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    arch, main = [root], root
    cap = 8
    anchor_tasks = build_tasks(E, random.Random(31337), 8, offset=11)
    anchor_hist = []
    detected_at = None
    k_cur = kids
    eff = eff0

    def jsc(c, tasks):
        out = []
        for t in tasks:
            rs = retrieve_strong(E, t, c)
            if not rs:
                out.append(0.0); continue
            real = sum(x["true_quality"] for x in rs) / len(rs)
            surf = sum((x["length"] + x["formatting"] + x["kw_density"]
                        + x["has_citation"]) / 4.0 for x in rs) / len(rs)
            out.append(eff * real + (1 - eff) * surf)
        return _m(out)

    def jscore(E, t, c):
        return jsc(c, [t])

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

    def pareto_strong(a, tr, he):
        pts = [((_m(jscore(E, t, c) for t in tr),
                 _m(jscore(E, t, c) for t in he)), c) for c in a]
        front = []
        for (A, ca) in pts:
            if not any(B[0] >= A[0] and B[1] >= A[1] and (B[0] > A[0] or B[1] > A[1])
                       for (B, _cb) in pts):
                front.append(ca)
        return front or a[-1:]

    for g in range(1, gens + 1):
        # ── 世界漂移 ──
        if scen in ("world", "both") and g >= DRIFT_AT:
            r = random.Random(seed * 1000 + g)
            for e in E:
                if r.random() < rate:
                    e["true_quality"] = r.random() * 0.3
        # ── judge 漂移：judge 越来越看表象（eff 缓慢下降）──
        if scen in ("judge", "both") and g >= DRIFT_AT and not blind:
            # blind 时 judge 通道已被切断，表象漂移无法影响评价
            eff = max(0.30, eff0 - 0.04 * (g - DRIFT_AT + 1))

        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
        for _ in range(k_cur):
            cand = rnd.choice(arch[-3:])
            ch = mut(cand)
            d_tr = jsc(ch, tr) - jsc(cand, tr) + rnd.gauss(0, 0.05)
            d_he = jsc(ch, he) - jsc(cand, he) + rnd.gauss(0, 0.05)
            if d_tr > -tol:
                arch.append(ch)
            arch = pareto_strong(arch, tr, he)
            if len(arch) > cap:
                arch = rnd.sample(arch, cap)
            if d_tr > margin and d_he > 0 and jsc(ch, tr) > jsc(main, tr):
                main = ch

        anchor_hist.append(jsc(root, anchor_tasks))
        if detected_at is None and len(anchor_hist) >= 7:
            pre = statistics.mean(anchor_hist[-7:-1])
            if anchor_hist[-1] < pre - 0.02:
                detected_at = g
                if mode == "boost":
                    k_cur = kids * 4

    gain = _m(tscore(E, t, main) for t in audit_set) - base
    surf_mag_final = sum(getattr(main, k) for k in ("w_len", "w_fmt", "w_den", "w_cit"))
    return gain, (detected_at or -1), surf_mag_final


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    combos = [(sc, md, bl) for sc in ("world", "judge", "both")
              for md in ("never", "boost") for bl in (False, True)]
    for sc, md, bl in combos:
        k = f"{sc}_{md}{'_blind' if bl else ''}"
        got = res.get(k, [])
        for s in range(len(got) + 1, N_SEEDS + 1):
            try:
                got.append(run(s, sc, mode=md, blind=bl))
            except Exception as ex:
                print("ERR", k, s, ex)
                break
            res[k] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {k}: {len(res.get(k, []))}/{N_SEEDS}")

    if not all(len(res.get(f"{sc}_{md}{'_blind' if bl else ''}", [])) >= N_SEEDS
               for sc, md, bl in combos):
        print("未完成，续跑")
        return

    print("\n" + "=" * 74)
    print(f"E146c 锚定探针的混淆边界（n={N_SEEDS}）")
    print("%-8s %-8s %10s %10s %10s %20s" % ("场景", "盲评", "never", "boost", "触发率", "boost 收益"))
    for bl in (False, True):
        suf = "_blind" if bl else ""
        for sc in ("world", "judge", "both"):
            nv = [x[0] for x in res[f"{sc}_never{suf}"][:N_SEEDS]]
            bv = [x[0] for x in res[f"{sc}_boost{suf}"][:N_SEEDS]]
            trig = sum(1 for x in res[f"{sc}_boost{suf}"][:N_SEEDS] if x[1] > 0) / N_SEEDS
            d = [y - x for x, y in zip(nv, bv)]
            se = statistics.pstdev(d) / math.sqrt(len(d))
            print("%-8s %-8s %+10.4f %+10.4f %9.0f%% %+12.4f ± %.4f (t=%.2f)"
                  % (sc, "Y" if bl else "N", statistics.mean(nv), statistics.mean(bv),
                     trig * 100, statistics.mean(d), se,
                     statistics.mean(d) / se if se else 0))
        print("-" * 74)
    print("-" * 74)
    print("surf 权重终值（judge 漂移下应更高 = 系统学会迎合）:")
    for bl in (False, True):
        suf = "_blind" if bl else ""
        for sc in ("world", "judge", "both"):
            n = statistics.mean(x[2] for x in res[f"{sc}_never{suf}"][:N_SEEDS])
            b = statistics.mean(x[2] for x in res[f"{sc}_boost{suf}"][:N_SEEDS])
            print("  %-8s blind=%-3s never=%.2f  boost=%.2f  差=%+.2f"
                  % (sc, "Y" if bl else "N", n, b, b - n))
    print("=" * 74)


if __name__ == "__main__":
    main()
