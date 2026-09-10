"""E139 —— 参数元判断 II：tol / cap 是否也依赖世界？

第三十轮证明 margin 的最优值依赖世界（强信号 vs E3 原始结论相反）。
推论：任何"标定"出的参数都不可迁移。

本轮检验另两个参数：
  tol  档案准入宽松度（E7：宽松准入是双门的前提）
  cap  档案容量（E16：Pareto 防灾难性遗忘）

在【两个世界】各扫一遍：
  世界 A = 强信号（evolve31.build_world_strong, corr=0.85）
  世界 B = E3 原始（evolve3.evolve, reliability=0.6）

判据：若某参数的最优值在世界 A / B 不同 → 又是一个"不可标定"参数。
"""
import sys, os, json, statistics, math, random
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong, tscore, jscore

OUT = "/data/workspace/res_e139.json"
N_SEEDS = 24
GENS = 20


def run_A(seed, tol=0.04, cap=8, gens=GENS, kids=4, blind=True, scale=2.0, margin=0.0):
    """世界 A：强信号"""
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit)
    eff = 0.95 if blind else 0.5
    arch, main = [root], root

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

    for g in range(gens):
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
            if d_tr > margin and d_he > 0 and jsc(ch, tr) > jsc(main, tr):
                main = ch
    return _m(tscore(E, t, main) for t in audit) - base


def run_B(seed, margin=0.01, gated=True, **kw):
    """世界 B：E3 原始"""
    from evolve3 import evolve
    r = evolve(seed, gated=gated, margin=margin, **kw)
    return r['best_he'] - r['root_he']


SCAN = {
    "tol":  (0.0, 0.04, 0.10, 0.25),
    "cap":  (2, 4, 8, 16),
}


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    keys = [f"A_tol_{v}" for v in SCAN["tol"]] + [f"A_cap_{v}" for v in SCAN["cap"]]
    for k in keys:
        pname, val = k.split("_")[1], (int(k.split("_")[2]) if k.split("_")[1]=="cap" else float(k.split("_")[2]))
        got = res.get(k, [])
        for s in range(len(got) + 1, N_SEEDS + 1):
            try:
                got.append(run_A(s, **{pname: val}))
            except Exception as ex:
                print("ERR", k, s, ex)
                break
            res[k] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {k}: {len(res.get(k, []))}/{N_SEEDS}")

    if not all(len(res.get(k, [])) >= N_SEEDS for k in keys):
        print("未完成，续跑")
        return

    print("\n" + "=" * 66)
    print(f"E139 世界 A（强信号）参数扫描（n={N_SEEDS}）")
    for pname in ("tol", "cap"):
        print(f"  {pname}:")
        vals = SCAN[pname]
        row = []
        for v in vals:
            mu = statistics.mean(res[f"A_{pname}_{v}"][:N_SEEDS])
            row.append((v, mu))
        best = max(row, key=lambda x: x[1])
        for v, mu in row:
            mark = " ← 最优" if v == best[0] else ""
            print("    %-6s %+.4f%s" % (v, mu, mark))
    print("=" * 66)


if __name__ == "__main__":
    main()
