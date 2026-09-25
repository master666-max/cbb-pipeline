# -*- coding: utf-8 -*-
"""test_neo4j_export.py — Neo4j 导出工具单测（零网络：伪 commit 收集器 + 临时 fixture 库）。
py -X utf8 cbb/tools/test_neo4j_export.py
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent

# 本模块统一给一个测试命名空间；"不给就拒绝"另有专测（TestNamespace）。
def setUpModule():
    import os
    os.environ["CBB_NAMESPACE"] = "ut-ns"


def tearDownModule():
    import os
    os.environ.pop("CBB_NAMESPACE", None)
sys.path.insert(0, str(HERE.parent / "cbb-store"))
sys.path.insert(0, str(HERE.parent / "contracts"))
sys.path.insert(0, str(HERE))
import cbb_store  # noqa: E402
import neo4j_export as m  # noqa: E402


def mk_entity(name, etype="人物", lib="character", rid=None):
    return {"record_id": rid or f"cand-entity-{name}", "record_type": "entity", "library": lib,
            "status": "provisional", "canonical": {"name": name, "entity_type": etype},
            "evidence": [{"vol": 1, "chapter": 1, "line": 1, "quote": f"{name}的引文"}],
            "verified_against": {"path": "t", "sha": "0" * 7, "verified_at": "1970-01-01"},
            "provenance": {"extractor_confidence": 0.9, "extractor": "t", "gate_trace": [],
                           "precedent_refs": [], "status_history": []},
            "version": 1, "supersedes": None}


def mk_relation(s, rel, o, rid=None):
    return {"record_id": rid or f"cand-relation-{s}-{rel}-{o}", "record_type": "relation",
            "library": "relation", "status": "provisional",
            "canonical": {"subject": s, "rel_type": rel, "object": o, "claim": False},
            "observations": [{"category": "relation", "text": f"{s}{rel}{o}", "chapter": 1}],
            "evidence": [{"vol": 1, "chapter": 1, "line": 2, "quote": f"{s}{rel}{o}的证据"}],
            "verified_against": {"path": "t", "sha": "0" * 7, "verified_at": "1970-01-01"},
            "provenance": {"extractor_confidence": 0.9, "extractor": "t", "gate_trace": [],
                           "precedent_refs": [], "status_history": []},
            "version": 1, "supersedes": None}


class Recorder:
    def __init__(self):
        self.batches = []

    def __call__(self, statements):
        self.batches.append(statements)


class TestCollectGraph(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = cbb_store.ThreeStateStore(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_nodes_and_edges_collected(self):
        self.store.admit_or_merge(mk_entity("基督·欧亚"))
        self.store.admit_or_merge(mk_entity("迷宫", "地点", "setting"))
        self.store.admit_or_merge(mk_relation("基督·欧亚", "探索", "迷宫"))
        g = m.collect_graph(Path(self.tmp.name))
        self.assertEqual(len(g["nodes"]), 2)
        self.assertEqual(len(g["edges"]), 1)
        self.assertEqual(g["edges"][0]["fact"], "基督·欧亚探索迷宫")

    def test_superseded_excluded(self):
        old = mk_entity("缇亚", rid="cand-entity-old")
        self.store.admit_or_merge(old)
        new = dict(old, canonical={"name": "缇亚", "entity_type": "人物", "note": "v2"})
        new["record_id"] = "cand-entity-new"
        self.store.supersede("cand-entity-old", new)
        g = m.collect_graph(Path(self.tmp.name))
        self.assertEqual(len(g["nodes"]), 1)
        self.assertEqual(g["nodes"][0]["record_id"], "cand-entity-new")

    def test_events_not_exported_as_graph(self):
        ev = {"record_id": "cand-event-x", "record_type": "event", "library": "event",
              "status": "provisional", "canonical": {"name": "事件", "tick": 1},
              "evidence": [{"vol": 1, "chapter": 1, "line": 3, "quote": "事件引文"}],
              "verified_against": {"path": "t", "sha": "0" * 7, "verified_at": "1970-01-01"},
              "provenance": {"extractor_confidence": 0.9, "extractor": "t", "gate_trace": [],
                             "precedent_refs": [], "status_history": []},
              "version": 1, "supersedes": None}
        self.store.admit_or_merge(ev)
        g = m.collect_graph(Path(self.tmp.name))
        self.assertEqual(g["nodes"], [])
        self.assertEqual(g["edges"], [])


class TestCypher(unittest.TestCase):
    def test_node_merges_on_name_key(self):
        st = m.node_statement({"name": "基督", "entity_type": "人物", "lib": "character",
                               "status": "provisional", "version": 1})
        self.assertIn("MERGE (e:Entity {ns:$ns, name:$name})", st["statement"])   # 键里必须带命名空间
        self.assertEqual(st["parameters"]["name"], "基督")
        self.assertEqual(st["parameters"]["ns"], "ut-ns")
        self.assertIn("SET e.ns=$ns", st["statement"])          # 命名空间还要落到属性上，读侧才过滤得到

    def test_edge_merges_both_endpoints_and_rel(self):
        st = m.edge_statement({"subject": "a", "rel_type": "朋友", "object": "b",
                               "claim": False, "fact": "f"})
        s = st["statement"]
        self.assertIn("MERGE (s:Entity {ns:$ns, name:$subject})", s)
        self.assertIn("MERGE (o:Entity {ns:$ns, name:$object})", s)
        self.assertIn("MERGE (s)-[r:REL {ns:$ns, rel_type:$rel_type}]->(o)", s)

    def test_constraint_idempotent_if_not_exists(self):
        self.assertIn("IF NOT EXISTS", m.CONSTRAINT_CYPHER)


class TestExportGraph(unittest.TestCase):
    def test_batching_and_order(self):
        graph = {"nodes": [{"name": f"n{i}", "entity_type": "人物", "lib": "character",
                            "status": "provisional", "version": 1} for i in range(600)],
                 "edges": [{"subject": "n0", "rel_type": "认识", "object": "n1",
                            "claim": False, "fact": "f"}]}
        rec = Recorder()
        report = m.export_graph(graph, rec)
        self.assertEqual(len(rec.batches), 5)          # 1 约束 + ceil(600/250)=3 节点批 + 1 边批
        self.assertEqual(report["batches"], 5)
        self.assertEqual(report["nodes"], 600)
        self.assertEqual(report["edges"], 1)
        self.assertEqual(rec.batches[0][0]["statement"], m.CONSTRAINT_CYPHER)
        # 幂等语义：同样的图再导出，语句文本完全一致（MERGE 重放零增殖的前提）
        rec2 = Recorder()
        m.export_graph(graph, rec2)
        self.assertEqual([b for b in rec.batches], [b for b in rec2.batches])

    def test_empty_graph_only_constraint(self):
        rec = Recorder()
        report = m.export_graph({"nodes": [], "edges": []}, rec)
        self.assertEqual(report, {"nodes": 0, "edges": 0, "mentions": 0, "batches": 1})


class TestChapterNodes(unittest.TestCase):
    """U-F03：章节点与 MENTIONS 边（"某一章出现了什么"一条查询可答）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = cbb_store.ThreeStateStore(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_mentions_collected_and_deduped(self):
        e = mk_entity("涡波")
        e["evidence"] = [{"vol": 1, "chapter": 3, "line": 1, "quote": "a"},
                         {"vol": 1, "chapter": 7, "line": 2, "quote": "b"},
                         {"vol": 1, "chapter": 7, "line": 9, "quote": "c"}]  # 同章两条证据
        self.store.admit_or_merge(e)
        self.store.admit_or_merge(mk_relation("涡波", "认识", "缇达"))  # 章1，两端都应被提及
        g = m.collect_graph(Path(self.tmp.name))
        pairs = {(x["chapter"], x["name"]) for x in g["mentions"]}
        self.assertIn((3, "涡波"), pairs)
        self.assertIn((7, "涡波"), pairs)
        self.assertEqual(sum(1 for x in g["mentions"] if x == {"chapter": 7, "name": "涡波"}), 1,
                         "同章重复证据必须去重成一条 mentions")
        self.assertIn((1, "缇达"), pairs)
        self.assertIn((1, "涡波"), pairs)

    def test_chapter_statement_merge_only_shape(self):
        st = m.chapter_statement({"chapter": 14, "name": "涡波"})
        s = st["statement"]
        self.assertIn("MERGE (c:Chapter {ns:$ns, no:$no})", s)          # 两本书的第 1 章不该是同一个节点
        self.assertIn("MERGE (e:Entity {ns:$ns, name:$name})", s)
        self.assertIn("MERGE (c)-[:MENTIONS {ns:$ns}]->(e)", s)
        self.assertNotIn("CREATE ", s.replace("ON CREATE", ""))  # 纯 MERGE＝重放零增殖
        self.assertEqual(st["parameters"], {"ns": "ut-ns", "no": 14, "name": "涡波"})

    def test_export_graph_commits_chapters_and_counts(self):
        graph = {"nodes": [], "edges": [],
                 "mentions": [{"chapter": 1, "name": "甲"}, {"chapter": 2, "name": "乙"}]}
        rec = Recorder()
        report = m.export_graph(graph, rec)
        self.assertEqual(report["mentions"], 2)
        self.assertEqual(report["batches"], 2)  # 1 约束 + 1 章提及批（nodes/edges 为空）
        flat = [s for b in rec.batches for s in b]
        self.assertTrue(any("Chapter" in s["statement"] for s in flat))
        # 幂等语义：重放语句逐字一致
        rec2 = Recorder()
        m.export_graph(graph, rec2)
        self.assertEqual([b for b in rec.batches], [b for b in rec2.batches])


class TestAuditR4Fixes(unittest.TestCase):
    """R4 审计修复批反例（A13）。"""

    def test_a13_default_base_port_aligned(self):
        """不变量＝两件工具的默认基址一致（端口值本身不该是某台机器的容器映射）。
        旧断言把 7695 钉进发布件＝那台机器上映射给上一项目容器的端口，换机即错。"""
        if "NEO4J_HTTP" not in os.environ:
            self.assertEqual(m.DEFAULT_BASE, "http://localhost:7474")  # 出厂默认；钉具体映射端口＝把某台机器写进发布件
        # 跨件口径对齐：巡检同一变量默认值必须与导出器一致（分歧即测试红）
        patrol_src = (HERE / "连续性巡检.py").read_text(encoding="utf-8")
        self.assertIn('os.environ.get("NEO4J_HTTP", "http://localhost:7474")', patrol_src)



class TestDanglingEndpointNormalization(unittest.TestCase):
    """悬挂端点归一（2026-09-25 裁决内化）：边端点不在实体名集时，
    双向子串命中现役名（最长优先）归一；同三元组合并；计数披露。"""

    def _write(self, store, rel_dir, rid, obj):
        d = store / "libraries" / rel_dir / "provisional"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{rid}.json").write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

    def test_variant_normalized_and_deduped(self):
        with tempfile.TemporaryDirectory() as td:
            store = Path(td)
            self._write(store, "character", "e1", {
                "record_id": "e1", "record_type": "entity", "library": "character",
                "status": "provisional", "version": 1,
                "canonical": {"name": "持有物品", "entity_type": "物品"},
                "evidence": [{"vol": 1, "chapter": 1, "line": 1, "quote": "持有物品出场"}]})
            self._write(store, "character", "e2", {
                "record_id": "e2", "record_type": "entity", "library": "character",
                "status": "provisional", "version": 1,
                "canonical": {"name": "缇达", "entity_type": "人物"},
                "evidence": [{"vol": 1, "chapter": 1, "line": 1, "quote": "缇达出场"}]})
            self._write(store, "relation", "r1", {
                "record_id": "r1", "record_type": "relation", "library": "relation",
                "status": "provisional", "version": 1,
                "canonical": {"subject": "《持有物品》", "rel_type": "属于", "object": "缇达"},
                "evidence": [{"vol": 1, "chapter": 1, "line": 2, "quote": "属于缇达"}]})
            self._write(store, "relation", "r2", {
                "record_id": "r2", "record_type": "relation", "library": "relation",
                "status": "provisional", "version": 1,
                "canonical": {"subject": "『持有物品』", "rel_type": "属于", "object": "缇达"},
                "evidence": [{"vol": 1, "chapter": 2, "line": 1, "quote": "仍属于缇达"}]})
            g = m.collect_graph(store)
            self.assertEqual({n["name"] for n in g["nodes"]}, {"持有物品", "缇达"})
            self.assertEqual([(e["subject"], e["object"]) for e in g["edges"]],
                             [("持有物品", "缇达")])  # 两变体归一且合并为一条
            self.assertEqual(g["normalized_endpoints"], 2)



class TestNamespace(unittest.TestCase):
    """命名空间是写侧的硬前置：不给就拒，不许拿无命名空间的 MERGE 键写共享库。"""

    def setUp(self):
        import os
        self.os = os
        self.had = os.environ.pop("CBB_NAMESPACE", None)

    def tearDown(self):
        if self.had is not None:
            self.os.environ["CBB_NAMESPACE"] = self.had

    def test_无命名空间拒绝生成节点语句(self):
        with self.assertRaises(RuntimeError) as cm:
            m.node_statement({"name": "a", "entity_type": "人物", "lib": "character",
                              "status": "provisional", "version": 1})
        self.assertIn("命名空间", str(cm.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)