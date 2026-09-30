# -*- coding: utf-8 -*-
"""test_v3_derive.py — Phase B：归属单键（D-13）/双时序/投影检查点/债务 repay（D-14）。
运行：py -X utf8 test_v3_derive.py"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import derive  # noqa: E402


def test_ns_single_key_write_read_same():
    """D-13 根治：写侧 upsert 与读侧归属判定共用 NS_PROPERTY 单键。"""
    assert derive.NS_PROPERTY == "group_id"
    cy, params = derive.upsert_node_cypher(
        {"canonical": {"name": "缇达", "entity_type": "人物"}, "library": "character",
         "record_id": "e1", "t_valid": "ch0014", "at": "ch0014"}, ns="迷深实战")
    assert "group_id" in cy and params["ns"] == "迷深实战"
    vcy, vparams = derive.ownership_verify_cypher("迷深实战")
    assert derive.NS_PROPERTY in vcy and vparams["ns"] == "迷深实战"
    assert "ns`" not in cy.replace("`group_id`", "")  # 不再出现旧 ns 属性写


def test_bitemporal_fields_flow_to_query():
    rec = {"canonical": {"name": "帕林", "entity_type": "人物"}, "library": "character",
           "record_id": "e2", "t_valid": "ch0014", "at": "ch0014"}
    cy, p = derive.upsert_node_cypher(rec, ns="迷深实战")
    assert p["valid_at"] == "ch0014" and p["invalid_at"] is None
    inv = {"t_invalid": "ch0020"}
    cy2, p2 = derive.upsert_node_cypher(rec, ns="迷深实战", invalidation=inv)
    assert p2["invalid_at"] == "ch0020"  # 失效记账登记值优先生效
    er = {"canonical": {"subject": "卢卡", "rel_type": "同盟", "object": "缇达"},
          "record_id": "rel-1", "t_valid": "ch0003", "at": "ch0003"}
    ecy, ep = derive.upsert_edge_cypher(er, ns="迷深实战")
    assert ep["edge_id"] == "rel-1" and ep["valid_at"] == "ch0003"


def test_checkpoint_roundtrip_and_replay():
    with tempfile.TemporaryDirectory() as td:
        cp = derive.ProjectionCheckpoint(Path(td), "neo4j")
        assert cp.load() is None and cp.replay_needed(10)  # 无检查点=需重放
        cp.commit(ledger_offset=10, sha="abc", at="ch0020")
        assert cp.load()["ledger_offset"] == 10
        assert cp.replay_needed(15)  # B2 修复：账本前进=视图陈旧，需重喂
        assert cp.replay_needed(5)   # 账本回卷=检查点失效须重放
        assert not cp.replay_needed(10)  # 恰好同步=无需重放


def test_debt_incur_repay_open_zero_reachable():
    """D-14 根治：债务可清偿——"债务=0∧终审可用"可达。"""
    with tempfile.TemporaryDirectory() as td:
        d = derive.DebtLedger(Path(td))
        assert d.open_count() == 0
        d.incur("neo4j-export", "daemon 不在", at="ch0010")
        d.incur("neo4j-export", "daemon 不在", at="ch0012")
        assert d.open_count("neo4j-export") == 2
        r1 = d.repay("neo4j-export", at="ch0014", note="服务恢复重导出")
        assert r1["repays"]  # FIFO 核销最旧
        assert d.open_count("neo4j-export") == 1
        d.repay("neo4j-export", at="ch0014")
        assert d.open_count("neo4j-export") == 0  # 归零可达
        assert d.repay("neo4j-export", at="ch0014") is None  # 无债可还


def test_debt_targets_isolated():
    with tempfile.TemporaryDirectory() as td:
        d = derive.DebtLedger(Path(td))
        d.incur("a-view", "x", at="ch0001")
        assert d.open_count("b-view") == 0 and d.open_count() == 1


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
