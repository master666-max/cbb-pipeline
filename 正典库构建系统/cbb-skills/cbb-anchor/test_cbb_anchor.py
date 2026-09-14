# -*- coding: utf-8 -*-
"""test_cbb_anchor.py — cbb_anchor 单测（py -X utf8 运行）

含三类防线：伪锚点纯函数、**时间精度抽检电池**（下发单完成判据之一）、
禁墙钟静态+功能双检、锚点 Record 契约合规、版本化不覆盖。
"""
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cbb_anchor as ca

CTX = {"day_offset": 13, "precision": "day", "anchor_id": "anchor-v01c0014"}  # 第14章=序13


class TestPseudoAnchor(unittest.TestCase):
    def test_origin_and_leap_year(self):
        self.assertEqual(ca.pseudo_anchor(0), date(2000, 1, 1))
        self.assertEqual(ca.pseudo_anchor(31), date(2000, 2, 1))   # 闰年 1 月 31 天
        self.assertEqual(ca.pseudo_anchor(365), date(2000, 12, 31))

    def test_monotonic(self):
        days = [ca.pseudo_anchor(i) for i in range(50)]
        self.assertEqual(days, sorted(days))

    def test_no_wall_clock(self):
        src = Path(ca.__file__).read_text(encoding="utf-8")
        for banned in (".now(", ".today(", ".utcnow("):
            self.assertNotIn(banned, src, f"禁墙钟被违反：源码出现 {banned}")
        # 功能双检：伪锚点与归一化输出不含真实当前年份时间戳
        out = json.dumps(ca.normalize_relative("三天后", CTX), ensure_ascii=False)
        self.assertNotIn("2026", out)


class TestPrecisionSpotCheck(unittest.TestCase):
    """时间精度抽检电池（判据：cbb-anchor 过时间精度抽检）。

    每条 = 相对表述 × 上下文锚 → 期望(anchored, precision, day_offset/增量, flags)。
    """

    CASES = [
        ("次日",        CTX, dict(anchored=True, precision="day", day_offset=14)),
        ("第二天",      CTX, dict(anchored=True, precision="day", day_offset=14)),
        ("当晚",        CTX, dict(anchored=True, precision="day", day_offset=13)),
        ("三天后",      CTX, dict(anchored=True, precision="day", day_offset=16)),
        ("十天后",      CTX, dict(anchored=True, precision="day", day_offset=23)),
        ("二十五天后",  CTX, dict(anchored=True, precision="day", day_offset=38)),
        ("7天后",       CTX, dict(anchored=True, precision="day", day_offset=20)),
        ("两个月后",    CTX, dict(anchored=True, precision="month", month_delta=2)),
        ("半年后",      CTX, dict(anchored=True, precision="month", month_delta=6)),
        ("次年",        CTX, dict(anchored=True, precision="year", year_delta=1)),
        ("三年后",      CTX, dict(anchored=True, precision="year", year_delta=3)),
        ("那年冬天",    CTX, dict(anchored=True, precision="season", season="冬")),
        ("数日后",      CTX, dict(anchored=False, flags=["unresolved_time"])),
        ("几天后",      CTX, dict(anchored=False, flags=["unresolved_time"])),
        ("那天",        CTX, dict(anchored=False, flags=["ambiguous_reference"])),
        ("当时",        CTX, dict(anchored=False, flags=["ambiguous_reference"])),
        ("玄之又玄的表述", CTX, dict(anchored=False, flags=["unresolved_time"])),
        ("三天后",      None, dict(anchored=False, flags=["missing_anchor"])),
    ]

    def test_battery(self):
        failed = []
        for expr, ctx, expect in self.CASES:
            got = ca.normalize_relative(expr, ctx)
            for k, v in expect.items():
                actual = got.get(k) if k != "flags" else got["flags"]
                if actual != v:
                    failed.append(f"{expr!r}[{k}] 期望 {v!r} 实得 {actual!r}")
        self.assertEqual(failed, [], "时间精度抽检未过：\n" + "\n".join(failed))

    def test_month_not_folded_to_days(self):
        got = ca.normalize_relative("两个月后", CTX)
        self.assertIsNone(got.get("day_offset"))  # 月粒度不折天（保守纪律）


class TestCompare(unittest.TestCase):
    def test_day_precision_comparable(self):
        a = ca.normalize_relative("次日", CTX)
        b = ca.normalize_relative("三天后", CTX)
        self.assertEqual(ca.compare_story_time(a, b), -1)
        self.assertEqual(ca.compare_story_time(b, a), 1)
        self.assertEqual(ca.compare_story_time(a, a), 0)

    def test_coarse_precision_returns_none(self):
        a = ca.normalize_relative("次日", CTX)
        y = ca.normalize_relative("次年", CTX)
        self.assertIsNone(ca.compare_story_time(a, y))  # 粗精度宁缺毋滥


class TestAnchorRecords(unittest.TestCase):
    def test_tree_records_contract_valid(self):
        tree = ca.build_pseudo_tree([14, 38, 114])
        self.assertEqual(len(tree["anchors"]), 3)
        for rec in tree["anchors"]:
            self.assertEqual(rec["record_type"], "anchor")  # validate_record 已在构造内执行
        # 阅读序保序：第14章=day 0，第38章=day 1，第114章=day 2
        self.assertEqual([a["canonical"]["day_offset"] for a in tree["anchors"]], [0, 1, 2])
        self.assertEqual(tree["anchors"][0]["status"], "provisional")  # 人工前置：默认未确认

    def test_save_versioned_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            t1 = ca.build_pseudo_tree([14, 38], version=1)
            p1, c1 = ca.save_tree(t1, Path(td))
            p1b, c1b = ca.save_tree(t1, Path(td))          # 同版本重存 → 跳过
            t2 = ca.build_pseudo_tree([14, 38, 114], version=2)
            p2, c2 = ca.save_tree(t2, Path(td))            # 修订 → 新版本新文件
            self.assertTrue(c1)
            self.assertFalse(c1b)
            self.assertTrue(c2)
            self.assertNotEqual(p1, p2)
            latest = ca.load_latest_tree(Path(td))
            self.assertEqual(latest["version"], 2)


class TestThreeStateStub(unittest.TestCase):
    def test_anchor_record_routes(self):
        with tempfile.TemporaryDirectory() as td:
            rec = ca.build_pseudo_tree([14])["anchors"][0]
            for st in ("provisional", "confirmed"):
                path, created = ca.three_state_write_stub(rec, Path(td) / "sink", st)
                self.assertTrue(created)
            _, again = ca.three_state_write_stub(rec, Path(td) / "sink", "provisional")
            self.assertFalse(again)  # 重跑零副作用


if __name__ == "__main__":
    unittest.main(verbosity=2)
