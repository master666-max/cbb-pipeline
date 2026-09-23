# -*- coding: utf-8 -*-
"""test_词表.py — 裁决 ③A 三规则的机械测试（正对照成对）"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib
m = importlib.import_module("词表")


def _mk_store(tmp_path, records):
    for i, r in enumerate(records):
        lib = r["library"]
        d = tmp_path / "libraries" / lib / "provisional"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"cand-{i:04d}.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")


def test_bootstrap_counts_and_containment_pairs(tmp_path):
    """正对照：频次统计正确＋包含对被抓出并给归并建议。"""
    recs = [
        {"library": "character", "canonical": {"entity_type": "人物"}},
        {"library": "character", "canonical": {"entity_type": "人物(迷宫生物)"}},
        {"library": "character", "canonical": {"entity_type": "人物"}},
        {"library": "setting", "canonical": {"entity_type": "魔法体系"}},
    ]
    _mk_store(tmp_path, recs)
    rep = m.bootstrap(tmp_path, fields=("entity_type",))
    vals = rep["entity_type"]["values"]
    assert vals == {"人物": 2, "人物(迷宫生物)": 1, "魔法体系": 1}
    pairs = rep["entity_type"]["containment_pairs"]
    assert any(p["short"] == "人物" and p["long"] == "人物(迷宫生物)" for p in pairs)
    assert all("待确认" in p["态"] for p in pairs)  # 四选一归人，机器不裁断


def test_lint_vocab_catches_containment(tmp_path):
    """负对照：词表里放包含对必须报；正对照：干净词表零违规。"""
    bad = {"entity_type": ["人物", "人物(迷宫生物)"]}
    assert any(x["reason"] == "GRANULARITY_CONFLICT" for x in m.lint_vocab(bad))
    good = {"entity_type": ["人物(迷宫生物)", "人物(传说)", "组织"]}
    assert m.lint_vocab(good) == []  # 无包含关系（"人物(迷宫生物)"与"人物(传说)"互不包含）


def test_check_record_reason_codes(tmp_path):
    vocab = {"entity_type": ["人物(迷宫生物)", "组织"]}
    rec_ok = {"library": "character", "canonical": {"entity_type": "人物(迷宫生物)", "name": "缇达"}}
    assert m.check_record(rec_ok, vocab) == []  # 在册 → 过
    rec_gran = {"library": "character", "canonical": {"entity_type": "人物", "name": "x"}}
    v1 = m.check_record(rec_gran, vocab)
    assert v1[0]["reason"] == "GRANULARITY_VARIANT" and v1[0]["suggest"] == "人物(迷宫生物)"
    rec_out = {"library": "character", "canonical": {"entity_type": "魔法体系", "name": "x"}}
    v2 = m.check_record(rec_out, vocab)
    assert v2[0]["reason"] == "NOT_IN_VOCAB"
    req = {"character": ("name",)}
    rec_miss = {"library": "character", "canonical": {"entity_type": "组织"}}
    v3 = m.check_record(rec_miss, vocab, req)
    assert any(x["reason"] == "MISSING_REQUIRED" and x["field"] == "name" for x in v3)


def test_check_store_dryrun_readonly(tmp_path):
    recs = [
        {"library": "character", "record_id": "r1", "canonical": {"entity_type": "人物"}},
        {"library": "character", "record_id": "r2", "canonical": {"entity_type": "人物(迷宫生物)"}},
    ]
    _mk_store(tmp_path, recs)
    vocab = {"entity_type": ["人物(迷宫生物)"]}
    before = sorted(p.name for p in (tmp_path / "libraries" / "character" / "provisional").iterdir())
    rep = m.check_store(tmp_path, vocab)
    after = sorted(p.name for p in (tmp_path / "libraries" / "character" / "provisional").iterdir())
    assert before == after  # 只读干跑：目录零变化
    assert rep["checked"] == 2 and rep["violations"] == 1
    assert rep["by_reason"] == {"GRANULARITY_VARIANT": 1}


if __name__ == "__main__":
    import tempfile
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        with tempfile.TemporaryDirectory() as td:
            fn(Path(td))
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
