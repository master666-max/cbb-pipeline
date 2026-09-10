"""E144 —— 危险数量扫描：架构在几种危险同时出现时崩溃？

E143 发现：4 种危险同时出现时，即使【全套防御】，终局仍是 −0.0187（负）。
这与 E60/E66/E80/E115 的"复合失配"一致，但从未量化临界点。

本轮：危险从 0 种逐项加到 4 种，全套防御固定，看收益曲线。
  ① surf   judge 看表象（eff=0.5）
  ② write  低质量自写入
  ③ drift  中途漂移
  ④ corrupt 配置跑飞

关键问题：
  Q1 崩溃发生在几种危险时？
  Q2 是"数量"还是"特定组合"导致？（对比：随机 2 种 vs 特定 2 种）

设计：n=16，全套防御（blind+monitor+prune+audit）
"""
import sys, os, json, statistics, math, random
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong, retrieve_strong, tscore

OUT = "/data/workspace/res_e144.json"
N_SEEDS = 16
GENS = 24
ALL = ("surf", "write", "drift", "corrupt")


def run(seed, dangers, gens=GENS, kids=4, scale=2.0, tol=0.04, wq=0.2):
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    arch, main, best, btr = [root], root, root, None
    eff = 0.5 if "surf" in dangers else 0.95     # 全套防御含盲评，故 surf 通过 eff 体现
    probe = build_tasks(E, random.Random(4242), 4, offset=7)
    cap = 8
    margin = 0.0
    n_written = 0
    stall = 0

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
        if "drift" in dangers and g == gens // 3:
            r = random.Random(seed + 999)
            for e in E:
                if r.random() < 0.35:
                    e["true_quality"] = r.random() * 0.3
        if "corrupt" in dangers and g == gens // 2:
            main = Cfg2(w_kw=-2.0, w_content=-1.0, w_imp=-1.0, w_age=1.0,
                        w_len=6.0, w_fmt=6.0, w_den=6.0, w_cit=6.0)
            arch = [main]

        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
        adopts = 0
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
                adopts += 1

        if "write" in dangers:
            for wi in range(3):
                kw_i = (n_written + wi) % 6
                q = wq * 0.9 + (1 - wq) * 0.1 + rnd.gauss(0, 0.12)
                E.append({"id": f"w{n_written}", "kw": f"K{kw_i}", "topic": f"T{kw_i}",
                          "keywords": [f"K{kw_i}"], "content": f"w{n_written}",
                          "importance": 2, "age_days": 0, "spur": 0,
                          "true_quality": max(0.0, min(1.0, q)),
                          "tf": max(0.0, min(1.0, q)),
                          "length": 0.95, "formatting": 0.95,
                          "kw_density": 0.95, "has_citation": 1.0})
                n_written += 1

        # 停摆监控
        if adopts == 0:
            stall += 1
        else:
            stall = 0
        if stall >= 3:
            margin = max(0.005, margin * 0.5)
            stall = 0
        # 整理
        if g % 6 == 0:
            E[:] = [e for e in E if (not e["id"].startswith("w"))
                    or e["true_quality"] > 0.5]
        # 审计
        if g % 5 == 0:
            cur = _m(tscore(E, t, main) for t in probe)
            if btr is None:
                btr, best = cur, main
            elif cur < btr - 0.01:
                cb = _m(tscore(E, t, best) for t in probe)
                if cb > cur + 0.01:
                    main, arch = best, [best]
                    btr, best = cb, main
                else:
                    btr, best = cur, main
            else:
                btr, best = cur, main

    return _m(tscore(E, t, main) for t in audit_set) - base


# 危险叠加顺序（按"最易发生"排序）+ 全部 2 种组合
SETS = [
    ("0 无", ()),
    ("1 surf", ("surf",)),
    ("2 +write", ("surf", "write")),
    ("3 +drift", ("surf", "write", "drift")),
    ("4 +corrupt", ("surf", "write", "drift", "corrupt")),
    ("alt 2: drift+corrupt", ("drift", "corrupt")),
    ("alt 2: write+drift", ("write", "drift")),
]


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for name, ds in SETS:
        got = res.get(name, [])
        for s in range(len(got) + 1, N_SEEDS + 1):
            try:
                got.append(run(s, ds))
            except Exception as ex:
                print("ERR", name, s, ex)
                break
            res[name] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {name}: {len(res.get(name, []))}/{N_SEEDS}")

    if not all(len(res.get(n, [])) >= N_SEEDS for n, _ in SETS):
        print("未完成，续跑")
        return

    print("\n" + "=" * 66)
    print(f"E144 危险数量扫描（全套防御，n={N_SEEDS}, {GENS} 代）")
    print("%-22s %10s %12s" % ("危险组合", "真值增益", "边际"))
    prev = None
    for name, ds in SETS[:5]:
        v = res[name][:N_SEEDS]
        mu = statistics.mean(v)
        if prev is None:
            print("%-22s %+10.4f %12s" % (name, mu, "—"))
        else:
            d = [y - x for x, y in zip(res[prev][:N_SEEDS], v)]
            se = statistics.pstdev(d) / math.sqrt(len(d))
            print("%-22s %+10.4f %+8.4f ±%.4f (t=%.2f)"
                  % (name, mu, statistics.mean(d), se,
                     statistics.mean(d) / se if se else 0))
        prev = name
    print("-" * 66)
    for name, ds in SETS[5:]:
        v = res[name][:N_SEEDS]
        print("%-22s %+10.4f" % (name, statistics.mean(v)))
    print("=" * 66)


if __name__ == "__main__":
    main()
