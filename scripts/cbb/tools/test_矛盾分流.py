# -*- coding: utf-8 -*-
"""test_矛盾分流.py — 裁决 ⑤ 四分类与双模式执行的机械测试（正对照成对）"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib
m = importlib.import_module("矛盾分流")


def test_classify_pairs():
    """正对照：五类各归其位；机械档对齐方向=库内值。"""
    assert m.classify_pair("entity_type", "组织", "组织")["cls"] == "identical"
    assert m.classify_pair("entity_type", "ｵｰｸﾞ", "奥格")["cls"] == "orthographic" \
        or m.classify_pair("entity_type", "组织 ", "组织")["cls"] == "orthographic"
    g = m.classify_pair("entity_type", "人物", "人物(迷宫生物)")
    assert g["cls"] == "granularity" and g["mechanical"] and g["align_to"] == "人物(迷宫生物)"
    i = m.classify_pair("entity_type", "人物", None)
    assert i["cls"] == "incomplete" and not i["mechanical"]
    d = m.classify_pair("entity_type", "技能魔法", "魔法体系")
    assert d["cls"] == "direct_conflict" and not d["mechanical"] and d["align_to"] is None


def test_parse_dual_track_detail():
    p = m.parse_dual_track_detail("entity_type: 入库='人物' vs 库内='人物(迷宫生物)'")
    assert p == ("entity_type", "人物", "人物(迷宫生物)")
    assert m.parse_dual_track_detail("嵌入相似度存疑(0.85~0.95)：A vs B sim=0.88") is None


def test_propose_reads_quarantine(tmp_path):
    q = tmp_path / "quarantine-zone"
    q.mkdir(parents=True)
    items = [
        {"item_id": "q1", "status": "pending", "subclass": "contradiction_pending",
         "record_id": "r1", "detail": "entity_type: 入库='人物' vs 库内='人物(迷宫生物)'"},
        {"item_id": "q2", "status": "pending", "subclass": "contradiction_pending",
         "record_id": "r2", "detail": "嵌入相似度存疑：A vs B sim=0.9"},
        {"item_id": "q3", "status": "pending", "subclass": "extrapolation_unverified",
         "detail": "置信度路由：0.8<0.85"},
    ]
    (q / "items.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in items),
                                   encoding="utf-8")
    rep = m.propose(tmp_path)
    assert rep["by_cls"]["granularity"] == 1
    assert len(rep["proposals"]) == 1  # 口径：非双轨形态不计入
    assert rep["proposals"][0]["align_to"] == "人物(迷宫生物)"


def test_apply_auto_vs_batch_confirm(tmp_path):
    props = [
        {"item_id": "q1", "record_id": "r1", "field": "entity_type",
         "val_in": "人物", "val_stored": "人物(迷宫生物)", "cls": "granularity",
         "mechanical": True, "align_to": "人物(迷宫生物)", "why": "粒度差异"},
        {"item_id": "q9", "record_id": "r9", "field": "entity_type",
         "val_in": "技能魔法", "val_stored": "魔法体系", "cls": "direct_conflict",
         "mechanical": False, "align_to": None, "why": "真冲突"},
    ]
    # auto：机械档执行，direct_conflict 永不执行（正对照成对）
    s1 = m.apply(props, "auto", store_root=tmp_path, at="2026-09-22")
    assert s1["executed"] == 1 and s1["skipped_direct_conflict"] == 1
    ledger = [json.loads(x) for x in (tmp_path / "处置台账.jsonl").read_text(encoding="utf-8").splitlines()]
    assert ledger[0]["to"] == "人物(迷宫生物)" and ledger[0]["at"] == "2026-09-22"
    # batch_confirm：未确认不执行（负对照）＋确认后执行（正对照）
    s2 = m.apply(props, "batch_confirm", confirmations=[], store_root=tmp_path)
    assert s2["executed"] == 0 and s2["skipped_not_confirmed"] == 1
    s3 = m.apply(props, "batch_confirm", confirmations=["q1"], store_root=tmp_path)
    assert s3["executed"] == 1
    try:
        m.apply(props, "yolo")
        raise AssertionError("非法 mode 应拒")
    except ValueError:
        pass


def test_align_candidate_pure_function():
    rec = {"record_id": "r1", "library": "character", "canonical": {"entity_type": "人物", "name": "x"}}
    out = m.align_candidate(rec, "entity_type", "人物(迷宫生物)")
    assert out["canonical"]["entity_type"] == "人物(迷宫生物)"
    assert out["_meta"]["alignment"]["aligned_to"] == "人物(迷宫生物)"
    assert rec["canonical"]["entity_type"] == "人物"  # 纯函数：入参不动


if __name__ == "__main__":
    import tempfile
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        if fn.__code__.co_argcount:  # 需要 tmp_path 的才注入
            with tempfile.TemporaryDirectory() as td:
                fn(Path(td))
        else:
            fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
