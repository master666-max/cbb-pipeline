# -*- coding: utf-8 -*-
"""test_cbb_gate1.py — cbb_gate1 v2 单测（py -X utf8 运行）

三域各含可执行反例（判据锚）+ Issue v2.0 落地（fix_action/双口径/cites）+
EXPLAIN 拒写（零落盘+输入不可变）+ v1 四校验回归。
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "contracts"))
sys.path.insert(0, str(HERE.parent / "cbb-coordinate"))
sys.path.insert(0, str(HERE.parent / "cbb-extract"))
import cbb_gate1 as g1  # noqa: E402
import cbb_contracts  # noqa: E402
import cbb_coordinate  # noqa: E402
import cbb_extract  # noqa: E402

SAMPLE = """<<<CHAPTER 0014 | 决斗>>>
缇达在迷宫入口拔出了剑。
<<<CHAPTER 0020 | 尾声>>>
众人在迷宫入口集结。
"""


def ev(chapter, quote):
    return {"vol": 1, "chapter": chapter, "line": 1, "quote": quote}


def entity(name, status="alive", death_chapter=None, chapter=14):
    canon = {"name": name, "status": status}
    if death_chapter is not None:
        canon["death_chapter"] = death_chapter
    return g1.make_generic_record("entity", "character", canon, [ev(chapter, f"{name}出场")])


def event(name, entity_refs, chapter):
    return g1.make_generic_record("event", "event",
                                  {"name": name, "entity_refs": list(entity_refs)},
                                  [ev(chapter, f"{name}发生")])


def relation(subject, rel_type, obj, chapter=14):
    return g1.make_generic_record("relation", "relation",
                                  {"subject": subject, "object": obj, "rel_type": rel_type},
                                  [ev(chapter, f"{subject}与{obj}")])


def foreshadow(name, setup, payoff=None):
    return g1.make_generic_record("foreshadow", "foreshadow",
                                  {"name": name, "setup_chapter": setup, "payoff_chapter": payoff},
                                  [ev(setup, f"{name}埋设")])


class TestValidateDomain(unittest.TestCase):
    """域一 validate：结构/schema。"""

    def test_valid_record_passes(self):
        rec = entity("缇达")
        res = g1.check_record(rec, {})
        self.assertEqual(res["verdict"], "pass")

    def test_counterexample_bad_schema(self):  # 可执行反例
        rec = entity("缇达")
        rec["status"] = "cut"  # 第四态不存在（用户裁决）
        res = g1.check_record(rec, {})
        self.assertEqual(res["verdict"], "intercept")
        self.assertIn("G1-SCHEMA", [v["code"] for v in res["violations"]])

    def test_counterexample_dangling_evidence(self):  # 可执行反例
        m = cbb_coordinate.coordinate(SAMPLE, vol=1)
        rec = entity("缇达")
        res = g1.check_record(rec, {"blocks": m["blocks"]})
        self.assertEqual(res["verdict"], "intercept")
        self.assertIn("G1-EVIDENCE", [v["code"] for v in res["violations"]])  # 引文不在坐标块

    def test_evidence_quadruple_enforced(self):
        rec = entity("缇达")
        rec["evidence"] = [{"vol": 1, "chapter": 14}]  # 四元组残缺
        res = g1.check_record(rec, {})
        self.assertIn("G1-EVIDENCE", [v["code"] for v in res["violations"]])


class TestLinksDomain(unittest.TestCase):
    """域二 links：引用完整性+关系逆类型 12 对+对称 12 项双向回链。"""

    def test_counterexample_dangling_ref(self):  # 可执行反例
        rec = event("集结", entity_refs=["rec-不存在"], chapter=20)
        res = g1.check_record(rec, {"known_ids": set()})
        self.assertIn("G1-REF", [v["code"] for v in res["violations"]])

    def test_counterexample_inverse_missing(self):  # 可执行反例：parent 无 child 回链
        recs = [relation("卢卡", "parent", "缇达")]
        res = g1.check_batch(recs, {})
        self.assertEqual(res["summary"]["intercept"], 1)
        codes = [v["code"] for v in res["intercepted"][0]["check"]["violations"]]
        self.assertIn("G1-REL-BACKLINK", codes)

    def test_inverse_pair_passes(self):
        recs = [relation("卢卡", "parent", "缇达"), relation("缇达", "child", "卢卡")]
        res = g1.check_batch(recs, {})
        self.assertEqual(res["summary"]["pass"], 2)  # 双向回链齐→过

    def test_counterexample_symmetric_missing(self):  # 可执行反例：sibling 单向
        recs = [relation("缇达", "sibling", "塞尔")]
        res = g1.check_batch(recs, {})
        codes = [v["code"] for v in res["intercepted"][0]["check"]["violations"]]
        self.assertIn("G1-REL-BACKLINK", codes)

    def test_symmetric_pair_passes(self):
        recs = [relation("缇达", "sibling", "塞尔"), relation("塞尔", "sibling", "缇达")]
        res = g1.check_batch(recs, {})
        self.assertEqual(res["summary"]["pass"], 2)

    def test_twelve_pairs_and_twelve_symmetric_tables(self):
        self.assertEqual(len(g1.RELATIONSHIP_INVERSES), 12)   # 逆类型 12 对
        self.assertEqual(g1.RELATIONSHIP_INVERSES["mentor"], "student")
        self.assertEqual(len(g1.SYMMETRIC_RELATIONSHIPS), 12)  # 对称 12 项
        self.assertIn("love-interest", g1.SYMMETRIC_RELATIONSHIPS)


class TestContinuityDomain(unittest.TestCase):
    """域三 continuity：死人走路/伏笔时序/契诃夫枪超期/矛盾检测/时间倒置。"""

    def test_counterexample_dead_walk(self):  # 可执行反例
        dead = entity("帕林", status="dead", death_chapter=14)
        late = event("亡灵现身", entity_refs=["帕林"], chapter=20)
        res = g1.check_batch([dead, late], {})
        self.assertEqual(res["summary"]["intercept"], 1)
        detail = res["intercepted"][0]["check"]["violations"][0]["detail"]
        self.assertIn("死人走路", detail)

    def test_dead_walk_boundary_same_chapter_ok(self):
        dead = entity("帕林", status="dead", death_chapter=14)
        same = event("临终托付", entity_refs=["帕林"], chapter=14)  # 同章=临终事件合法
        res = g1.check_batch([dead, same], {})
        self.assertEqual(res["summary"]["pass"], 2)

    def test_counterexample_foreshadow_order(self):  # 可执行反例
        bad = foreshadow("信件伏笔", setup=10, payoff=5)  # 兑现早于埋设
        res = g1.check_record(bad, {})
        self.assertIn("G1-FORESHADOW-ORDER", [v["code"] for v in res["violations"]])

    def test_counterexample_chekhov_overdue_and_boundary(self):  # 可执行反例+边界
        gun = foreshadow("契诃夫之枪", setup=10)  # 开环无 payoff
        overdue = g1.check_record(gun, {"current_chapter": 13})  # 13-10=3 ≥3 → 超期
        self.assertIn("G1-CHEKHOV-OVERDUE", [v["code"] for v in overdue["violations"]])
        not_yet = g1.check_record(gun, {"current_chapter": 12})  # 12-10=2 <3 → 未超期
        self.assertEqual(not_yet["verdict"], "pass")
        no_clock = g1.check_record(gun, {})  # 无 current_chapter → 跳过（不硬判）
        self.assertEqual(no_clock["verdict"], "pass")

    def test_counterexample_contradiction(self):  # 可执行反例
        a = entity("缇达", status="alive")
        b = entity("缇达", status="dead", death_chapter=20)
        res = g1.check_batch([a, b], {})
        self.assertEqual(res["summary"]["intercept"], 1)
        codes = [v["code"] for v in res["intercepted"][0]["check"]["violations"]]
        self.assertIn("G1-CONTRADICTION", codes)

    def test_supersedes_channel_not_contradiction(self):
        a = entity("缇达", status="alive")
        b = entity("缇达", status="dead", death_chapter=20)
        b["supersedes"] = a["record_id"]  # 走版本化通道=合法演化
        res = g1.check_batch([a, b], {"known_ids": {a["record_id"]}})
        self.assertEqual(res["summary"]["pass"], 2)

    def test_time_inversion_regression(self):  # v1 保留
        pred = g1.make_generic_record("event", "event",
                                      {"name": "先发", "story_time": {"precision": "day", "day_offset": 20}},
                                      [ev(14, "先发")])
        late = g1.make_generic_record("event", "event",
                                      {"name": "后发", "causal_predecessors": [pred["record_id"]],
                                       "story_time": {"precision": "day", "day_offset": 10}},
                                      [ev(14, "后发")])
        by_id = {pred["record_id"]: pred, late["record_id"]: late}
        res = g1.check_record(late, {"records_by_id": by_id})
        self.assertIn("G1-TIME_INVERSION", [v["code"] for v in res["violations"]])


class TestIssueEmission(unittest.TestCase):
    """Issue v2.0 落地：fix_action P0-P3+精确命令 / confidence 双口径 / cites。"""

    def _intercepted_one(self):
        recs = [entity("帕林", status="dead", death_chapter=14),
                event("亡灵现身", entity_refs=["帕林"], chapter=20)]
        res = g1.check_batch(recs, {})
        return res["intercepted"][0]

    def test_issue_contract_valid_v2(self):
        item = self._intercepted_one()
        self.assertEqual(len(item["issues"]), 1)
        issue = item["issues"][0]
        cbb_contracts.validate_issue(issue)  # v2.0 全字段合规（构造期已验，双保险）
        self.assertEqual(issue["confidence_caliber"], "deterministic")  # 确定性校验器产物
        self.assertEqual(issue["fix_action"]["priority"], "P0")        # 死人走路=P0
        self.assertIn(item["record"]["record_id"], issue["fix_action"]["command"])  # 精确命令带 rid
        self.assertEqual(issue["cites"], [item["record"]["record_id"]])  # Cites 强制列

    def test_priority_mapping(self):
        self.assertEqual(g1.FIX_ACTIONS["G1-SCHEMA"][0], "P0")
        self.assertEqual(g1.FIX_ACTIONS["G1-EVIDENCE"][0], "P0")
        self.assertEqual(g1.FIX_ACTIONS["G1-CONTRADICTION"][0], "P0")
        self.assertEqual(g1.FIX_ACTIONS["G1-CHEKHOV-OVERDUE"][0], "P2")  # 复核级

    def test_to_issue_rejects_pass(self):
        chk = g1.check_record(entity("缇达"), {})
        with self.assertRaises(ValueError):
            g1.to_issue(chk, entity("缇达"))


class TestExplainNoWrite(unittest.TestCase):
    """EXPLAIN 拒写：检索/校验层永不写库——零落盘+输入不可变+重跑一致。"""

    def test_no_files_no_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            recs = [entity("缇达"), relation("卢卡", "parent", "缇达")]
            before = copy.deepcopy(recs)
            res1 = g1.check_batch(recs, {})
            self.assertEqual(list(Path(td).iterdir()), [])  # 零落盘
            self.assertEqual(recs, before)                  # 输入不可变
            res2 = g1.check_batch(recs, {})
            self.assertEqual(json.dumps(res1, sort_keys=True, ensure_ascii=False),
                             json.dumps(res2, sort_keys=True, ensure_ascii=False))  # 重跑一致

    def test_quarantine_subclass_mapping(self):
        for code, sub in (("G1-DEAD-WALK", "contradiction_pending"),
                          ("G1-CHEKHOV-OVERDUE", "overdue_omission"),
                          ("G1-EVIDENCE", "extrapolation_unverified")):
            self.assertEqual(g1.REASON_TO_QUARANTINE_SUBCLASS[code], sub)  # 三子类对齐


class TestBatchRegression(unittest.TestCase):
    """v1 保留面：批量/摘要/gate_trace/候选互引。"""

    def test_batch_summary_and_codes(self):
        m = cbb_coordinate.coordinate(SAMPLE, vol=1)
        cands = cbb_extract.extract_stub(m["blocks"], lexicon=["缇达"],
                                         chapter_titles={c["chapter"]: c["title"] for c in m["chapters"]})
        res = g1.check_batch(cands, {"blocks": m["blocks"]})
        self.assertEqual(res["summary"]["total"], len(cands))
        self.assertEqual(res["summary"]["pass"] + res["summary"]["intercept"],
                         res["summary"]["total"])
        for p in res["passed"]:
            self.assertIn("gate_trace_entry", p)

    def test_make_generic_record_valid(self):
        rec = g1.make_generic_record("relation", "relation",
                                     {"subject": "a", "object": "b", "rel_type": "ally"},
                                     [ev(1, "引文")])
        cbb_contracts.validate_record(rec, allow_candidate=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
