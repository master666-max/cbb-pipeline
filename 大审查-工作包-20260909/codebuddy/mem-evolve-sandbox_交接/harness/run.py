"""mem-evolve-sandbox 命令行入口。

用法见 docs/实验设计.md。所有结果落到 runs/ 下的 JSONL + summary.json，可复现、可审计。
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import bs3 as bs3mod          # noqa: E402
import evolve                  # noqa: E402
import gate                    # noqa: E402
import metrics                 # noqa: E402
import v4core                  # noqa: E402
from genome import DEFAULT, clamp                                # noqa: E402
from kernel import Library, equivalence_gate                     # noqa: E402
from world import NOW, TERRAINS, World                          # noqa: E402

ROOT = HERE.parent
RUNS = ROOT / "runs"


def _out(name):
    d = RUNS / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def _dump(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=str),
                          encoding="utf-8", newline="\n")


def _mean(xs):
    return round(statistics.fmean(xs), 6) if xs else 0.0


def _std(xs):
    return round(statistics.pstdev(xs), 6) if len(xs) > 1 else 0.0


# ─────────────────────────────────────────────────────────────
# 0. selftest：等价性门禁 + 冲突存在性门禁（实验能否开跑的前置条件）
# ─────────────────────────────────────────────────────────────

def cmd_selftest(a):
    b3 = bs3mod.load(a.src)
    world = World(seed=1, terrain="clean")
    eq = equivalence_gate(b3, world)
    print(f"[equiv] checked={eq['checked_pairs']} mismatch={len(eq['mismatch'])} "
          f"passed={eq['passed']}")
    for m in eq["mismatch"]:
        print("   ", m)

    # 冲突存在性门禁（报告实验设计失败 #4：目标不冲突时比较策略毫无意义）
    # 判据：(召回, -成本) 的 Pareto 前沿必须 ≥2 个点，否则"多目标/档案"类结论全部无意义。
    lib = Library(world.entries, NOW)
    grid = []
    for hb in (20, 100, 200, 400):
        for ma in (30, 180, 3650):
            g = clamp({**DEFAULT, "hot_budget": hb, "max_age_days": ma})
            lib.apply(g)
            p, _ = metrics.evaluate(world, lib, world.queries["audit"], g, k=5)
            grid.append({"hot_budget": hb, "max_age_days": ma,
                         "recall@5": round(p["recall@5"], 4), "MRR": round(p["MRR"], 4),
                         "cost": round(p["cost_norm"], 4),
                         "u": round(world.utility(p, 0, g), 4)})
    pts = [(r["recall@5"], -r["cost"]) for r in grid]

    def dominated(p, others):
        return any((o[0] >= p[0] and o[1] >= p[1] and (o[0] > p[0] or o[1] > p[1]))
                   for o in others if o != p)

    front = [p for p in pts if not dominated(p, pts)]
    conflict = len(set(front)) >= 2
    print("[conflict] grid:")
    for r in grid:
        print(f"   hot={r['hot_budget']:>3} age={r['max_age_days']:>4} "
              f"recall={r['recall@5']:.3f} mrr={r['MRR']:.3f} cost={r['cost']:.3f} u={r['u']:+.4f}")
    print(f"[conflict] pareto_front_size={len(set(front))} tradeoff_exists={conflict}")

    ok = eq["passed"] and conflict
    _dump(_out("selftest") / "selftest.json",
          {"equivalence": eq, "grid": grid, "front": sorted(set(front)), "conflict": conflict})
    print(f"\nselftest: {'PASS' if ok else 'FAIL'}（不通过则整个实验不得开跑）")
    return 0 if ok else 1


# ─────────────────────────────────────────────────────────────
# 1. consistency：C1–C5 一致性探针（v3 真身）
# ─────────────────────────────────────────────────────────────

def cmd_consistency(a):
    b3 = bs3mod.load(a.src)
    res = bs3mod.consistency_suite(b3, str(a.src), n_proc=a.procs)

    # v4 对照臂 G6
    tmp = Path(tempfile.mkdtemp(prefix="v4_"))
    v4 = v4core.V4(tmp)
    for i in range(6):
        v4.append(bs3mod.entry(i))
    v4.snapshot_to_human()          # 人侧抄录（攻击前）
    doc4 = v4.doctor()
    v4.truncate(2)                  # 攻击者重算 state.json，但拿不到人侧锚点
    doc4t = v4.doctor()
    out = {"v3": res, "v4": {"clean": doc4, "after_truncate": doc4t}}
    _dump(_out("consistency") / "consistency.json", out)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    return 0


# ─────────────────────────────────────────────────────────────
# 2. concurrency：v3 vs v4 并发写丢失率
# ─────────────────────────────────────────────────────────────

def cmd_concurrency(a):
    b3 = bs3mod.load(a.src)
    v3 = bs3mod.probe_concurrency(b3, str(a.src), n_proc=a.procs)

    tmp = Path(tempfile.mkdtemp(prefix="v4conc_"))
    v4 = v4core.V4(tmp)
    for i in range(3):
        v4.append(bs3mod.entry(i))
    procs = [subprocess.Popen(
        [sys.executable, "-c", v4core.V4_WORKER, str(tmp), str(i), str(HERE)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for i in range(a.procs)]
    for p in procs:
        p.wait()
    expect = 3 * 1 + a.procs * 5
    actual = v4.importance_accum()
    v4res = {"expected_accum": expect, "actual_accum": actual,
             "loss_rate": round(1 - actual / expect, 4)}

    out = {"v3": v3, "v4": v4res}
    _dump(_out("consistency") / "concurrency.json", out)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


# ─────────────────────────────────────────────────────────────
# 3. evolve：主实验
# ─────────────────────────────────────────────────────────────

def cmd_evolve(a):
    rows = []
    outdir = _out(f"evolve_{a.terrain}{('_' + a.tag) if a.tag else ''}_{int(time.time())}")
    for seed in range(a.seeds):
        for cfg in a.cfgs:
            w = World(seed=seed + 1, terrain=a.terrain)
            if a.terrain == "switch":
                w.switch_gen = a.gens // 2
            if a.terrain == "drift":
                w.drift_alpha = a.alpha
            r = evolve.run_once(w, cfg=cfg, seed=seed + 1, gens=a.gens,
                                fanout=a.fanout, n_genes=a.n_genes,
                                rotate=a.rotate, genes=a.genes,
                                use_cheap=not a.no_cheap,
                                use_holdout_gate=not a.no_holdout,
                                use_stall=not a.no_stall,
                                archive_mode=("single" if a.archive == "single" else "pareto"))
            r["tag"] = a.tag
            rows.append({k: v for k, v in r.items() if k != "log"})
            _dump(outdir / f"log_s{seed+1}_{cfg}.json", {"log": r["log"], "summary": rows[-1]})
            print(f"seed={seed+1:>3} cfg={cfg:<16} Δaudit={r['delta']:+.4f} "
                  f"recall@5={r['final_recall@5']:.3f} evals={r['evals']} "
                  f"adopt={r['adoptions']}/{a.gens} {r['wall_seconds']}s")

    summary = {}
    for cfg in a.cfgs:
        ds = [r["delta"] for r in rows if r["cfg"] == cfg]
        rc = [r["final_recall@5"] for r in rows if r["cfg"] == cfg]
        ev = [r["evals"] for r in rows if r["cfg"] == cfg]
        sel = [r for r in rows if r["cfg"] == cfg]
        esc = [1 if r.get("escaped_local_optimum") else 0 for r in sel]
        gap = [r.get("final_self_report_gap", 0.0) for r in sel]
        summary[cfg] = {"n": len(ds), "delta_mean": _mean(ds), "delta_std": _std(ds),
                        "recall_mean": _mean(rc), "evals_mean": _mean(ev),
                        "positive_seeds": sum(1 for d in ds if d > 0),
                        "escaped": f"{sum(esc)}/{len(esc)}",
                        "self_report_gap": _mean(gap),
                        "peak_u": _mean([r.get("peak_audit_u", 0.0) for r in sel]),
                        "drawdown": _mean([r.get("drift_drawdown", 0.0) for r in sel]),
                        "frozen": f"{sum(1 for r in sel if r.get('frozen_by_anchor'))}/{len(sel)}",
                        "anchor_agreement_min": _mean([r.get("anchor_agreement_min", 1.0) for r in sel])}
    _dump(outdir / "summary.json", {"args": vars(a), "rows": rows, "summary": summary})
    print("\n=== summary ===")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


# ─────────────────────────────────────────────────────────────
# 4. matrix：全场景 × 对照臂矩阵（E63 风格）
# ─────────────────────────────────────────────────────────────

def cmd_matrix(a):
    outdir = _out(f"matrix_{int(time.time())}")
    table, rows = {}, []
    for terrain in (a.terrains or list(TERRAINS)):
        table[terrain] = {}
        for cfg in a.cfgs:
            ds = []
            for seed in range(a.seeds):
                w = World(seed=seed + 1, terrain=terrain)
                if terrain == "switch":
                    w.switch_gen = a.gens // 2
                r = evolve.run_once(w, cfg=cfg, seed=seed + 1, gens=a.gens,
                                    fanout=a.fanout, rotate=a.rotate)
                ds.append(r["delta"])
                rows.append({"terrain": terrain, "cfg": cfg, "seed": seed + 1,
                             "delta": r["delta"], "recall@5": r["final_recall@5"],
                             "MRR": r["final_MRR"], "evals": r["evals"],
                             "top10_evolved": r["top10_quality_evolved"],
                             "top10_selfrep": r["top10_quality_selfreported"]})
            table[terrain][cfg] = {"delta_mean": _mean(ds), "delta_std": _std(ds),
                                   "positive": sum(1 for d in ds if d > 0), "n": len(ds)}
        print(f"[{terrain}] " + " | ".join(
            f"{c}:{table[terrain][c]['delta_mean']:+.4f}" for c in a.cfgs))

    _dump(outdir / "matrix.json", {"table": table, "rows": rows})
    print("\n=== matrix ===")
    print(json.dumps(table, ensure_ascii=False, indent=1))
    return 0


# ─────────────────────────────────────────────────────────────
# 4b. sweep：drift 地形 α 扫描（判定 H7；α=0 是零误报对照）
# ─────────────────────────────────────────────────────────────

def cmd_show(a):
    """通用汇总打印：接受 summary.json 路径或 runs/ 下的目录名（取最新）。"""
    p = Path(a.path)
    if not p.exists():
        cands = (sorted((ROOT / "runs").glob(f"*{a.path}*/summary.json"))
                 or sorted((ROOT / "runs").glob(f"*{a.path}*/*.json"))
                 or sorted((ROOT / "runs").glob(f"*{a.path}*.json")))
        if not cands:
            print(f"找不到 {a.path}")
            return 1
        p = cands[-1]
    if p.is_dir():
        p = p / "summary.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    print(f"# {p}")
    summ = d.get("summary", d.get("table", d))
    for cfg, v in summ.items():
        if not isinstance(v, dict):
            continue
        if v and all(isinstance(x, dict) for x in v.values()):   # 两层：terrain → arm
            print(f"[{cfg}]")
            for arm, vv in v.items():
                print(f"  {arm:<18}{_cols(vv)}")
        else:
            print(f"{cfg:<18}{_cols(v)}")
    return 0


def _cols(v):
    return "  ".join(f"{k}={val}" for k, val in v.items()
                     if k in ("n", "delta_mean", "delta_std", "recall_mean",
                              "evals_mean", "positive_seeds", "escaped",
                              "drawdown_mean", "self_report_gap", "frozen",
                              "agreement_min", "champion_W1", "archive_best_W1"))


ABLATIONS = [
    # 留一法：从"完整两级门控"逐项拆掉一条护栏，测它的边际贡献
    ("full",            dict(cfg="two-tier")),
    ("-cheap",          dict(cfg="two-tier", use_cheap=False)),
    ("-holdout-gate",   dict(cfg="two-tier", use_holdout_gate=False)),
    ("-pareto-archive", dict(cfg="two-tier", archive_mode="single")),
    ("-stall-monitor",  dict(cfg="two-tier", use_stall=False)),
    ("none(全拆)",       dict(cfg="none")),
]


def cmd_ablate(a):
    """E67 消融：哪条护栏在赚钱（报告 E66 说档案+锚定占 85%，本沙盒逐项验证）。"""
    outdir = _out(f"ablate_{int(time.time())}")
    table, rows = {}, []
    for terrain in a.terrains:
        table[terrain] = {}
        for name, kw in ABLATIONS:
            ds, rc, ev, esc = [], [], [], []
            for seed in range(a.seeds):
                w = World(seed=seed + 1, terrain=terrain)
                if terrain == "switch":
                    w.switch_gen = a.gens // 2
                r = evolve.run_once(w, seed=seed + 1, gens=a.gens, fanout=a.fanout,
                                    genes=a.genes, **kw)
                ds.append(r["delta"]); rc.append(r["final_recall@5"]); ev.append(r["evals"])
                esc.append(1 if r.get("escaped_local_optimum") else 0)
                rows.append({"terrain": terrain, "arm": name, "seed": seed + 1,
                             "delta": r["delta"], "recall@5": r["final_recall@5"],
                             "evals": r["evals"]})
            table[terrain][name] = {"delta_mean": _mean(ds), "delta_std": _std(ds),
                                    "recall_mean": _mean(rc), "evals_mean": _mean(ev),
                                    "escaped": f"{sum(esc)}/{len(esc)}"}
        base = table[terrain].get("full", {}).get("delta_mean", 0.0)
        print(f"[{terrain}] full Δ={base:+.4f}")
        for name, _ in ABLATIONS:
            v = table[terrain][name]
            print(f"    {name:<18} Δ={v['delta_mean']:+.4f}  相对 full "
                  f"{v['delta_mean'] - base:+.4f}  recall={v['recall_mean']:.3f} "
                  f"evals={v['evals_mean']:.0f} escaped={v['escaped']}", flush=True)
    _dump(outdir / "ablate.json", {"table": table, "rows": rows})
    print("\n=== ablation ===")
    print(json.dumps(table, ensure_ascii=False, indent=1))
    return 0


def cmd_noise(a):
    """E70 金标噪声：独立(E52) vs 相关(E57)。审计集始终干净，故 ΔU 是可信标尺。"""
    outdir = _out(f"noise_{int(time.time())}")
    conds = [("clean", 0.0, "none")]
    for p in a.ps:
        for kind in ("independent", "correlated"):
            conds.append((f"{kind[:4]}{p}", p, kind))
    table, rows = {}, []
    for name, p, kind in conds:
        ds, rc = [], []
        for seed in range(a.seeds):
            w = World(seed=seed + 1, terrain=a.terrain, noise_p=p, noise_kind=kind)
            r = evolve.run_once(w, cfg=a.cfg, seed=seed + 1, gens=a.gens, fanout=a.fanout)
            ds.append(r["delta"]); rc.append(r["final_recall@5"])
            rows.append({"cond": name, "p": p, "kind": kind, "seed": seed + 1,
                         "delta": r["delta"], "recall@5": r["final_recall@5"]})
        table[name] = {"p": p, "kind": kind, "delta_mean": _mean(ds), "delta_std": _std(ds),
                       "recall_mean": _mean(rc),
                       "positive": f"{sum(1 for d in ds if d > 0)}/{len(ds)}"}
        base = table["clean"]["delta_mean"]
        print(f"{name:<16} Δ={table[name]['delta_mean']:+.4f} 相对 clean "
              f"{table[name]['delta_mean'] - base:+.4f}  recall={table[name]['recall_mean']:.3f} "
              f"{table[name]['positive']}", flush=True)
    # 配对 bootstrap：各噪声条件 vs clean（同源种子配对）
    rng = random.Random(20260908)
    clean = {r["seed"]: r["delta"] for r in rows if r["cond"] == "clean"}
    print("\n配对检验（clean − 条件，bootstrap 95% 下界 > 0 表示噪声造成显著损失）")
    for name, _, _ in conds:
        if name == "clean":
            continue
        cur = {r["seed"]: r["delta"] for r in rows if r["cond"] == name}
        seeds = sorted(set(clean) & set(cur))
        d = [clean[s] - cur[s] for s in seeds]
        lo, mean = gate.boot_ci_lower(d, rng)
        print(f"  {name:<16} 损失={mean:+.4f} 下界={lo:+.4f} "
              f"{'显著' if lo > 0 else '不显著'}  ({sum(1 for x in d if x > 0)}/{len(seeds)})")
    # 相关 vs 独立（同噪声量）
    for p in a.ps:
        a_, b_ = ({r["seed"]: r["delta"] for r in rows if r["cond"] == f"inde{p}"},
                  {r["seed"]: r["delta"] for r in rows if r["cond"] == f"corr{p}"})
        seeds = sorted(set(a_) & set(b_))
        if not seeds:
            continue
        d = [a_[s] - b_[s] for s in seeds]
        lo, mean = gate.boot_ci_lower(d, rng)
        print(f"  独立{p} − 相关{p}: 差={mean:+.4f} 下界={lo:+.4f} "
              f"{'相关噪声显著更毒' if lo > 0 else '未达显著'}")
    _dump(outdir / "noise.json", {"table": table, "rows": rows})
    return 0


def cmd_gate_budget(a):
    """E71 注意力预算 → 门控判决样本数 → 终局效用（E17 + E64 的机制性复现）。"""
    outdir = _out(f"gate_budget_{int(time.time())}")
    out = []
    for b in a.budgets:
        n_t = max(2, min(40, b // 10))
        ds, rc = [], []
        for seed in range(a.seeds):
            w = World(seed=seed + 1, terrain=a.terrain)
            r = evolve.run_once(w, cfg="two-tier", seed=seed + 1, gens=a.gens,
                                fanout=a.fanout, gate_tasks=n_t)
            ds.append(r["delta"]); rc.append(r["final_recall@5"])
        out.append({"budget": b, "gate_tasks": n_t, "delta_mean": _mean(ds),
                    "delta_std": _std(ds), "recall_mean": _mean(rc),
                    "positive": f"{sum(1 for d in ds if d > 0)}/{len(ds)}"})
        print(f"budget={b:>4} 判决样本={n_t:>2}  Δ={_mean(ds):+.4f} "
              f"recall={_mean(rc):.3f}  {out[-1]['positive']}", flush=True)
    _dump(outdir / "gate_budget.json", out)
    return 0


def cmd_calibrate(a):
    """锚定阈值标定（红线 34 / E34 教训）：先在**零漂移**基线上测一致率分布，
    再决定阈值。未经标定直接套 0.85 → 实测 11/12 误报并冻结演化。
    """
    outdir = _out(f"calibrate_{int(time.time())}")
    dist = {}
    for alpha in a.alphas:
        vals = []
        for seed in range(a.seeds):
            w = World(seed=seed + 1, terrain="drift")
            w.drift_alpha = alpha
            w.drift_start = a.drift_start
            r = evolve.run_once(w, cfg="two-tier+anchor", seed=seed + 1, gens=a.gens)
            vals += [x["anchor"]["agreement"] for x in r["log"] if x.get("anchor")]
        vals.sort()
        if not vals:
            continue
        dist[str(alpha)] = {"n": len(vals), "min": round(vals[0], 4),
                            "p5": round(vals[int(0.05 * len(vals))], 4),
                            "median": round(vals[len(vals) // 2], 4),
                            "max": round(vals[-1], 4)}
        print(f"α={alpha}: n={len(vals)} min={vals[0]:.3f} p5={dist[str(alpha)]['p5']:.3f} "
              f"median={dist[str(alpha)]['median']:.3f} max={vals[-1]:.3f}", flush=True)

    zero = dist.get("0.0") or dist.get("0")
    rec = None
    if zero:
        # 零误报要求：阈值 ≤ 零漂移下观测到的最低一致率（再留一点余量）
        rec = round(max(0.0, zero["min"] - 0.02), 4)
        print(f"\n[标定] 零误报上界 = {zero['min']:.3f} → 建议 ANCHOR_THRESHOLD = {rec}")
        print(f"用法：$env:ANCHOR_THRESHOLD='{rec}'  然后重跑 sweep")
    _dump(outdir / "calibrate.json", {"dist": dist, "recommended_threshold": rec})
    return 0


def cmd_sweep_show(a):
    """把 sweep.json 打成紧凑表（避免手工翻 JSON）。"""
    files = sorted((ROOT / "runs").glob("drift_sweep_*/sweep.json"))
    if not files:
        print("没有 sweep 结果，先跑 run.py sweep")
        return 1
    f = files[-1] if a.latest else Path(a.path or files[-1])
    blob = json.loads(Path(f).read_text(encoding="utf-8"))
    d, rows = blob["table"], blob["rows"]
    print(f"# {f}")
    print(f"{'alpha':<6}{'cfg':<18}{'Δaudit':>9}{'peak':>8}{'回撤':>9}{'自报-真实':>10}{'冻结':>8}{'agreement':>11}")
    for alp, row in d.items():
        for cfg, v in row.items():
            print(f"{alp:<6}{cfg:<18}{v['delta_mean']:>+9.4f}{v['peak_mean']:>8.3f}"
                  f"{v['drawdown_mean']:>9.4f}{v['self_report_gap']:>+10.3f}"
                  f"{v['frozen']:>8}{v['agreement_min']:>11.3f}")

    # 配对 bootstrap：同种子、同 α 下，各臂与**第一个臂（基线）**配对（红线 10/15）
    order = [c for c in blob.get("args", {}).get("cfgs", [])]
    cfgs = [c for c in order if c in {r["cfg"] for r in rows}] or sorted({r["cfg"] for r in rows})
    if len(cfgs) >= 2:
        base = cfgs[0]
        print(f"\n配对检验（基线 = {base}；同种子配对，bootstrap 95% 下界，判据 下界 > 0）")
        print(f"{'alpha':<6}{'对比臂':<20}{'ΔU 差':>9}{'下界':>9}"
              f"{'回撤差':>9}{'下界':>9}{'缺口差':>9}{'下界':>9}{'回撤差>0':>10}")
        rng = random.Random(20260908)
        for alp in sorted({r["alpha"] for r in rows}, key=float):
            mb = {r["seed"]: r for r in rows if r["alpha"] == alp and r["cfg"] == base}
            for c in cfgs[1:]:
                mc = {r["seed"]: r for r in rows if r["alpha"] == alp and r["cfg"] == c}
                seeds = sorted(set(mb) & set(mc))
                if not seeds:
                    continue
                dd = [mb[s]["delta"] - mc[s]["delta"] for s in seeds]
                dw = [mb[s]["drawdown"] - mc[s]["drawdown"] for s in seeds]
                dg = [mb[s]["gap"] - mc[s]["gap"] for s in seeds]
                lo_d, _ = gate.boot_ci_lower(dd, rng)
                lo_w, _ = gate.boot_ci_lower(dw, rng)
                lo_g, _ = gate.boot_ci_lower(dg, rng)
                print(f"{str(alp):<6}{c:<20}{statistics.fmean(dd):>+9.4f}{lo_d:>+9.4f}"
                      f"{statistics.fmean(dw):>+9.4f}{lo_w:>+9.4f}"
                      f"{statistics.fmean(dg):>+9.4f}{lo_g:>+9.4f}"
                      f"{sum(1 for x in dw if x > 0):>7}/{len(seeds)}")
    return 0


def cmd_sweep(a):
    outdir = _out(f"drift_sweep_{int(time.time())}")
    table, rows = {}, []
    for alpha in a.alphas:
        table[str(alpha)] = {}
        for cfg in a.cfgs:
            ds, dd, gap, froz, ag = [], [], [], [], []
            for seed in range(a.seeds):
                w = World(seed=seed + 1, terrain="drift")
                w.drift_alpha = alpha
                w.drift_start = a.drift_start
                r = evolve.run_once(w, cfg=cfg, seed=seed + 1, gens=a.gens,
                                    fanout=a.fanout)
                ds.append(r["delta"])
                dd.append(r["drift_drawdown"])
                gap.append(r["final_self_report_gap"])
                froz.append(1 if r["frozen_by_anchor"] else 0)
                ag.append(r["anchor_agreement_min"])
                rows.append({"alpha": alpha, "cfg": cfg, "seed": seed + 1,
                             "delta": r["delta"], "drawdown": r["drift_drawdown"],
                             "peak": r["peak_audit_u"], "gap": r["final_self_report_gap"],
                             "frozen": r["frozen_by_anchor"],
                             "agreement_min": r["anchor_agreement_min"]})
            table[str(alpha)][cfg] = {
                "delta_mean": _mean(ds), "delta_std": _std(ds),
                "drawdown_mean": _mean(dd), "peak_mean": _mean(
                    [r["peak"] for r in rows if r["alpha"] == alpha and r["cfg"] == cfg]),
                "self_report_gap": _mean(gap),
                "frozen": f"{sum(froz)}/{len(froz)}",
                "agreement_min": _mean(ag),
            }
        line = " | ".join(
            f"{c}: Δ={table[str(alpha)][c]['delta_mean']:+.4f} "
            f"回撤={table[str(alpha)][c]['drawdown_mean']:.4f} "
            f"冻结={table[str(alpha)][c]['frozen']} "
            f"agree={table[str(alpha)][c]['agreement_min']:.3f}" for c in a.cfgs)
        print(f"α={alpha}: {line}", flush=True)
    _dump(outdir / "sweep.json", {"table": table, "rows": rows, "args": vars(a)})
    print("\n=== drift α sweep ===")
    print(json.dumps(table, ensure_ascii=False, indent=1))
    return 0


# ─────────────────────────────────────────────────────────────
# 5. budget：注意力预算 → 终局效用曲线（E64 复现）
# ─────────────────────────────────────────────────────────────

def cmd_budget(a):
    outdir = _out(f"budget_{int(time.time())}")
    out = []
    for b in a.budgets:
        g = metrics.max_gens(b, init_cost=a.init_cost)
        ds = []
        for seed in range(a.seeds):
            w = World(seed=seed + 1, terrain="clean")
            r = evolve.run_once(w, cfg="two-tier", seed=seed + 1, gens=max(1, g))
            ds.append(r["delta"])
        out.append({"budget": b, "max_gens": g, "delta_mean": _mean(ds), "delta_std": _std(ds)})
        print(f"budget={b:>4} gens={g:>3} Δ={_mean(ds):+.4f}")
    _dump(outdir / "budget.json", out)
    return 0


# ─────────────────────────────────────────────────────────────
# 6. forget / reorg：专项能力实验
# ─────────────────────────────────────────────────────────────

def cmd_forget(a):
    """E16 复现：目标切换后旧目标能力的保留度（单一最优 vs Pareto 档案）。"""
    outdir = _out(f"forget_{int(time.time())}")
    rows = []
    for seed in range(a.seeds):
        for mode in ("single", "pareto"):
            w = World(seed=seed + 1, terrain="switch")
            w.switch_gen = a.gens // 2
            r = evolve.run_once(w, cfg="two-tier", seed=seed + 1, gens=a.gens,
                                archive_mode=mode)
            lib = Library(w.entries, NOW)
            lib.apply(clamp(DEFAULT))
            before, _ = metrics.evaluate(w, lib, w.queries["audit"], clamp(DEFAULT), k=5)
            rows.append({"seed": seed + 1, "archive": mode,
                         "old_objective_before": round(before["recall@5"], 4),
                         "final_audit_u": r["final_audit_u"],
                         "delta": r["delta"],
                         "champion_W1": r["champion_W1"],
                         "archive_best_W1": r["archive_best_W1"],
                         "W1_default": r["W1_default"],
                         "W1_at_switch": r["W1_at_switch"],
                         "delta_W1": r["delta_W1"],
                         "adoptions": r["adoptions"]})
    summary = {m: {"delta_mean(跨口径,勿读)": _mean([r["delta"] for r in rows if r["archive"] == m]),
                   "delta_W1": _mean([r["delta_W1"] for r in rows if r["archive"] == m]),
                   "W1_default": _mean([r["W1_default"] for r in rows if r["archive"] == m]),
                   "W1_at_switch": _mean([r["W1_at_switch"] for r in rows if r["archive"] == m]),
                   "champion_W1": _mean([r["champion_W1"] for r in rows if r["archive"] == m]),
                   "archive_best_W1": _mean([r["archive_best_W1"] for r in rows if r["archive"] == m]),
                   "adoptions": _mean([r["adoptions"] for r in rows if r["archive"] == m])}
               for m in ("single", "pareto")}
    _dump(outdir / "forget.json", {"rows": rows, "summary": summary})
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


def cmd_reorg(a):
    """E28 复现：层次化归并 vs 平铺。"""
    outdir = _out(f"reorg_{int(time.time())}")
    rows = []
    for seed in range(a.seeds):
        w = World(seed=seed + 1, terrain="clean")
        lib = Library(w.entries, NOW)
        res = {}
        for mode in ("flat", "hier"):
            g = clamp({**DEFAULT, "merge_mode": mode})
            lib.apply(g)
            p, _ = metrics.evaluate(w, lib, w.queries["audit"], g, k=5)
            res[mode] = {"recall@5": round(p["recall@5"], 4), "MRR": round(p["MRR"], 4),
                         "u": round(w.utility(p, 0, g), 4)}
        rows.append({"seed": seed + 1, **res})
    summ = {m: {"recall_mean": _mean([r[m]["recall@5"] for r in rows]),
                "u_mean": _mean([r[m]["u"] for r in rows])} for m in ("flat", "hier")}
    _dump(outdir / "reorg.json", {"rows": rows, "summary": summ})
    print(json.dumps(summ, ensure_ascii=False, indent=1))
    return 0


def cmd_importance(a):
    """E32 复现：importance 用自称 vs 实测采纳率，top-10 条目真实质量。"""
    outdir = _out(f"importance_{int(time.time())}")
    rows = []
    for seed in range(a.seeds):
        w = World(seed=seed + 1, terrain="clean")
        lib = Library(w.entries, NOW)
        base = clamp(DEFAULT)
        # 先用默认基因组跑若干轮"真实使用"，累积采纳日志
        for _ in range(a.warmup):
            lib.apply(base)
            metrics.evaluate(w, lib, w.queries["train"], base, k=5, feedback=True)
        res = {}
        for src in ("self", "measured"):
            g = clamp({**DEFAULT, "importance_source": src})
            lib.apply(g)
            q, top = metrics.top_quality(lib, g, k=10)
            res[src] = {"top10_true_quality": round(q, 4), "ids": top}
        rows.append({"seed": seed + 1, **res})
    summ = {s: _mean([r[s]["top10_true_quality"] for r in rows]) for s in ("self", "measured")}
    gain = (summ["measured"] - summ["self"]) / summ["self"] if summ["self"] else 0.0
    _dump(outdir / "importance.json", {"rows": rows, "summary": summ, "relative_gain": gain})
    print(json.dumps({"summary": summ, "relative_gain": round(gain, 4)},
                     ensure_ascii=False, indent=1))
    return 0


def cmd_world(a):
    w = World(seed=a.seed, terrain=a.terrain)
    _dump(ROOT / "runs" / f"world_{a.terrain}_{a.seed}.json", {
        "seed": a.seed, "terrain": a.terrain,
        "n_entries": len(w.entries),
        "n_invalid": sum(1 for e in w.entries if (e.get("validity") or {}).get("t_invalid")),
        "queries": {k: len(v) for k, v in w.queries.items()},
        "sample_entry": w.entries[0],
        "sample_query": w.queries["train"][0],
    })
    print(f"world {a.terrain} seed={a.seed}: {len(w.entries)} entries, "
          f"{ {k: len(v) for k, v in w.queries.items()} } queries")
    return 0


# ─────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser("mem-evolve-sandbox")
    p.add_argument("--src", default=str(bs3mod.DEFAULT_SRC))
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("selftest")
    s.set_defaults(fn=cmd_selftest)

    s = sub.add_parser("consistency")
    s.add_argument("--procs", type=int, default=12)
    s.set_defaults(fn=cmd_consistency)

    s = sub.add_parser("concurrency")
    s.add_argument("--procs", type=int, default=12)
    s.set_defaults(fn=cmd_concurrency)

    s = sub.add_parser("evolve")
    s.add_argument("--terrain", default="clean", choices=list(TERRAINS))
    s.add_argument("--cfgs", nargs="+", default=["static", "two-tier"])
    s.add_argument("--seeds", type=int, default=8)
    s.add_argument("--gens", type=int, default=40)
    s.add_argument("--fanout", type=int, default=3)
    s.add_argument("--n-genes", type=int, default=1)
    s.add_argument("--rotate", action="store_true")
    s.add_argument("--archive", default="pareto", choices=["pareto", "single"])
    s.add_argument("--tag", default="", help="结果目录后缀，用于区分消融臂")
    s.add_argument("--genes", nargs="*", default=None,
                   help="隔离实验：只允许这些基因参与变异（如 --genes w_kw filter_zero）")
    s.add_argument("--alpha", type=float, default=0.15,
                   help="drift 地形下评判者被系统输出锚定的速率（E14）")
    s.add_argument("--no-cheap", action="store_true", help="消融：关闭廉价筛选")
    s.add_argument("--no-holdout", action="store_true", help="消融：关闭留出集门")
    s.add_argument("--no-stall", action="store_true", help="消融：关闭停摆监控")
    s.set_defaults(fn=cmd_evolve)

    s = sub.add_parser("matrix")
    s.add_argument("--terrains", nargs="*", default=None)
    s.add_argument("--cfgs", nargs="+", default=["static", "none", "two-tier"])
    s.add_argument("--seeds", type=int, default=8)
    s.add_argument("--gens", type=int, default=40)
    s.add_argument("--fanout", type=int, default=3)
    s.add_argument("--rotate", action="store_true")
    s.set_defaults(fn=cmd_matrix)

    s = sub.add_parser("sweep", help="drift 地形 α 扫描（H7 判定；α=0 为零误报对照）")
    s.add_argument("--alphas", nargs="+", type=float, default=[0.0, 0.05, 0.10, 0.20, 0.30])
    s.add_argument("--cfgs", nargs="+", default=["two-tier", "two-tier+anchor"])
    s.add_argument("--seeds", type=int, default=12)
    s.add_argument("--gens", type=int, default=40)
    s.add_argument("--drift-start", type=int, default=15)
    s.add_argument("--fanout", type=int, default=3)
    s.set_defaults(fn=cmd_sweep)

    s = sub.add_parser("ablate", help="E67 消融：逐项拆掉护栏，测边际贡献")
    s.add_argument("--terrains", nargs="+", default=["pseudo", "deceptive"])
    s.add_argument("--seeds", type=int, default=12)
    s.add_argument("--gens", type=int, default=30)
    s.add_argument("--fanout", type=int, default=3)
    s.add_argument("--genes", nargs="*", default=None)
    s.set_defaults(fn=cmd_ablate)

    s = sub.add_parser("show", help="打印任意 summary.json / runs 目录下的汇总")
    s.add_argument("--path", required=True)
    s.set_defaults(fn=cmd_show)

    s = sub.add_parser("noise", help="E70 金标噪声：独立 vs 相关（E52/E57）")
    s.add_argument("--terrain", default="clean")
    s.add_argument("--cfg", default="two-tier")
    s.add_argument("--ps", nargs="+", type=float, default=[0.3, 0.7])
    s.add_argument("--seeds", type=int, default=12)
    s.add_argument("--gens", type=int, default=25)
    s.add_argument("--fanout", type=int, default=3)
    s.set_defaults(fn=cmd_noise)

    s = sub.add_parser("gate-budget", help="E71 注意力预算 → 门控判决可靠性（E17+E64）")
    s.add_argument("--terrain", default="pseudo")
    s.add_argument("--budgets", nargs="+", type=int, default=[20, 40, 80, 150, 300, 600])
    s.add_argument("--seeds", type=int, default=12)
    s.add_argument("--gens", type=int, default=25)
    s.add_argument("--fanout", type=int, default=3)
    s.set_defaults(fn=cmd_gate_budget)

    s = sub.add_parser("calibrate", help="锚定阈值标定：零漂移基线上的一致率分布")
    s.add_argument("--alphas", nargs="+", type=float, default=[0.0, 0.10])
    s.add_argument("--seeds", type=int, default=8)
    s.add_argument("--gens", type=int, default=40)
    s.add_argument("--drift-start", type=int, default=15)
    s.set_defaults(fn=cmd_calibrate)

    s = sub.add_parser("sweep-show")
    s.add_argument("--path", default=None)
    s.add_argument("--latest", action="store_true", default=True)
    s.set_defaults(fn=cmd_sweep_show)

    s = sub.add_parser("budget")
    s.add_argument("--budgets", nargs="+", type=int, default=[40, 60, 100, 150, 300, 600])
    s.add_argument("--seeds", type=int, default=8)
    s.add_argument("--init-cost", type=int, default=40)
    s.set_defaults(fn=cmd_budget)

    s = sub.add_parser("forget")
    s.add_argument("--seeds", type=int, default=8)
    s.add_argument("--gens", type=int, default=40)
    s.set_defaults(fn=cmd_forget)

    s = sub.add_parser("reorg")
    s.add_argument("--seeds", type=int, default=8)
    s.set_defaults(fn=cmd_reorg)

    s = sub.add_parser("importance")
    s.add_argument("--seeds", type=int, default=8)
    s.add_argument("--warmup", type=int, default=6)
    s.set_defaults(fn=cmd_importance)

    s = sub.add_parser("world")
    s.add_argument("--seed", type=int, default=1)
    s.add_argument("--terrain", default="clean", choices=list(TERRAINS))
    s.set_defaults(fn=cmd_world)

    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
