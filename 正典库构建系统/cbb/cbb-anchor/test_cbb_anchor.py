# -*- coding: utf-8 -*-
"""test_cbb_anchor.py — cbb_anchor v2 单测（py -X utf8 运行）

三类防线（保留）：伪锚点纯函数、**时间精度抽检电池 18 条**（回归判据）、
禁墙钟静态+功能双检、锚点 Record 契约合规（v2.0）、版本化不覆盖。
v2 新增：双时间轴（tick 单调/instant 可回退/time 不参与排序/as-of 双语义/
缺坐标判不可见）、倒计时到点兑现、章号轴回放降级。
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
        out = json.dumps(ca.normalize_relative("三天后", CTX), ensure_ascii=False)
        self.assertNotIn("2026", out)


class TestPrecisionSpotCheck(unittest.TestCase):
    """时间精度抽检电池 18 条（v1.0 保留面回归判据——原文逐条不动）。
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

    def test_battery_count_18(self):
        self.assertEqual(len(self.CASES), 18)  # 判据锚：18 条不许缩水

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
    def test_tree_records_contract_valid_v2(self):
        va = {"path": "mepub/v1", "sha": "3f160cb9a45d", "verified_at": "2026-09-15"}
        tree = ca.build_pseudo_tree([14, 38, 114], verified_against=va)
        self.assertEqual(len(tree["anchors"]), 3)
        for rec in tree["anchors"]:
            self.assertEqual(rec["record_type"], "anchor")  # validate_record 已在构造内执行（v2.0）
        # 摄入序保序 + 双时间轴字段：tick=摄入序，instant=None（伪锚点不自充故事时间）
        self.assertEqual([a["canonical"]["tick"] for a in tree["anchors"]], [0, 1, 2])
        self.assertEqual([a["canonical"]["instant"] for a in tree["anchors"]], [None, None, None])
        self.assertEqual(tree["anchors"][0]["verified_against"], va)
        self.assertEqual(tree["anchors"][0]["status"], "provisional")  # 人工前置：默认未确认

    def test_placeholder_verified_against_still_valid(self):
        rec = ca.make_anchor_record(14, 0)  # 未传 verified_against → 占位三件套
        self.assertEqual(rec["verified_against"]["verified_at"], "1970-01-01")

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


