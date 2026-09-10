"""自演化试点 · 离线分析器

在【你的环境里】对 traces.jsonl 跑，输出一份 go/no-go 报告。
不联网、不上传、只用标准库。

回答四个问题（每个都对应一次实验教训）：
  Q1 采纳信号够强吗？        —— E17：n 小时假阳性率 42%，先估统计功效
  Q2 重要性实测值长什么样？  —— E32：实测 vs 自称，差多少
  Q3 离线回放能改进多少？    —— 反事实评估：换排序策略，采纳率能升多少
  Q4 值不值得开自演化？      —— E64：预算 <150 恒为负，先算账

用法：
    python3 pilot/analyze.py traces.jsonl
    python3 pilot/analyze.py traces.jsonl --report out.md
"""
from __future__ import annotations
import json, sys, math, random, statistics, argparse
from collections import defaultdict, Counter
from typing import List, Dict, Any


# ══════════════ 加载 ══════════════
def load(path: str) -> List[dict]:
    """加载并合并 amend 记录（采纳发生在检索之后，用 amend 回补）"""
    rows: Dict[int, dict] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("amend_seq"):
                tgt = rows.get(r["amend_seq"])
                if tgt is not None:
                    tgt["adopted"] = r.get("adopted")
                continue
            if not r.get("cand"):
                continue
            rows[r.get("seq", len(rows) + 1)] = r
    return list(rows.values())


# ══════════════ Q1 信号强度 ══════════════
def signal_power(rows: List[dict]) -> dict:
    n = len(rows)
    ad = sum(1 for r in rows if r.get("adopted"))
    p = ad / n if n else 0.0
    # 简化功效估计：检出 10% 相对改进所需样本量（正态近似，alpha=.05, power=.8）
    if 0 < p < 1:
        # n ≈ 2*(1.96+0.84)^2 * p(1-p) / (0.1*p)^2
        need = 2 * (1.96 + 0.84) ** 2 * p * (1 - p) / ((0.1 * p) ** 2)
    else:
        need = float("inf")
    return {"traces": n, "adopted": ad, "adopt_rate": round(p, 4),
            "need_for_10pct_lift": int(need) if need != float("inf") else None,
            "enough": n >= need if need != float("inf") else False}


# ══════════════ Q2 实测重要性 ══════════════
def measured_importance(rows: List[dict]) -> dict:
    shown, adopted = Counter(), Counter()
    for r in rows:
        for c in r["cand"]:
            shown[c["id"]] += 1
        a = r.get("adopted")
        if a:
            adopted[a] += 1
    items = []
    for i in shown:
        s, ad = shown[i], adopted.get(i, 0)
        items.append((i, s, ad, ad / s if s else 0.0))
    items.sort(key=lambda x: (-x[1], x[0]))
    rates = [x[3] for x in items]
    return {
        "n_items": len(items),
        "top10": [{"id": i, "shown": s, "adopted": a, "rate": round(r, 3)}
                  for i, s, a, r in items[:10]],
        "mean_rate": round(statistics.mean(rates), 4) if rates else 0.0,
        # 曝光>=5 的条目里，采纳率的标准差 —— 衡量"条目间是否真有差异"
        "sd_rate_shown5": round(statistics.pstdev([x[3] for x in items if x[1] >= 5]), 4)
        if sum(1 for x in items if x[1] >= 5) > 2 else None,
    }


# ══════════════ Q3 反事实回放 ══════════════
def feats_of(c: dict) -> Dict[str, float]:
    return c.get("f") or {}


def rank_with(row: dict, w: Dict[str, float]) -> List[str]:
    out = []
    for c in row["cand"]:
        f = feats_of(c)
        s = sum(w.get(k, 0.0) * v for k, v in f.items()) if f else 0.0
        out.append((s, c["id"]))
    out.sort(key=lambda x: (-x[0], x[1]))
    return [i for _, i in out]


def mrr(rows: List[dict], w: Dict[str, float]) -> float:
    tot = 0.0
    n = 0
    for r in rows:
        a = r.get("adopted")
        if not a:
            continue
        order = rank_with(r, w)
        if a in order:
            tot += 1.0 / (order.index(a) + 1)
        n += 1
    return tot / n if n else 0.0


def p_at1(rows: List[dict], w: Dict[str, float]) -> float:
    hit = tot = 0
    for r in rows:
        a = r.get("adopted")
        if not a:
            continue
        order = rank_with(r, w)
        tot += 1
        if order and order[0] == a:
            hit += 1
    return hit / tot if tot else 0.0


def replay(rows: List[dict], seed: int = 0, iters: int = 400) -> dict:
    """离线回放：在留出集上估"换策略能提升多少"。

    ★ 必须用 train/held 分离（E3/E8）：
      - 在 train 上搜出最优权重
      - 在 held 上报告收益
      否则就是过拟合，无门控时必然灾难。
    """
    feats = sorted({k for r in rows for c in r["cand"] for k in feats_of(c)})
    if not feats:
        return {"ok": False, "reason": "候选没有特征（feat 为空），无法做反事实回放。"}
    rnd = random.Random(seed)
    idx = list(range(len(rows)))
    rnd.shuffle(idx)
    cut = int(len(idx) * 0.6)
    tr = [rows[i] for i in idx[:cut]]
    he = [rows[i] for i in idx[cut:]]
    if len(he) < 5:
        return {"ok": False, "reason": f"留出集太小（{len(he)}），至少需要 5 条。"}

    base = {k: 1.0 for k in feats}
    best_w, best_tr = dict(base), mrr(tr, base)
    for _ in range(iters):
        w = {k: rnd.uniform(-2, 2) for k in feats}
        s = mrr(tr, w)
        if s > best_tr:
            best_tr, best_w = s, w
    he_base = mrr(he, base)
    he_best = mrr(he, best_w)
    return {
        "ok": True,
        "features": feats,
        "n_train": len(tr), "n_held": len(he),
        "mrr_train_base": round(mrr(tr, base), 4),
        "mrr_train_tuned": round(best_tr, 4),
        "mrr_held_base": round(he_base, 4),
        "mrr_held_tuned": round(he_best, 4),
        "held_gain": round(he_best - he_base, 4),
        "overfit_gap": round(best_tr - he_best, 4),   # 大 = 过拟合严重
    }


