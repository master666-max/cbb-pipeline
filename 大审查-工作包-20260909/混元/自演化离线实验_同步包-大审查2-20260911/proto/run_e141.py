"""E141 —— 数据空间深化：自写入 + 整理的完整 2×2

第 26 轮（E121-E124）开了数据空间的口子但只做了 5 个实验。
第 25 轮发现"跨空间污染"：配置空间的审计管不住数据空间的污染（E119 −0.067）。

本轮做完整的 2×2：
  写入质量 wq ∈ {0.9 高, 0.2 低}   （系统写入条目的真实质量）
  整理     pr ∈ {False, True}      （定期淘汰低质量自写条目）

关键问题：
  Q1 整理在低质量写入下是否仍是解药？（E120 说 −0.055 → +0.018）
  Q2 整理 + 审计 是否配对？（E123 说审计×整理配对）
  Q3 高写入质量是否真的是 4 倍资产？（E119 说 +0.293）

设计：2(写入) × 2(整理) × 2(审计) = 8 组，n=16
"""
import sys, os, json, statistics, math, random
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong, tscore, jscore

OUT = "/data/workspace/res_e141.json"
N_SEEDS = 16
WRITE_PER_GEN = 3   # 每代写入条数（修正后）
GENS = 24


def run(seed, wq=0.9, prune=False, audit=True, gens=GENS, kids=4,
        blind=True, scale=2.0, tol=0.04, margin=0.0, prune_every=6):
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    eff = 0.95 if blind else 0.5
    arch, main, best, btr = [root], root, root, None
    cap = 8
    probe = build_tasks(E, random.Random(4242), 4, offset=7)
    reverts = reanchors = prunes = 0
    n_written = 0

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

        # ── 数据空间：自写入 ──
        # ★ 第一版失败：每代只写 1 条，24 代共 24 条，从未挤进 top-5
        #   （源条目质量 0.85，写入 0.24，源恒赢）→ 污染根本没发生
        #   修正：每代写 WRITE_PER_GEN 条，覆盖全部 6 类 kw，
        #   累积后低质量条目靠数量优势挤占 top-K（真实"记忆库膨胀"的形态）
        for wi in range(WRITE_PER_GEN):
            kw_i = (n_written + wi) % 6
            q = wq * 0.9 + (1 - wq) * 0.1 + rnd.gauss(0, 0.12)
            E.append({
                "id": f"w{n_written}", "kw": f"K{kw_i}", "topic": f"T{kw_i}",
                "keywords": [f"K{kw_i}"], "content": f"自写{n_written} K{kw_i}",
                "importance": 2, "age_days": 0, "spur": 0,
                "true_quality": max(0.0, min(1.0, q)),
                "tf": max(0.0, min(1.0, q)),
                # ★ 表象拉满：让低质量自写条目在 judge 眼里很好看
                #   （真实的"迎合式写入"：漂亮但空洞）
                "length": 0.9 + 0.1 * rnd.random(),
                "formatting": 0.9 + 0.1 * rnd.random(),
                "kw_density": 0.9 + 0.1 * rnd.random(),
                "has_citation": 1.0,
            })
            n_written += 1

        # ── 数据空间：整理（淘汰低质量自写条目）──
        if prune and g % prune_every == 0:
            before = len(E)
            E[:] = [e for e in E if (not e["id"].startswith("w"))
                    or e["true_quality"] > 0.5]
            prunes += before - len(E)

        if audit and g % 5 == 0:
            cur = _m(tscore(E, t, main) for t in probe)
            if btr is None:
                btr, best = cur, main
            elif cur < btr - 0.01:
                cur_best = _m(tscore(E, t, best) for t in probe)
                if cur_best > cur + 0.01:
                    main, arch = best, [best]
                    reverts += 1
                    btr, best = cur_best, main
                else:
                    btr, best = cur, main
                    reanchors += 1
            else:
                btr, best = cur, main

    gain = _m(tscore(E, t, main) for t in audit_set) - base
    return gain, {"reverts": reverts, "reanchors": reanchors,
                  "prunes": prunes, "written": n_written, "size": len(E)}


def retrieve_top(E, q, c, k=1):
    from evolve31 import retrieve_strong
    return retrieve_strong(E, q, c, k)


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    combos = [(wq, pr, bl) for wq in (0.9, 0.2) for pr in (False, True)
              for bl in (False, True)]
    for wq, pr, bl in combos:
        k = f"wq{wq}_{'pr' if pr else 'nopr'}_{'blind' if bl else 'see'}"
        got = res.get(k, [])
        for s in range(len(got) + 1, N_SEEDS + 1):
            try:
                got.append(run(s, wq=wq, prune=pr, audit=False, blind=bl))
            except Exception as ex:
                print("ERR", k, s, ex)
                break
            res[k] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {k}: {len(res.get(k, []))}/{N_SEEDS}")

    if not all(len(res.get(f"wq{wq}_{'pr' if pr else 'nopr'}_{'blind' if bl else 'see'}", [])) >= N_SEEDS
               for wq, pr, bl in combos):
        print("未完成，续跑")
        return

    print("\n" + "=" * 76)
    print(f"E141 数据空间 2×2×2（n={N_SEEDS}, {GENS} 代）")
    print("%-6s %-6s %-6s %10s %8s %8s" %
          ("写入", "整理", "judge", "真值增益", "重锚", "淘汰"))
    for wq in (0.9, 0.2):
        for pr in (False, True):
            for bl in (False, True):
                k = f"wq{wq}_{'pr' if pr else 'nopr'}_{'blind' if bl else 'see'}"
                v = res[k][:N_SEEDS]
                g = [x[0] for x in v]
                st = [x[1] for x in v]
                print("%-6s %-6s %-6s %+10.4f %8.1f %8.1f" % (
                    wq, "Y" if pr else "N", "盲" if bl else "看表象",
                    statistics.mean(g),
                    statistics.mean(s["reanchors"] for s in st),
                    statistics.mean(s["prunes"] for s in st)))
    print("-" * 76)
    for wq in (0.9, 0.2):
        for bl in (False, True):
            a = res[f"wq{wq}_nopr_{'blind' if bl else 'see'}"][:N_SEEDS]
            b = res[f"wq{wq}_pr_{'blind' if bl else 'see'}"][:N_SEEDS]
            da = [x[0] for x in a]; db = [x[0] for x in b]
            d = [y - x for x, y in zip(da, db)]
            se = statistics.pstdev(d) / math.sqrt(len(d))
            print("  写入%.1f %s: 整理收益 %+.4f ± %.4f (t=%.2f)" % (
                wq, "盲评" if bl else "看表象", statistics.mean(d), se,
                statistics.mean(d) / se if se else 0))
    print("=" * 76)


if __name__ == "__main__":
    main()
