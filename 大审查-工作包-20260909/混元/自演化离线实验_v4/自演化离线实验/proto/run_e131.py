"""E131 —— 在【漂移世界】重测 strict vs rolling

★ 关键修正：E127 的"strict 无效"结论建立在回退仅 0.5 次的基础上。
  审计没触发 → strict 与 rolling 无从区别 → 必然无差异。
  这与 E41 是同类错误：在不含该机制所防危险的环境里测试它。

本实验注入漂移（第 gens//3 代重洗部分条目质量），让审计真的触发。

配对设计：同一 seed 比较 strict vs rolling。
n = 44（可检出 0.03 效应，见第二十七轮样本量表）
"""
import sys, os, json, statistics, math, random
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, surf_mag, SURF
import evolve31
from evolve31 import build_world_strong, retrieve_strong, tscore, jscore, strip, frac

OUT = "/data/workspace/res_e131.json"
N_PAIRS = 44


def run(seed, mode, gens=24, kids=4, alpha=0.5, blind=True,
        scale=2.0, drift=0.35, audit=True):
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    eff = 0.95 if blind else alpha
    arch, main, best, btr = [root], root, root, None
    m, tol, cap = 0.02, 0.04, 8
    thr = 0.01
    probe = build_tasks(E, random.Random(4242), 4, offset=7)
    reverts = reanchors = 0
    degrade_streak = 0
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
        if audit and g % 5 == 0:
            cur = _m(tscore(E, t, main) for t in probe)
            if btr is None:
                btr, best = cur, main
            elif cur < btr - thr:
                degrade_streak += 1
                if degrade_streak >= 2 and mode == "reanchor":
                    btr, best, degrade_streak = cur, main, 0
                    reanchors += 1
                else:
                    main, arch = best, [best]
                    reverts += 1
                    if mode == "rolling":
                        btr, best = cur, main
            else:
                degrade_streak = 0
                if mode == "strict":
                    if cur > btr:
                        btr, best = cur, main
                else:
                    btr, best = cur, main
    gain = _m(tscore(E, t, main) for t in audit_set) - base
    return gain, reverts, reanchors


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    modes = ["rolling", "strict", "reanchor"]
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
        print(f"漂移世界 · 审计基线策略（配对 n={N_PAIRS}）")
        print("%-10s %10s %8s %8s" % ("策略", "真值增益", "回退", "重锚"))
        base_v = None
        for md in modes:
            v = [x[0] for x in res[md][:N_PAIRS]]
            rv = statistics.mean(x[1] for x in res[md][:N_PAIRS])
            ra = statistics.mean(x[2] for x in res[md][:N_PAIRS])
            print("%-10s %+10.4f %8.1f %8.1f" % (md, statistics.mean(v), rv, ra))
            if md == "rolling":
                base_v = v
            else:
                diff = [b - a for a, b in zip(base_v, v)]
                m_ = statistics.mean(diff)
                sd = statistics.pstdev(diff)
                se = sd / math.sqrt(len(diff))
                t = m_ / se if se else 0
                print("           vs rolling: %+.4f ± %.4f (t=%.2f, n=%d)"
                      % (m_, se, t, len(diff)))
        print("=" * 62)


if __name__ == "__main__":
    main()
