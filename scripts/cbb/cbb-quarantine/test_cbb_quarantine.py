# -*- coding: utf-8 -*-
"""test_cbb_quarantine.py — cbb_quarantine v2 单测（py -X utf8 运行）

判据锚：三子类分流 + urgency 排序。保留面：五分组报告/append-only 裁决/幂等登记。
新增：🔴超期态/🟡🟢 分档/top_urgent 前 3/[?] 内联扫描+行号汇总。
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cbb_quarantine as cq


def make_zone():
    td = tempfile.TemporaryDirectory()
    zone = cq.QuarantineZone(Path(td.name))
    return zone, td


class TestSubclassRouting(unittest.TestCase):
    """三子类分流（判据①）。"""

    def test_default_group_to_subclass(self):
        self.assertEqual(cq.GROUP_TO_SUBCLASS["unresolved_time"], "extrapolation_unverified")
        self.assertEqual(cq.GROUP_TO_SUBCLASS["missing_anchor"], "extrapolation_unverified")
        self.assertEqual(cq.GROUP_TO_SUBCLASS["entity_unalignable"], "contradiction_pending")  # 实体不可归一→矛盾待裁决

    def test_gate1_carried_subclass_wins(self):
        zone, td = make_zone()
        self.addCleanup(td.cleanup)
        # gate1 死人走路带 contradiction_pending，group 用 unresolved_time 占位——显式子类优先
        iid, created = zone.register("unresolved_time", "死人走路", subclass="contradiction_pending")
        self.assertTrue(created)
        self.assertEqual(zone.pending()[0]["subclass"], "contradiction_pending")

    def test_tier_item_defaults_to_overdue_omission(self):
        zone, td = make_zone()
        self.addCleanup(td.cleanup)
        zone.register("unresolved_time", "契诃夫之枪", tier="core",
                      planted_chapter=10, target_chapter=13)
        self.assertEqual(zone.pending()[0]["subclass"], "overdue_omission")  # 期限项自动归超期遗漏

    def test_by_subclass_counts(self):
        zone, td = make_zone()
        self.addCleanup(td.cleanup)
        zone.register("unresolved_time", "a")
        zone.register("missing_anchor", "b")
        zone.register("entity_unalignable", "c")
        zone.register("unresolved_time", "d", tier="subplot", planted_chapter=1, target_chapter=5)
        counts = zone.by_subclass()
        self.assertEqual(counts["extrapolation_unverified"], 2)
        self.assertEqual(counts["contradiction_pending"], 1)
        self.assertEqual(counts["overdue_omission"], 1)

    def test_bad_subclass_tier_group_rejected(self):
        zone, td = make_zone()
        self.addCleanup(td.cleanup)
        with self.assertRaises(ValueError):
            zone.register("unresolved_time", "x", subclass="第四态")  # 不存在的子类
        with self.assertRaises(ValueError):
            zone.register("unresolved_time", "x", tier="vital")      # 不在层级表
        with self.assertRaises(ValueError):
            zone.register("乱组", "x")


class TestUrgency(unittest.TestCase):
    """urgency 公式+排序（判据②：三层级 3.0/2.0/1.0+进度比+🔴🟡🟢）。"""

    def test_formula_ratio_times_tier(self):
        item = {"tier": "core", "planted_chapter": 10, "target_chapter": 20}
        self.assertAlmostEqual(cq.urgency_of(item, current_chapter=15), 1.5)   # 0.5×3.0
        sub = {"tier": "subplot", "planted_chapter": 10, "target_chapter": 20}
        self.assertAlmostEqual(cq.urgency_of(sub, current_chapter=15), 1.0)    # 0.5×2.0
        dec = {"tier": "decorative", "planted_chapter": 10, "target_chapter": 20}
        self.assertAlmostEqual(cq.urgency_of(dec, current_chapter=15), 0.5)    # 0.5×1.0

    def test_status_three_bands(self):
        item = {"tier": "core", "planted_chapter": 10, "target_chapter": 20}
        self.assertEqual(cq.urgency_status(item, 20), "🔴")  # 到点即超期（countdowns_due 同口径）
        self.assertEqual(cq.urgency_status(item, 21), "🔴")  # 过点持续
        self.assertEqual(cq.urgency_status(item, 19), "🟡")  # (19-10)/10=0.9 ≥0.8 警告
        self.assertEqual(cq.urgency_status(item, 18), "🟡")  # 0.8 恰在警戒线
        self.assertEqual(cq.urgency_status(item, 17), "🟢")  # 0.7 <0.8 正常
        self.assertEqual(cq.urgency_status(item, 15), "🟢")  # 0.5 正常

    def test_no_deadline_returns_none(self):
        self.assertIsNone(cq.urgency_of({"tier": None}, 20))
        self.assertIsNone(cq.urgency_status({}, 20))
        bad_span = {"tier": "core", "planted_chapter": 10, "target_chapter": 10}
        self.assertIsNone(cq.urgency_of(bad_span, 12))  # 期限非法（target≤planted）不参与

    def test_sorting_expected_order(self):
        zone, td = make_zone()
        self.addCleanup(td.cleanup)
        zone.register("unresolved_time", "装饰远点", tier="decorative", planted_chapter=10, target_chapter=25)
        zone.register("unresolved_time", "核心近点", tier="core", planted_chapter=10, target_chapter=25)
        zone.register("unresolved_time", "支线超期", tier="subplot", planted_chapter=10, target_chapter=15)
        top = zone.top_urgent(current_chapter=24, n=3)
        # 核心：0.933×3.0=2.8；支线超期：(24-10)/5=2.8×2.0=5.6；装饰：0.933×1.0=0.93
        # → 支线超期(5.6) > 核心近点(2.8) > 装饰远点(0.93)：超期高进度比压过层级权重
        self.assertEqual([it["detail"] for it in top], ["支线超期", "核心近点", "装饰远点"])

    def test_top_urgent_caps_at_n(self):
        zone, td = make_zone()
        self.addCleanup(td.cleanup)
        for i in range(6):
            zone.register("unresolved_time", f"枪{i}", tier="core",
                          planted_chapter=1, target_chapter=100 + i)
        self.assertEqual(len(zone.top_urgent(current_chapter=50)), 3)  # 只取前 3 条纪律

    def test_overdue_symbol_in_report(self):
        zone, td = make_zone()
        self.addCleanup(td.cleanup)
        zone.register("unresolved_time", "超期的契诃夫之枪", tier="core",
                      planted_chapter=10, target_chapter=13)
        md = zone.report_markdown(current_chapter=20)
        self.assertIn("🔴", md)                      # 超期态遗漏告警可见
        # urgency=(20-10)/(13-10)=3.333 进度比 ×3.0 = 10.00
        self.assertIn("urgency=10.00", md)


class TestInlineScan(unittest.TestCase):
    """[?] 内联标记+行号汇总（graphify-novel 吸收）。"""

    def test_scan_lines_and_excerpt(self):
        text = "第一行干净\n第二行有 [?] 存疑标记\n\n第四行另一个 [?] 标记"
        hits = cq.scan_inline_unsure(text)
        self.assertEqual([h["line"] for h in hits], [2, 4])
        self.assertIn("[?]", hits[0]["excerpt"])

    def test_scan_empty_and_none(self):
        self.assertEqual(cq.scan_inline_unsure("干净文本"), [])
        self.assertEqual(cq.scan_inline_unsure(""), [])

    def test_inline_report_format(self):
        md = cq.inline_report({"a.md": [{"line": 6, "excerpt": "status: alive # [?] ch.12 命运不明"}],
                               "b.md": []})
        self.assertIn("a.md — line 6", md)
        self.assertIn("1 处", md)


class TestAdjudicationChannel(unittest.TestCase):
    """保留面：append-only 裁决通道+五分组报告+幂等登记。"""

    def test_register_idempotent(self):
        zone, td = make_zone()
        self.addCleanup(td.cleanup)
        i1, c1 = zone.register("unresolved_time", "同一细节")
        i2, c2 = zone.register("unresolved_time", "同一细节")
        self.assertEqual((i1, c1, c2), (i2, True, False))

    def test_adjudicate_final_state(self):
        zone, td = make_zone()
        self.addCleanup(td.cleanup)
        iid, _ = zone.register("low_confidence", "低置信条目")
        zone.adjudicate(iid, "confirmed", note="采信")
        with self.assertRaises(ValueError):
            zone.adjudicate(iid, "rejected")  # 终态不可再裁
        self.assertEqual(zone.pending(), [])          # 裁决后出列
        self.assertEqual(len(zone.adjudicated()), 1)  # 留档不删

    def test_report_keeps_five_groups_and_confirm_wording(self):
        zone, td = make_zone()
        self.addCleanup(td.cleanup)
        zone.register("missing_anchor", "无锚")
        zone.register("ambiguous_reference", "指代不明")
        md = zone.report_markdown()
        for g in ("missing_anchor", "ambiguous_reference"):
            self.assertIn(g, md)
        self.assertIn("请你确认", md)     # 五分组请你确认报告保留
        self.assertIn("矛盾待裁决", md)   # 三子类统计新增

    def test_zone_reload_state_consistent(self):
        zone, td = make_zone()
        self.addCleanup(td.cleanup)
        zone.register("unresolved_time", "a")
        iid, _ = zone.register("low_confidence", "b")
        zone.adjudicate(iid, "rejected")
        zone2 = cq.QuarantineZone(zone.root)  # 同 root 新实例=读盘对账
        self.assertEqual([it["detail"] for it in zone2.pending()], ["a"])
        self.assertEqual(len(zone2.adjudicated()), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
