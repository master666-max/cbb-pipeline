# -*- coding: utf-8 -*-
"""test_抽样排序.py — 岗位②测试（桩传输；正负对照成对）"""
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
排序 = importlib.import_module("抽样排序")


def _items():
    return [
        {"record_id": "r1", "claim": "甲在第四章死亡", "quote": "甲倒在血泊中再也没有起来。"},   # 支撑高
        {"record_id": "r2", "claim": "甲乙结为兄弟", "quote": "今天天气不错，适合出门散步。"},  # 支撑≈0（最可疑）
        {"record_id": "r3", "claim": "甲持有手环", "quote": "甲接过手环看了看。"},              # 支撑中
    ]


def _transport_by_doc(doc_keyword_score):
    """按 document 内容关键词回分数的桩（确定性）。"""
    def t(endpoint, payload, timeout):
        d = json.loads(payload.decode("utf-8"))
        doc = d["documents"][0]
        s = 0.9
        for k, v in doc_keyword_score.items():
            if k in doc:
                s = v
        return json.dumps({"results": [{"index": 0, "relevance_score": s}]}).encode("utf-8")
    return t


def test_suspicious_first_when_rerank_available():
    t = _transport_by_doc({"血泊": 0.95, "手环": 0.6, "天气": 0.01})
    rep = 排序.rank_for_review(_items(), transport=t)
    assert rep["backend"] == "rerank"
    first = rep["order"][0]
    assert _items()[first]["record_id"] == "r2"  # 支撑≈0 的最可疑排最前（正对照）
    assert len(rep["order"]) == 3 and set(rep["order"]) == {0, 1, 2}  # 集合不变
    assert rep["supports"]["r2"] == 0.01


def test_mechanical_fallback_keeps_original_order():
    """判据：缺席即降级——保持原序，backend 如实标注（负对照）。"""
    def t(endpoint, payload, timeout):
        raise OSError("端点不在")
    rep = 排序.rank_for_review(_items(), transport=t)
    assert rep["backend"] == "mechanical" and rep["order"] == [0, 1, 2]


def test_missing_text_forces_mechanical():
    items = _items() + [{"record_id": "r4", "claim": "", "quote": ""}]
    t = _transport_by_doc({"血泊": 0.95})
    rep = 排序.rank_for_review(items, transport=t)
    assert rep["backend"] == "mechanical" and rep["order"] == [0, 1, 2, 3]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
