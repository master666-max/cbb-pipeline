# -*- coding: utf-8 -*-
"""g17_patrol_queue.py — G17 区段巡检启动·首圈队列生成（总工单 G17 执行件·前置）。

对象：全部 confirmed 群体（隔离区 confirmed 743+ + 主库 G16b 晋升批——台账为准）。
动作：FSRS ReviewScheduler.schedule(record_id, tenure_segments, stability) 建卡；
      首圈 due(current_segment=1) 抽样名单落盘，供巡检执行（重推导一致率报告）。
判据（完整版在 G16b 收口后出）：巡检报告（重推导一致率）+改判率序列入 CUSUM 备用。
用法：py -X utf8 g17_patrol_queue.py [--sample 50]
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cbb-v2"))

from cbb2.schedule import ReviewScheduler  # noqa: E402

STORE = ROOT / "迷深实战-本体库"
QZ = STORE / "quarantine-zone" / "items.jsonl"
G16B = STORE / "G16b-票面台账.jsonl"
OUT = STORE / "G17-首圈巡检队列.json"


def confirmed_ids() -> list:
    ids = []
    for l in QZ.read_text(encoding="utf-8").splitlines():
        if l.strip() and json.loads(l).get("status") == "confirmed":
            ids.append(json.loads(l)["item_id"])
    if G16B.exists():
        for l in G16B.read_text(encoding="utf-8").splitlines():
            if l.strip() and json.loads(l).get("verdict") == "promote":
                ids.append(json.loads(l)["record_id"])
    return ids


def main():
    sample_n = 50
    if "--sample" in sys.argv:
        sample_n = int(sys.argv[sys.argv.index("--sample") + 1])

    ids = confirmed_ids()
    rs = ReviewScheduler(STORE)
    scheduled = 0
    for rid in ids:
        if rid not in rs.state:  # state 即卡册（key 覆盖写，天然幂等）
            rs.schedule(rid, tenure_segments=1, stability=1.0)  # 首圈冷启动 stability=1.0
            scheduled += 1
    due = rs.due(current_segment=1)
    rng = random.Random(20260927)  # 固定种子可复算（对样门纪律）
    sample = sorted(due) if len(due) <= sample_n else rng.sample(sorted(due), sample_n)
    OUT.write_text(json.dumps({
        "unit": "G17", "at": "2026-09-27",
        "confirmed总数": len(ids),
        "新建卡": scheduled, "已有卡": len(ids) - scheduled,
        "due首圈": len(due), "首圈抽样": sample,
        "抽样口径": f"固定种子 20260927，n={len(sample)}",
        "下一步": "巡检执行=逐条重推导（考官复核或 NLI 复判）→ record_check(passed) →"
                 "重推导一致率报告+改判率序列入 CUSUM 备用",
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"confirmed {len(ids)}（新建卡 {scheduled}）；due 首圈 {len(due)}；抽样 {len(sample)} → {OUT}")


if __name__ == "__main__":
    main()
