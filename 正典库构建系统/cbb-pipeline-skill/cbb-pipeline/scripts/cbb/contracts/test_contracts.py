# -*- coding: utf-8 -*-
"""test_contracts.py — 四契约 v2.0 schema 与校验器单测（py -X utf8 运行）

覆盖：四 schema 好/坏样本双向；v2.0 新字段逐项（verified_against/observations/
fix_action/confidence_caliber/cites/critique 键序/分带一致/rule_applied 强制/
counter_example 三段式/retro_tags 词形）；边界值（分带 91/90/80/79.9、SHA 短哈希）；
v1.0 行为回归（二态/allow_candidate/证据四元组）。
"""
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
    "evidence": [{"vol": 1, "chapter": 14, "line": 3, "quote": "缇达拔出了剑",
                  "file": "mepub/v1/ch14.md"}],
    "observations": [
        {"category": "event", "text": "缇达在比武场拔剑", "chapter": 14},
        {"category": "status_change", "text": "由观望转入战斗"},
    ],
    "verified_against": {"path": "mepub/v1/ch14.md", "sha": "3f160cb9a45d", "verified_at": "2026-09-15"},
    "provenance": {
        "extractor_confidence": 92,
        "gate_trace": [{"gate": "1", "verdict_id": "v-x", "ts": "2026-09-15T00:00:00"}],
        "precedent_refs": [],
        "status_history": [{"from": "candidate", "to": "confirmed", "at": "2026-09-15", "by": "promotion"}],
    },
    "version": 1,
    "supersedes": None,
}

ISSUE_OK = {
    "issue_id": "iss-0001",
    "skill": "cbb-gate1",
    "error_type": "continuity-dead-walk",
    "claim": "角色在第14章已死亡，第20章再次行动",
    "evidence_span": {"vol": 1, "chapter": 20, "line": 8, "quote": "……"},
    "graph_context": {"neighbors": []},
    "severity": "major",
    "extraction_confidence": 97,
    "fix_action": {"priority": "P0", "command": "py -X utf8 cbb/cbb-store/audit.py --record rec-dead-walk", "note": "先核死亡记录"},
    "confidence_caliber": "deterministic",
    "cites": ["rec-0001", "rec-0009"],
}

VERDICT_OK = {  # 键序：critique 先于 label（构造时即按此序）
    "issue_id": "iss-0001",
    "critique": "死亡事件 ch.14 与行动事件 ch.20 均有原文直证，时间线无回退解释",
    "label": "conflict",
    "confidence": 93,
    "confidence_band": "high",
    "rule_applied": {"school": "later_books", "field": "facts",
                     "rationale": "事实后书优先；首次出场基准不适用于生死事实"},
    "judge_id": "judge-local-v0",
    "reasoning": "时间戳排序矛盾",
    "evidence_check": {"quote_found": True},
}

CASE_OK = {
    "case_id": "case-0001",
    "issue": ISSUE_OK,
    "verdict": VERDICT_OK,
    "provenance": {"source": "human", "trust_weight": 1.0},
    "retrieval_hints": {"tags": ["时间"], "entities": ["缇达"], "counter_example_of": "case-0000"},
    "counter_example": {
        "source_text": "她黑色的长发垂落（原文仅写发色）",
        "wrong": "外貌：日本人特征的黑长直、身材娇小（AI 先验补全）",
        "right": "外貌：黑长发// 原文未提及：身材、国籍特征",
    },
    "retro_tags": ["#死人走路", "#跨章矛盾"],
    "usage": {"retrieval_count": 0, "agreement_rate_when_cited": 0.0},
    "gate_scenario": "extraction",
}


class TestSchemasLoad(unittest.TestCase):
    def test_all_four_load_v2(self):
        for name in ("record", "issue", "verdict", "case"):
            schema = cc.load_schema(name)
            self.assertIn("required", schema)
            self.assertIn("v2.0", schema["$id"], f"{name} 应为 v2.0")


