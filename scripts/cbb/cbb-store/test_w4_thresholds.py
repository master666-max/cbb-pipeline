# -*- coding: utf-8 -*-
"""test_w4_thresholds.py — 漂移修正 W4 单测（工单 v1.4 §0；2026-09-17 U-C03.5）。

覆盖三件：
  ① 三阈值显式：TAU_CONFIRMED/TAU_PROVISIONAL/TAU_QUARANTINE 常量与 THRESHOLDS 字典在案，
     语义=三档两边界（B1：confirmed 永不因置信度单独达成）；
  ② 量纲统一 0-100（2026-10-03 审计修正：extractor_confidence/CORROBORATION_BUMP
     本就是百分制，旧 0-1 小数阈与之混用）；route_by_confidence 全仓零调用随死代码退役
     （回归：函数必须不存在，防复活）；
  ③ B3 校准报告：fixture 库上分布计数正确、阈值假设回显、建议制输出。
"""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "contracts"))
sys.path.insert(0, str(HERE.parent / "cbb-quarantine"))
import cbb_store  # noqa: E402

VA = {"path": "test://corpus", "sha": "0123456789abcdef", "verified_at": "2026-09-17"}


def mk_entity(name, conf, etype="人物"):
    return {
        "record_id": f"cand-entity-{name}", "record_type": "entity", "library": "character",
        "status": "candidate",
        "canonical": {"name": name, "entity_type": etype},
        "evidence": [{"vol": 1, "chapter": 14, "line": 3, "quote": f"{name}在场"}],
        "verified_against": VA,
        "provenance": {"extractor_confidence": conf, "gate_trace": [], "precedent_refs": [],
                       "status_history": []},
        "version": 1, "supersedes": None,
    }


class TestThresholdsExplicit(unittest.TestCase):
    def test_three_taus_defined(self):
        self.assertEqual(cbb_store.TAU_CONFIRMED, 97.0)
        self.assertEqual(cbb_store.TAU_PROVISIONAL, 85.0)
        self.assertEqual(cbb_store.TAU_QUARANTINE, 85.0)
        for k in ("tau_confirmed", "tau_provisional", "tau_quarantine", "corroboration_bump"):
            self.assertIn(k, cbb_store.THRESHOLDS)
        self.assertIn("B1", cbb_store.THRESHOLDS["note"])  # confirmed 纪律随阈值出账

    def test_route_by_confidence_retired_scale_unified(self):
        """修2④ 回归：route_by_confidence 全仓零调用=死代码已退役，不许复活；
        三阈值量纲与 extractor_confidence 同为 0-100（旧 0-1 小数阈与百分制混用）。"""
        self.assertFalse(hasattr(cbb_store, "route_by_confidence"),
                         "route_by_confidence 已删（零调用死代码），不得复活")
        self.assertTrue(85.0 <= cbb_store.TAU_PROVISIONAL <= cbb_store.TAU_CONFIRMED <= 100.0)
        self.assertGreaterEqual(cbb_store.TAU_QUARANTINE, 1.0)  # 百分制，不是 0-1 小数


class TestConfirmedNeverByConfidence(unittest.TestCase):
    def test_admit_high_confidence_stays_provisional(self):
        with tempfile.TemporaryDirectory() as td:
            store = cbb_store.ThreeStateStore(Path(td))
            store.admit_or_merge(mk_entity("高置信者", 99))
            rec = store.find_by_identity(mk_entity("高置信者", 0.99))
            self.assertEqual(rec["status"], "provisional")  # B1：置信 0.99 仍 provisional


class TestCalibrationReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = cbb_store.ThreeStateStore(Path(self.tmp.name))
        for name, conf in (("甲", 90), ("乙", 86), ("丙", 99)):
            self.store.admit_or_merge(mk_entity(name, conf))
        self.store.admit(mk_entity("低置信者", 0.60), "quarantine",
                         quarantine_group="low_confidence", quarantine_detail="测试低置信")

    def tearDown(self):
        self.tmp.cleanup()

    def test_report_counts_and_thresholds(self):
        rep = self.store.calibration_report()
        dist = rep["library_confidence_distribution"]
        self.assertEqual(dist["records_with_confidence"], 3)
        self.assertEqual(dist["ge_tau_confirmed"], 1)      # 丙 99
        self.assertEqual(dist["provisional_band"], 2)      # 甲乙
        self.assertEqual(dist["below_tau_quarantine_in_library"], 0)
        self.assertEqual(dist["min"], 86)
        self.assertEqual(rep["thresholds"]["tau_quarantine"], 85.0)
        self.assertEqual(rep["quarantine_by_group"].get("low_confidence"), 1)

    def test_report_is_advisory(self):
        rep = self.store.calibration_report()
        self.assertIn("建议制", rep["decision_rule"])
        self.assertIsInstance(rep["suggestions"], list)
        self.assertIsInstance(rep["assumption_checks"], list)
        # 建议制不自动改：报告调用前后阈值不变
        self.assertEqual(cbb_store.TAU_QUARANTINE, 85.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
