# -*- coding: utf-8 -*-
"""build_evidence_index.py — evidence 级片段索引构建（U-F07 v2 续件 · 批量任务 · 可断点续传）

把全库记录的证据引文（10 万级）逐条嵌入写入 LanceDB `evidence` 表——
用途：G2 证据门的片段级检索、引文核验辅助、双复查的样本采集。
**小时级批量件**：建议挂夜间/闲时窗口跑；进度落盘可续（中断重跑自动跳过已完成）。

用法：py -X utf8 build_evidence_index.py [--store <本体库>] [--index <索引目录>] [--batch 16]
"""
from __future__ import annotations

import argparse
import importlib
import json
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
import sys
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
m = importlib.import_module("neo4j_export")

EMB = "http://127.0.0.1:8080/v1/embeddings"
MODEL = "text-embedding-qwen3-embedding-8b@q4_k_m"


def collect_evidence(store: Path) -> list[dict]:
    """全库记录的 evidence 四元组 → 待嵌入行（去重键＝record_id+line+quote 前 80 字）。"""
    rows, seen = [], set()
    for f in sorted(store.glob("libraries/*/*/*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        rid = rec.get("record_id")
        for ev in rec.get("evidence") or []:
            q = (ev.get("quote") or "").strip()
            if not q:
                continue
            key = (rid, ev.get("line"), q[:80])
            if key in seen:
                continue
            seen.add(key)
            rows.append({"record_id": rid, "chapter": ev.get("chapter"), "line": ev.get("line"),
                         "vol": ev.get("vol"), "quote": q})
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="evidence 级片段索引（批量·可续）")
    ap.add_argument("--store", default=str(HERE.parent / "迷深实战-本体库"))
    ap.add_argument("--index", default=str(HERE.parent / "迷深实战-工作区" / "索引" / "lancedb"))
    ap.add_argument("--batch", type=int, default=16)
    ns = ap.parse_args(argv)

    rows = collect_evidence(Path(ns.store))
    prog = Path(ns.index).parent / "_evidence-progress.jsonl"
    done: dict[str, list[float]] = {}
    if prog.exists():
        for ln in prog.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                r = json.loads(ln)
                done[r["k"]] = r["vec"]
        print(f"续传：已有 {len(done)} 条")
    todo = [r for r in rows if f"{r['record_id']}|{r['line']}|{r['quote'][:40]}" not in done]
    print(f"待嵌入 {len(todo)} / {len(rows)}（批量任务，可随时中断续跑）")
    prog.parent.mkdir(parents=True, exist_ok=True)
    with prog.open("a", encoding="utf-8") as pf:
        for i in range(0, len(todo), ns.batch):
            b = todo[i:i + ns.batch]
            payload = json.dumps({"model": MODEL, "input": [r["quote"] for r in b]},
                                 ensure_ascii=False).encode("utf-8")
            for attempt in range(3):
                try:
                    req = urllib.request.Request(EMB, data=payload,
                                                 headers={"Content-Type": "application/json"})
                    d = json.loads(urllib.request.urlopen(req, timeout=300).read().decode("utf-8"))
                    arr = sorted(d["data"], key=lambda x: x["index"])
                    for r, x in zip(b, arr):
                        k = f"{r['record_id']}|{r['line']}|{r['quote'][:40]}"
                        done[k] = x["embedding"]
                        pf.write(json.dumps({"k": k, "vec": x["embedding"]}, ensure_ascii=False) + "\n")
                    pf.flush()
                    break
                except Exception as e:
                    print(f"  批 {i} 第 {attempt+1} 次失败: {str(e)[:50]}；重试")
                    time.sleep(5)
            else:
                raise SystemExit(f"批 {i} 三连失败；进度已落盘，重跑续传（已完成 {len(done)}）")
            if (i // ns.batch) % 50 == 0:
                print(f"  进度 {i + len(b)}/{len(todo)}")

    import lancedb
    import pyarrow as pa
    final = [r for r in rows if f"{r['record_id']}|{r['line']}|{r['quote'][:40]}" in done]
    db = lancedb.connect(ns.index)
    tbl = db.create_table("evidence", pa.table({
        "record_id": [r["record_id"] for r in final],
        "chapter": [r["chapter"] for r in final],
        "line": [r["line"] for r in final],
        "quote": [r["quote"] for r in final],
        "vector": [done[f"{r['record_id']}|{r['line']}|{r['quote'][:40]}"] for r in final],
    }), mode="overwrite")
    print("evidence 索引落盘:", tbl.count_rows(), "行")
    prog.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
