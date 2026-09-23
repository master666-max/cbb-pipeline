# -*- coding: utf-8 -*-
"""test_连续性巡检.py — U-F02 判据测试：双载体一致（夹具）、图缺席兜底、规则单一来源"""
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
巡检 = importlib.import_module("连续性巡检")


def _mk_fixture_store(tmp_path: Path) -> Path:
    """造一个含四类已知问题的迷你库（夹具即真值）。"""
    store = tmp_path / "store"
    libs = store / "libraries"

    def put(lib, rid, rec):
        d = libs / lib / "provisional"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{rid}.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")

    # 实体：甲、乙；丙 只作为关系出现 → 孤悬
    put("character", "e-jia", {"record_id": "e-jia", "record_type": "entity", "library": "character",
                               "canonical": {"name": "甲", "entity_type": "人物"}})
    put("character", "e-yi", {"record_id": "e-yi", "record_type": "entity", "library": "character",
                              "canonical": {"name": "乙", "entity_type": "人物", "death_chapter": 10}})
    # 关系：甲-[parent]->乙 缺逆回链；甲-[结拜]->丙 孤悬
    put("relation", "r-1", {"record_id": "r-1", "record_type": "relation", "library": "relation",
                            "canonical": {"subject": "甲", "rel_type": "parent", "object": "乙"}})
    put("relation", "r-2", {"record_id": "r-2", "record_type": "relation", "library": "relation",
                            "canonical": {"subject": "甲", "rel_type": "结拜", "object": "丙"}})
    # 别名冲突：别名"阿甲"指向两个实体
    (store / "aliases.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in [
            {"alias": "阿甲", "entity_id": "e-jia", "entity_type": "人物", "key": "阿甲|e-jia"},
            {"alias": "阿甲", "entity_id": "e-other", "entity_type": "人物", "key": "阿甲|e-other"},
        ]), encoding="utf-8")
    # 死人走路：乙死于第 10 章，第 12 章仍有出场
    (store / "appearances.jsonl").write_text(
        json.dumps({"chapter": 12, "entity": "乙", "key": "乙|ch12"}, ensure_ascii=False),
        encoding="utf-8")
    return store


def test_file_backend_finds_all_four(tmp_path):
    store = _mk_fixture_store(tmp_path)
    rep = 巡检.run(store, "file")
    rules = {f["rule"] for f in rep["findings"]}
    assert rules == {"orphan_ref", "inverse_backlink", "dead_walking", "alias_conflict"}, rules
    assert rep["backend"] == "file"


def test_double_carrier_consistency(tmp_path, monkeypatch=None):
    """判据①：两载体在同一逻辑数据上产出**逐条一致**（图装载器以桩替代，逻辑数据等价）。"""
    store = _mk_fixture_store(tmp_path)
    file_view = 巡检.file_loader(store)

    def fake_graph_loader(base=None, database="neo4j", user=None, password=None):
        return {"entities": set(file_view["entities"]), "aliases": {},
                "relations": list(file_view["relations"]), "appearances": None, "deaths": {},
                "capabilities": {"entities": True, "aliases": False, "relations": True,
                                 "appearances": False, "deaths": False,
                                 "orphan_detectable": False},
                "backend": "graph"}

    a = {(f["rule"], f["detail"]) for f in 巡检.evaluate(file_view)}
    b = {(f["rule"], f["detail"]) for f in 巡检.evaluate(fake_graph_loader())}
    # 判据①的正确表述：**能力交集内逐条一致**；能力外必须显式标注"不可用"（不许给不同答案、也不许静默省略）
    capable = {"inverse_backlink"}   # 图载体真正等价的能力（孤悬在图上结构性失明——见下断言）
    assert {x for x in a if x[0] in capable} == {x for x in b if x[0] in capable}, "能力交集内不一致"
    assert any(x[0] == "orphan_ref" and "结构性失明" in x[1] for x in b), "图载体未显式标注孤悬结构性失明"
    assert any(x[0] == "dead_walking" and x[1].startswith("不可用") for x in b), "图载体未显式标注出场数据不可用"
    assert any(x[0] == "alias_conflict" and x[1].startswith("不可用") for x in b), "图载体未显式标注别名数据不可用"


def test_graph_absent_falls_back_to_file(tmp_path, monkeypatch=None):
    """判据②：图不可用 → auto 自动落文件，输出同形且口径注明。"""
    store = _mk_fixture_store(tmp_path)
    import types
    m = 巡检
    orig_probe, orig_gl = m.probe_graph, m.graph_loader
    m.probe_graph = lambda base=None, timeout=4.0: False          # 图探活失败
    try:
        rep = m.run(store, "auto")
    finally:
        m.probe_graph, m.graph_loader = orig_probe, orig_gl
    assert rep["backend"] == "file" and "自动兜底" in rep["note"]
    assert isinstance(rep["findings"], list) and rep["findings"]


def test_rules_single_source():
    """判据③：规则单一来源——逆类型/对称表来自门1（数量与内容可核）。"""
    assert len(巡检.RELATIONSHIP_INVERSES) >= 12
    assert len(巡检.SYMMETRIC_RELATIONSHIPS) >= 1  # 对称项存在
    assert "parent" in 巡检.RELATIONSHIP_INVERSES


if __name__ == "__main__":
    import tempfile
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        if fn.__code__.co_argcount:
            with tempfile.TemporaryDirectory() as td:
                fn(Path(td))
        else:
            fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
