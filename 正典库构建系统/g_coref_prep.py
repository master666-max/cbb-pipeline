# -*- coding: utf-8 -*-
"""g_coref_prep.py — B1 核指消解·批文件准备（工作流前置机械件）。

对象：补充证据-回填.jsonl 里 status=unbackfillable/partial 的件（窗口匹配没能全锚，
需要 LLM 读章消解零指代/找先行语）。
产出：迷深实战-工作区/coref_batches/batch-NN.json（每批 10 件，内联章窗口原文+
行号），供工作流子代理逐批消解。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STORE = ROOT / "迷深实战-本体库"
BACKFILL = STORE / "补充证据-回填.jsonl"
CORPUS = ROOT.parent / "语料分析" / "corpus" / "clean_full.txt"
BOUNDARY = ROOT / "迷深实战-工作区" / "manifest" / "boundary-table-v1.json"
OUTDIR = ROOT / "迷深实战-工作区" / "coref_batches"
PER_BATCH = 10
WINDOW = 30  # 证据行 ±30 行


def main():
    boundary = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    chap_of = {c["chapter_no"]: c for c in boundary["chapters"]}
    lines = CORPUS.read_text(encoding="utf-8").splitlines()

    sys.path.insert(0, str(ROOT / "cbb-v2"))
    from cbb2.anchor_check import missing_keys, norm

    rows = [json.loads(l) for l in BACKFILL.read_text(encoding="utf-8").splitlines() if l.strip()]
    targets = [r for r in rows if r["status"] in ("unbackfillable", "partial")]
    print(f"核指候选: {len(targets)} 件（unbackfillable+partial）")

    batches = []
    cur = []
    for r in targets:
        rec_path = next(STORE.glob(f"libraries/{r['library']}/*/{r['record_id']}.json"), None)
        if rec_path is None:
            continue
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        c = rec.get("canonical") or {}
        # 仍缺的 key（partial 的部分 key 已被窗口回填锚定）
        quotes_all = norm("；".join(
            [e.get("quote", "") for e in (rec.get("evidence") or [])] +
            [s.get("quote", "") for s in r.get("supplements", [])]))
        mk = missing_keys(r["library"], c, quotes_all)
        if not mk:
            continue
        # 章窗口：取证据章 ±30 行（多证据章取并集）
        ch_no = (rec.get("evidence") or [{}])[0].get("chapter")
        ch = chap_of.get(ch_no)
        if not ch:
            continue
        anchors = [ch["line_start"] - 1 + e["line"] for e in rec.get("evidence") or [] if e.get("line")]
        lo = max(ch["line_start"], (min(anchors) - WINDOW) if anchors else ch["line_start"])
        hi = min(min(ch["line_end"], len(lines)), (max(anchors) + WINDOW) if anchors else ch["line_end"])
        window = [f"L{i}: {lines[i-1]}" for i in range(lo, hi + 1)]
        cur.append({
            "record_id": r["record_id"], "library": r["library"],
            "chapter": ch_no, "line_start_abs": lo,
            "missing_keys": mk,
            "canonical": c,
            "window_lines": window,
        })
        if len(cur) >= PER_BATCH:
            batches.append(cur)
            cur = []
    if cur:
        batches.append(cur)

    OUTDIR.mkdir(exist_ok=True)
    manifest = []
    for i, b in enumerate(batches, 1):
        p = OUTDIR / f"batch-{i:02d}.json"
        p.write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
        manifest.append({"batch": i, "file": p.name, "records": len(b)})
    (OUTDIR / "manifest.json").write_text(
        json.dumps({"batches": manifest, "total_records": sum(m["records"] for m in manifest)},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"批文件 {len(batches)} 个（{sum(m['records'] for m in manifest)} 件）→ {OUTDIR}")


if __name__ == "__main__":
    main()
