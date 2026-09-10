"""E148 —— 未知未知：对【未建模故障】的鲁棒性边界

★ 全部 147 个实验的危险都是我【人为设计】的：
  drift / surf / write / corrupt / noise / 停摆 ...

真实系统会出现我没想到的失败模式。E78 已证明：
  **无外部信号时，内部指标只能识别 6 种失败中的 1 种。**

本轮方法：**随机故障注入（fault injection）**
  不看"哪种危险"，而是随机扰动系统的各个部件，看架构能否存活。
  这模拟"我没想到过的故障"。

注入点（14 个，覆盖三层 + 观测 + 数据）：
  观测层： judge 加噪 / judge 反转 / judge 饱和 / 探针被污染
  配置层： 变异算子失效 / 变异幅度突变 / Pareto 前沿退化 / 准入恒真
  数据层： 条目丢失 / 条目重复 / 质量字段损坏 / 自写入失控
  元层：   审计恒通过 / 审计恒失败 / 预算突然减半

判据：
  Q1 哪些故障是致命的（增益显著低于基线）？
  Q2 现有防御能挡住多少？（blind / anchor / prune / audit 全开 vs 全关）
  Q3 是否存在"内部指标全绿但真值崩塌"的故障？（E78 场景）

设计：n=10 per fault（先扫一遍找致命项），致命项再补到 n=20
"""
import sys, os, json, statistics, math, random
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong, retrieve_strong, tscore

OUT = "/data/workspace/res_e148.json"
N_SEEDS = 10
GENS = 20

FAULTS = [
    ("baseline",      "无故障（对照）"),
    # ── 观测层 ──
    ("judge_noise",   "judge 加噪 σ=0.3"),
    ("judge_invert",  "judge 反转（好坏颠倒）"),
    ("judge_saturate", "judge 饱和（>0.8 截断）"),
    ("probe_poison",  "探针集被污染（混入坏样本）"),
    # ── 配置层 ──
    ("mutate_dead",   "变异算子失效（子代=父代）"),
    ("scale_spike",   "变异幅度突变 ×10"),
    ("pareto_degrade", "Pareto 退化为取最近（F-20 回归）"),
    ("admit_always",  "准入恒真（tol=∞）"),
    # ── 数据层 ──
    ("entry_lose",    "每代丢失 5% 条目"),
    ("entry_dup",     "每代复制 5% 条目"),
    ("quality_corrupt", "质量字段随机损坏"),
    ("write_explode", "自写入量 ×10"),
    # ── 元层 ──
    ("audit_always",  "审计恒通过（门失效）"),
    ("audit_never",   "审计恒失败（永不回退）"),
    ("budget_halve",  "预算中途减半"),
]


