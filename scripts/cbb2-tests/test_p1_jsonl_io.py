# -*- coding: utf-8 -*-
"""test_p1_jsonl_io.py — P-028 回归：U+2028/2029 撕裂读面 + 坏行披露不静默。

旧读面 str.splitlines() 把 U+2028/U+2029/U+0085 当行界——JSON 字符串合法包含
这些字符时被撕裂（json.loads 裸崩或行静默丢失）。修复后：共享读面 cbb2.jsonl_io
只按 \\n 切行；坏行进 skipped 披露（实例属性 + 模块级缓冲），不静默丢弃。
"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import gaps, jsonl_io, plant, quarantine, search  # noqa: E402
from cbb2.derive import DebtLedger  # noqa: E402
from cbb2.er import MergeLog  # noqa: E402

U2028 = "\u2028"


def setup_function(fn):
    jsonl_io.reset_disclosures()


def test_p1_read_jsonl_lines_keeps_u2028_inline():
    text = json.dumps({"detail": f"左{U2028}右"}, ensure_ascii=False) + "\n" + '{"ok": 1}\n'
    lines = jsonl_io.read_jsonl_lines(text)
    assert len(lines) == 2  # 旧 splitlines() 在此撕成 3 段
    assert json.loads(lines[0])["detail"] == f"左{U2028}右"  # 行内 U+2028 原样保留
    rows, skipped = jsonl_io.parse_jsonl(text, source="t.jsonl")
    assert len(rows) == 2 and skipped == []


def test_p1_parse_jsonl_discloses_bad_line_not_silent():
    good = json.dumps({"a": 1}, ensure_ascii=False)
    rows, skipped = jsonl_io.parse_jsonl(good + "\nnot-json{{\n" + good + "\n", source="x.jsonl")
    assert len(rows) == 2
    assert len(skipped) == 1 and skipped[0]["line"] == 2 and skipped[0]["source"] == "x.jsonl"
    assert jsonl_io.disclosed_skips()[-1]["source"] == "x.jsonl"  # 模块级披露缓冲留痕


def test_p1_quarantine_u2028_roundtrip_and_corrupt_disclosure():
    with tempfile.TemporaryDirectory() as td:
        z = quarantine.QuarantineZone(Path(td))
        detail = f"甲{U2028}乙"  # 旧读面：_load 撕裂此行直接裸崩
        iid, _ = z.register("low_confidence", detail, record_id="r1")
        z2 = quarantine.QuarantineZone(Path(td))  # 重开实例——走读面
        items = z2._load()
        assert any(it.get("detail") == detail for it in items)
        assert z2.skipped == []
        with z2.items_path.open("a", encoding="utf-8") as f:
            f.write("{{bad line\n")  # 真坏行
        z3 = quarantine.QuarantineZone(Path(td))
        z3._load()
        assert len(z3.skipped) == 1 and z3.skipped[0]["line"] == 2  # 披露不静默
        assert [i["item_id"] for i in z3.pending()] == [iid]  # 坏行不阻塞 pending 读面


def test_p1_merge_log_debt_ledger_u2028_survive():
    with tempfile.TemporaryDirectory() as td:
        ml = MergeLog(Path(td))
        name = f"水{U2028}影"
        ml.merge(name, "丙", rule="alias", confidence=0.99, at="2026-10-03")
        ml2 = MergeLog(Path(td))
        assert ml2.groups().get(name) == [name, "丙"] or ml2.resolve("丙") == name
        assert ml2.skipped == []
        d = DebtLedger(Path(td) / "sub")
        d.incur(f"t{U2028}x", "r", "2026-10-03")
        d2 = DebtLedger(Path(td) / "sub")
        assert [r["target"] for r in d2.open_items()] == [f"t{U2028}x"]
        assert d2.skipped == []


def test_p1_gaps_plant_search_corrupt_line_not_fatal():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        qp = root / gaps.QUEUE
        qp.write_text(json.dumps({"type": "词表缺口", "evidence": "e1"}, ensure_ascii=False)
                      + "\nbroken{{\n", encoding="utf-8")
        gaps._append(root, {"type": "词表缺口", "evidence": "e1"})  # 幂等命中——坏行不崩
        rows = gaps.load_queue(root)
        assert [r.get("evidence") for r in rows] == ["e1"]  # 坏行不入结果但已披露
        assert any(s["source"] == gaps.QUEUE for s in jsonl_io.disclosed_skips())
        pp = root / plant.STATE
        pp.write_text(json.dumps({"plant_id": "p1", "name": "金标甲", "expect": {}},
                                 ensure_ascii=False) + "\ngarbage{{\n", encoding="utf-8")
        rep = plant.capture_rate(root, [], chapter=None)
        assert rep["plants"] == 1 and rep["miss"][0]["plant_id"] == "p1"
        ap = root / "aliases.jsonl"
        ap.write_text(json.dumps({"alias": "涡波", "entity_id": "rid1"}, ensure_ascii=False)
                      + f"\n{{broken{U2028}\n", encoding="utf-8")
        char = root / "libraries" / "character" / "confirmed" / "rid1.json"
        char.parent.mkdir(parents=True, exist_ok=True)
        char.write_text(json.dumps({"record_id": "rid1",
                                    "canonical": {"name": "相川涡波"}}, ensure_ascii=False),
                        encoding="utf-8")
        assert search.alias_recall("涡波登场", root)[0]["name"] == "相川涡波"  # 坏别名行不崩


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
