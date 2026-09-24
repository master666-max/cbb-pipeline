# -*- coding: utf-8 -*-
"""test_build_evidence_index.py — evidence 级索引构建件单测（零网络：预置进度件→走落表段）。

判据（2026-09-24 内存修复配套）：
①分块落表（--chunk 小于总行数时仍全量落，schema 稳定）；
②续传按**键扫描**（进度件可达 10GB，禁全载向量）；
③进度件里已不属当前库的键被过滤（不静默：落表行数与库内行数口径在输出注明）；
④建成即清进度件。
"""
import importlib
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
m = importlib.import_module("build_evidence_index")


def test_chunked_build_key_only_resume(tmp_path):
    store = tmp_path / "store" / "libraries" / "character" / "provisional"
    store.mkdir(parents=True)
    rec = {"record_id": "rec-1",
           "evidence": [{"vol": 1, "chapter": 1, "line": 2, "quote": "甲" * 60},
                        {"vol": 1, "chapter": 1, "line": 3, "quote": "乙" * 60}]}
    (store / "rec-1.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")

    idx = tmp_path / "idx"
    idx.mkdir()
    prog = idx / "_evidence-progress.jsonl"
    rows = [{"record_id": "rec-1", "chapter": 1, "line": 2, "quote": "甲" * 60},
            {"record_id": "rec-1", "chapter": 1, "line": 3, "quote": "乙" * 60},
            {"record_id": "rec-1", "chapter": 1, "line": 3, "quote": "乙" * 60},  # 重复键（并发批写的现实形态）
            {"record_id": "ghost", "chapter": 9, "line": 9, "quote": "丙" * 60}]  # 库外键
    with prog.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({"k": m._k(r), "vec": [0.1, 0.2, 0.3, 0.4]},
                               ensure_ascii=False) + "\n")

    rc = m.main(["--store", str(tmp_path / "store"), "--index", str(idx / "lancedb"),
                 "--chunk", "1"])  # chunk=1：强制多块（首块建表+后续 add 路径）
    assert rc == 0
    assert not prog.exists(), "建成后进度件应清除"

    import lancedb
    t = lancedb.connect(str(idx / "lancedb")).open_table("evidence")
    assert t.count_rows() == 2, f"库外键过滤 + 重复键去重后应 2 行，实得 {t.count_rows()}"
    assert {"record_id", "chapter", "line", "quote", "vector"} <= set(t.schema.names)
    df = t.to_pandas()
    assert set(df["line"]) == {2, 3}
    assert list(df["vector"][0]) == [0.1, 0.2, 0.3, 0.4]
    keys = df["record_id"].astype(str) + "|" + df["line"].astype(str) + "|" + df["quote"].str[:40]
    assert keys.nunique() == len(df) == 2, "表内键必须唯一（进度件重复行不得落表两遍）"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        with tempfile.TemporaryDirectory() as td:
            fn(Path(td))
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
