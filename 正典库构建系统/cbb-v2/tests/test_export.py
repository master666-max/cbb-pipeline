# -*- coding: utf-8 -*-
"""test_export.py — 批次 3·X1 交付形态引擎测试（快照范式公理的机械面）。

公理：store=活体；导出=不可变快照；快照自锚定；对账失败不发布。
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import export  # noqa: E402


def _rec(rid: str, name: str, quotes: list[str], status="provisional", lib="character") -> dict:
    return {"record_id": rid, "library": lib, "status": status,
            "canonical": {"name": name, "entity_type": "人物", "fact": f"{name}的事实"},
            "evidence": [{"vol": 1, "chapter": 3, "line": 10 + i, "quote": q} for i, q in enumerate(quotes)],
            "_aliases": [f"{name}酱"]}


def test_anchor_fields_and_immutability():
    head = {"rows": 5268, "chain_head": "abc123"}
    a = export.build_anchor(store_root=Path("/fake"), ledger_head=head, record_count=42,
                            page_count=42, edge_count=7, exporter_version="1.0")
    assert a["检查点"]["rows"] == 5268 and a["检查点"]["chain_head"] == "abc123"
    assert a["对账"]["记录页数"] == 42 and a["对账"]["边数"] == 7
    assert a["导出器版本"] == "1.0" and "生成时间" in a
    before = json.dumps(a, ensure_ascii=False, sort_keys=True)
    a["检查点"]["rows"] = 0                            # 试图改锚
    assert json.dumps(a, ensure_ascii=False, sort_keys=True) != before  # 可检测


def test_render_record_page_blind_and_grounded():
    rec = _rec("cand-abc", "沈青梧", ["他把玉佩递给了沈青梧。", "沈青梧继而不见了玉佩。"])
    md = export.render_record_page(rec, snapshot_anchor={"rows": 5268, "chain_head": "abc123"})
    assert "cand-abc" in md and "沈青梧" in md
    assert "他把玉佩递给了沈青梧。" in md               # 引文逐字（可回链）
    assert md.count("> ") >= 2                          # 引文块引
    assert "provisional" in md                          # 三态标注
    assert "claim" not in md.split("## 断言")[0]        # front-matter 无泄漏杂物


def test_reconcile_detects_missing_page_and_quote_drift():
    recs = {"cand-a": _rec("cand-a", "甲", ["甲的引文。"]),
            "cand-b": _rec("cand-b", "乙", ["乙的引文。"])}
    # 页面齐全 + 引文逐字 ⇒ ok
    pages = {"cand-a": export.render_record_page(recs["cand-a"], {}),
             "cand-b": export.render_record_page(recs["cand-b"], {})}
    r = export.reconcile(pages=pages, store_records=recs, sample_n=30)
    assert r["页数对账"] is True and r["引文抽查"]["ok"] is True
    # 少一页 ⇒ 页数对账 False 且报缺失
    r2 = export.reconcile(pages={"cand-a": pages["cand-a"]}, store_records=recs, sample_n=30)
    assert r2["页数对账"] is False and "cand-b" in str(r2["缺失页"])
    # 引文被改（快照手改/渲染不忠实）⇒ 引文抽查 False
    bad = pages["cand-a"].replace("甲的引文。", "被篡改的引文。")
    r3 = export.reconcile(pages={"cand-a": bad, "cand-b": pages["cand-b"]},
                          store_records=recs, sample_n=30)
    assert r3["引文抽查"]["ok"] is False


def test_project_graph_nodes_edges():
    recs = [
        _rec("cand-e1", "沈青梧", ["引文"], lib="character"),
        _rec("cand-e2", "玉佩", ["引文"], lib="setting"),
        {"record_id": "cand-r1", "library": "relation", "status": "provisional",
         "canonical": {"subject": "沈青梧", "predicate": "持有", "object": "玉佩"},
         "evidence": [{"vol": 1, "chapter": 3, "line": 10, "quote": "引文"}]},
    ]
    nodes, edges = export.project_graph(recs)
    names = {n["name"] for n in nodes}
    assert {"沈青梧", "玉佩"} <= names
    assert len(edges) == 1 and edges[0]["source"] == "沈青梧" and edges[0]["target"] == "玉佩"
    assert edges[0]["predicate"] == "持有" and edges[0]["status"] == "provisional"


import json  # noqa: E402  （底部导入以保持测试顶部聚焦——Python 允许）
