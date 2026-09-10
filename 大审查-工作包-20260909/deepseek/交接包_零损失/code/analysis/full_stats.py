# -*- coding: utf-8 -*-
"""full_stats.py — full 协议独立分析: 配对 Wilcoxon(exact) + bootstrap 95% CI + sign-test + 判据
用法: py -3 full_stats.py --dirs out_v2_full_a out_v2_full_b [--label FULL]
绝不 import 运行器; 只读 rows_*.json。"""
import sys, os, json, glob, statistics, pathlib, argparse, datetime, random

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def wilcoxon_exact(diffs, alternative="two-sided"):
    """配对符号秩检验(exact, n 小); 并列取平均秩; 返回双侧 p。"""
    nz = [(i, abs(d)) for i, d in enumerate(diffs) if d != 0]
    if not nz:
        return 1.0
    nz.sort(key=lambda x: x[1])
    idxs, rvals = [], []
    i = 0
    while i < len(nz):
        j = i
        while j + 1 < len(nz) and abs(nz[j + 1][1] - nz[i][1]) < 1e-12:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            idxs.append(nz[k][0])
            rvals.append(avg)
        i = j + 1
    wplus = sum(r for idx, r in zip(idxs, rvals) if diffs[idx] > 0)
    dp = {0: 1}
    for r in rvals:
        nd = dict(dp)
        for s, c in dp.items():
            nd[s + r] = nd.get(s + r, 0) + c
        dp = nd
    total_c = 2 ** len(rvals)
    cnt_le = sum(c for s, c in dp.items() if s <= wplus)          # P(W+ <= w)
    cnt_lt = sum(c for s, c in dp.items() if s < wplus)           # P(W+ < w)
    p_low = cnt_le / total_c
    p_high = (total_c - cnt_lt) / total_c                         # P(W+ >= w)
    if alternative == "two-sided":
        return min(1.0, 2 * min(p_low, p_high))
    return min(1.0, p_high if alternative == "greater" else p_low)


def bootstrap_ci(deltas, n=10000, seed=1):
    rng = random.Random(seed)
    means = []
    for _ in range(n):
        rs = [deltas[rng.randrange(len(deltas))] for _ in range(len(deltas))]
        means.append(statistics.mean(rs))
    means.sort()
    lo = means[int(0.025 * n)]
    hi = means[int(0.975 * n)]
    return round(lo, 4), round(hi, 4), round(statistics.mean(means), 4)


def load_rows(dirs):
    rows = []
    for d in dirs:
        for f in sorted(glob.glob(str(pathlib.Path(d) / "rows_*.json"))):
            rows.extend(json.load(open(f, encoding="utf-8")))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", required=True)
    ap.add_argument("--label", default="FULL")
    ap.add_argument("--seed-per-arm", default=None)
    a = ap.parse_args()
    rows = load_rows(a.dirs)
    scenes = sorted({r["scene"] for r in rows})
    arms = sorted({r["mode"] for r in rows})
    out = []
    out.append("# Full 协议统计（%s）" % a.label)
    out.append("")
    out.append("> 生成 %s | 场景: %s | 臂: %s | n_seeds=%d" % (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), ",".join(scenes),
        ",".join(arms), len({r['seed'] for r in rows})))
    out.append("")
    verdicts = []
    for sc in scenes:
        sr = [r for r in rows if r["scene"] == sc]
        st_map = {r["seed"]: r for r in sr if r["mode"] == "static"}
        out.append("## scene=%s" % sc)
        out.append("| arm | u_audit_mean | u_audit_std |")
        out.append("|---|---|---|")
        for ar in arms:
            rs = [r for r in sr if r["mode"] == ar]
            if rs:
                out.append("| %s | %.4f | %.4f |" % (ar,
                    statistics.mean(r["u_audit"] for r in rs),
                    statistics.pstdev(r["u_audit"] for r in rs)))
        out.append("")
        for ar in arms:
            if ar == "static" or not st_map:
                continue
            ds = []
            for r in sr:
                if r["mode"] == ar and r["seed"] in st_map:
                    ds.append(r["u_audit"] - st_map[r["seed"]]["u_audit"])
            if not ds:
                continue
            pos = sum(1 for d in ds if d > 0)
            p = wilcoxon_exact(ds)
            lo, hi, bm = bootstrap_ci(ds)
            out.append("配对 Δ(同 seed) %s vs static: n=%d mean=%+.4f med=%+.4f | 正种子 %d/%d | Wilcoxon p=%.4f | bootstrap 95%%CI [%+.4f, %+.4f] 下界>0=%s" % (
                ar, len(ds), statistics.mean(ds), statistics.median(ds),
                pos, len(ds), p, lo, hi, "YES" if lo > 0 else "no"))
            verdicts.append({"scene": sc, "arm": ar, "n": len(ds), "pos": pos,
                             "mean": round(statistics.mean(ds), 4), "wilcoxon": round(p, 4),
                             "ci_lo": lo, "ci_hi": hi})
        out.append("")
    # F1-style: gated vs static
    out.append("## F1 判据速查(gated vs static, 需 ≥70% 正种子 且 CI 下界>0)")
    out.append("| scene | n | 正种子 | 比例 | Wilcoxon p | CI 下界 | F1? |")
    out.append("|---|---|---|---|---|---|---|")
    for v in verdicts:
        if v["arm"] == "gated":
            ok = (v["pos"] / v["n"] >= 0.7) and v["ci_lo"] > 0
            out.append("| %s | %d | %d | %.2f | %.4f | %+.4f | %s |" % (
                v["scene"], v["n"], v["pos"], v["pos"] / v["n"], v["wilcoxon"],
                v["ci_lo"], "PASS" if ok else "fail"))
    md = "\n".join(out)
    target = pathlib.Path(a.dirs[0]) / ("full_stats_%s.md" % a.label)
    target.write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
