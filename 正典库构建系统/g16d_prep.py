# -*- coding: utf-8 -*-
"""g16d_prep.py — 核指结果后核+成军（B1 收口件）。

①每条引文对语料原文后核（line_abs 定位+归一包含，extended/窗口内一视同仁）
②核验通过的写 补充证据-核心指代.jsonl（status=full——核心指代补充后锚定达标）
③供 G16d 重审：g16c_rejudge --sidecar 补充证据-核心指代.jsonl
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cbb-v2"))
from cbb2.anchor_check import norm  # noqa: E402

STORE = ROOT / "迷深实战-本体库"
RESULTS = ROOT / "迷深实战-工作区" / "coref_batches"
CORPUS = ROOT.parent / "语料分析" / "corpus" / "clean_full.txt"
BOUNDARY = ROOT / "迷深实战-工作区" / "manifest" / "boundary-table-v1.json"
OUT = STORE / "补充证据-核心指代.jsonl"


def main():
    boundary = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    chap_of = {c["chapter_no"]: c for c in boundary["chapters"]}
    lines = CORPUS.read_text(encoding="utf-8").splitlines()

    # 批文件元数据：record_id → (library, chapter)
    meta = {}
    for bf in sorted(RESULTS.glob("batch-*.json")):
        for rec in json.loads(bf.read_text(encoding="utf-8")):
            meta[rec["record_id"]] = {"library": rec["library"], "chapter": rec["chapter"]}

    out_rows = []
    stats = Counter()
    for rf in sorted(RESULTS.glob("results/batch-*.json")):
        data = json.loads(rf.read_text(encoding="utf-8"))
        results = data.get("results", []) if isinstance(data, dict) else data
        for rr in results:
            rid = rr["record_id"]
            m = meta.get(rid)
            if not m:
                stats["no_meta"] += 1
                continue
            supplements = []
            ok = True
            for pair in rr.get("pairs", []):
                if not pair.get("found") or not pair.get("quote") or not pair.get("line_abs"):
                    ok = False
                    continue
                line_abs = pair["line_abs"]
                q = pair["quote"]
                if line_abs > len(lines) or norm(q) not in norm(lines[line_abs - 1]):
                    ok = False  # 后核 FAIL：语料对应行没有这句（防编造）
                    stats["postverify_fail"] += 1
                    continue
                ch_no = next((cn for cn, c in chap_of.items()
                              if c["line_start"] <= line_abs <= c["line_end"]), None)
                if ch_no is None:
                    ok = False
                    continue
                supplements.append({
                    "vol": 1, "chapter": ch_no,
                    "line": line_abs - chap_of[ch_no]["line_start"] + 1,
                    "quote": q, "backfill": True, "coref": True,
                    "for_key": pair["key"],
                })
            if supplements and ok:
                out_rows.append({"record_id": rid, "status": "full",
                                 "library": m["library"],
                                 "supplements": supplements, "via": "llm-coref",
                                 "idem": rid})
                stats["verified_full"] += 1
            elif supplements:
                stats["partial"] += 1
            else:
                stats["no_coref"] += 1

    with OUT.open("w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"核心指代成军: {dict(stats)} → {OUT}（{len(out_rows)} 行）")


if __name__ == "__main__":
    main()
