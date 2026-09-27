# -*- coding: utf-8 -*-
"""g13_weighting_report.py — 票权加权报告（总工单 G13 执行件）。

数据源：G16-晋升报告.json 的 658×3 真实票面矩阵。
口径（如实登记）：质量后验以"与其他考官多数票的一致率"为代理（无逐条金标的
GLAD 简化版）；金标审计仅 n=10（全站得住），作旁证不作分母。
单考官异常检测：错误率/unsure 率/超时率显著偏离同侪即标出（QWEN 超时 42 实测）。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cbb-v2"))

from cbb2.governance import ExaminerQualityTracker  # noqa: E402

REP = ROOT / "迷深实战-本体库" / "G16-晋升报告.json"
OUT = ROOT / "迷深实战-本体库" / "G13-票权加权报告.json"


def main():
    rep = json.loads(REP.read_text(encoding="utf-8"))
    tickets = rep["票面"]
    tracker = ExaminerQualityTracker()

    stats = {}
    for rid, m in tickets.items():
        votes = m.get("votes", {})
        # 多数票（忽略 unsure；并列为无多数）
        vals = [v for v in votes.values() if v in ("support", "against")]
        if not vals:
            continue
        majority = max(set(vals), key=vals.count)
        if vals.count(majority) <= len(vals) / 2:
            continue
        for ex, v in votes.items():
            s = stats.setdefault(ex, {"votes": 0, "support": 0, "unsure": 0,
                                      "against": 0, "errors": 0, "agree_majority": 0,
                                      "comparable": 0})
            s["votes"] += 1
            if v in ("support", "unsure", "against"):
                s[v] += 1
            if v in ("support", "against"):
                s["comparable"] += 1
                if v == majority:
                    s["agree_majority"] += 1
                    tracker.record(ex, True)
                else:
                    tracker.record(ex, False)
        for e in m.get("errors", []):
            s = stats.setdefault(e["examiner"], {"votes": 0, "support": 0, "unsure": 0,
                                                 "against": 0, "errors": 0,
                                                 "agree_majority": 0, "comparable": 0})
            s["errors"] += 1

    # 全量统计兜底（stats 只在循环里建键）
    for rid, m in tickets.items():
        for e in m.get("errors", []):
            stats.setdefault(e["examiner"], {"votes": 0, "support": 0, "unsure": 0,
                                             "against": 0, "errors": 0,
                                             "agree_majority": 0, "comparable": 0})

    report = {}
    for ex, s in stats.items():
        q = tracker.quality(ex)
        s["unsure_rate"] = round(s["unsure"] / s["votes"], 4) if s["votes"] else None
        s["error_rate"] = round(s["errors"] / (s["votes"] + s["errors"]), 4) \
            if (s["votes"] + s["errors"]) else None
        s["agreement_proxy"] = round(s["agree_majority"] / s["comparable"], 4) \
            if s["comparable"] else None
        s["quality_posterior"] = round(q, 4)
        s["weight_建议"] = round(max(0.5, min(1.5, q * 2)), 3)
        anomalies = []
        if s["error_rate"] and s["error_rate"] > 0.05:
            anomalies.append(f"错误率 {s['error_rate']} 显著偏离（单考官异常可检）")
        if s["unsure_rate"] and s["unsure_rate"] > 0.6:
            anomalies.append(f"unsure 率 {s['unsure_rate']} 偏高")
        s["anomalies"] = anomalies
        report[ex] = s

    out = {
        "unit": "G13", "at": "2026-09-27",
        "口径": "质量后验=与其他考官多数票一致率的 Beta(2,1) 后验代理（GLAD 简化版，"
               "无逐条金标）；金标审计 n=10 全站得住作旁证；扩样 n≥80 后应复核权重",
        "数据源": "G16-晋升报告.json 票面矩阵（658 件×3 考官）",
        "examiners": report,
        "接线状态": "promote.vote 已支持可选 weights 入参（缺省等权，行为不变）；"
                   "G16b 主库大批起按 weight_建议 传入",
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for ex, s in report.items():
        print(f"[{ex}] 票{s['votes']} 错{s['errors']} unsure率={s['unsure_rate']} "
              f"一致率代理={s['agreement_proxy']} 质量后验={s['quality_posterior']} "
              f"权重建议={s['weight_建议']} 异常={s['anomalies'] or '无'}")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
