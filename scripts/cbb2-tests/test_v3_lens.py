# -*- coding: utf-8 -*-
"""test_v3_lens.py — Phase F·G02 只读分析层。运行：py -X utf8 test_v3_lens.py"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import lens  # noqa: E402


def test_tri_state_counts():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        lib = root / "libraries" / "character" / "provisional"
        lib.mkdir(parents=True)
        for i in range(5):
            (lib / f"c{i}.json").write_text("{}", encoding="utf-8")
        qz = root / "quarantine-zone"
        qz.mkdir(parents=True)
        (qz / "items.jsonl").write_text(
            json.dumps({"item_id": "q1", "status": "pending", "subclass": "contradiction_pending"}) + "\n" +
            json.dumps({"item_id": "q2", "status": "confirmed", "subclass": "contradiction_pending"}) + "\n",
            encoding="utf-8")
        r = lens.tri_state_counts(root)
        assert r["provisional"] == 5 and r["quarantine_pending"] == 1 and r["quarantine_confirmed"] == 1


def test_invalidation_chain():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "invalidations.jsonl").write_text(
            json.dumps({"record_id": "e1", "t_invalid": "ch0020"}) + "\n", encoding="utf-8")
        r = lens.invalidation_chain(root)
        assert len(r) == 1 and r[0]["record_id"] == "e1"


def test_complementary_count():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        root.mkdir(exist_ok=True)
        (root / "complementary-statements.jsonl").write_text(
            json.dumps({"event_id": "ce-1"}) + "\n" +
            json.dumps({"event_id": "ce-2"}) + "\n", encoding="utf-8")
        assert lens.complementary_count(root) == 2


def test_full_report():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        root.mkdir(exist_ok=True)
        r = lens.full_report(root)
        assert "tri_state" in r and "invalidations" in r and "complementary" in r


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
