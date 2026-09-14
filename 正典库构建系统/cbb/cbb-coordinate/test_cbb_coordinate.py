# -*- coding: utf-8 -*-
"""test_cbb_coordinate.py — cbb_coordinate v2 单测（py -X utf8 运行）

覆盖：v1.0 回归（坐标四元组/行号/block_id/引文定位/preamble/幂等缓存/无时钟字段）
+ v2.0 新行为（追加序：乱序插入预期+永不重排；查重占位：(series,key) 幂等+落盘即占位+
断点重放一致+故事序视图不改号）。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cbb_coordinate as cc

SAMPLE = """<<<CHAPTER 0001 | 测试之章>>>
第一段第一行
第一段第二行

第二段独行

<<<CHAPTER 0002 | 又一章>>>
第二章内容仅一段
"""


class TestCoordinateRegression(unittest.TestCase):
    """v1.0 保留面回归（实验版同款用例）。"""

    def setUp(self):
        self.m = cc.coordinate(SAMPLE, vol=1)

    def test_chapter_count_and_titles(self):
        self.assertEqual(self.m["chapter_count"], 2)
        self.assertEqual([c["title"] for c in self.m["chapters"]], ["测试之章", "又一章"])

    def test_quadruple_and_line_numbering(self):
        ch1 = self.m["chapters"][0]
        self.assertEqual([(p["line_start"], p["line_end"]) for p in ch1["paragraphs"]],
                         [(1, 2), (4, 4)])
        self.assertEqual(self.m["chapters"][1]["paragraphs"][0]["line_start"], 1)

    def test_block_id_format(self):
        b = self.m["blocks"][0]
        self.assertEqual(b["block_id"], "v01c0001p0001")
        self.assertEqual((b["vol"], b["chapter"], b["para"]), (1, 1, 1))

    def test_quote_locatable(self):
        hit = cc.locate_quote(self.m["blocks"], 1, 1, "第一段第二行")
        self.assertIsNotNone(hit)
        self.assertEqual(hit["block_id"], "v01c0001p0001")
        self.assertIsNone(cc.locate_quote(self.m["blocks"], 1, 2, "第一段第二行"))
        self.assertIsNone(cc.locate_quote(self.m["blocks"], 1, 1, "不存在的引文"))

    def test_preamble_not_silently_dropped(self):
        m = cc.coordinate("散落前导文本\n\n<<<CHAPTER 0001 | 章>>>\n正文\n")
        self.assertEqual(m["chapters"][0]["chapter"], 0)
        self.assertIn("散落前导文本", m["chapters"][0]["paragraphs"][0]["text"])

    def test_cache_hit_and_identical_output(self):
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td)
            src = tp / "sample.txt"
            src.write_text(SAMPLE, encoding="utf-8")
            first = cc.process_file(src, tp / "cache")
            self.assertFalse(first["cache_hit"])
            second = cc.process_file(src, tp / "cache")
            self.assertTrue(second["cache_hit"])
            a = {k: v for k, v in first.items() if k != "cache_hit"}
            b = {k: v for k, v in second.items() if k != "cache_hit"}
            self.assertEqual(a, b)  # 断点协议：命中即跳过，输出逐键一致

    def test_no_clock_fields(self):
        manifest = json.dumps(cc.coordinate(SAMPLE), ensure_ascii=False)
        for banned in ('"now"', '"timestamp"', '"created_at"', "datetime"):
            self.assertNotIn(banned, manifest)


class TestNumberingAppendOrder(unittest.TestCase):
    """v2.0 吸收①：事件 ID 追加序纪律。"""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.path = Path(self.td.name) / "reg.jsonl"

    def test_sequential_by_allocation(self):
        reg = cc.NumberingRegistry(self.path)
        self.assertEqual(reg.register("EVT", "e1", story_pos=100), "EVT-0001")
        self.assertEqual(reg.register("EVT", "e2", story_pos=5), "EVT-0002")   # 追溯补录：story 序在前
        self.assertEqual(reg.register("EVT", "e3", story_pos=50), "EVT-0003")

    def test_out_of_order_insertion_expected_never_renumber(self):
        reg = cc.NumberingRegistry(self.path)
        ids_before = [reg.register("EVT", k, p) for k, p in [("a", 100), ("b", 5), ("c", 50)]]
        # 故事序视图按 story_pos 排序，但编号保持分配序——乱序是预期，永不重排
        story_view = reg.by_story_order("EVT")
        self.assertEqual([e["id"] for e in story_view], ["EVT-0002", "EVT-0003", "EVT-0001"])
        self.assertEqual([e["story_pos"] for e in story_view], [5, 50, 100])
        # 再补录：既有 ID 不因新插入而变化（永不重排的反例断言）
        reg.register("EVT", "d", story_pos=1)
        story_view2 = reg.by_story_order("EVT")
        self.assertEqual([e["id"] for e in story_view2],
                         ["EVT-0004", "EVT-0002", "EVT-0003", "EVT-0001"])
        self.assertEqual(ids_before, ["EVT-0001", "EVT-0002", "EVT-0003"])

    def test_story_pos_none_sinks_by_allocation(self):
        reg = cc.NumberingRegistry(self.path)
        reg.register("EVT", "known", story_pos=10)
        reg.register("EVT", "unknown")  # 章未知（graphify-novel ch.? 同思路）
        reg.register("EVT", "known2", story_pos=2)
        view = reg.by_story_order("EVT")
        self.assertEqual([e["key"] for e in view], ["known2", "known", "unknown"])

    def test_series_independent_counters(self):
        reg = cc.NumberingRegistry(self.path)
        self.assertEqual(reg.register("EVT", "x"), "EVT-0001")
        self.assertEqual(reg.register("REL", "x"), "REL-0001")  # 同 key 不同 series 不撞
        self.assertEqual(reg.register("EVT", "y"), "EVT-0002")

    def test_bad_story_pos_rejected(self):
        reg = cc.NumberingRegistry(self.path)
        with self.assertRaises(ValueError):
            reg.register("EVT", "x", story_pos=-1)
        with self.assertRaises(ValueError):
            reg.register("EVT", "x", story_pos="五")


class TestNumberingDedupOccupy(unittest.TestCase):
    """v2.0 吸收②：先查重即占位（R-015）。"""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.path = Path(self.td.name) / "reg.jsonl"

    def test_register_idempotent_by_key(self):
        reg = cc.NumberingRegistry(self.path)
        r1 = reg.register("EVT", "e1")
        r2 = reg.register("EVT", "e1")  # 查重命中：同号返回，不重复占位
        self.assertEqual(r1, r2)
        self.assertEqual(len(reg.snapshot()), 1)
        self.assertEqual(self.path.read_text(encoding="utf-8").count("\n"), 1)  # 账本只追加未虚增

    def test_occupy_is_immediate_disk_append(self):
        reg = cc.NumberingRegistry(self.path)
        reg.register("EVT", "e1")
        # 落盘即占位：另一实例从盘重放即可见（R-015：取号前重放最新账本）
        reg2 = cc.NumberingRegistry(self.path)
        self.assertEqual(reg2.locate("EVT", "e1"), "EVT-0001")
        self.assertEqual(reg2.register("EVT", "e1"), "EVT-0001")  # 重放后不双发
        self.assertEqual(reg2.register("EVT", "e2"), "EVT-0002")  # 计数正确续接

    def test_replay_rebuilds_state_identically(self):
        reg = cc.NumberingRegistry(self.path)
        for k, p in [("a", 3), ("b", 1), ("c", None)]:
            reg.register("EVT", k, story_pos=p)
        reg_reloaded = cc.NumberingRegistry(self.path)  # 断点续跑：重放重建
        self.assertEqual(reg.snapshot(), reg_reloaded.snapshot())
        self.assertEqual(reg_reloaded.register("EVT", "d"), "EVT-0004")

    def test_append_only_never_mutates(self):
        reg = cc.NumberingRegistry(self.path)
        reg.register("EVT", "a", story_pos=9)
        lines1 = self.path.read_text(encoding="utf-8").splitlines()
        reg.register("EVT", "b", story_pos=1)  # 乱序插入不回写不重排
        reg.by_story_order("EVT")
        lines2 = self.path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines2[:len(lines1)], lines1)  # 旧行逐字节不变
        self.assertEqual(len(lines2), len(lines1) + 1)  # 只追加

    def test_registry_no_clock_fields(self):
        reg = cc.NumberingRegistry(self.path)
        reg.register("EVT", "a", story_pos=1)
        blob = self.path.read_text(encoding="utf-8")
        for banned in ("now", "timestamp", "created_at", "datetime"):
            self.assertNotIn(banned, blob)


if __name__ == "__main__":
    unittest.main(verbosity=2)
