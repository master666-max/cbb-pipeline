# -*- coding: utf-8 -*-
"""test_cbb_coordinate.py — cbb_coordinate 单测（py -X utf8 运行）"""
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


class TestCoordinate(unittest.TestCase):
    def setUp(self):
        self.m = cc.coordinate(SAMPLE, vol=1)

    def test_chapter_count_and_titles(self):
        self.assertEqual(self.m["chapter_count"], 2)
        self.assertEqual([c["title"] for c in self.m["chapters"]], ["测试之章", "又一章"])

    def test_quadruple_and_line_numbering(self):
        # 章1：行1-2=段1，行3空，行4=段2，行5空
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
        self.assertIsNone(cc.locate_quote(self.m["blocks"], 1, 2, "第一段第二行"))  # 章号错→悬空
        self.assertIsNone(cc.locate_quote(self.m["blocks"], 1, 1, "不存在的引文"))

    def test_preamble_not_silently_dropped(self):
        m = cc.coordinate("散落前导文本\n\n<<<CHAPTER 0001 | 章>>>\n正文\n")
        self.assertEqual(m["chapters"][0]["chapter"], 0)
        self.assertIn("散落前导文本", m["chapters"][0]["paragraphs"][0]["text"])


class TestIdempotentCache(unittest.TestCase):
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
            self.assertEqual(a, b)  # 幂等：除命中标志外逐键一致

    def test_no_clock_fields(self):
        manifest = json.dumps(cc.coordinate(SAMPLE), ensure_ascii=False)
        for banned in ('"now"', '"timestamp"', '"created_at"', "datetime"):
            self.assertNotIn(banned, manifest)  # 确定性：无时钟字段


class TestThreeStateStub(unittest.TestCase):
    def test_write_and_skip_existing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rec = {"block_id": "v01c0001p0001", "text": "x"}
            p1, created1 = cc.three_state_write_stub(rec, root, "confirmed")
            p2, created2 = cc.three_state_write_stub(rec, root, "confirmed")
            self.assertTrue(created1)
            self.assertFalse(created2)  # 重跑零副作用
            self.assertEqual(p1, p2)
            self.assertTrue(p1.exists())

    def test_pools_isolated(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rec = {"record_id": "r1"}
            for st in ("confirmed", "provisional", "quarantine"):
                cc.three_state_write_stub(rec, root, st)
            self.assertEqual(sorted(p.name for p in root.iterdir()),
                             ["confirmed", "provisional", "quarantine"])
            with self.assertRaises(ValueError):
                cc.three_state_write_stub(rec, root, "candidate")  # 桩只收三态


if __name__ == "__main__":
    unittest.main(verbosity=2)
