# -*- coding: utf-8 -*-
"""test_cbb_store.py — cbb_store 单测（py -X utf8 运行）

断言：三态路由纪律（B1：库中只有 confirmed/provisional，quarantine 不进 library）；
幂等入库；supersede 版本化旧件字节不动（B5）；状态迁移旁车日志；
route_by_confidence 永不单凭置信度给 confirmed。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "contracts"))
import cbb_store as st  # noqa: E402
import cbb_contracts  # noqa: E402


def candidate(**over):
    rec = {
        "record_id": "cand-event-test01",
        "record_type": "event",
        "library": "event",
        "status": "candidate",
        "canonical": {"name": "决斗开始"},
        "evidence": [{"vol": 1, "chapter": 14, "line": 1, "quote": "缇达拔出了剑"}],
        "provenance": {"extractor_confidence": 0.8, "gate_trace": [],
                       "precedent_refs": [], "status_history": []},
        "version": 1, "supersedes": None,
    }
    rec.update(over)
    return rec


class StoreTestBase(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.store = st.ThreeStateStore(Path(self.td.name) / "kb")

    def tearDown(self):
        self.td.cleanup()


class TestAdmit(StoreTestBase):
    def test_provisional_admit(self):
        path, created = self.store.admit(candidate(), "provisional",
                                         gate_trace_entry={"gate": "1", "verdict_id": "g1-x"})
        self.assertTrue(created)
        stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["status"], "provisional")
        self.assertEqual(stored["provenance"]["status_history"][-1],
                         {"from": "candidate", "to": "provisional", "by": "promotion"})
        self.assertEqual(stored["provenance"]["gate_trace"][-1]["gate"], "1")
        cbb_contracts.validate_record(stored)  # 库内态严格合规

    def test_idempotent_admit(self):
        _, c1 = self.store.admit(candidate(), "provisional")
        _, c2 = self.store.admit(candidate(), "provisional")
        self.assertTrue(c1)
        self.assertFalse(c2)
        self.assertEqual(self.store.stats()["libraries"]["event"]["provisional"], 1)

    def test_quarantine_never_in_libraries(self):
        iid, created = self.store.admit(candidate(), "quarantine",
                                        quarantine_group="low_confidence",
                                        quarantine_detail="置信度不足")
        self.assertTrue(created)
        self.assertTrue(iid.startswith("q-"))
        libs = self.store.root / "libraries"
        self.assertFalse(libs.exists())  # B1：隔离件不落任何 library 目录
        self.assertEqual(self.store.stats()["quarantine_pending"], 1)

    def test_invalid_decision_and_bad_record(self):
        with self.assertRaises(ValueError):
            self.store.admit(candidate(), "maybe")
        bad = candidate(evidence=[])  # 违反 B4 minItems
        with self.assertRaises(cbb_contracts.ContractViolation):
            self.store.admit(bad, "provisional")


class TestRouteByConfidence(unittest.TestCase):
    def test_never_confirmed_by_confidence_alone(self):
        self.assertEqual(st.route_by_confidence(0.99), "provisional")  # 即使 0.99
        self.assertEqual(st.route_by_confidence(0.86), "provisional")
        self.assertEqual(st.route_by_confidence(0.85), "provisional")
        self.assertEqual(st.route_by_confidence(0.84), "quarantine")
        self.assertEqual(st.route_by_confidence(0.10), "quarantine")


class TestTransition(StoreTestBase):
    def test_human_promotion_via_sidecar(self):
        self.store.admit(candidate(), "provisional")
        before = (self.store.root / "libraries" / "event" / "provisional"
                  / "cand-event-test01.json").read_bytes()
        entry = self.store.status_transition("cand-event-test01", "confirmed", by="human",
                                             note="人工复核")
        self.assertEqual((entry["from"], entry["to"]), ("provisional", "confirmed"))
        after = (self.store.root / "libraries" / "event" / "provisional"
                 / "cand-event-test01.json").read_bytes()
        self.assertEqual(before, after)  # 记录文件字节不动（旁车日志承担历史）
        self.assertEqual(self.store.effective_status("cand-event-test01"), "confirmed")

    def test_invalid_transition(self):
        with self.assertRaises(KeyError):
            self.store.status_transition("ghost", "confirmed")  # 不在库


class TestSupersede(StoreTestBase):
    def test_versioned_supersede_b5(self):
        self.store.admit(candidate(), "provisional")
        old_path = self.store.root / "libraries" / "event" / "provisional" / "cand-event-test01.json"
        old_bytes = old_path.read_bytes()
        new = candidate(record_id="cand-event-test01-v2",
                        canonical={"name": "决斗开始（修订）"})
        path, created = self.store.supersede("cand-event-test01", new)
        self.assertTrue(created)
        stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["version"], 2)
        self.assertEqual(stored["supersedes"], "cand-event-test01")
        self.assertEqual(old_path.read_bytes(), old_bytes)  # 旧件不动
        latest = self.store.resolve_latest("cand-event-test01")
        self.assertEqual(latest["record_id"], "cand-event-test01-v2")

    def test_supersede_requires_new_id(self):
        self.store.admit(candidate(), "provisional")
        with self.assertRaises(ValueError):
            self.store.supersede("cand-event-test01", candidate())

    def test_supersede_unknown_old(self):
        with self.assertRaises(KeyError):
            self.store.supersede("ghost", candidate(record_id="x"))


class TestBackendStub(unittest.TestCase):
    def test_neo4d_backend_explicit_stub(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(NotImplementedError):
                st.ThreeStateStore(Path(td), backend="neo4j")


if __name__ == "__main__":
    unittest.main(verbosity=2)
