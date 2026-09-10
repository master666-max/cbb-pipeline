"""E137 —— 元判断：最优 margin 是否依赖【世界是否含陷阱】？

E136 意外发现：在干净强信号世界里 margin=0 最好，且显著
  (0 vs 0.02: +0.0050 p=0.0003; 0 vs 0.05: +0.0325 p<0.0001)

这与 E3「双门必需」及"margin 是 P0 参数"的长期结论冲突。
推测：干净世界里留出集门只带来噪声成本，无收益；
只有【世界含陷阱】（伪特征在训练分布上与真信号相关、留出集上反转）时门才有用。

E3 的原始实验正是含陷阱的。所以：
  ★ 最优 margin 依赖世界是否含陷阱 → 参数不能在干净世界标定后外推。

设计 2×2：
  trap=False  干净世界
  trap=True   含伪特征 pf：在 A 组关键词上与 true_quality 正相关，
              在 B 组上反相关；训练任务取自 A 组，留出任务取自 B 组
  margin ∈ {0, 0.02, 0.05}
"""
import sys, os, json, statistics, math, random
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong

OUT = "/data/workspace/res_e137.json"
MARGINS = (0.0, 0.02, 0.05)
N_SEEDS = 24
GENS = 20
A_KW = ("K0", "K1", "K2")      # 训练分布
B_KW = ("K3", "K4", "K5")      # 留出分布


def build_world_trap(seed, n=60, kws=6, corr=0.85):
    """含伪特征的世界：pf 在 A 组与真值正相关，B 组反相关"""
    E = build_world_strong(seed, n=n, kws=kws, corr=corr)
    rnd = random.Random(seed + 555)
    for e in E:
        if e["kw"] in A_KW:
            e["pf"] = e["true_quality"] + rnd.gauss(0, 0.15)   # 正相关
        else:
            e["pf"] = 1.0 - e["true_quality"] + rnd.gauss(0, 0.15)  # 反相关
        e["pf"] = max(0.0, min(1.0, e["pf"]))
    return E


def retrieve_pf(E, q, c, k=5):
    """检索：w_imp 通道改为乘 pf（伪特征）而非 tf"""
    qw = (q["q"] if isinstance(q, dict) else q).split()
    out = []
    for e in E:
        kh = sum(1 for w in qw if w in e["kw"])
        ch = sum(1 for w in qw if w in e["content"])
        if c.filter_zero and kh == 0 and ch == 0:
            continue
        s = (c.w_kw * kh + c.w_content * ch
             + c.w_imp * (e.get("pf", 0.0) if "pf" in e else e["tf"])
             - c.w_age * (e["age_days"] / 400.0))
        s += (c.w_len * e["length"] + c.w_fmt * e["formatting"]
              + c.w_den * e["kw_density"] + c.w_cit * e["has_citation"])
        out.append((s, e["id"], e))
    out.sort(key=lambda x: (-x[0], x[1]))
    return [x[2] for x in out[:k]]


def tscore(E, task, c):
    rs = retrieve_pf(E, task, c)
    return sum(r["true_quality"] for r in rs) / len(rs) if rs else 0.0


def jscore(E, task, c, eff):
    rs = retrieve_pf(E, task, c)
    if not rs:
        return 0.0
    real = sum(r["true_quality"] for r in rs) / len(rs)
    surf = sum((r["length"] + r["formatting"] + r["kw_density"]
                + r["has_citation"]) / 4.0 for r in rs) / len(rs)
    return eff * real + (1 - eff) * surf


def mk_tasks(E, rnd, n, group):
    """从指定关键词组生成任务"""
    pool = [e for e in E if e["kw"] in group]
    if not pool:
        pool = E
    out = []
    for _ in range(n):
        e = pool[rnd.randrange(len(pool))]
        out.append({"q": f"T{rnd.randrange(16)} {e['kw']}", "kw": e["kw"],
                    "golden": e["id"]})
    return out


def run(seed, trap, margin, gens=GENS, kids=4, blind=True, scale=2.0, tol=0.04):
    rnd = random.Random(seed)
    E = build_world_trap(seed) if trap else build_world_strong(seed, corr=0.85)
    audit = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit)
    eff = 0.95 if blind else 0.5
    arch, main = [root], root
    m, cap = margin, 8

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
        tr = mk_tasks(E, rnd, 16, A_KW)
        he = mk_tasks(E, rnd, 16, B_KW) if trap else build_tasks(E, rnd, 16, offset=3)
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
    return _m(tscore(E, t, main) for t in audit) - base


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    keys = [f"{'trap' if tp else 'clean'}_{mg}" for tp in (False, True) for mg in MARGINS]
    for k in keys:
        tp, mg = k.split("_")
        got = res.get(k, [])
        for s in range(len(got) + 1, N_SEEDS + 1):
            try:
                got.append(run(s, tp == "trap", float(mg)))
            except Exception as ex:
                print("ERR", k, s, ex)
                break
            res[k] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {k}: {len(res.get(k, []))}/{N_SEEDS}")

    if not all(len(res.get(k, [])) >= N_SEEDS for k in keys):
        print("未完成，续跑")
        return

    print("\n" + "=" * 70)
    print(f"E137 最优 margin 是否依赖世界含陷阱（配对 n={N_SEEDS}）")
    print("%-8s %10s %10s %10s  %s" % ("世界", "m=0", "m=0.02", "m=0.05", "最优"))
    for tp in ("clean", "trap"):
        row, bm, bv = [], None, -1e9
        for mg in MARGINS:
            v = res[f"{tp}_{mg}"][:N_SEEDS]
            mu = statistics.mean(v)
            row.append(mu)
            if mu > bv:
                bv, bm = mu, mg
        print("%-8s %10.4f %10.4f %10.4f  m=%s" %
              (tp, row[0], row[1], row[2], bm))
    print("-" * 70)
    for tp in ("clean", "trap"):
        a = res[f"{tp}_0.0"][:N_SEEDS]
        b = res[f"{tp}_0.05"][:N_SEEDS]
        d = [x - y for x, y in zip(a, b)]
        se = statistics.pstdev(d) / math.sqrt(len(d))
        print("  %-6s margin0 − margin0.05 = %+.4f ± %.4f (t=%.2f)"
              % (tp, statistics.mean(d), se, statistics.mean(d) / se if se else 0))
    print("=" * 70)


if __name__ == "__main__":
    main()
