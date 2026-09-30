# -*- coding: utf-8 -*-
"""test_v3_fastscan_coldstore.py — Phase F·G04 AC 粗筛 + G07 zstd 冷段。"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import coldstore, fastscan  # noqa: E402


def test_fastscan_literal_and_regex():
    pats = ["月票", "求收藏", "章末说"]
    hits = fastscan.scan_patterns("本章说求月票求收藏", pats)
    assert all(h["pattern"] in pats for h in hits)
    assert len(hits) >= 2  # 月票/求收藏


def test_fastscan_empty():
    assert fastscan.scan_patterns("", ["x"]) == []
    assert fastscan.scan_patterns("text", []) == []


def test_coldstore_segment_and_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        root.mkdir(exist_ok=True)
        lines = [json.dumps({"seq": i, "hash": f"h{i:04d}"}) for i in range(1, 101)]
        (root / "ledger.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        r = coldstore.segment_ledger(root, segment_size=30)
        assert r["status"] == "segmented"
        rows = coldstore.load_all_rows(root)
        assert len(rows) == 100
        assert json.loads(rows[0])["seq"] == 1
        assert json.loads(rows[-1])["seq"] == 100


def test_coldstore_empty():
    with tempfile.TemporaryDirectory() as td:
        assert coldstore.segment_ledger(Path(td))["status"] == "no-ledger"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
