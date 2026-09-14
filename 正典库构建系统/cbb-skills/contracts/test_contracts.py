# -*- coding: utf-8 -*-
"""test_contracts.py — 四契约 schema 与最小校验器单测（py -X utf8 运行）"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cbb_contracts as cc


RECORD_OK = {
    "record_id": "rec-0001",
    "record_type": "event",
    "library": "event",
    "status": "confirmed",
    "canonical": {"name": "决斗开始"},
    "evidence": [{"vol": 1, "chapter": 14, "line": 3, "quote": "缇达拔出了剑"}],
    "provenance": {
        "extractor_confidence": 0.9,
        "gate_trace": [{"gate": "1", "verdict_id": "v-x", "ts": "2026-09-14T00:00:00"}],
        "precedent_refs": [],
        "status_history": [{"from": "candidate", "to": "confirmed", "at": "2026-09-14", "by": "promotion"}],
    },
    "version": 1,
    "supersedes": None,
}

ISSUE_OK = {
    "issue_id": "iss-0001",
    "skill": "S1",
    "error_type": None,
    "claim": "事件A与锚点时间倒置",
    "evidence_span": {"vol": 1, "chapter": 14, "line": 3, "quote": "……"},
    "graph_context": {"neighbors": []},
    "severity": "major",
    "extraction_confidence": 0.42,
}

VERDICT_OK = {
    "issue_id": "iss-0001",
    "label": "conflict",
    "confidence": 0.88,
    "judge_id": "judge-local-v0",
    "reasoning": "时间戳排序矛盾",
    "evidence_check": {"quote_found": True},
}

CASE_OK = {
    "case_id": "case-0001",
    "issue": ISSUE_OK,
    "verdict": VERDICT_OK,
    "provenance": {"source": "human", "trust_weight": 1.0},
    "retrieval_hints": {"tags": ["时间"], "entities": ["缇达"], "counter_example_of": None},
    "usage": {"retrieval_count": 0, "agreement_rate_when_cited": 0.0},
    "gate_scenario": "admission",
}


class TestSchemasLoad(unittest.TestCase):
    def test_all_four_load(self):
        for name in ("record", "issue", "verdict", "case"):
            schema = cc.load_schema(name)
            self.assertIn("required", schema)


class TestRecord(unittest.TestCase):
    def test_ok(self):
        cc.validate_record(RECORD_OK)

    def test_missing_evidence_rejected(self):
        bad = dict(RECORD_OK, evidence=[])
        with self.assertRaises(cc.ContractViolation):
            cc.validate_record(bad)

    def test_bad_status_rejected(self):
        bad = dict(RECORD_OK, status="quarantine")
        with self.assertRaises(cc.ContractViolation):
            cc.validate_record(bad)

    def test_bad_record_type_rejected(self):
        bad = dict(RECORD_OK, record_type="chapter")
        with self.assertRaises(cc.ContractViolation):
            cc.validate_record(bad)

    def test_candidate_only_with_flag(self):
        cand = dict(RECORD_OK, status="candidate")
        with self.assertRaises(cc.ContractViolation):
            cc.validate_record(cand)
        cc.validate_record(cand, allow_candidate=True)  # 其余字段合规时放行

    def test_evidence_quadruple_fields(self):
        self.assertTrue(cc.evidence_ok(RECORD_OK["evidence"][0]))
        self.assertFalse(cc.evidence_ok({"vol": 1, "chapter": 1, "line": 0, "quote": ""}))
        self.assertFalse(cc.evidence_ok({"vol": "一", "chapter": 1, "line": 0, "quote": "x"}))


class TestIssueVerdictCase(unittest.TestCase):
    def test_issue_null_error_type_allowed(self):
        cc.validate_issue(ISSUE_OK)  # admission 场景 error_type 可 null

    def test_issue_missing_claim_rejected(self):
        bad = {k: v for k, v in ISSUE_OK.items() if k != "claim"}
        with self.assertRaises(cc.ContractViolation):
            cc.validate_issue(bad)

    def test_verdict_label_enum(self):
        cc.validate_verdict(VERDICT_OK)
        bad = dict(VERDICT_OK, label="maybe")
        with self.assertRaises(cc.ContractViolation):
            cc.validate_verdict(bad)

    def test_case_gate_scenario_and_source(self):
        cc.validate_case(CASE_OK)
        for bad in (dict(CASE_OK, gate_scenario="review"),
                    {**CASE_OK, "provenance": {"source": "machine", "trust_weight": 1.0}}):
            with self.assertRaises(cc.ContractViolation):
                cc.validate_case(bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
