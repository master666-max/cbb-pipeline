"""E132 —— 重测 E27「回滚几乎无差」（差值仅 0.002，远低于检出限）

在漂移世界、配对 n=44 下重测三种策略：
  norevert   审计发现退化也不回滚，继续演化
  continue   回滚到历史最优，然后【继续】演化
  stop       回滚到历史最优，然后【停止】演化（冻结配置）

E27 原结论：stop(+0.0238) vs continue(+0.0221) 几乎无差 → "可回滚不是主要应对"
该差值 0.0017 远低于检出限 0.062，属假阴性高风险。
"""
import sys, os, json, statistics, math, random
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong, tscore, jscore

OUT = "/data/workspace/res_e132.json"
N_PAIRS = 44


def run(seed, mode, gens=24, kids=4, blind=True, scale=2.0, drift=0.35):
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    eff = 0.95 if blind else 0.5
    arch, main, best, btr = [root], root, root, None
    m, tol, cap = 0.02, 0.04, 8
    probe = build_tasks(E, random.Random(4242), 4, offset=7)
    reverts = 0
    frozen = False
    drift_at = gens // 3

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

    def pareto_strong(a, tr, he):
        pts = [((_m(jscore(E, t, c, eff) for t in tr),
                 _m(jscore(E, t, c, eff) for t in he)), c) for c in a]
        front = []
        for (A, ca) in pts:
            if not any(B[0] >= A[0] and B[1] >= A[1] and (B[0] > A[0] or B[1] > A[1])
                       for (B, _cb) in pts):
                front.append(ca)
        return front or a[-1:]

    for g in range(1, gens + 1):
        if g == drift_at:
            r = random.Random(seed + 999)
            for e in E:
                if r.random() < drift:
                    e["true_quality"] = r.random() * 0.3
        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
        if not frozen:
            for _ in range(kids):
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
        if g % 5 == 0:
            cur = _m(tscore(E, t, main) for t in probe)
            if btr is None:
                btr, best = cur, main
            elif cur < btr - 0.01:
                if mode == "norevert":
                    btr, best = cur, main
                else:
                    main, arch = best, [best]
                    reverts += 1
                    btr, best = cur, main
                    if mode == "stop":
                        frozen = True      # ★ 回滚后停止演化
            else:
                btr, best = cur, main
    gain = _m(tscore(E, t, main) for t in audit_set) - base
    return gain, reverts


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    modes = ["norevert", "continue", "stop"]
    for md in modes:
        got = res.get(md, [])
        for s in range(len(got) + 1, N_PAIRS + 1):
            try:
                got.append(run(s, md))
            except Exception as ex:
                print("ERR", md, s, ex)
                break
            res[md] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {md}: {len(res.get(md, []))}/{N_PAIRS}")

    if all(len(res.get(m, [])) >= N_PAIRS for m in modes):
        print("\n" + "=" * 62)
        print(f"E132 重测：回滚策略（漂移世界，配对 n={N_PAIRS}）")
        print("%-10s %10s %8s" % ("策略", "真值增益", "回退"))
        base_v = [x[0] for x in res["continue"][:N_PAIRS]]
        for md in modes:
            v = [x[0] for x in res[md][:N_PAIRS]]
            rv = statistics.mean(x[1] for x in res[md][:N_PAIRS])
            line = "%-10s %+10.4f %8.1f" % (md, statistics.mean(v), rv)
            if md != "continue":
                diff = [b - a for a, b in zip(base_v, v)]
                m_ = statistics.mean(diff)
                se = statistics.pstdev(diff) / math.sqrt(len(diff))
                line += "   vs continue: %+.4f ± %.4f (t=%.2f)" % (m_, se, m_ / se if se else 0)
            print(line)
        print("=" * 62)


if __name__ == "__main__":
    main()
