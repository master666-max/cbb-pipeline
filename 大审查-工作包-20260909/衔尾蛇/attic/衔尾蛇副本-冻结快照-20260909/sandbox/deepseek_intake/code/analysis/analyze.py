# -*- coding: utf-8 -*-
"""analysis/analyze.py — 独立分析(后处理): 主表 + 配对 Δ 与 sign-test + 摘要 md

绝不 import 运行器; 只读 out_v2/rows_*.json 与 manifest.json。
用法: py -3 analysis/analyze.py --in ../out_v2 --out ../out_v2
"""
import sys, os, json, glob, statistics, pathlib, argparse, datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_rows(in_dir):
    rows = []
    for f in sorted(glob.glob(str(in_dir / "rows_*.json"))):
        rows.extend(json.loads(open(f, encoding="utf-8").read()))
    return rows


def pair_table(scene_rows, scene, arms):
    """按 seed 配对: 对每个 arm, 与 static 同 seed 差 u_audit; 输出 sign 计数与均值差"""
    by_seed = {}
    for r in scene_rows:
        by_seed.setdefault(r["seed"], {})[r["mode"]] = r
    lines = []
    if "static" not in by_seed.get(list(by_seed)[0], {}):
        return lines  # 无 static 对照, 跳过配对
    for arm in arms:
        if arm == "static":
            continue
        ds = []
        seeds_ok = 0
        for seed in sorted(by_seed):
            row = by_seed[seed]
            if arm in row and "static" in row:
                ds.append(row[arm]["u_audit"] - row["static"]["u_audit"])
                seeds_ok += 1
        if not ds:
            continue
        pos = sum(1 for d in ds if d > 0)
        lines.append({
            "scene": scene, "arm": arm, "n": len(ds),
            "pos_seeds": pos, "mean_delta": round(statistics.mean(ds), 4),
            "median_delta": round(statistics.median(ds), 4),
            "min_delta": round(min(ds), 4), "max_delta": round(max(ds), 4),
        })
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_dir", default=str(pathlib.Path(__file__).resolve().parent.parent / "out_v2"))
    ap.add_argument("--out", dest="out_dir", default="")
    a = ap.parse_args()
    in_dir = pathlib.Path(a.in_dir)
    out_dir = pathlib.Path(a.out_dir) if a.out_dir else in_dir
    if not in_dir.exists():
        sys.exit("no such dir: %s" % in_dir)

    rows = load_rows(in_dir)
    scenes = sorted({r["scene"] for r in rows})
    arms = sorted({r["mode"] for r in rows})

    md = ["# V2 沙盒实验 · 分析摘要", "", "> 生成: %s | 场景: %s | 臂: %s" % (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), ",".join(scenes), ",".join(arms)), ""]
    comp = []
    for sc in scenes:
        sr = [r for r in rows if r["scene"] == sc]
        md.append("## scene=%s" % sc)
        has_best = any("bestA_true" in r for r in sr)
        hdr = "| arm | u_audit(真值) | u_trainA(自报) | uA_true |" + (" bestA(档案) |" if has_best else "") + " u_hold | adopts | sec |"
        md.append(hdr)
        md.append("|" + "---|" * (8 if has_best else 7))
        for arm in arms:
            rs = [r for r in sr if r["mode"] == arm]
            if not rs:
                continue
            uA = statistics.mean([r.get("uA_true", 0) or 0 for r in rs])
            if has_best:
                vals = [r.get("bestA_true") for r in rs if r.get("bestA_true") is not None]
                bA = statistics.mean(vals) if vals else 0.0
                md.append("| %s | %.4f | %.4f | %.4f | %.4f | %.4f | %.1f | %.2f |" % (
                    arm, statistics.mean(r["u_audit"] for r in rs),
                    statistics.mean(r.get("u_trainA", 0) for r in rs),
                    uA, bA,
                    statistics.mean(r["u_hold"] for r in rs),
                    statistics.mean(r["adopts"] for r in rs),
                    statistics.mean(r["sec"] for r in rs)))
            else:
                md.append("| %s | %.4f | %.4f | %.4f | %.4f | %.1f | %.2f |" % (
                    arm, statistics.mean(r["u_audit"] for r in rs),
                    statistics.mean(r.get("u_trainA", 0) for r in rs),
                    uA,
                    statistics.mean(r["u_hold"] for r in rs),
                    statistics.mean(r["adopts"] for r in rs),
                    statistics.mean(r["sec"] for r in rs)))
        md.append("")
        md.append("配对 Δu_audit(vs static, 同 seed):")
        hdr = "| arm | n | 正种子 | Δ均值 | Δ中位 | Δmin | Δmax |"
        md.append(hdr)
        md.append("|---|---|---|---|---|---|---|")
        for it in pair_table(sr, sc, arms):
            md.append("| %s | %d | %d/%d | %+.4f | %+.4f | %+.4f | %+.4f |" % (
                it["arm"], it["n"], it["pos_seeds"], it["n"], it["mean_delta"],
                it["median_delta"], it["min_delta"], it["max_delta"]))
            comp.append(it)
        md.append("")
        md.append("诚实度 gap(自报 u_trainA − 真值 u_audit, 均值):")
        md.append("| arm | self − truth |")
        md.append("|---|---|")
        for arm in arms:
            rs = [r for r in sr if r["mode"] == arm]
            if not rs:
                continue
            gap = statistics.mean(r.get("u_trainA", 0) for r in rs) - statistics.mean(r["u_audit"] for r in rs)
            md.append("| %s | %+.4f |" % (arm, gap))
        md.append("")

    # 主判据计数: 各场景 gated 相对 static 的正种子比例
    md.append("## H1 判据速查(gated vs static, u_audit 真值集)")
    md.append("| scene | n | 正种子 | 比例 |")
    md.append("|---|---|---|---|")
    for it in comp:
        if it["arm"] == "gated":
            md.append("| %s | %d | %d | %.2f |" % (it["scene"], it["n"], it["pos_seeds"],
                                                   it["pos_seeds"] / it["n"] if it["n"] else 0))
    md.append("")
    (out_dir / "analysis_summary.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
