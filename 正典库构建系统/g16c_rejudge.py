# -*- coding: utf-8 -*-
"""g16c_rejudge.py — G16c 重审（回填后）：双外部考官对回填件重投票。
考官输入审计（硬约束）：prompt 载荷白名单=canonical+引文串——出现任何图派生键即 abort
（"图给人当路标，不给机器当证词"，2026-09-28 用户质询后立此防线）。
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

STORE = ROOT / "迷深实战-本体库"
SIDECAR = STORE / "补充证据-回填-试点.jsonl"
G16B = STORE / "G16b-票面台账.jsonl"
JOURNAL = STORE / "G16c-重审台账-试点.jsonl"

ALLOWED_PAYLOAD_KEYS = {"canonical", "evidence_quotes"}
FORBIDDEN_MARKERS = ("edges", "neighbors", "graph", "adjacency", "图")


def build_payload(rec, supplements):
    """考官载荷：canonical+合并引文（原文+回填原文句）。白名单外一键即 abort。"""
    quotes = [e.get("quote", "") for e in (rec.get("evidence") or [])]
    quotes += [s.get("quote", "") for s in supplements]
    payload = {"canonical": rec.get("canonical") or {}, "evidence_quotes": quotes}
    bad = set(payload) - ALLOWED_PAYLOAD_KEYS
    assert not bad, f"考官输入审计 FAIL：白名单外字段 {bad}"
    blob = json.dumps(payload, ensure_ascii=False)
    for m in FORBIDDEN_MARKERS:
        assert m not in blob.lower() or m == "图" and "图谱" not in blob, \
            f"考官输入审计 FAIL：疑似图派生内容 {m}"
    return payload


def main():
    rows = [json.loads(l) for l in SIDECAR.read_text(encoding="utf-8").splitlines() if l.strip()]
    full = [r for r in rows if r["status"] == "full"]
    print(f"回填 full 件: {len(full)}")

    g16b = {}
    for l in G16B.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            g16b[r["record_id"]] = r["verdict"]

    panel, missing = promote.build_panel(("DEEPSEEK", "QWEN"))
    print(f"编制: {[c.kind for c in panel]}（缺席 {missing or '无'}）；full_size=3 → promote=双 support")
    if not panel:
        return

    def review_one(row):
        # 从库件重读（sidecar 不存 canonical 全文）
        rec_path = None
        for f in STORE.glob(f"libraries/{row['library']}/*/{row['record_id']}.json"):
            rec_path = f
            break
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        payload = build_payload(rec, row["supplements"])
        conclusion = json.dumps(payload["canonical"], ensure_ascii=False, sort_keys=True)
        evidence = "；".join(payload["evidence_quotes"])
        res = promote.vote(conclusion, evidence, panel, full_size=3)
        res["record_id"] = row["record_id"]
        res["g16b_verdict"] = g16b.get(row["record_id"])
        return res

    t0 = time.time()
    results = []
    with JOURNAL.open("a", encoding="utf-8") as jf, \
            ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(review_one, r) for r in full]
        for n, fu in enumerate(as_completed(futs), 1):
            try:
                res = fu.result()
            except Exception as e:  # noqa: BLE001 — 单件异常计数不拖批
                res = {"verdict": "error", "errors": [{"reason": str(e)[:120]}]}
            results.append(res)
            jf.write(json.dumps(res, ensure_ascii=False, sort_keys=True) + "\n")
            jf.flush()
            if n % 10 == 0 or n == len(full):
                print(f"  {n}/{len(full)}  {time.time()-t0:.0f}s")

    flips = Counter()
    for r in results:
        a, b = r.get("g16b_verdict"), r.get("verdict")
        flips[f"{a} → {b}"] += 1
    print("\n翻转分布:")
    for k, v in flips.most_common():
        print(f"  {k}: {v}")
    print(f"耗时 {time.time()-t0:.0f}s → {JOURNAL}")


if __name__ == "__main__":
    main()
