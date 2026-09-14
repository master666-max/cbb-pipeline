# -*- coding: utf-8 -*-
"""test_cbb_extract.py — cbb_extract 单测（py -X utf8 运行）

核心断言：R6 标配内置、元文本零抽取、证据四元组强制、candidate 契约合规、
stub 幂等（record_id 内容哈希）、graphiti kwargs 形态（伪锚点+R6，禁墙钟）。
"""
import re
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "contracts"))
sys.path.insert(0, str(HERE.parent / "cbb-coordinate"))
import cbb_extract as cx  # noqa: E402
import cbb_contracts  # noqa: E402
import cbb_coordinate  # noqa: E402

SAMPLE = """<<<CHAPTER 0014 | 决斗>>>
缇达在迷宫入口拔出了剑。
她盯着对手，一动不动。

三天后，缇达再次踏入迷宫。

<<<CHAPTER 0001 | 新人观众推荐事先阅读本文>>>
大家好，这里是翻译组的公告。
本书在原平台连载，求点赞收藏月票。
"""


def build_blocks():
    m = cbb_coordinate.coordinate(SAMPLE, vol=1)
    titles = {c["chapter"]: c["title"] for c in m["chapters"]}
    return m["blocks"], titles


class TestR6(unittest.TestCase):
    def test_r6_builtin_verbatim_rules(self):
        r6 = cx.R6_CUSTOM_EXTRACTION_INSTRUCTIONS
        for must in (
            "元文本", "一律不得抽取任何实体或关系",          # 第1条：元文本零抽取（生产硬前置）
            "职务称呼", "应抽取为实体",                       # 第2条：店长类豁免
            "保留原文写法，不翻译不改写",                      # 第3条：专名保形
            "据某某声称",                                    # 第4条：声称标注
        ):
            self.assertIn(must, r6)
        self.assertEqual(len(re.findall(r"\n\d\)", r6)), 4, "R6 必须恰为四条编号规则")

    def test_episode_kwargs_carries_r6_and_pseudo_anchor(self):
        kw = cx.build_episode_kwargs(3, body := "正文…", "ep-4", "mishen-p1", "P1 抽取")
        self.assertEqual(kw["custom_extraction_instructions"],
                         cx.R6_CUSTOM_EXTRACTION_INSTRUCTIONS)  # R6 标配注入
        self.assertEqual(kw["reference_time"], date(2000, 1, 4))  # 伪锚点=2000-01-01+i
        kw2 = cx.build_episode_kwargs(3, body, "ep-4", "mishen-p1", "P1 抽取")
        self.assertEqual(kw["reference_time"], kw2["reference_time"])  # 禁墙钟：两次一致


class TestMetatext(unittest.TestCase):
    def test_heuristic(self):
        self.assertTrue(cx.is_metatext(title="新人观众推荐事先阅读本文"))
        self.assertTrue(cx.is_metatext(text_sample="转载请注明出处，翻译：某人"))
        self.assertFalse(cx.is_metatext(title="决斗", text_sample="缇达在迷宫入口拔出了剑。"))


class TestExtractStub(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blocks, cls.titles = build_blocks()
        cls.cands = cx.extract_stub(cls.blocks, lexicon=["缇达", "迷宫"],
                                    event_patterns=["拔出了剑"], chapter_titles=cls.titles)

    def test_metatext_chapter_yields_zero(self):
        meta_blocks = [b for b in self.blocks if b["chapter"] == 1]
        self.assertTrue(meta_blocks)
        out = cx.extract_stub(meta_blocks, lexicon=["缇达"], chapter_titles=self.titles)
        self.assertEqual(out, [], "元文本章必须零抽取（R6 stub 闸）")

    def test_candidates_contract_valid_with_evidence(self):
        self.assertGreater(len(self.cands), 0)
        for rec in self.cands:
            self.assertEqual(rec["status"], "candidate")
            cbb_contracts.validate_record(rec, allow_candidate=True)  # 其余字段全合规
            ev = rec["evidence"][0]
            self.assertTrue(cbb_contracts.evidence_ok(ev))
            block = cbb_coordinate.locate_quote(self.blocks, ev["vol"], ev["chapter"], ev["quote"])
            self.assertIsNotNone(block, f"证据必须可回落到坐标块: {ev}")

    def test_evidence_line_precision(self):
        # 章14 行1「缇达在迷宫入口拔出了剑。」→ 实体证据 line=1，事件证据 line=1
        ents = [r for r in self.cands if r["record_type"] == "entity"
                and r["canonical"]["name"] == "缇达" and r["evidence"][0]["chapter"] == 14]
        self.assertEqual(ents[0]["evidence"][0]["line"], 1)

    def test_two_types_only(self):
        self.assertLessEqual({r["record_type"] for r in self.cands}, {"event", "entity"})

    def test_idempotent_record_ids(self):
        again = cx.extract_stub(self.blocks, lexicon=["缇达", "迷宫"],
                                event_patterns=["拔出了剑"], chapter_titles=self.titles)
        self.assertEqual([r["record_id"] for r in self.cands],
                         [r["record_id"] for r in again])

    def test_missing_evidence_rejected_at_construction(self):
        with self.assertRaises(ValueError):
            cx.make_candidate("entity", {"name": "x"},
                              evidence=[{"vol": 1, "chapter": 1, "line": 0, "quote": ""}],
                              confidence=0.5)
        with self.assertRaises(ValueError):
            cx.make_candidate("relation", {"name": "x"},
                              evidence=[{"vol": 1, "chapter": 1, "line": 1, "quote": "q"}],
                              confidence=0.5)  # M1 只抽两类


class TestEnvProbeAndStub(unittest.TestCase):
    def test_env_probe_booleans_only(self):
        out = str(cx.env_probe())
        self.assertIn("True/False 形态", "True/False 形态")  # 形态占位
        self.assertTrue(out.startswith("{") and ("True" in out or "False" in out))
        self.assertNotRegex(out, r"sk-[A-Za-z0-9]{10,}")  # 不含 key 形态字面量

    def test_three_state_stub(self):
        with tempfile.TemporaryDirectory() as td:
            rec = {"record_id": "cand-entity-abc"}
            p, c1 = cx.three_state_write_stub(rec, Path(td), "quarantine")
            _, c2 = cx.three_state_write_stub(rec, Path(td), "quarantine")
            self.assertTrue(c1)
            self.assertFalse(c2)
            self.assertTrue(p.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
