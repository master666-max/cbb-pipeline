# -*- coding: utf-8 -*-
"""test_aggregate.py — 批次 6·A1 聚合引擎（保守两源：精确名簇 + aliases 证据面）。"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import aggregate  # noqa: E402


def _rec(rid, name, lib="character", status="provisional"):
    return {"record_id": rid, "library": lib, "status": status,
            "canonical": {"name": name, "entity_type": "人物"},
            "evidence": [{"vol": 1, "chapter": 3, "line": 10, "quote": f"{name}引文"}],
            "_aliases": []}


def test_exact_name_cluster():
    recs = [_rec("a1", "相川涡波"), _rec("a2", "相川涡波"), _rec("b1", "玛利亚")]
    clusters = aggregate.build_clusters(records=recs, alias_rows=[])
    by_main = {c["main_name"]: c for c in clusters}
    assert by_main["相川涡波"]["members"] == ["a1", "a2"]
    assert by_main["玛利亚"]["members"] == ["b1"]
    assert len(clusters) == 2


def test_alias_evidence_joins_cluster():
    recs = [_rec("cand-main", "拉丝缇娅拉"), _rec("cand-x", "缇娅")]
    alias_rows = [{"alias": "缇娅", "entity_id": "cand-main", "entity_type": "人物"}]
    clusters = aggregate.build_clusters(records=recs, alias_rows=alias_rows)
    by_main = {c["main_name"]: c for c in clusters}
    # 别名证据面：cand-x（名"缇娅"）并进 cand-main 的簇
    assert "cand-x" in by_main["拉丝缇娅拉"]["members"]
    assert len(clusters) == 1


def test_conflicting_alias_splits_with_flag(tmp_path=None):
    recs = [_rec("cand-m1", "玛利亚"), _rec("cand-m2", "玛利亚")]
    # 同名两记录；alias "玛利亚" 指向另一实体 cand-other（不在库）——
    # 保守策略：alias→entity_id 与名簇冲突时分裂并标存疑
    alias_rows = [{"alias": "玛利亚", "entity_id": "cand-other", "entity_type": "人物"}]
    clusters = aggregate.build_clusters(records=recs, alias_rows=alias_rows)
    by_main = {c["main_name"]: c for c in clusters}
    assert len(clusters) == 1                                    # 名精确簇保持
    c = by_main["玛利亚"]
    assert c["members"] == ["cand-m1", "cand-m2"]
    assert c["存疑外部映射"] == ["cand-other"]                     # 保守：不并入，标注待人工


def test_no_cross_name_merge_without_evidence():
    recs = [_rec("a", "相川涡波"), _rec("b", "拉丝缇娅拉")]
    alias_rows = [{"alias": "相川涡波", "entity_id": "b", "entity_type": "人物"}]
    clusters = aggregate.build_clusters(records=recs, alias_rows=alias_rows)
    # 有证据映射（alias 声明 b 实体的别名是"相川涡波"）⇒ 保守两源下仍合并（L2 证据面允许）
    by_main = {c["main_name"]: c for c in clusters}
    merged = [c for c in clusters if "a" in c["members"] and "b" in c["members"]]
    assert len(merged) == 1, "证据面别名应连通两记录"


def test_render_aggregate_page():
    members = [{"record_id": "a1", "status": "confirmed", "chapter": 3,
                "name": "相川涡波", "quote": "涡波的引文。"},
               {"record_id": "a2", "status": "provisional", "chapter": 1,
                "name": "相川涡波", "quote": "更早的引文。"}]
    md = aggregate.render_aggregate_page(
        main_name="相川涡波", aliases=["涡波", "小麦"], members=members,
        anchor={"rows": 5268, "chain_head": "abc"})
    assert "相川涡波" in md and "涡波、小麦" in md
    assert md.index("更早的引文") < md.index("涡波的引文。")       # 时间线按章排序
    assert "confirmed" in md and "provisional" in md              # 三态徽章
    assert "a1" in md and "a2" in md                              # 源记录回链
