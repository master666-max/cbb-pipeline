# -*- coding: utf-8 -*-
"""test_失效宣告.py — 裁决 ①A 的机械闸测试（含正对照：拒对了＋放过了）"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib
m = importlib.import_module("失效宣告")


def test_forbidden_kinds_rejected(tmp_path):
    """负对照：三种禁止情形必须被拒（它们是返工，不是历史）。"""
    for kind in m.FORBIDDEN_KINDS:
        try:
            m.write_invalidation(tmp_path, record_id="r1", invalid_at=100,
                                 kind=kind, verdict_ref="v1", evidence_sides=2,
                                 by="human")
            raise AssertionError(f"{kind} 应被拒绝")
        except ValueError as e:
            assert "禁止写入" in str(e), str(e)


def test_value_conflict_requires_human_and_dual_evidence(tmp_path):
    """value_conflict：by=agent 拒；单侧证据拒；human+双侧 过。"""
    kw = dict(record_id="r1", invalid_at=200, kind="value_conflict",
              verdict_ref="q-1", by="agent", evidence_sides=2)
    try:
        m.write_invalidation(tmp_path, **kw)
        raise AssertionError("agent 不得写 value_conflict")
    except ValueError as e:
        assert "人工确认" in str(e)
    try:
        m.write_invalidation(tmp_path, record_id="r1", invalid_at=200,
                             kind="value_conflict", verdict_ref="q-1",
                             by="human", evidence_sides=1)
        raise AssertionError("单侧证据不得写 value_conflict")
    except ValueError as e:
        assert "双方证据" in str(e)
    rec, created = m.write_invalidation(tmp_path, record_id="r1", invalid_at=200,
                                        kind="value_conflict", verdict_ref="q-1",
                                        by="human", evidence_sides=2, at="2026-09-22")
    assert created and rec["at"] == "2026-09-22"


def test_superseded_allows_agent_and_requires_dual(tmp_path):
    rec, ok = m.write_invalidation(tmp_path, record_id="r2", invalid_at=300,
                                   kind="superseded", verdict_ref="rec-new",
                                   by="agent", evidence_sides=2)
    assert ok
    try:
        m.write_invalidation(tmp_path, record_id="r3", invalid_at=1,
                             kind="superseded", verdict_ref="x", by="agent",
                             evidence_sides=1)
        raise AssertionError("superseded 单侧应拒")
    except ValueError:
        pass


def test_idempotent_double_write(tmp_path):
    kw = dict(record_id="r4", invalid_at=50, kind="termination",
              verdict_ref="q-9", by="human", evidence_sides=1)
    r1, c1 = m.write_invalidation(tmp_path, **kw)
    r2, c2 = m.write_invalidation(tmp_path, **kw)
    assert c1 and not c2 and r1 == r2
    assert len(m.load_invalidations(tmp_path)) == 1  # append-only 且不重复


def test_missing_verdict_ref_rejected(tmp_path):
    try:
        m.write_invalidation(tmp_path, record_id="r5", invalid_at=10,
                             kind="superseded", verdict_ref="", by="agent",
                             evidence_sides=2)
        raise AssertionError("无指针应拒")
    except ValueError as e:
        assert "verdict_ref" in str(e)


def test_apply_to_edges_min_semantics(tmp_path):
    edges = tmp_path / "edges.jsonl"
    rows = [
        {"record_id": "a", "valid_at": 10, "invalid_at": None},
        {"record_id": "b", "valid_at": 20, "invalid_at": 40},   # 已有更晚失效
        {"record_id": "c", "valid_at": 30, "invalid_at": None},  # 无宣告，不动
    ]
    edges.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    invs = [
        {"record_id": "a", "invalid_at": 99, "verdict_ref": "v1", "kind": "superseded"},
        {"record_id": "b", "invalid_at": 25, "verdict_ref": "v2", "kind": "superseded"},  # 更早→采纳
        {"record_id": "b", "invalid_at": 70, "verdict_ref": "v3", "kind": "superseded"},  # 更晚→保留 25
    ]
    out = tmp_path / "edges-view.jsonl"
    stat = m.apply_to_edges(edges, invs, out)
    assert stat["edges"] == 3 and stat["invalidated"] == 2 and stat["kept_earlier"] == 1
    after = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert after[0]["invalid_at"] == 99 and after[0]["invalidation_ref"] == "v1"
    assert after[1]["invalid_at"] == 25 and after[1]["invalidation_ref"] == "v2"
    assert after[2]["invalid_at"] is None
    # 输入字节不动（旧件不动纪律）
    assert json.loads(edges.read_text(encoding="utf-8").splitlines()[0])["invalid_at"] is None


if __name__ == "__main__":
    import tempfile
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        with tempfile.TemporaryDirectory() as td:
            fn(Path(td))
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
