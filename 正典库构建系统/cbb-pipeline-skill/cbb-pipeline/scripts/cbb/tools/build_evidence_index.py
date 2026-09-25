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
import os
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


def _k(r: dict) -> str:
    """去重/续传键（与进度件落盘键同构）。"""
    return f"{r['record_id']}|{r['line']}|{r['quote'][:40]}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="evidence 级片段索引（批量·可续）")
    import 路径惯例 as 惯
    _s = os.environ.get("CBB_STORE") or str(惯.store_of(HERE.parent.parent))
    ap.add_argument("--store", default=_s)
    ap.add_argument("--index", default=os.environ.get("CBB_INDEX")
                    or str(惯.workspace_of(Path(_s)) / "索引" / "lancedb"))
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--chunk", type=int, default=1000,
                    help="落表分块行数（内存上限≈chunk×dim×24B；2026-09-24 A-新:原一次性建 11 万行表 → ArrowMemoryError 3.87GB）")
    ns = ap.parse_args(argv)

    rows = collect_evidence(Path(ns.store))
    meta = {_k(r): r for r in rows}          # 仅文本元数据（小）；向量一律不驻留内存
    prog = Path(ns.index).parent / "_evidence-progress.jsonl"
    done_keys: set[str] = set()
    if prog.exists():
        # 只扫键（逐行 parse 即弃向量）：进度件可达 10GB 级，全读入内存必崩
        with prog.open(encoding="utf-8") as pf:
            for ln in pf:
                if ln.strip():
                    done_keys.add(json.loads(ln)["k"])
        print(f"续传：已有 {len(done_keys)} 条（键扫描，不载向量）")
    todo = [r for r in rows if _k(r) not in done_keys]
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
                        pf.write(json.dumps({"k": _k(r), "vec": x["embedding"]},
                                            ensure_ascii=False) + "\n")
                    pf.flush()
                    break
                except Exception as e:
                    print(f"  批 {i} 第 {attempt+1} 次失败: {str(e)[:50]}；重试")
                    time.sleep(5)
            else:
                raise SystemExit(f"批 {i} 三连失败；进度已落盘，重跑续传"
                                 f"（已完成 {len(done_keys) + i}）")
            if (i // ns.batch) % 50 == 0:
                print(f"  进度 {i + len(b)}/{len(todo)}")

    import lancedb
    import pyarrow as pa
    db = lancedb.connect(ns.index)
    tbl = None
    buf: list[tuple[str, list[float]]] = []
    n_rows = 0

    def flush() -> None:
        """分块落表：首块建表（overwrite），后续 add——峰值内存=一块。"""
        nonlocal tbl, buf, n_rows
        if not buf:
            return
        keys = [k for k, _ in buf]
        vecs = [v for _, v in buf]
        chunk = pa.table({
            "record_id": [meta[k]["record_id"] for k in keys],
            "chapter": pa.array([meta[k]["chapter"] for k in keys], type=pa.int64()),
            "line": pa.array([meta[k]["line"] for k in keys], type=pa.int64()),
            "quote": [meta[k]["quote"] for k in keys],
            "vector": pa.array(vecs, type=pa.list_(pa.float32(), len(vecs[0]))),
        })
        if tbl is None:
            tbl = db.create_table("evidence", chunk, mode="overwrite")
        else:
            tbl.add(chunk)
        n_rows += len(keys)
        buf = []

    if prog.exists():
        seen: set[str] = set()
        with prog.open(encoding="utf-8") as pf:
            for ln in pf:
                if not ln.strip():
                    continue
                r = json.loads(ln)
                if r["k"] in seen or r["k"] not in meta:
                    continue  # 去重（进度件可含重复行）／库外键跳过（三数在输出注明，不静默）
                seen.add(r["k"])
                buf.append((r["k"], r["vec"]))
                if len(buf) >= ns.chunk:
                    flush()
        flush()
    print("evidence 索引落盘:", tbl.count_rows() if tbl is not None else 0,
          f"行（进度件 {len(done_keys)} 键 / 当前库 {len(rows)} 行）")
    prog.unlink(missing_ok=True)  # 索引建成，10GB 级进度件清掉
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
