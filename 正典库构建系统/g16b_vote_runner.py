# -*- coding: utf-8 -*-
"""g16b_vote_runner.py — G5 票数晋升·主库 provisional 大批（总工单 G16 余量执行件）。

对象：迷深实战-本体库/libraries/*/*/*.json 里 status=provisional 的 6,278 件。
机制：与 g16_vote_runner 同法（三考官隔离双序+答案对调+B13 需票满编制），
     增量三点：①G13 权重入列（加权需票=满编权重和×2/3，against=0/n≥2 硬门不变）；
     ②考官消费回执（calls/errors/latency 逐考官入报告）；③票面台账=resume 日志
     （append-only，重跑跳过已评审 rid）。
产出：迷深实战-本体库/G16b-票面台账.jsonl + G16b-晋升报告.json
用法：py -X utf8 g16b_vote_runner.py [--limit N]
env：EXAMINER_{LOCAL,DEEPSEEK,QWEN}_{BASE,MODEL}+key 全进程 env（D-004）。
"""
import json
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cbb-v2"))

from cbb2 import promote  # noqa: E402
from cbb2 import ops  # noqa: E402

STORE = ROOT / "迷深实战-本体库"
JOURNAL = STORE / "G16b-票面台账.jsonl"
REPORT = STORE / "G16b-晋升报告.json"
G13 = STORE / "G13-票权加权报告.json"


def main():
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    done = set()
    if JOURNAL.exists():
        for l in JOURNAL.read_text(encoding="utf-8").splitlines():
            if l.strip():
                done.add(json.loads(l)["record_id"])

    records = []
    for p in sorted(STORE.glob("libraries/*/*/*.json")):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — 坏件计数不拖批
            continue
        if r.get("status") != "provisional" or r.get("record_id") in done:
            continue
        ev = "；".join(e.get("quote", "") for e in (r.get("evidence") or []))
        if not ev.strip():
            continue
        records.append(r)
    if limit:
        records = records[:limit]
    total_lib = len(list(STORE.glob("libraries/*/*/*.json")))
    print(f"主库 json {total_lib} 件；本轮评审 {len(records)}（已评审跳过 {len(done)}）")

    panel, missing = promote.build_panel()
    print(f"考官编制: {[c.kind for c in panel]}（缺席: {missing or '无'}）")
    if not panel or not records:
        print("G16b BLOCKED 或无可评件")
        return

    weights = {}
    if G13.exists():
        g13 = json.loads(G13.read_text(encoding="utf-8"))
        weights = {k: v.get("weight_建议", 1.0) for k, v in g13.get("examiners", {}).items()}
    print(f"G13 权重: {weights or '（无——等权）'}")

    receipts = {c.kind: {"calls": 0, "errors": 0, "latency_s": 0.0} for c in panel}

    def review_one(rec):
        conclusion = json.dumps(rec.get("canonical") or {}, ensure_ascii=False, sort_keys=True)
        evidence = "；".join(e.get("quote", "") for e in (rec.get("evidence") or []))
        res = promote.vote(conclusion, evidence, panel, full_size=3,
                           weights=weights or None)
        res["record_id"] = rec.get("record_id")
        res["library"] = rec.get("library")
        return res

    t0 = time.time()
    results = []
    with JOURNAL.open("a", encoding="utf-8") as jf, \
            ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(review_one, r): r for r in records}
        for n, fu in enumerate(as_completed(futs), 1):
            try:
                res = fu.result()
            except Exception as e:  # noqa: BLE001 — 单件异常不拖垮整批
                res = {"verdict": "error", "votes": {}, "errors": [{"examiner": "runner",
                        "reason": str(e)[:120]}], "degraded": True,
                        "record_id": futs[fu].get("record_id")}
            results.append(res)
            jf.write(json.dumps(res, ensure_ascii=False, sort_keys=True) + "\n")
            jf.flush()
            # 消费回执聚合（双序=每考官×2 调用；错误行计入 errors）
            for kind, v in res.get("votes", {}).items():
                receipts.setdefault(kind, {"calls": 0, "errors": 0, "latency_s": 0.0})
                receipts[kind]["calls"] += 2
            for e in res.get("errors", []):
                k = e.get("examiner")
                if k in receipts:
                    receipts[k]["errors"] += 1
            if n % 50 == 0 or n == len(records):
                cc = Counter(r["verdict"] for r in results)
                el = time.time() - t0
                print(f"  进度 {n}/{len(records)}  {dict(cc)}  {el:.0f}s"
                      f"（{el/n:.1f}s/件，ETA {(el/n)*(len(records)-n)/60:.0f}min）")

    cc = Counter(r["verdict"] for r in results)
    report = {
        "unit": "G16b", "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "panel": [c.kind for c in panel], "panel_missing": missing,
        "weights": weights,
        "主库json总数": total_lib, "本轮评审": len(records),
        "历史已评审": len(done), "判定分布": dict(cc),
        "考官消费回执": receipts,
        "tenure口径": "首晋升批——tenure 自确认日起算，G17 首圈巡检承接存续核证",
        "耗时s": round(time.time() - t0, 1),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ 台账累计 {len(done)+len(results)}；判定分布 {dict(cc)}；报告 → {REPORT}")


if __name__ == "__main__":
    main()
