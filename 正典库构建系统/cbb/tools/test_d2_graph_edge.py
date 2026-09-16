# -*- coding: utf-8 -*-
"""test_d2_graph_edge.py — 漂移修正 D2 单测（工单 v1.4 §0；2026-09-17 U-C03.5）。

覆盖三件：
  ① 契约：evidence[].graph_edge 可选位——缺省合法（旧记录零改动）、
     在场合法（三子字段齐）、畸形（缺 edge_id / valid_at 类型错）被拒；
  ② 导出器：edge_id 确定性、edge_statement 携带 edge_id/valid_at/invalid_at（D1 时序字段）；
  ③ 回填：evidence_edge_backfill 产出的 graph_edge 对象符合契约位；
     侧车追加键级去重（重放零增殖）；库内记录文件不被回填触碰（旧件字节不动）。
评分器与金标零改动（本测试不触碰 step0 评分链）。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "contracts"))
sys.path.insert(0, str(HERE.parent / "cbb-store"))
sys.path.insert(0, str(HERE))
import cbb_contracts  # noqa: E402
import cbb_store      # noqa: E402
import neo4j_export as m  # noqa: E402


def mk_record(evidence):
    return {
        "record_id": "cand-relation-d2test", "record_type": "relation", "library": "relation",
        "status": "provisional",
        "canonical": {"subject": "甲", "rel_type": "认识", "object": "乙", "claim": False},
        "evidence": evidence,
        "verified_against": {"path": "test://corpus", "sha": "0123456789abcdef", "verified_at": "2026-09-17"},
        "provenance": {"extractor_confidence": 0.9, "gate_trace": [], "precedent_refs": [],
                       "status_history": []},
        "version": 1, "supersedes": None,
    }


GOOD_EDGE = {"edge_id": "e-abc123def456", "valid_at": 14, "invalid_at": None}


class TestSchemaGraphEdge(unittest.TestCase):
    def test_absent_graph_edge_still_valid(self):
        """可选位：不带 graph_edge 的旧形态证据照常过契约（零破坏）。"""
        cbb_contracts.validate_record(mk_record(
            [{"vol": 1, "chapter": 14, "line": 3, "quote": "甲与乙相识"}]), allow_candidate=True)

    def test_present_graph_edge_valid(self):
        cbb_contracts.validate_record(mk_record(
            [{"vol": 1, "chapter": 14, "line": 3, "quote": "甲与乙相识", "graph_edge": GOOD_EDGE}]),
            allow_candidate=True)

    def test_malformed_graph_edge_rejected(self):
        with self.assertRaises(cbb_contracts.ContractViolation):
            cbb_contracts.validate_record(mk_record(
                [{"vol": 1, "chapter": 14, "line": 3, "quote": "甲与乙相识",
                  "graph_edge": {"valid_at": 14, "invalid_at": None}}]))  # 缺 edge_id
        with self.assertRaises(cbb_contracts.ContractViolation):
            cbb_contracts.validate_record(mk_record(
                [{"vol": 1, "chapter": 14, "line": 3, "quote": "甲与乙相识",
                  "graph_edge": {"edge_id": "e-x", "valid_at": "第14章", "invalid_at": None}}]))  # 类型错


class TestExporterEdgeFields(unittest.TestCase):
    def test_edge_id_deterministic(self):
        a = m.edge_id_for("斯诺·沃克", "情报传递(手环关键)", "拉丝缇娅拉")
        b = m.edge_id_for("斯诺·沃克", "情报传递(手环关键)", "拉丝缇娅拉")
        c = m.edge_id_for("斯诺·沃克", "敌对", "拉丝缇娅拉")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertTrue(a.startswith("e-") and len(a) == 14)

    def test_edge_statement_carries_temporals(self):
        st = m.edge_statement({"subject": "甲", "rel_type": "认识", "object": "乙",
                               "claim": False, "fact": "f",
                               "valid_at": 14, "invalid_at": None})
        self.assertIn("r.edge_id=$edge_id", st["statement"])
        self.assertIn("r.valid_at=$valid_at", st["statement"])
        self.assertIn("r.invalid_at=$invalid_at", st["statement"])
        self.assertTrue(st["parameters"]["edge_id"].startswith("e-"))
        self.assertEqual(st["parameters"]["valid_at"], 14)
        self.assertIsNone(st["parameters"]["invalid_at"])

    def test_edge_statement_derives_edge_id_when_absent(self):
        st = m.edge_statement({"subject": "甲", "rel_type": "认识", "object": "乙",
                               "claim": False, "fact": "f"})
        self.assertEqual(st["parameters"]["edge_id"], m.edge_id_for("甲", "认识", "乙"))

    def test_collect_graph_carries_temporals_and_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = cbb_store.ThreeStateStore(root)
            store.admit_or_merge(mk_record(
                [{"vol": 1, "chapter": 14, "line": 3, "quote": "甲与乙相识"},
                 {"vol": 1, "chapter": 9, "line": 8, "quote": "乙初见甲"}]))
            g = m.collect_graph(root)
            e = g["edges"][0]
            self.assertEqual(e["valid_at"], 9)          # 最早证据章
            self.assertIsNone(e["invalid_at"])          # 活版本=开放区间
            self.assertEqual(len(e["evidence"]), 2)
            self.assertEqual(e["edge_id"], m.edge_id_for("甲", "认识", "乙"))


class TestBackfill(unittest.TestCase):
    def test_backfill_entries_conform_to_contract(self):
        graph = {"edges": [{"subject": "甲", "rel_type": "认识", "object": "乙", "claim": False,
                            "fact": "f", "record_id": "r1",
                            "edge_id": m.edge_id_for("甲", "认识", "乙"),
                            "valid_at": 14, "invalid_at": None,
                            "evidence": [{"vol": 1, "chapter": 14, "line": 3, "quote": "甲与乙相识"}]}]}
        entries = m.evidence_edge_backfill(graph)
        self.assertEqual(len(entries), 1)
        ge = entries[0]["evidence"][0]["graph_edge"]
        self.assertEqual(ge["edge_id"], m.edge_id_for("甲", "认识", "乙"))
        # 回填对象放回证据位后整条记录仍过契约（证据链闭合到图）
        rec = mk_record([{"vol": 1, "chapter": 14, "line": 3, "quote": "甲与乙相识",
                          "graph_edge": ge}])
        cbb_contracts.validate_record(rec, allow_candidate=True)

    def test_backfill_skips_edgeless_relations(self):
        graph = {"edges": [{"subject": "甲", "rel_type": "认识", "object": "乙", "claim": False,
                            "fact": "f", "record_id": "r2", "valid_at": None,
                            "invalid_at": None, "evidence": []}]}
        self.assertEqual(m.evidence_edge_backfill(graph), [])

    def test_sidecar_append_dedupes_on_replay(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "evidence-graph-edges.jsonl"
            graph = {"edges": [{"subject": "甲", "rel_type": "认识", "object": "乙", "claim": False,
                                "fact": "f", "record_id": "r1",
                                "edge_id": m.edge_id_for("甲", "认识", "乙"),
                                "valid_at": 14, "invalid_at": None,
                                "evidence": [{"vol": 1, "chapter": 14, "line": 3, "quote": "甲与乙相识"}]}]}
            r1 = m.append_backfill_sidecar(p, m.evidence_edge_backfill(graph))
            r2 = m.append_backfill_sidecar(p, m.evidence_edge_backfill(graph))  # 幂等重放
            self.assertEqual((r1["added"], r2["added"]), (1, 0))
            self.assertEqual(r2["total_lines"], 1)

    def test_backfill_never_touches_library_files(self):
        """回填走侧车：库内记录文件字节不动（铁律② 的机制性证明）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = cbb_store.ThreeStateStore(root)
            store.admit_or_merge(mk_record(
                [{"vol": 1, "chapter": 14, "line": 3, "quote": "甲与乙相识"}]))
            lib_file = next((root / "libraries" / "relation" / "provisional").glob("*.json"))
            before = lib_file.read_bytes()
            m.append_backfill_sidecar(root / "evidence-graph-edges.jsonl",
                                      m.evidence_edge_backfill(m.collect_graph(root)))
            self.assertEqual(lib_file.read_bytes(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