class TestRecordV2(unittest.TestCase):
    def test_ok(self):
        cc.validate_record(RECORD_OK)

    def test_verified_against_required(self):
        bad = {k: v for k, v in RECORD_OK.items() if k != "verified_against"}
        with self.assertRaises(cc.ContractViolation):
            cc.validate_record(bad)

    def test_verified_against_triple_complete(self):
        for missing in ("path", "sha", "verified_at"):
            bad = dict(RECORD_OK, verified_against={k: v for k, v in RECORD_OK["verified_against"].items() if k != missing})
            with self.assertRaises(cc.ContractViolation):
                cc.validate_record(bad)

    def test_sha_pattern(self):
        bad = dict(RECORD_OK, verified_against=dict(RECORD_OK["verified_against"], sha="ZZZnot-hex"))
        with self.assertRaises(cc.ContractViolation):
            cc.validate_record(bad)
        short7 = dict(RECORD_OK, verified_against=dict(RECORD_OK["verified_against"], sha="3f160cb"))
        cc.validate_record(short7)  # 7 位短哈希合法

    def test_verified_at_iso_prefix(self):
        bad = dict(RECORD_OK, verified_against=dict(RECORD_OK["verified_against"], verified_at="yesterday"))
        with self.assertRaises(cc.ContractViolation):
            cc.validate_record(bad)

    def test_observation_vocabulary(self):
        bad = dict(RECORD_OK, observations=[{"category": "vibe", "text": "不在词表"}])
        with self.assertRaises(cc.ContractViolation):
            cc.validate_record(bad)
        ok_extra = dict(RECORD_OK, observations=[{"category": "knowledge", "text": "知情：卢卡不知坠井事"}])
        cc.validate_record(ok_extra)  # CBB 自增类目在词表内

    def test_observation_text_minlength(self):
        bad = dict(RECORD_OK, observations=[{"category": "event", "text": ""}])
        with self.assertRaises(cc.ContractViolation):
            cc.validate_record(bad)

    def test_evidence_optional_file_anchor(self):
        no_file = dict(RECORD_OK, evidence=[{k: v for k, v in RECORD_OK["evidence"][0].items() if k != "file"}])
        cc.validate_record(no_file)  # file 可选

    def test_no_fourth_state(self):
        for state in ("cut", "contradicted", "archived"):
            bad = dict(RECORD_OK, status=state)
            with self.assertRaises(cc.ContractViolation):
                cc.validate_record(bad)

    def test_candidate_only_with_flag(self):
        cand = dict(RECORD_OK, status="candidate")
        with self.assertRaises(cc.ContractViolation):
            cc.validate_record(cand)
        cc.validate_record(cand, allow_candidate=True)

    def test_evidence_quadruple_fields(self):
        self.assertTrue(cc.evidence_ok(RECORD_OK["evidence"][0]))
        self.assertFalse(cc.evidence_ok({"vol": 1, "chapter": 1, "line": 0, "quote": ""}))
        self.assertFalse(cc.evidence_ok({"vol": "一", "chapter": 1, "line": 0, "quote": "x"}))


class TestIssueV2(unittest.TestCase):
    def test_ok(self):
        cc.validate_issue(ISSUE_OK)

    def test_fix_action_required(self):
        bad = {k: v for k, v in ISSUE_OK.items() if k != "fix_action"}
        with self.assertRaises(cc.ContractViolation):
            cc.validate_issue(bad)

    def test_fix_action_priority_enum(self):
        bad = dict(ISSUE_OK, fix_action=dict(ISSUE_OK["fix_action"], priority="P9"))
        with self.assertRaises(cc.ContractViolation):
            cc.validate_issue(bad)

    def test_fix_action_command_minlength(self):
        bad = dict(ISSUE_OK, fix_action=dict(ISSUE_OK["fix_action"], command=""))
        with self.assertRaises(cc.ContractViolation):
            cc.validate_issue(bad)

    def test_confidence_caliber_enum(self):
        bad = dict(ISSUE_OK, confidence_caliber="gut-feeling")
        with self.assertRaises(cc.ContractViolation):
            cc.validate_issue(bad)
        for ok in ("deterministic", "judgment"):
            cc.validate_issue(dict(ISSUE_OK, confidence_caliber=ok))

    def test_cites_min_items(self):
        bad = dict(ISSUE_OK, cites=[])
        with self.assertRaises(cc.ContractViolation):
            cc.validate_issue(bad)
        bad2 = {k: v for k, v in ISSUE_OK.items() if k != "cites"}
        with self.assertRaises(cc.ContractViolation):
            cc.validate_issue(bad2)

    def test_null_error_type_still_allowed(self):
        cc.validate_issue(dict(ISSUE_OK, error_type=None))


