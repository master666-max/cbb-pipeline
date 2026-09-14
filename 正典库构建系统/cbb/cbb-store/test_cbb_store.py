# -*- coding: utf-8 -*-
"""test_cbb_store.py — cbb_store v2 单测（py -X utf8 运行）

判据锚：双轨分流（一致重复上调合并/矛盾隔离+Verdict 不静默合并）+约束防重+漂移钩子。
保留面：三态写入/旁车迁移/幂等/supersede 版本化/置信度路由。
新增：UNIQUE 约束族/时序回放/写入安全围栏/multiversion 四动作合并。
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "contracts"))
sys.path.insert(0, str(HERE.parent / "cbb-quarantine"))
sys.path.insert(0, str(HERE.parent / "cbb-gate1"))
import cbb_store as cs  # noqa: E402
import cbb_contracts  # noqa: E402
import cbb_gate1  # noqa: E402


def make_store():
    td = tempfile.TemporaryDirectory()
    store = cs.ThreeStateStore(Path(td.name))
    return store, td


def entity_rec(name, status="alive", conf=80, rid=None, chapter=14):
    rec = cbb_gate1.make_generic_record(
        "entity", "character", {"name": name, "status": status},
        [{"vol": 1, "chapter": chapter, "line": 1, "quote": f"{name}出场"}],
        confidence=conf)
    if rid:
        rec["record_id"] = rid
    return rec


def relation_rec(subject, rel_type, obj, rid=None):
    rec = cbb_gate1.make_generic_record(
        "relation", "relation", {"subject": subject, "rel_type": rel_type, "object": obj},
        [{"vol": 1, "chapter": 14, "line": 2, "quote": f"{subject}与{obj}"}],
        confidence=75)
    if rid:
        rec["record_id"] = rid
    return rec


class TestRouteAndAdmit(unittest.TestCase):
    """保留面：置信度路由+三态写入。"""

    def test_route_by_confidence(self):
        self.assertEqual(cs.route_by_confidence(0.99), "provisional")  # confirmed 永不因置信度单独达成
        self.assertEqual(cs.route_by_confidence(0.10), "quarantine")

    def test_admit_three_states(self):
        store, td = make_store()
        self.addCleanup(td.cleanup)
        rec = entity_rec("缇达", rid="rec-a")
        p, created = store.admit(rec, "provisional")
        self.assertTrue(created and p.exists())
        _, again = store.admit(rec, "provisional")
        self.assertFalse(again)  # 已存在即跳过（文件写后不改）
        iid, created_q = store.admit(entity_rec("低信", conf=10, rid="rec-q"), "quarantine")
        self.assertTrue(created_q)
        self.assertTrue(iid.startswith("q-"))                      # 隔离区条目在册
        self.assertEqual(len(store.zone.pending()), 1)


class TestDualTrack(unittest.TestCase):
    """双轨合并（判据①）。"""

    def test_on_create_when_no_existing(self):
        store, td = make_store()
        self.addCleanup(td.cleanup)
        res = store.dual_track(entity_rec("缇达", rid="obs-1"))
        self.assertEqual(res["track"], "on-create")
        self.assertTrue(res["created"])

    def test_consistent_duplicate_confidence_bump_and_union(self):
        store, td = make_store()
        self.addCleanup(td.cleanup)
        first = entity_rec("缇达", conf=80, rid="obs-1")
        store.dual_track(first)
        second = entity_rec("缇达", conf=84, rid="obs-2")  # 同名同字段、不同观察、新证据行
        second["evidence"] = [{"vol": 1, "chapter": 20, "line": 3, "quote": "缇达再次出场"}]
        res = store.dual_track(second)
        self.assertEqual(res["track"], "consistent-duplicate")
        self.assertAlmostEqual(res["confidence"], 86.0)  # max(80,84)+2.0 上调
        latest = store.resolve_latest("obs-1")
        self.assertEqual(latest["record_id"], "obs-1-m")          # supersede 新版本
        self.assertEqual(latest["supersedes"], "obs-1")
        self.assertEqual(len(latest["evidence"]), 2)              # 证据并集
        self.assertEqual(latest["version"], 2)

    def test_contradiction_quarantine_and_verdict_not_silent_merge(self):
        store, td = make_store()
        self.addCleanup(td.cleanup)
        store.dual_track(entity_rec("缇达", status="alive", rid="obs-1"))
        res = store.dual_track(entity_rec("缇达", status="dead", rid="obs-2"))
        self.assertEqual(res["track"], "contradiction")
        self.assertIsNotNone(res["quarantine_item"])              # 进隔离区
        cbb_contracts.validate_verdict(res["verdict"])            # 契约合规裁决文书（构造期已验，双保险）
        self.assertEqual(res["verdict"]["label"], "conflict")
        self.assertEqual(res["verdict"]["rule_applied"]["school"], "documented_variance")  # 并陈
        # 不静默合并：库内无 obs-2，隔离区一条矛盾待裁决
        self.assertIsNone(store._find("obs-2"))
        subs = store.zone.by_subclass()
        self.assertEqual(subs["contradiction_pending"], 1)

    def test_relation_triple_dual_track(self):
        store, td = make_store()
        self.addCleanup(td.cleanup)
        store.dual_track(relation_rec("卢卡", "parent", "缇达", rid="rel-1"))
        self.assertTrue(store.relation_triple_exists("卢卡", "parent", "缇达"))  # 三元组已占
        res = store.dual_track(relation_rec("卢卡", "parent", "缇达", rid="rel-2"))
        self.assertEqual(res["track"], "consistent-duplicate")    # 同三元组=一致重复（ON MATCH）


class TestUniqueConstraints(unittest.TestCase):
    """UNIQUE 约束族（判据②：schema 层防重）。"""

    def test_alias_composite_pk(self):
        store, td = make_store()
        self.addCleanup(td.cleanup)
        k1, c1 = store.register_alias("小缇", "ent-1", "character")
        k2, c2 = store.register_alias("小缇", "ent-1", "character")
        self.assertEqual((k1, c1, c2), (k2, True, False))          # 同复合键只登记一次
        k3, c3 = store.register_alias("小缇", "ent-2", "character")
        self.assertTrue(c3)                                        # 同名不同实体=不同键（别名歧义合法，裁决归 gate/P3）
        k4, c4 = store.register_alias("小缇", "ent-1", "faction")
        self.assertTrue(c4)                                        # 同名同 id 不同类型=不同键

    def test_appearance_unique_entity_chapter(self):
        store, td = make_store()
        self.addCleanup(td.cleanup)
        k1, c1 = store.record_appearance("缇达", 14)
        _, c2 = store.record_appearance("缇达", 14)
        _, c3 = store.record_appearance("缇达", 15)
        _, c4 = store.record_appearance("卢卡", 14)
        self.assertEqual((c1, c2, c3, c4), (True, False, True, True))

    def test_constraints_declared(self):
        self.assertEqual(len(cs.UNIQUE_CONSTRAINTS), 3)  # 别名 PK/关系三元组/出场


class TestDriftHook(unittest.TestCase):
    """verified_against 漂移钩子（判据③）。"""

    def test_drift_check_stale(self):
        store, td = make_store()
        self.addCleanup(td.cleanup)
        rec = entity_rec("缇达", rid="dr-1")
        rec["verified_against"] = {"path": "mepub/v1/ch14.md", "sha": "aaa0000", "verified_at": "2026-09-01"}
        store.admit(rec, "provisional")
        fresh = store.drift_check(store._find("dr-1"), "aaa0000")
        self.assertFalse(fresh["stale"])                          # SHA 未变=新鲜
        stale = store.drift_check(store._find("dr-1"), "bbb1111")
        self.assertTrue(stale["stale"])                           # 源变更=stale 须重验

    def test_stale_records_scan(self):
        store, td = make_store()
        self.addCleanup(td.cleanup)
        rec = entity_rec("缇达", rid="dr-1")
        rec["verified_against"] = {"path": "mepub/v1/ch14.md", "sha": "aaa0000", "verified_at": "2026-09-01"}
        store.admit(rec, "provisional")
        self.assertEqual(store.stale_records({"mepub/v1/ch14.md": "aaa0000"}), [])
        stale = store.stale_records({"mepub/v1/ch14.md": "zzz9999"})
        self.assertEqual([d["record_id"] for d in stale], ["dr-1"])


class TestReplay(unittest.TestCase):
    """时序回放：state_changes 追加日志+chapter<=? 顺序覆盖。"""

    def test_entity_state_at_chapter(self):
        store, td = make_store()
        self.addCleanup(td.cleanup)
        store.log_state_change("缇达", "location", "迷宫入口", chapter=5)
        store.log_state_change("缇达", "location", "地下城三层", chapter=10)
        store.log_state_change("缇达", "status", "重伤", chapter=10)
        self.assertEqual(store.entity_state_at_chapter("缇达", 7),
                         {"location": "迷宫入口"})                 # ch7 只见第一次
        self.assertEqual(store.entity_state_at_chapter("缇达", 12),
                         {"location": "地下城三层", "status": "重伤"})  # ch12 顺序覆盖
        self.assertEqual(store.entity_state_at_chapter("缇达", 4), {})  # 章前无状态


class TestSafetyFence(unittest.TestCase):
    """写入安全围栏：根围栏+符号链接拒绝。"""

    def test_root_fence_rejects_escape(self):
        store, td = make_store()
        self.addCleanup(td.cleanup)
        # _lib_path=root/libraries/character/provisional/<rid>.json——四层 .. 才出 root
        evil = entity_rec("逃逸", rid="../../../../evil")
        with self.assertRaises(PermissionError):
            store.admit(evil, "provisional")                       # record_id 注释攻击→围栏拦

    def test_symlink_rejected(self):
        store, td = make_store()
        self.addCleanup(td.cleanup)
        outside = Path(td.name).parent / "outside-target.json"
        link = store.root / "libraries-link"
        try:
            os.symlink(str(Path(td.name) / "libraries"), str(link), target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("本平台符号链接不可用（Windows 权限）")
        try:
            with self.assertRaises(PermissionError):
                store._assert_within_root(link / "character" / "provisional" / "x.json")
        finally:
            os.unlink(link)
        self.assertFalse(outside.exists())


class TestMultiversionMerge(unittest.TestCase):
    """cbb-merge 并入：Keep/Range/Flag/Pick+冲突表（claude-book 四动作）。"""

    def SRC(self, name, canonical):
        return {"source_name": name, "canonical": canonical}

    def test_keep_range_flag_pick(self):
        res = cs.multiversion_merge([
            self.SRC("文库版", {"发色": "黑发", "身高": 165, "出身": "平民区", "口头禅": "就这样吧"}),
            self.SRC("web版",  {"发色": "黑发", "身高": 172, "口头禅": "算了，就这样吧，不说了"}),
        ])
        self.assertEqual(res["merged"]["发色"], "黑发")
        self.assertEqual(res["actions"]["发色"], "keep")            # 全源同值
        self.assertEqual(res["merged"]["身高"], "165-172")
        self.assertEqual(res["actions"]["身高"], "range")           # 数值波动→区间
        self.assertEqual(res["actions"]["出身"], "flag")            # 单源→标记待证
        self.assertEqual(res["merged"]["出身"], "平民区")
        self.assertEqual(res["actions"]["口头禅"], "pick")          # 异值→取最长
        self.assertEqual(res["merged"]["口头禅"], "算了，就这样吧，不说了")
        conflict_fields = {c["field"] for c in res["conflicts"]}
        self.assertEqual(conflict_fields, {"出身", "口头禅"})       # 冲突表登记 Flag/Pick 项

    def test_single_source_and_empty(self):
        res = cs.multiversion_merge([self.SRC("only", {"a": 1})])
        # 退化情形：单源输入无交叉佐证——全部字段 flag（单源待证），merger 面向多版本对齐
        self.assertEqual(res["actions"]["a"], "flag")
        self.assertEqual(res["merged"]["a"], 1)
        self.assertEqual(len(res["conflicts"]), 1)
        empty = cs.multiversion_merge([])
        self.assertEqual(empty, {"merged": {}, "actions": {}, "conflicts": []})


class TestTransitionAndSupersede(unittest.TestCase):
    """保留面：旁车迁移幂等+supersede 链。"""

    def test_transition_idempotent_and_effective(self):
        store, td = make_store()
        self.addCleanup(td.cleanup)
        store.admit(entity_rec("缇达", rid="tr-1"), "provisional")
        e1 = store.status_transition("tr-1", "confirmed", by="human")
        self.assertEqual((e1["from"], e1["to"]), ("provisional", "confirmed"))
        e2 = store.status_transition("tr-1", "confirmed", by="human")
        self.assertTrue(e2["repeated"])                            # 目标态已达不重复入账
        self.assertEqual(store.effective_status("tr-1"), "confirmed")
        store.status_transition("tr-1", "provisional", by="shadow")  # 影子审计降级
        self.assertEqual(store.effective_status("tr-1"), "provisional")

    def test_supersede_chain_and_old_immutable(self):
        store, td = make_store()
        self.addCleanup(td.cleanup)
        store.admit(entity_rec("缇达", rid="tr-1"), "provisional")
        old_bytes = (store._lib_path("character", "provisional", "tr-1")).read_bytes()
        v2 = entity_rec("缇达", status="重伤", rid="tr-2")
        path, created = store.supersede("tr-1", v2)
        self.assertTrue(created)
        self.assertEqual((store._lib_path("character", "provisional", "tr-1")).read_bytes(),
                         old_bytes)                                # 旧件字节不动
        latest = store.resolve_latest("tr-1")
        self.assertEqual(latest["record_id"], "tr-2")
        self.assertEqual(latest["version"], 2)
        self.assertEqual(latest["supersedes"], "tr-1")
        with self.assertRaises(ValueError):
            store.supersede("tr-1", entity_rec("缇达", rid="tr-1"))  # 不换 id=拒


if __name__ == "__main__":
    unittest.main(verbosity=2)
