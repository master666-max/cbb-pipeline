# -*- coding: utf-8 -*-
"""test_neo4j_export.py — Neo4j 导出工具单测（零网络：伪 commit 收集器 + 临时 fixture 库）。
py -X utf8 cbb/tools/test_neo4j_export.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
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
        self.assertIn("MERGE (e:Entity {name:$name})", st["statement"])
        self.assertEqual(st["parameters"]["name"], "基督")

    def test_edge_merges_both_endpoints_and_rel(self):
        st = m.edge_statement({"subject": "a", "rel_type": "朋友", "object": "b",
                               "claim": False, "fact": "f"})
        s = st["statement"]
        self.assertIn("MERGE (s:Entity {name:$subject})", s)
        self.assertIn("MERGE (o:Entity {name:$object})", s)
        self.assertIn("MERGE (s)-[r:REL {rel_type:$rel_type}]->(o)", s)

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
        self.assertEqual(report, {"nodes": 0, "edges": 0, "batches": 1})


if __name__ == "__main__":
    unittest.main(verbosity=2)
