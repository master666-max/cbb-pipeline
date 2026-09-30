# -*- coding: utf-8 -*-
"""test_v3_gate.py — U-A03 候选态输入档：畸形输入出码不崩（D-1/D-25）。运行：py -X utf8 test_v3_gate.py"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import gate  # noqa: E402


def test_canonical_string_gets_code_not_crash():
    """D-1：canonical 写成字符串 ⇒ G1-SCHEMA 码，不抛异常。"""
    out = gate.ensure_input({"record_type": "entity", "canonical": "人物", "evidence": []})
    assert "G1-SCHEMA" in out["codes"]
    assert isinstance(out["record"]["canonical"], dict) and "_raw" in out["record"]["canonical"]


def test_null_record_id_gets_deterministic_placeholder():
    """D-25：record_id=null ⇒ 哈希占位（同输入同占位）。"""
    a = gate.ensure_input({"record_type": "entity", "canonical": {"name": "缇达"}, "evidence": []})
    b = gate.ensure_input({"record_type": "entity", "canonical": {"name": "缇达"}, "evidence": []})
    assert a["record"]["record_id"].startswith("rec-auto-")
    assert a["record"]["record_id"] == b["record"]["record_id"]
    assert "ID-PLACEHOLDER" in a["codes"]


def test_clean_input_zero_codes():
    out = gate.ensure_input({"record_id": "x1", "record_type": "entity",
                             "canonical": {"name": "卢卡"}, "evidence": [{"vol": 1}]})
    assert out["codes"] == [] and out["record"]["record_id"] == "x1"


def test_make_record_survives_malformed_canonical():
    rec = gate.make_record("entity", "character", "人物", [])
    assert isinstance(rec["canonical"], dict)


def test_all_modules_import_clean():
    """D-18 族守卫：全模块导入零 NameError。"""
    import importlib
    for mod in ("config", "contract", "corpus", "defenses", "gate", "ledger",
                "quarantine", "search", "store"):
        importlib.import_module(f"cbb2.{mod}")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