class TestDualTimeline(unittest.TestCase):
    """v2 双时间轴：tick 单调 / instant 可回退 / time 不参与排序 / as-of 双语义 / 缺坐标不可见。"""

    def setUp(self):
        # 倒叙样本：摄入序 tick 0..4；第4条（tick=3）是回忆章——instant 后退到 2
        self.tl = ca.build_timeline([
            {"entry_id": "e1", "tick": 0, "instant": 10, "time": "第一天"},
            {"entry_id": "e2", "tick": 1, "instant": 11, "time": "次日"},
            {"entry_id": "e3", "tick": 2, "instant": 15, "time": "四天后"},
            {"entry_id": "e4", "tick": 3, "instant": 2,  "time": "那年冬天（回忆）"},  # 倒叙：tick 增 instant 退
            {"entry_id": "e5", "tick": 4, "instant": None, "time": "某个雨夜"},        # 缺坐标
        ])

    def test_tick_must_be_strictly_increasing(self):
        with self.assertRaises(ValueError):
            ca.build_timeline([{"entry_id": "a", "tick": 1}, {"entry_id": "b", "tick": 1}])  # 重复
        with self.assertRaises(ValueError):
            ca.build_timeline([{"entry_id": "a", "tick": 2}, {"entry_id": "b", "tick": 1}])  # 回退
        bad = ca.build_timeline([{"entry_id": "a", "tick": 0}])  # 合法单条
        self.assertEqual(len(bad), 1)

    def test_instant_regression_allowed(self):
        # 倒叙合法：e4 tick=3 > e3 tick=2 而 instant 2 < 15——这正是必须双轴的原因
        self.assertEqual(self.tl[3]["instant"], 2)
        self.assertLess(self.tl[3]["instant"], self.tl[2]["instant"])
        self.assertGreater(self.tl[3]["tick"], self.tl[2]["tick"])

    def test_asof_tick_knowledge_boundary(self):
        got = ca.asof(self.tl, as_of_tick=2)
        self.assertEqual([e["entry_id"] for e in got], ["e1", "e2", "e3"])  # 叙事推进到 tick2 已知的

    def test_asof_instant_world_state(self):
        got = ca.asof(self.tl, as_of_instant=15)
        self.assertEqual([e["entry_id"] for e in got], ["e1", "e2", "e3", "e4"])
        # e4 是回忆章：instant=2 ≤ 15 → 世界状态里可见（即使叙事摄入更晚）

    def test_missing_coordinate_invisible(self):
        got = ca.asof(self.tl, as_of_instant=999)  # 全开窗
        self.assertNotIn("e5", [e["entry_id"] for e in got])  # 缺坐标判不可见——宁可漏召回不可泄漏
        got_all = ca.asof(self.tl)  # 双空=全知
        self.assertEqual(len(got_all), 5)

    def test_asof_both_and(self):
        got = ca.asof(self.tl, as_of_tick=3, as_of_instant=11)
        # e4 instant=2≤11 但 tick=3≤3 ✓ → 在；e3 tick=2≤3 但 instant=15>11 → 不在
        self.assertEqual([e["entry_id"] for e in got], ["e1", "e2", "e4"])

    def test_story_order_restores_flashback(self):
        order = ca.story_order(self.tl)
        self.assertEqual([e["entry_id"] for e in order], ["e4", "e1", "e2", "e3", "e5"])
        # 倒叙还原：e4（回忆 instant=2）排最前；缺坐标 e5 沉底保持 tick 序

    def test_time_never_participates_in_sorting(self):
        # 同 instant 不同 time 字符串 → 排序稳定不因 time 变化（time 不可比较）
        tl2 = ca.build_timeline([
            {"entry_id": "a", "tick": 0, "instant": 5, "time": "乙日"},
            {"entry_id": "b", "tick": 1, "instant": 5, "time": "甲日"},
        ])
        self.assertEqual([e["entry_id"] for e in ca.story_order(tl2)], ["a", "b"])

    def test_replay_chapter_axis_fallback(self):
        # 章号轴回放：instant 缺失也不影响按 tick 的时序回放（降级方案）
        rp = ca.replay(self.tl)
        self.assertEqual([e["entry_id"] for e in rp], ["e1", "e2", "e3", "e4", "e5"])
        rp_upto = ca.replay(self.tl, upto_tick=2)
        self.assertEqual([e["entry_id"] for e in rp_upto], ["e1", "e2", "e3"])

    def test_instant_from_relative_day_only(self):
        got = ca.instant_from_relative("三天后", CTX)
        self.assertEqual(got["instant"], 16)          # day 精度 → instant 可得
        self.assertEqual(got["time"], "三天后")        # 原文 verbatim
        coarse = ca.instant_from_relative("两年后", CTX)
        self.assertIsNone(coarse["instant"])           # 粗精度不冒充 instant
        flagged = ca.instant_from_relative("那天", CTX)
        self.assertEqual(flagged["flags"], ["ambiguous_reference"])


class TestCountdowns(unittest.TestCase):
    """倒计时到点兑现（chinese-webnovel 吸收）。"""

    CDS = [
        {"key": "burned-letter", "due_tick": 5, "resolved_tick": None},
        {"key": "kira-rescue", "due_tick": 2, "resolved_tick": 3},   # 已兑现
        {"key": "lineage", "due_tick": 10, "resolved_tick": None},
    ]

    def test_not_due_before(self):
        self.assertEqual(ca.countdowns_due(self.CDS, at_tick=4), [])

    def test_due_at_and_after(self):
        due5 = ca.countdowns_due(self.CDS, at_tick=5)
        self.assertEqual([c["key"] for c in due5], ["burned-letter"])  # 到点即浮出；已兑现不算
        due12 = ca.countdowns_due(self.CDS, at_tick=12)
        self.assertEqual([c["key"] for c in due12], ["burned-letter", "lineage"])  # 超期持续浮出


if __name__ == "__main__":
    unittest.main(verbosity=2)