def run(seed, fault, defend=True, gens=GENS, kids=4, scale=2.0,
        tol=0.04, margin=0.0, wq=0.9, stress=False):
    """stress=True：注入 drift，让审计真正有事可做

    ★ 修正：audit_always / audit_never / budget_halve 三个故障在【干净世界】
      与 baseline 逐位相同 —— 因为审计根本没触发过，改不改它都一样。
      识别信号：结果过于整齐（10 个 seed 完全相同）。
      必须在【审计会触发】的场景下才能测出差异。
    """
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    arch, main, best, btr = [root], root, root, None
    cap = 8
    probe = build_tasks(E, random.Random(4242), 4, offset=7)
    anchor_tasks = build_tasks(E, random.Random(31337), 8, offset=11)
    anchor_hist = []
    drift_at = None
    k_cur = kids
    n_written = 0
    reverts = 0

    eff = 0.95 if defend else 0.5       # 盲评
    use_anchor = defend
    use_prune = defend
    use_audit = defend

    def jsc(c, tasks):
        out = []
        for t in tasks:
            rs = retrieve_strong(E, t, c)
            if not rs:
                out.append(0.0); continue
            real = sum(x["true_quality"] for x in rs) / len(rs)
            surf = sum((x["length"] + x["formatting"] + x["kw_density"]
                        + x["has_citation"]) / 4.0 for x in rs) / len(rs)
            v = eff * real + (1 - eff) * surf
            if fault == "judge_noise":
                v += rnd.gauss(0, 0.3)
            elif fault == "judge_invert":
                v = 1.0 - v
            elif fault == "judge_saturate":
                v = min(v, 0.8)
            out.append(max(0.0, min(1.0, v)))
        return _m(out)

    def jscore(E, t, c):
        return jsc(c, [t])

    def mut(c):
        if fault == "mutate_dead":
            return c
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
                d[p] * (1 + rnd.choice([-0.4, -0.15, 0.2, 0.6]) * sc_eff)
                + rnd.choice([0, 0, 0.5, -0.5]) * sc_eff)), 4)
        return Cfg2(**d)

    sc_eff = scale * 10 if fault == "scale_spike" else scale

    def pareto_strong(a, tr, he):
        if fault == "pareto_degrade":
            return a[-cap:]                     # F-20 回归
        pts = [((_m(jscore(E, t, c) for t in tr),
                 _m(jscore(E, t, c) for t in he)), c) for c in a]
        front = []
        for (A, ca) in pts:
            if not any(B[0] >= A[0] and B[1] >= A[1] and (B[0] > A[0] or B[1] > A[1])
                       for (B, _cb) in pts):
                front.append(ca)
        return front or a[-1:]

    for g in range(1, gens + 1):
        if stress and g == gens // 3:
            r = random.Random(seed + 999)
            for e in E:
                if r.random() < 0.30:
                    e["true_quality"] = r.random() * 0.3
        # ── 数据层故障 ──
        if fault == "entry_lose" and g % 3 == 0:
            k = max(1, len(E) // 20)
            E[:] = E[:-k]
        elif fault == "entry_dup" and g % 3 == 0:
            k = max(1, len(E) // 20)
            E.extend(E[:k])
        elif fault == "quality_corrupt" and g % 4 == 0:
            r = random.Random(seed * 7 + g)
            for e in E:
                if r.random() < 0.1:
                    e["true_quality"] = r.random()

        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
        if fault == "probe_poison":
            tr = tr + [f"poison{rnd.randrange(1000)}" for _ in range(4)]

        if fault == "budget_halve" and g == gens // 2:
            k_cur = max(1, k_cur // 2)      # ★ 原本没实现

        for _ in range(k_cur):
            cand = rnd.choice(arch[-3:])
            ch = mut(cand)
            d_tr = jsc(ch, tr) - jsc(cand, tr) + rnd.gauss(0, 0.05)
            d_he = jsc(ch, he) - jsc(cand, he) + rnd.gauss(0, 0.05)
            tol_eff = 1e9 if fault == "admit_always" else tol
            if d_tr > -tol_eff:
                arch.append(ch)
            arch = pareto_strong(arch, tr, he)
            if len(arch) > cap:
                arch = rnd.sample(arch, cap) if fault != "pareto_degrade" else arch[-cap:]
            if d_tr > margin and d_he > 0 and jsc(ch, tr) > jsc(main, tr):
                main = ch

        # ── 数据空间：自写入 ──
        wn = 30 if fault == "write_explode" else 3
        for wi in range(wn):
            kw_i = (n_written + wi) % 6
            q = wq * 0.9 + 0.1 + rnd.gauss(0, 0.12)
            E.append({"id": f"w{n_written}", "kw": f"K{kw_i}", "topic": f"T{kw_i}",
                      "keywords": [f"K{kw_i}"], "content": f"w{n_written}",
                      "importance": 2, "age_days": 0, "spur": 0,
                      "true_quality": max(0.0, min(1.0, q)),
                      "tf": max(0.0, min(1.0, q)),
                      "length": 0.6, "formatting": 0.6,
                      "kw_density": 0.6, "has_citation": 0.5})
            n_written += 1

        # ── 整理 ──
        if use_prune and g % 6 == 0:
            E[:] = [e for e in E if (not e["id"].startswith("w"))
                    or e["true_quality"] > 0.5]

        # ── 锚定探针 ──
        if use_anchor:
            anchor_hist.append(jsc(root, anchor_tasks))
            if (len(anchor_hist) >= 7
                    and anchor_hist[-1] < sum(anchor_hist[-7:-1]) / 6.0 - 0.02):
                if drift_at is None:
                    drift_at = g
                    k_cur = kids * 4

        # ── 审计 ──
        if use_audit and g % 5 == 0:
            cur = _m(tscore(E, t, main) for t in probe)
            if fault == "audit_always":
                pass                      # 门失效：永不动作
            elif fault == "audit_never":
                btr, best = cur, main     # 恒失败：只记录不回退
            else:
                if btr is None:
                    btr, best = cur, main
                elif cur < btr - 0.01:
                    cb = _m(tscore(E, t, best) for t in probe)
                    if cb > cur + 0.01:
                        main, arch = best, [best]
                        btr, best = cb, main
                        reverts += 1
                    else:
                        btr, best = cur, main
                else:
                    btr, best = cur, main

    gain = _m(tscore(E, t, main) for t in audit_set) - base
    return gain


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    STRESS = {"audit_always", "audit_never", "budget_halve", "baseline"}
    for name, _ in FAULTS:
        for tag, df in (("def", True), ("bare", False)):
            k = f"{name}_{tag}"
            got = res.get(k, [])
            for s in range(len(got) + 1, N_SEEDS + 1):
                try:
                    got.append(run(s, name, defend=df,
                                   stress=(name in STRESS)))
                except Exception as ex:
                    print("ERR", k, s, ex)
                    break
                res[k] = got
                json.dump(res, open(OUT, "w"))
            done = len(res.get(k, []))
        print(f"  {name}: def={len(res.get(name+'_def',[]))} "
              f"bare={len(res.get(name+'_bare',[]))}", flush=True)

    if not all(len(res.get(f"{n}_{t}", [])) >= N_SEEDS
               for n, _ in FAULTS for t in ("def", "bare")):
        print("未完成，续跑")
        return

    print("\n" + "=" * 78)
    print(f"E148 未知故障注入（n={N_SEEDS}, {GENS} 代）")
    print("%-16s %-24s %10s %10s %12s" %
          ("故障", "说明", "有防御", "无防御", "防御收益"))
    base_def = statistics.mean(res["baseline_def"][:N_SEEDS])
    base_bare = statistics.mean(res["baseline_bare"][:N_SEEDS])
    rows = []
    for name, desc in FAULTS:
        dv = statistics.mean(res[f"{name}_def"][:N_SEEDS])
        bv = statistics.mean(res[f"{name}_bare"][:N_SEEDS])
        d = [y - x for x, y in zip(res[f"{name}_def"][:N_SEEDS],
                                   res[f"{name}_bare"][:N_SEEDS])]
        se = statistics.pstdev(d) / math.sqrt(len(d))
        t = statistics.mean(d) / se if se else 0
        rows.append((name, desc, dv, bv, t))
    rows_sorted = sorted(rows, key=lambda r: r[2])
    for name, desc, dv, bv, t in rows_sorted:
        flag = ""
        if name != "baseline":
            if dv < base_def - 0.05:
                flag = " ⬅致命"
            elif dv < base_def - 0.02:
                flag = " ⚠"
        print("%-16s %-24s %+10.4f %+10.4f %+8.4f(t=%+.1f)%s"
              % (name, desc[:24], dv, bv, dv - bv, t, flag))
    print("=" * 78)
    print(f"基线：有防御 {base_def:+.4f} / 无防御 {base_bare:+.4f}")


if __name__ == "__main__":
    main()