# ══════════════ Q4 预算账 ══════════════
def budget(rows: List[dict], audit_every: int = 5, probe_n: int = 4,
           cost_per_sample: int = 12) -> dict:
    n = len(rows)
    traces_per_gen = 20                # 假设每代 20 次检索
    gens = max(1, n // traces_per_gen)
    audits = gens // audit_every
    cost = audits * probe_n * cost_per_sample
    return {
        "estimated_generations": gens,
        "estimated_audits": audits,
        "attention_cost": cost,
        "threshold": 150,              # E64：低于此终局恒为负
        "verdict": "预算足够，可考虑开启" if cost >= 150
                   else f"预算不足（{cost} < 150），继续影子期攒数据",
    }


# ══════════════ 报告 ══════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--report", default=None)
    a = ap.parse_args()
    rows = load(a.path)
    out = []
    P = out.append

    P("# 自演化试点 · 离线分析报告\n")
    P(f"轨迹文件：`{a.path}`　有效记录：**{len(rows)}** 条\n")
    if len(rows) < 20:
        P("> ⚠️ 样本太少（<20），以下结论仅供参考。建议先攒到 200+ 条。\n")

    P("\n## Q1 采纳信号\n")
    sp = signal_power(rows)
    P(f"- 轨迹 {sp['traces']} 条，其中被采纳 {sp['adopted']} 次")
    P(f"- **采纳率 {sp['adopt_rate']:.1%}**")
    if sp["need_for_10pct_lift"]:
        P(f"- 检出 10% 相对改进约需 **{sp['need_for_10pct_lift']}** 条"
          f"（E17：n=10 时假阳性率 42%）")
        P(f"- 当前是否足够：**{'是' if sp['enough'] else '否'}**")

    P("\n## Q2 实测重要性（E32）\n")
    mi = measured_importance(rows)
    P(f"- 曝光过的条目：{mi['n_items']} 个，平均采纳率 {mi['mean_rate']:.3f}")
    if mi["sd_rate_shown5"] is not None:
        P(f"- 曝光≥5 次的条目，采纳率标准差 **{mi['sd_rate_shown5']}**"
          f"（越大说明条目间真有差异，实测重要性越有价值）")
    if mi["top10"]:
        P("\n| 条目 | 曝光 | 采纳 | 实测重要性 |")
        P("|---|---|---|---|")
        for t in mi["top10"]:
            P(f"| {t['id'][:12]} | {t['shown']} | {t['adopted']} | {t['rate']} |")

    P("\n## Q3 反事实回放（能否改进）\n")
    rp = replay(rows)
    if not rp.get("ok"):
        P(f"> 无法回放：{rp.get('reason')}")
    else:
        P(f"- 特征：{', '.join(rp['features'])}")
        P(f"- 训练 {rp['n_train']} / 留出 {rp['n_held']}")
        P(f"- MRR 基线 {rp['mrr_held_base']} → 调优后 **{rp['mrr_held_tuned']}**"
          f"（留出集收益 **{rp['held_gain']:+.4f}**）")
        P(f"- 过拟合缺口 {rp['overfit_gap']}（训练集 {rp['mrr_train_tuned']}）")
        P("\n> ★ 只有【留出集收益】才算数。E8 已证明留出集会被消耗，需定期轮换。")

    P("\n## Q4 预算账（E64）\n")
    b = budget(rows)
    P(f"- 估算可跑 {b['estimated_generations']} 代，审计 {b['estimated_audits']} 次")
    P(f"- 注意力成本 **{b['attention_cost']}** 单位")
    P(f"- 结论：**{b['verdict']}**")

    P("\n## 结论与建议\n")
    go = (sp.get("enough") and rp.get("ok") and rp.get("held_gain", 0) > 0.01
          and b["attention_cost"] >= 150)
    if go:
        P("✅ 信号、可改进性、预算三项均达标 → **可以进入 S1（判断集采集）**。")
    else:
        P("⏸ 尚未达标 → **继续影子期**。优先补：")
        if not sp.get("enough"):
            P("  - 轨迹数量（采纳信号的统计功效）")
        if not (rp.get("ok") and rp.get("held_gain", 0) > 0.01):
            P("  - 候选特征（feat）—— 没有特征就无法做反事实回放与演化")
        if b["attention_cost"] < 150:
            P("  - 注意力预算（不足 150 时自演化终局恒为负，E64）")

    txt = "\n".join(out)
    if a.report:
        open(a.report, "w", encoding="utf-8").write(txt)
        print(f"报告已写入 {a.report}")
    else:
        print(txt)


if __name__ == "__main__":
    main()
