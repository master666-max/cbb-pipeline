"""E146b —— 渐进 drift 的应对：检出后加预算还有效吗？

E146a 证明【锚定探针】在渐进 drift 下 100% 检出 / 0% 误报。
E145d 证明【一次性 drift】下加搜索预算有效（kids 4→16: +0.127, t=3.45）。

本轮问：**渐进 drift 下加预算是否仍有效？**
  渐进 drift 是持续的（每代都在变），与一次性不同：
  一次性 → 加预算帮系统"追上新世界"，追上就结束
  渐进   → 系统需要【持续追】，加预算可能只是"追得更快"但仍追不上

策略：
  never   不应对
  boost   检出后 kids ×4（E145d 的解药）
  fresh   检出后清空档案重跑
  shorten 检出后只用近期任务

对比 abrupt（一次性）作为参照。

设计：n=20，24 代，drift 从第 8 代开始
"""
import sys, os, json, statistics, math, random
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong, retrieve_strong, tscore

OUT = "/data/workspace/res_e146b.json"
N_SEEDS = 20
GENS = 24
DRIFT_AT = 8


def run(seed, mode, scen="gradual", rate=0.03, gens=GENS, kids=4,
        scale=2.0, tol=0.04, margin=0.0, eff=0.95):
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
    recent_pool = []
    k_cur = kids

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
        if scen == "abrupt" and g == DRIFT_AT:
            r = random.Random(seed + 999)
            for e in E:
                if r.random() < 0.35:
                    e["true_quality"] = r.random() * 0.3
        elif scen == "gradual" and g >= DRIFT_AT:
            r = random.Random(seed * 1000 + g)
            for e in E:
                if r.random() < rate:
                    e["true_quality"] = r.random() * 0.3

        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
        if mode == "shorten" and detected_at is not None:
            recent_pool.append(tr)
            if len(recent_pool) > 4:
                recent_pool.pop(0)
            tr = [t for sub in recent_pool for t in sub] or tr

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

        # ── 锚定探针检测（E146a：100%/0%）──
        anchor_hist.append(jsc(root, anchor_tasks))
        if detected_at is None and len(anchor_hist) >= 7:
            pre = statistics.mean(anchor_hist[-7:-1])
            if anchor_hist[-1] < pre - 0.02:
                detected_at = g
                if mode == "boost":
                    k_cur = kids * 4
                elif mode == "fresh":
                    arch = [main]

    gain = _m(tscore(E, t, main) for t in audit_set) - base
    return gain, (detected_at or -1)


def main():
    import sys as _s
    scen = _s.argv[1] if len(_s.argv) > 1 else "gradual"
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    modes = ("never", "boost", "fresh", "shorten")
    for md in modes:
        k = f"{scen}_{md}"
        got = res.get(k, [])
        for s in range(len(got) + 1, N_SEEDS + 1):
            try:
                got.append(run(s, md, scen=scen))
            except Exception as ex:
                print("ERR", k, s, ex)
                break
            res[k] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {k}: {len(res.get(k, []))}/{N_SEEDS}")

    if not all(len(res.get(f"{scen}_{m}", [])) >= N_SEEDS for m in modes):
        print("未完成，续跑")
        return

    print("\n" + "=" * 70)
    print(f"E146b 渐进 drift 应对（场景={scen}, n={N_SEEDS}）")
    print("%-10s %10s %10s %20s" % ("策略", "真值增益", "检出代", "vs never"))
    nv = [x[0] for x in res[f"{scen}_never"][:N_SEEDS]]
    for md in modes:
        v = [x[0] for x in res[f"{scen}_{md}"][:N_SEEDS]]
        det = [x[1] for x in res[f"{scen}_{md}"][:N_SEEDS]]
        avg_det = (statistics.mean(d for d in det if d > 0)
                   if any(d > 0 for d in det) else -1)
        line = "%-10s %+10.4f %10.1f" % (md, statistics.mean(v), avg_det)
        if md != "never":
            d = [y - x for x, y in zip(nv, v)]
            se = statistics.pstdev(d) / math.sqrt(len(d))
            line += "  %+.4f ± %.4f (t=%.2f)" % (
                statistics.mean(d), se, statistics.mean(d) / se if se else 0)
        print(line)
    print("=" * 70)


if __name__ == "__main__":
    main()
