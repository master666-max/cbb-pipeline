"""E137b —— 精确界定：留出集门的价值来自【符号】还是【正阈值】？

E137 显示 margin=0 在干净世界与陷阱世界都最优。
这提出一个更精确的问题：E3「双门必需」到底必需的是哪一部分？

三种配置：
  nogate   无留出集门（只要求 d_tr > m）        ← 退化为单门
  sign     d_he > 0        （符号检验，margin=0）  ← E3 的最小形式
  pos      d_he > 0.05     （正阈值）

判据：
  若 sign >> nogate  → E3 成立，且价值在"符号"本身
  若 sign ≈ pos      → 正阈值无额外价值（E137 结论）
  若 sign ≈ nogate   → E3 在本世界不成立，需重新解释
"""
import sys, os, json, statistics, math, random
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong
from run_e137 import build_world_trap, retrieve_pf, tscore, jscore, mk_tasks, A_KW, B_KW

OUT = "/data/workspace/res_e137b.json"
N_SEEDS = 16
GENS = 20
MODES = ("nogate", "sign", "pos")


def run(seed, trap, mode, gens=GENS, kids=4, blind=True, scale=2.0, tol=0.04):
    rnd = random.Random(seed)
    E = build_world_trap(seed) if trap else build_world_strong(seed, corr=0.85)
    audit = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit)
    eff = 0.95 if blind else 0.5
    arch, main = [root], root
    cap = 8

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
            if mode == "nogate":
                ok = d_tr > 0.02
            elif mode == "sign":
                ok = d_tr > 0.02 and d_he > 0
            else:
                ok = d_tr > 0.02 and d_he > 0.05
            if ok and jsc(ch, tr) > jsc(main, tr):
                main = ch
    return _m(tscore(E, t, main) for t in audit) - base


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    keys = [f"{'trap' if tp else 'clean'}_{md}" for tp in (False, True) for md in MODES]
    for k in keys:
        tp, md = k.split("_")
        got = res.get(k, [])
        for s in range(len(got) + 1, N_SEEDS + 1):
            try:
                got.append(run(s, tp == "trap", md))
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
    print(f"E137b 门的价值来源（配对 n={N_SEEDS}）")
    print("%-8s %10s %10s %10s" % ("世界", "nogate", "sign(m=0)", "pos(m=0.05)"))
    for tp in ("clean", "trap"):
        v = {md: res[f"{tp}_{md}"][:N_SEEDS] for md in MODES}
        print("%-8s %10.4f %10.4f %10.4f" % (
            tp, statistics.mean(v["nogate"]),
            statistics.mean(v["sign"]), statistics.mean(v["pos"])))
        for a_md, b_md in (("nogate", "sign"), ("sign", "pos")):
            d = [x - y for x, y in zip(v[b_md], v[a_md])]
            se = statistics.pstdev(d) / math.sqrt(len(d))
            print("    %s − %s = %+.4f ± %.4f (t=%.2f)"
                  % (b_md, a_md, statistics.mean(d), se,
                     statistics.mean(d) / se if se else 0))
    print("=" * 70)


if __name__ == "__main__":
    main()