class TestVerdictV2(unittest.TestCase):
    def test_ok_conflict_with_rule(self):
        cc.validate_verdict(VERDICT_OK)

    def test_critique_order_enforced(self):
        # 同内容、键序反转（label 先于 critique）→ 拒
        bad = {}
        for k in ("label", "confidence", "confidence_band", "critique", "issue_id",
                  "judge_id", "reasoning", "evidence_check", "rule_applied"):
            bad[k] = VERDICT_OK[k]
        with self.assertRaises(cc.ContractViolation):
            cc.validate_verdict(bad)

    def test_band_consistency(self):
        bad = dict(VERDICT_OK, confidence=85, confidence_band="high")
        with self.assertRaises(cc.ContractViolation):
            cc.validate_verdict(bad)

    def test_confidence_scale_maximum(self):
        bad = dict(VERDICT_OK, confidence=101, confidence_band="high")
        with self.assertRaises(cc.ContractViolation):
            cc.validate_verdict(bad)

    def test_conflict_requires_rule_applied(self):
        bad = {k: v for k, v in VERDICT_OK.items() if k != "rule_applied"}
        with self.assertRaises(cc.ContractViolation):
            cc.validate_verdict(bad)

    def test_consistent_label_without_rule_ok(self):
        ok = {k: v for k, v in VERDICT_OK.items() if k != "rule_applied"}
        ok = dict(ok, label="consistent", confidence=95, confidence_band="high")
        cc.validate_verdict(ok)

    def test_rule_school_enum(self):
        bad = dict(VERDICT_OK, rule_applied=dict(VERDICT_OK["rule_applied"], school="coin_flip"))
        with self.assertRaises(cc.ContractViolation):
            cc.validate_verdict(bad)
        for school in cc.VERDICT_SCHOOLS:
            v = dict(VERDICT_OK, rule_applied=dict(VERDICT_OK["rule_applied"], school=school))
            cc.validate_verdict(v)

    def test_band_boundaries(self):
        self.assertEqual(cc.confidence_band(91), "high")
        self.assertEqual(cc.confidence_band(90), "medium")
        self.assertEqual(cc.confidence_band(80), "medium")
        self.assertEqual(cc.confidence_band(79.9), "low")
        self.assertEqual(cc.confidence_band(0), "low")


class TestCaseV2(unittest.TestCase):
    def test_ok(self):
        cc.validate_case(CASE_OK)

    def test_counter_example_trio_required(self):
        bad = dict(CASE_OK, counter_example={k: v for k, v in CASE_OK["counter_example"].items() if k != "right"})
        with self.assertRaises(cc.ContractViolation):
            cc.validate_case(bad)

    def test_counter_example_pairing(self):
        hints = dict(CASE_OK["retrieval_hints"], counter_example_of="case-0000")
        bad = {k: v for k, v in CASE_OK.items() if k != "counter_example"}
        bad["retrieval_hints"] = hints
        with self.assertRaises(cc.ContractViolation):
            cc.validate_case(bad)
        # counter_example_of 为 null 时不强制
        ok = dict(bad, retrieval_hints=dict(hints, counter_example_of=None))
        cc.validate_case(ok)

    def test_retro_tag_pattern(self):
        bad = dict(CASE_OK, retro_tags=["开篇慢"])  # 缺 # 前缀
        with self.assertRaises(cc.ContractViolation):
            cc.validate_case(bad)

    def test_gate_scenario_enum(self):
        bad = dict(CASE_OK, gate_scenario="review")
        with self.assertRaises(cc.ContractViolation):
            cc.validate_case(bad)

    def test_provenance_source_enum(self):
        bad = dict(CASE_OK, provenance={"source": "machine", "trust_weight": 1.0})
        with self.assertRaises(cc.ContractViolation):
            cc.validate_case(bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
