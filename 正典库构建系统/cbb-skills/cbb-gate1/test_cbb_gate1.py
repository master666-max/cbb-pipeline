# -*- coding: utf-8 -*-
"""test_cbb_gate1.py — cbb_gate1 单测（py -X utf8 运行）

断言：好件放行；四类缺陷各自命中原因码；粗精度时间不硬判（保守）；
判定确定性（verdict_id 可重放）；拦截→隔离分组映射；批量互引合法。
"""
import copy
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "contracts"))
sys.path.insert(0, str(HERE.parent / "cbb-coordinate"))
import cbb_gate1 as g1  # noqa: E402
import cbb_coordinate  # noqa: E402

SRC = """<<<CHAPTER 0014 | 决斗>>>
缇达在迷宫入口拔出了剑。
剑光一闪。
"""

BLOCKS = cbb_coordinate.coordinate(SRC, vol=1)["blocks"]


def good_candidate(**over):
    rec = {
        "record_id": "cand-event-aaaa",
        "record_type": "event",
        "library": "event",
        "status": "candidate",
        "canonical": {"name": "决斗开始", "trigger": "拔出了剑", "story_time": None,
                      "causal_predecessors": []},
        "evidence": [{"vol": 1, "chapter": 14, "line": 1, "quote": "缇达在迷宫入口拔出了剑。"}],
        "provenance": {"extractor_confidence": 0.8, "gate_trace": [],
                       "precedent_refs": [], "status_history": []},
        "version": 1, "supersedes": None,
    }
    rec.update(over)
    return rec


CTX = {"blocks": BLOCKS}


class TestPass(unittest.TestCase):
    def test_good_passes(self):
        chk = g1.check_record(good_candidate(), CTX)
        self.assertEqual(chk["verdict"], "pass")
        self.assertEqual(chk["violations"], [])
        self.assertEqual(chk["gate_trace_entry"]["gate"], "1")

    def test_deterministic_verdict_id(self):
        a = g1.check_record(good_candidate(), CTX)
        b = g1.check_record(good_candidate(), CTX)
        self.assertEqual(a["gate_trace_entry"]["verdict_id"],
                         b["gate_trace_entry"]["verdict_id"])


class TestIntercepts(unittest.TestCase):
    def test_schema_violation(self):
        bad = good_candidate()
        bad.pop("canonical")
        chk = g1.check_record(bad, CTX)
        self.assertEqual(chk["verdict"], "intercept")
        self.assertEqual(chk["violations"][0]["code"], "G1-SCHEMA")
        self.assertEqual(chk["quarantine_group"], "low_confidence")

    def test_dangling_quote(self):
        bad = good_candidate(evidence=[{"vol": 1, "chapter": 14, "line": 9, "quote": "不存在的引文"}])
        codes = [v["code"] for v in g1.check_record(bad, CTX)["violations"]]
        self.assertIn("G1-EVIDENCE", codes)

    def test_bad_chapter_dangling(self):
        bad = good_candidate(evidence=[{"vol": 1, "chapter": 99, "line": 1, "quote": "缇达在迷宫入口拔出了剑。"}])
        codes = [v["code"] for v in g1.check_record(bad, CTX)["violations"]]
        self.assertIn("G1-EVIDENCE", codes)  # 章 99 不存在 → 悬空

    def test_dangling_reference(self):
        bad = good_candidate(canonical={"name": "x", "trigger": "t", "story_time": None,
                                        "causal_predecessors": ["ghost-id"]})
        chk = g1.check_record(bad, {**CTX, "known_ids": set()})
        codes = [v["code"] for v in chk["violations"]]
        self.assertIn("G1-REF", codes)
        self.assertEqual(chk["quarantine_group"], "ambiguous_reference")

    def test_time_inversion_day_precision(self):
        preds = {"p1": good_candidate(record_id="p1",
                                      canonical={"name": "前事", "story_time":
                                                 {"precision": "day", "day_offset": 9}})}
        bad = good_candidate(canonical={"name": "后事",
                                        "story_time": {"precision": "day", "day_offset": 5},
                                        "causal_predecessors": ["p1"]})
        chk = g1.check_record(bad, {**CTX, "records_by_id": preds})
        codes = [v["code"] for v in chk["violations"]]
        self.assertIn("G1-TIME_INVERSION", codes)
        self.assertEqual(chk["quarantine_group"], "unresolved_time")

    def test_coarse_time_not_judged(self):
        preds = {"p1": good_candidate(record_id="p1",
                                      canonical={"name": "前事", "story_time":
                                                 {"precision": "year", "year_delta": 1}})}
        rec = good_candidate(canonical={"name": "后事",
                                        "story_time": {"precision": "day", "day_offset": 5},
                                        "causal_predecessors": ["p1"]})
        chk = g1.check_record(rec, {**CTX, "records_by_id": preds})
        self.assertEqual(chk["verdict"], "pass")  # 前驱粗精度不可比 → 保守放行给门2/人工

    def test_unresolvable_pred_not_judged(self):
        rec = good_candidate(canonical={"name": "事", "story_time": {"precision": "day", "day_offset": 1},
                                        "causal_predecessors": ["unknown-pred"]})
        chk = g1.check_record(rec, {**CTX, "known_ids": set(), "records_by_id": {}})
        codes = [v["code"] for v in chk["violations"]]
        self.assertIn("G1-REF", codes)      # 悬空引用照拦
        self.assertNotIn("G1-TIME_INVERSION", codes)  # 但不冒充时间倒置判定


class TestBatch(unittest.TestCase):
    def test_mixed_batch_and_cross_reference(self):
        a = good_candidate(record_id="cand-a")
        b = good_candidate(record_id="cand-b",
                           canonical={"name": "后事", "story_time": {"precision": "day", "day_offset": 4},
                                      "causal_predecessors": ["cand-a"]})
        a["canonical"] = {"name": "前事", "story_time": {"precision": "day", "day_offset": 0}}
        bad = good_candidate(record_id="cand-c",
                             evidence=[{"vol": 1, "chapter": 14, "line": 1, "quote": "悬空quote"}])
        result = g1.check_batch([a, b, bad], {"blocks": BLOCKS, "known_ids": set()})
        self.assertEqual(result["summary"]["total"], 3)
        self.assertEqual(result["summary"]["pass"], 2)      # a、b 互引在同批合法
        self.assertEqual(result["summary"]["intercept"], 1)
        self.assertEqual(result["summary"]["by_code"]["G1-EVIDENCE"], 1)

    def test_batch_idempotent(self):
        cands = [good_candidate()]
        r1 = g1.check_batch(cands, CTX)
        r2 = g1.check_batch(cands, CTX)
        self.assertEqual(r1["summary"], r2["summary"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
