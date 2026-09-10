"""E143 —— 防御预算分配：在【复合危险】下，钱该花在哪？

前 33 轮分别证明了各机制有效，但都在单一危险下测。
真实系统多种危险并存，而预算（注意力）有限（E64/E93/E105）。

本轮：在【同时含 4 种危险】的世界里，用逐项叠加法测边际收益：
  危险：① judge 看表象  ② 低质量自写入  ③ 中途漂移  ④ 配置跑飞

对策（按成本从低到高）：
  blind   盲评（零边际成本）
  prune   整理（每 6 代清理）
  audit   真值审计（每 5 代，探针成本）
  monitor 停摆监控（零成本）

判据：逐项叠加，测每加一项的边际收益 / 成本。
E66 曾用此法发现"阶段5参数调优 −0.027"，本轮复用于防御。
"""
import sys, os, json, statistics, math, random
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong, retrieve_strong, tscore

OUT = "/data/workspace/res_e143.json"
N_SEEDS = 16
GENS = 24
COST = {"blind": 0, "monitor": 0, "prune": 6, "audit": 40}   # 注意力单位


def run(seed, use, gens=GENS, kids=4, scale=2.0, tol=0.04, margin=0.0,
        wq=0.2, drift=0.35):
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    arch, main, best, btr = [root], root, root, None
    eff = 0.95 if "blind" in use else 0.5
    probe = build_tasks(E, random.Random(4242), 4, offset=7)
    cap = 8
    reverts = reanchors = prunes = relaxes = 0
    stall = 0
    n_written = 0

    def jsc(c, tasks):
        rs = [retrieve_strong(E, t, c) for t in tasks]
        out = []
        for r in rs:
            if not r:
                out.append(0.0); continue
            real = sum(x["true_quality"] for x in r) / len(r)
            surf = sum((x["length"] + x["formatting"] + x["kw_density"]
                        + x["has_citation"]) / 4.0 for x in r) / len(r)
            out.append(eff * real + (1 - eff) * surf)
        return _m(out)

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

    def jscore(E, t, c):
        return jsc(c, [t])

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
        # ── 危险 ③ 漂移 ──
        if g == gens // 3:
            r = random.Random(seed + 999)
            for e in E:
                if r.random() < drift:
                    e["true_quality"] = r.random() * 0.3
        # ── 危险 ④ 配置跑飞 ──
        if g == gens // 2:
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

        # ── 危险 ② 低质量自写入 ──
        for wi in range(3):
            kw_i = (n_written + wi) % 6
            q = wq * 0.9 + (1 - wq) * 0.1 + rnd.gauss(0, 0.12)
            E.append({"id": f"w{n_written}", "kw": f"K{kw_i}", "topic": f"T{kw_i}",
                      "keywords": [f"K{kw_i}"], "content": f"自写{n_written}",
                      "importance": 2, "age_days": 0, "spur": 0,
                      "true_quality": max(0.0, min(1.0, q)),
                      "tf": max(0.0, min(1.0, q)),
                      "length": 0.95, "formatting": 0.95,
                      "kw_density": 0.95, "has_citation": 1.0})
            n_written += 1

        # ── 对策：停摆监控 ──
        if adopts == 0:
            stall += 1
        else:
            stall = 0
        if "monitor" in use and stall >= 3:
            margin = max(0.005, margin * 0.5)
            relaxes += 1
            stall = 0

        # ── 对策：整理 ──
        if "prune" in use and g % 6 == 0:
            before = len(E)
            E[:] = [e for e in E if (not e["id"].startswith("w"))
                    or e["true_quality"] > 0.5]
            prunes += before - len(E)

        # ── 对策：真值审计 ──
        if "audit" in use and g % 5 == 0:
            cur = _m(tscore(E, t, main) for t in probe)
            if btr is None:
                btr, best = cur, main
            elif cur < btr - 0.01:
                cb = _m(tscore(E, t, best) for t in probe)
                if cb > cur + 0.01:
                    main, arch = best, [best]
                    reverts += 1
                    btr, best = cb, main
                else:
                    btr, best = cur, main
                    reanchors += 1
            else:
                btr, best = cur, main

    gain = _m(tscore(E, t, main) for t in audit_set) - base
    return gain


STEPS = [
    ("base",    set()),
    ("+blind",  {"blind"}),
    ("+monitor", {"blind", "monitor"}),
    ("+prune",  {"blind", "monitor", "prune"}),
    ("+audit",  {"blind", "monitor", "prune", "audit"}),
]


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for name, use in STEPS:
        k = name
        got = res.get(k, [])
        for s in range(len(got) + 1, N_SEEDS + 1):
            try:
                got.append(run(s, use))
            except Exception as ex:
                print("ERR", k, s, ex)
                break
            res[k] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {k}: {len(res.get(k, []))}/{N_SEEDS}")

    if not all(len(res.get(n, [])) >= N_SEEDS for n, _ in STEPS):
        print("未完成，续跑")
        return

    print("\n" + "=" * 72)
    print(f"E143 复合危险下的防御边际收益（n={N_SEEDS}, {GENS} 代）")
    print("%-10s %10s %12s %10s %12s" % ("配置", "真值增益", "边际收益", "累计成本", "边际/成本"))
    prev = None
    cum = 0
    for name, use in STEPS:
        v = res[name][:N_SEEDS]
        mu = statistics.mean(v)
        if prev is None:
            print("%-10s %+10.4f %12s %10d %12s" % (name, mu, "—", 0, "—"))
        else:
            d = [y - x for x, y in zip(res[prev][:N_SEEDS], v)]
            md = statistics.mean(d)
            se = statistics.pstdev(d) / math.sqrt(len(d))
            added = use - set(STEPS[[n for n, _ in STEPS].index(prev)][1])
            cost = sum(COST.get(a, 0) for a in added)
            cum += cost
            per = (md / cost) if cost else float('inf')
            ps = "∞" if cost == 0 else "%.5f" % per
            print("%-10s %+10.4f %+8.4f±%.4f(t=%.2f) %4d %12s"
                  % (name, mu, md, se, md / se if se else 0, cum, ps))
        prev = name
    print("=" * 72)


if __name__ == "__main__":
    main()
