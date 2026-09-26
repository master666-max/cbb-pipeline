# -*- coding: utf-8 -*-
"""test_v3_store.py — U-A02 写入决策树五分支 + at 强制 + sidecar 幂等（修前反例先行，PT-020）。

红＝能力缺席（write_decision 不存在）；绿＝五分支各归其位。
运行：py -X utf8 test_v3_store.py
"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2.store import Store  # noqa: E402
from cbb2.ledger import LedgedStore  # noqa: E402


def mk(rid, library, canonical, ch, quote=None, conf=80):
    return {
        "record_id": rid, "record_type": "relation" if library == "relation" else "entity",
        "library": library, "status": "provisional", "canonical": canonical,
        "evidence": [{"vol": 1, "chapter": ch, "line": 2,
                      "quote": quote or f"{canonical}出场于第{ch}章"}],
        "provenance": {"extractor_confidence": conf, "status_history": []},
        "version": 1, "supersedes": None,
        "verified_against": {"path": "t", "sha": "0" * 7, "verified_at": "1970-01-01"},
    }


def test_at_required_without_at_rejected():
    """D-2/D-24 修前反例：v3 写路径缺 at 必须拒——禁墙钟。"""
    with tempfile.TemporaryDirectory() as td:
        st = Store(Path(td))
        rec = mk("r1", "character", {"name": "缇达", "entity_type": "人物", "status": "alive"}, 14)
        try:
            st.write_decision(rec)
            raise AssertionError("缺 at 未拒")
        except ValueError as e:
            assert "at" in str(e)


def test_on_create_and_consistent_duplicate_semantics_kept():
    with tempfile.TemporaryDirectory() as td:
        st = Store(Path(td))
        r0 = st.write_decision(mk("c1", "character",
                                  {"name": "缇达", "entity_type": "人物", "status": "alive"}, 14),
                               at="ch0014")
        assert r0["track"] == "on-create"
        dup = mk("c1-obs2", "character", {"name": "缇达", "entity_type": "人物", "status": "alive"}, 20)
        r1 = st.write_decision(dup, at="ch0020")
        assert r1["track"] == "consistent-duplicate" and r1["confidence"] == 82.0


def test_complementary_statement_not_contradiction():
    """D-23 修前反例：同三元组 relation 仅 claim（陈述位）不同 ⇒ 互补陈述 event，
    不入矛盾轨、incoming 不丢（全文落 sidecar）。"""
    with tempfile.TemporaryDirectory() as td:
        st = Store(Path(td))
        st.write_decision(mk("rl1", "relation",
                             {"subject": "卢卡", "rel_type": "同盟", "object": "缇达",
                              "claim": "第3章于地下城结盟"}, 3), at="ch0003")
        before = len(list(Path(td).glob("libraries/*/*/*.json")))
        r = st.write_decision(mk("rl1-obs2", "relation",
                                 {"subject": "卢卡", "rel_type": "同盟", "object": "缇达",
                                  "claim": "第3章血誓结盟"}, 5), at="ch0005")
        assert r["track"] == "complementary-statement", r
        rows = [json.loads(x) for x in
                (Path(td) / "complementary-statements.jsonl").read_text(encoding="utf-8").splitlines()]
        assert len(rows) == 1 and rows[0]["fields"]["claim"].startswith("第3章血誓")
        assert rows[0]["evidence"][0]["chapter"] == 5  # incoming 证据保全
        after = len(list(Path(td).glob("libraries/*/*/*.json")))
        assert after == before  # 不产生新库件
        assert not (Path(td) / "quarantine-zone" / "items.jsonl").exists()  # 不入矛盾轨


def test_invalidation_mutable_with_temporal_order():
    """死亡行走=失效记账：mutable 位冲突∧时序可证 ⇒ 旧件保留+t_invalid 登记+新件正常写入。"""
    with tempfile.TemporaryDirectory() as td:
        st = Store(Path(td))
        st.write_decision(mk("e1", "character",
                             {"name": "帕林", "entity_type": "人物", "status": "alive"}, 14),
                          at="ch0014")
        old_raw = (Path(td) / "libraries" / "character" / "provisional" / "e1.json").read_text(encoding="utf-8")
        r = st.write_decision(mk("e1-i1", "character",
                                 {"name": "帕林", "entity_type": "人物", "status": "dead"}, 20),
                              at="ch0020")
        assert r["track"] == "invalidation-update" and r["invalidated"] == "e1"
        inv = [json.loads(x) for x in
               (Path(td) / "invalidations.jsonl").read_text(encoding="utf-8").splitlines()]
        assert inv and inv[0]["record_id"] == "e1" and inv[0]["t_invalid"] == "ch0020"
        assert (Path(td) / "libraries" / "character" / "provisional" / "e1.json").read_text(encoding="utf-8") == old_raw  # 旧件字节不动
        live = st.find_by_identity(mk("x", "character", {"name": "帕林", "entity_type": "人物"}, 20))
        assert live["canonical"]["status"] == "dead"  # 现役解析到新件


def test_mutable_without_temporal_order_falls_to_gate():
    """时序不可证（无证据章）⇒ 保守走闸，不得自动失效。"""
    with tempfile.TemporaryDirectory() as td:
        st = Store(Path(td))
        st.write_decision(mk("e2", "character",
                             {"name": "海莉", "entity_type": "人物", "status": "alive"}, 14), at="ch0014")
        incoming = mk("e2-i1", "character",
                      {"name": "海莉", "entity_type": "人物", "status": "dead"}, 99)
        incoming["evidence"] = []  # 无章序可证
        r = st.write_decision(incoming, at="ch0099",
                              nli_gate=lambda i, e, c: "contradicts")
        assert r["track"] == "contradiction"  # 保守：不可证时序不洗白


def test_immutable_conflict_routes_gate():
    """unclassified 字段（保守按 immutable）走闸；entity_type 已改 mutable 走失效记账（另测）。"""
    with tempfile.TemporaryDirectory() as td:
        st = Store(Path(td))
        st.write_decision(mk("g1", "character",
                             {"name": "诺斯菲", "entity_type": "人物", "rank": "骑士", "status": "alive"}, 3), at="ch0003")
        inc = mk("g1-i1", "character",
                 {"name": "诺斯菲", "entity_type": "人物", "rank": "深渊领主", "status": "alive"}, 4)
        r_neu = st.write_decision(dict(inc), at="ch0004", nli_gate=lambda i, e, c: "neutral")
        assert r_neu["track"] == "uncertain-coexist"
        rec = st._find(r_neu["new_id"])
        assert rec["_meta"]["uncertain"]["fields"] == ["rank"]
        inc2 = mk("g1-i2", "character",
                  {"name": "诺斯菲", "entity_type": "人物", "rank": "虚空领主", "status": "alive"}, 4)
        r_con = st.write_decision(dict(inc2), at="ch0004", nli_gate=lambda i, e, c: "contradicts")
        assert r_con["track"] == "contradiction"
        full = (Path(td) / "拦截件全文.jsonl").read_text(encoding="utf-8")
        assert "虚空领主" in full  # incoming 全文留存（D-6）
        inc3 = mk("g1-i3", "character",
                  {"name": "诺斯菲", "entity_type": "人物", "rank": "魔王", "status": "alive"}, 4)
        r_fb = st.write_decision(dict(inc3), at="ch0004")  # 无闸保守回落=v1 行为
        assert r_fb["track"] == "contradiction"


def test_entity_type_refinement_is_invalidation():
    """entity_type=随剧情精化（实证）：人物→人物(迷宫生物) 有时序 ⇒ 失效记账非矛盾。"""
    with tempfile.TemporaryDirectory() as td:
        st = Store(Path(td))
        st.write_decision(mk("r1", "character",
                             {"name": "卡欧斯", "entity_type": "人物", "status": "alive"}, 10), at="ch0010")
        r = st.write_decision(mk("r1-i1", "character",
                                 {"name": "卡欧斯", "entity_type": "人物(迷宫生物)", "status": "alive"}, 30),
                              at="ch0030")
        assert r["track"] == "invalidation-update", r
        live = st.find_by_identity(mk("x", "character", {"name": "卡欧斯", "entity_type": "人物(迷宫生物)"}, 30))
        assert live["canonical"]["entity_type"] == "人物(迷宫生物)"


def test_merge_gate2_intercepts_identical_duplicate():
    with tempfile.TemporaryDirectory() as td:
        st = Store(Path(td))
        st.write_decision(mk("m1", "character",
                             {"name": "卢卡", "entity_type": "人物", "status": "alive"}, 3), at="ch0003")
        r = st.write_decision(mk("m1-obs2", "character",
                                 {"name": "卢卡", "entity_type": "人物", "status": "alive"}, 9),
                              at="ch0009", nli_merge_gate=lambda i, e: "contradicts")
        assert r["track"] == "contradiction"  # 闸2 拦截：一致重复外观下的语义矛盾


def test_sidecar_idempotent_under_ledger():
    with tempfile.TemporaryDirectory() as td:
        ls = LedgedStore(Path(td))
        base = mk("s1", "relation",
                  {"subject": "缇娅拉", "rel_type": "同盟", "object": "缇达", "claim": "甲"}, 3)
        ls.write_decision(base, at="ch0003")
        inc = mk("s1-obs2", "relation",
                 {"subject": "缇娅拉", "rel_type": "同盟", "object": "缇达", "claim": "乙"}, 5)
        ls.write_decision(inc, at="ch0005")
        ls.write_decision(dict(inc), at="ch0005")  # 重放同件
        rows = (Path(td) / "complementary-statements.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(rows) == 1  # 幂等
        assert ls.ledger.verify(Path(td))["ok"]


def test_legacy_facade_documents_v1_flaw():
    """D-23 病灶存档：v1 门面 admit_or_merge 仍把互补陈述判矛盾（等价锚不许动）——
    本测试钉住旧行为，证明 v3 走 write_decision 的必要性。"""
    with tempfile.TemporaryDirectory() as td:
        st = Store(Path(td))
        st.admit(mk("f1", "relation",
                    {"subject": "卢卡", "rel_type": "同盟", "object": "缇达", "claim": "甲"}, 3),
                 "provisional")
        r = st.admit_or_merge(mk("f1-obs2", "relation",
                                 {"subject": "卢卡", "rel_type": "同盟", "object": "缇达", "claim": "乙"}, 5))
        assert r["track"] == "contradiction"  # 旧语义保持（等价锚）
        assert not (Path(td) / "complementary-statements.jsonl").exists()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
