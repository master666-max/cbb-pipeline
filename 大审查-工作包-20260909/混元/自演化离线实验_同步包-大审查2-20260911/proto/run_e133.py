"""E133 —— 决定性：回退的价值取决于【退化原因】

E131/E132 显示漂移世界里回退有害（norevert 最好）。
但审计本该在"配置跑飞"时有用。若回退在两种场景下价值相反，
则正确的机制必须【先判别退化原因，再决定动作】。

2×2 设计：
  场景 drift   世界变（重洗 35% 条目质量）
  场景 corrupt 配置跑飞（第 drift_at 代强制把 champion 换成差配置）

  动作 norevert / revert

判据：
  drift   下 revert - norevert < 0  → 回退有害
  corrupt 下 revert - norevert > 0  → 回退有益
两者成立 → 必须判别；回退不是无条件正确。
"""
import sys, os, json, statistics, math, random
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong, tscore, jscore

OUT = "/data/workspace/res_e133.json"
N_PAIRS = 44


def run(seed, scene, mode, gens=24, kids=4, blind=True, scale=2.0):
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
    event_at = gens // 3

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
        if g == event_at:
            if scene == "drift":
                r = random.Random(seed + 999)
                for e in E:
                    if r.random() < 0.35:
                        e["true_quality"] = r.random() * 0.3
            else:   # corrupt：强制把 champion 换成差配置（模拟演化跑飞）
                main = Cfg2(w_kw=-2.0, w_content=-1.0, w_imp=-1.0, w_age=1.0,
                            w_len=6.0, w_fmt=6.0, w_den=6.0, w_cit=6.0)
                arch = [main]
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
        if g % 5 == 0:
            cur = _m(tscore(E, t, main) for t in probe)
            if btr is None:
                btr, best = cur, main
            elif cur < btr - 0.01:
                if mode == "revert":
                    main, arch = best, [best]
                    reverts += 1
                    btr, best = cur, main
                else:
                    btr, best = cur, main
            else:
                btr, best = cur, main
    gain = _m(tscore(E, t, main) for t in audit_set) - base
    return gain, reverts


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    keys = [f"{sc}_{md}" for sc in ("drift", "corrupt") for md in ("norevert", "revert")]
    for k in keys:
        sc, md = k.split("_")
        got = res.get(k, [])
        for s in range(len(got) + 1, N_PAIRS + 1):
            try:
                got.append(run(s, sc, md))
            except Exception as ex:
                print("ERR", k, s, ex)
                break
            res[k] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {k}: {len(res.get(k, []))}/{N_PAIRS}")

    if all(len(res.get(k, [])) >= N_PAIRS for k in keys):
        print("\n" + "=" * 66)
        print(f"E133 回退价值 × 退化原因（配对 n={N_PAIRS}）")
        print("%-9s %10s %10s %9s %22s" % ("场景", "不回退", "回退", "回退次数", "回退收益"))
        for sc in ("drift", "corrupt"):
            nv = [x[0] for x in res[f"{sc}_norevert"][:N_PAIRS]]
            rv = [x[0] for x in res[f"{sc}_revert"][:N_PAIRS]]
            nrev = statistics.mean(x[1] for x in res[f"{sc}_revert"][:N_PAIRS])
            diff = [b - a for a, b in zip(nv, rv)]
            m_ = statistics.mean(diff)
            se = statistics.pstdev(diff) / math.sqrt(len(diff))
            print("%-9s %+10.4f %+10.4f %9.1f   %+.4f ± %.4f (t=%.2f)"
                  % (sc, statistics.mean(nv), statistics.mean(rv), nrev,
                     m_, se, m_ / se if se else 0))
        print("=" * 66)


if __name__ == "__main__":
    main()
