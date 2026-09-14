# -*- coding: utf-8 -*-
"""test_cbb_quarantine.py — cbb_quarantine 单测（py -X utf8 运行）

断言：五类分组登记/幂等/非法分组拒绝；阻塞下游计数降序排序；
裁决通道（confirmed|rejected 终态留档不删、不可二次裁决）；
报告含"请你确认"与分组统计（第一产出）；落盘持久化与确定性。
"""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cbb_quarantine as cq  # noqa: E402


class ZoneTestBase(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name) / "zone"
        self.zone = cq.QuarantineZone(self.root)

    def tearDown(self):
        self.td.cleanup()


class TestRegister(ZoneTestBase):
    def test_register_and_persistence(self):
        iid, created = self.zone.register("unresolved_time", "三天后无法挂锚",
                                          record_id="cand-x", source="cbb-anchor",
                                          blocks=["cand-y", "cand-z"])
        self.assertTrue(created)
        self.assertTrue(iid.startswith("q-"))
        # 新实例读盘对账（事实在磁盘）
        zone2 = cq.QuarantineZone(self.root)
        self.assertEqual(len(zone2.pending()), 1)
        self.assertEqual(zone2.pending()[0]["blocks_downstream"], ["cand-y", "cand-z"])

    def test_idempotent_register(self):
        self.zone.register("low_confidence", "quote 悬空", record_id="c1")
        _, created2 = self.zone.register("low_confidence", "quote 悬空", record_id="c1")
        self.assertFalse(created2)
        self.assertEqual(len(self.zone.pending()), 1)

    def test_invalid_group_rejected(self):
        with self.assertRaises(ValueError):
            self.zone.register("unknown_group", "x")

    def test_all_five_groups_accepted(self):
        for g in cq.GROUPS:
            self.zone.register(g, f"detail-{g}")
        self.assertEqual(len(self.zone.pending()), 5)
        self.assertTrue(all(v == 1 for v in self.zone.by_group().values()))


class TestAdjudicate(ZoneTestBase):
    def test_confirmed_and_rejected_terminal(self):
        i1, _ = self.zone.register("unresolved_time", "d1")
        i2, _ = self.zone.register("missing_anchor", "d2")
        self.zone.adjudicate(i1, "confirmed", note="人工核为真")
        self.zone.adjudicate(i2, "rejected", note="误报")
        self.assertEqual(self.zone.pending(), [])
        adj = {a["item_id"]: a["decision"] for a in self.zone.adjudicated()}
        self.assertEqual(adj, {i1: "confirmed", i2: "rejected"})  # 终态留档不删

    def test_double_adjudication_rejected(self):
        iid, _ = self.zone.register("entity_unalignable", "d")
        self.zone.adjudicate(iid, "rejected", "x")
        with self.assertRaises(ValueError):
            self.zone.adjudicate(iid, "confirmed", "y")

    def test_invalid_decision_and_unknown_item(self):
        iid, _ = self.zone.register("low_confidence", "d")
        with self.assertRaises(ValueError):
            self.zone.adjudicate(iid, "maybe")
        with self.assertRaises(KeyError):
            self.zone.adjudicate("q-nonexistent", "confirmed")


class TestReport(ZoneTestBase):
    def test_report_first_class_output(self):
        self.zone.register("unresolved_time", "低阻塞项", record_id="r-low", blocks=["b1"])
        self.zone.register("ambiguous_reference", "高阻塞项", record_id="r-high",
                           blocks=["b1", "b2", "b3"])
        iid3, _ = self.zone.register("missing_anchor", "已裁决项", record_id="r-done")
        self.zone.adjudicate(iid3, "rejected", "复核为元文本")
        md = self.zone.report_markdown()
        self.assertIn("请你确认", md)                      # 第一产出的标志性措辞
        self.assertIn("unresolved_time", md)
        self.assertIn("ambiguous_reference", md)
        self.assertIn("阻塞下游 3 项", md)
        self.assertLess(md.index("高阻塞项"), md.index("低阻塞项"))  # 阻塞计数降序
        self.assertIn("rejected", md)                       # 终态留档可见
        self.assertNotIn("已裁决项", md.split("## 已裁决")[0])  # 已裁决不占待裁决清单

    def test_report_deterministic(self):
        self.zone.register("low_confidence", "d", record_id="r", blocks=["x"])
        self.assertEqual(self.zone.report_markdown(), self.zone.report_markdown())


class TestThreeStateStub(unittest.TestCase):
    def test_quarantine_sink(self):
        with tempfile.TemporaryDirectory() as td:
            p, c1 = cq.three_state_write_stub({"record_id": "r1"}, Path(td), "quarantine")
            _, c2 = cq.three_state_write_stub({"record_id": "r1"}, Path(td), "quarantine")
            self.assertTrue(c1)
            self.assertFalse(c2)
            self.assertTrue(p.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
