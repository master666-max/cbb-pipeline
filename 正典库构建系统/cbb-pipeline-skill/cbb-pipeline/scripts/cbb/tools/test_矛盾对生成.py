# -*- coding: utf-8 -*-
"""test_矛盾对生成.py — U-C03.8 准备件单测：矛盾对生成（两族群+回收三层）+考卷确定性+判卷双门。
离线：临时目录全链路，不碰真库；git 回收层用 --no-git 语义（index_git_blobs 对非 git 目录静默空）。"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "contracts"))
sys.path.insert(0, str(HERE.parent / "cbb-store"))

import cbb_store  # noqa: E402
import 矛盾对生成 as mp  # noqa: E402


def _entity(rid, name, etype, chapter=7, quote="某物为某类"):
    return {"record_id": rid, "record_type": "entity", "library": "character",
            "status": "candidate",
            "canonical": {"name": name, "entity_type": etype},
            "observations": [], "version": 1, "supersedes": None,
            "evidence": [{"vol": 1, "chapter": chapter, "line": 12, "quote": quote}],
            "verified_against": {"path": "t.txt", "sha": "a" * 8, "verified_at": "2026-09-19"},
            "provenance": {"extractor_confidence": 0.9, "extractor": "test",
                           "gate_trace": [], "precedent_refs": [], "status_history": []}}


def _fixture(tmp: str):
    root = Path(tmp)
    store = cbb_store.ThreeStateStore(root / "store")
    store.admit(_entity("cand-entity-e1", "缇达", "人物(迷宫生物)"), "provisional")
    store.admit(_entity("cand-entity-e2", "缇亚", "人物"), "provisional")
    return root, store


def test_pairs_dual_track_full_recovery():
    with tempfile.TemporaryDirectory() as tmp:
        root, store = _fixture(tmp)
        iid, _ = store.zone.register(
            group="entity_unalignable",
            detail="entity_type: 入库='人物' vs 库内='人物(迷宫生物)'",
            record_id="cand-entity-e9", source="cbb-store-dual-track",
            subclass="contradiction_pending")
        cands = root / "cands"
        cands.mkdir()
        (cands / "cands-ch0009.json").write_text(json.dumps(
            {"candidates": [_entity("cand-entity-e9", "缇达", "人物", chapter=9)]},
            ensure_ascii=False), encoding="utf-8")
        idx = mp.index_current_cands(cands)
        pairs, stats = mp.build_pairs(store, idx)
        assert len(pairs) == 1, stats
        p = pairs[0]
        assert p["family"] == "dual_track_conflict" and p["recovery"] == "full"
        assert p["premise"]["claim"] == "缇达的实体类型为人物(迷宫生物)"
        assert p["hypothesis"]["claim"] == "缇达的实体类型为人物"
        assert p["premise"]["evidence"][0]["chapter"] == 7
        assert p["hypothesis"]["evidence"][0]["chapter"] == 9
        assert p["conflict_fields"] == ["entity_type"]
        assert stats["recovery_full"] == 1


def test_pairs_reconstructed_when_body_missing():
    with tempfile.TemporaryDirectory() as tmp:
        root, store = _fixture(tmp)
        iid, _ = store.zone.register(
            group="entity_unalignable",
            detail="entity_type: 入库='概念(大会)' vs 库内='概念'",
            record_id="cand-entity-gone", source="cbb-store-dual-track",
            subclass="contradiction_pending")
        pairs, stats = mp.build_pairs(store, {})
        assert len(pairs) == 1
        p = pairs[0]
        assert p["recovery"] == "reconstructed"
        assert p["hypothesis"]["claim"].endswith("为概念(大会)")
        assert p["premise"]["claim"].endswith("为概念")
        assert p["premise"]["claim"].startswith("案件主体")
        assert p["premise"]["evidence"] == [] and p["hypothesis"]["evidence"] == []
        assert stats["recovery_partial"] == 1


def test_pairs_embedding_family_and_name_miss():
    with tempfile.TemporaryDirectory() as tmp:
        root, store = _fixture(tmp)
        store.zone.register(
            group="low_confidence",
            detail="嵌入存疑(0.85-0.95)：缇亚 vs 缇达 sim=0.898（测试批收口扫描，只提示不静默）",
            record_id="embed-1", source="embed-scan",
            subclass="contradiction_pending")
        store.zone.register(
            group="low_confidence",
            detail="嵌入存疑(0.85-0.95)：缇亚 vs 无此人 sim=0.86（测试，只提示不静默）",
            record_id="embed-2", source="embed-scan",
            subclass="contradiction_pending")
        pairs, stats = mp.build_pairs(store, {})
        fam = [p for p in pairs if p["family"] == "embedding_notice"]
        assert len(fam) == 2
        full = next(p for p in fam if p["recovery"] == "full")
        # detail "新 vs 库内"：n1=假设侧（新），n2=前提侧（库内）
        assert full["hypothesis"]["claim"].startswith("缇亚的实体类型")
        assert full["premise"]["claim"].startswith("缇达的实体类型")
        miss = next(p for p in fam if p["recovery"] == "name_miss")
        assert miss["premise"]["entity"] == "无此人" and miss["premise"]["claim"] is None
        assert miss["hypothesis"]["claim"].startswith("缇亚的实体类型")
        assert stats["name_miss"] == 1


def test_exam_deterministic_rows_and_expected_labels():
    with tempfile.TemporaryDirectory() as tmp:
        root, store = _fixture(tmp)
        for i in range(3):
            iid, _ = store.zone.register(
                group="entity_unalignable",
                detail=f"entity_type: 入库='人物{i}' vs 库内='人物(迷宫生物)'",
                record_id=f"cand-entity-x{i}", source="cbb-store-dual-track",
                subclass="contradiction_pending")
            store.zone.adjudicate(iid, "rejected", note=f"案{i}作废")
        names = {it["item_id"]: "缇达" for it in store.zone.adjudicated()}
        paper1 = mp.build_exam(store, None, min_real=3)
        paper2 = mp.build_exam(store, None, min_real=3)
        assert paper1["rows"] == paper2["rows"], "考卷必须确定性（无 RNG）"
        assert paper1["meets_minimum"] and paper1["n_real"] == 3
        kinds = [r["kind"] for r in paper1["rows"]]
        assert kinds.count("base") == 3 and kinds.count("entails_control") == 3
        assert kinds.count("entails_paraphrase") == 3 and kinds.count("neutral_subject") == 3
        base = next(r for r in paper1["rows"] if r["kind"] == "base")
        assert base["expected"] == "contradicts"
        # 匿名主体：base 两断言同主体异值；neutral 主体必不同
        neu = next(r for r in paper1["rows"] if r["kind"] == "neutral_subject")
        subj_base = base["premise"].split("的实体类型")[0]
        subj_neu = neu["hypothesis"].split("的实体类型")[0]
        assert subj_base != subj_neu


def test_grade_dual_gate():
    rows = [
        {"pair_id": "a-base", "kind": "base", "expected": "contradicts",
         "premise": "p", "hypothesis": "h"},
        {"pair_id": "a-control", "kind": "entails_control", "expected": "entails",
         "premise": "p", "hypothesis": "p"},
        {"pair_id": "a-paraphrase", "kind": "entails_paraphrase", "expected": "entails",
         "premise": "p", "hypothesis": "p2"},
        {"pair_id": "a-neutral", "kind": "neutral_subject", "expected": "neutral",
         "premise": "p", "hypothesis": "h3"},
    ]
    good = [{"pair_id": "a-base", "label": "contradicts", "reason": "同主体异值"},
            {"pair_id": "a-control", "label": "entails", "reason": "逐字同"},
            {"pair_id": "a-paraphrase", "label": "entails", "reason": "重述"},
            {"pair_id": "a-neutral", "label": "neutral", "reason": "异主体"}]
    r = mp.grade(rows, good)
    assert r["separation"] == 1.0 and r["exact_match"] == 1.0 and r["pass"]
    # 永远-neutral 退化器：separation=0.75 但 exact=0.25 → 必须不通过（双门）
    degenerate = [{"pair_id": r_["pair_id"], "label": "neutral", "reason": "x"} for r_ in rows]
    r2 = mp.grade(rows, degenerate)
    assert r2["separation"] == 0.75 and not r2["pass"], r2
    # 缺行按保守计：缺 base 行 → separation 受罚
    r3 = mp.grade(rows, good[:3])
    assert "a-neutral" in r3["missing"] and not r3["pass"]


def test_real_store_smoke_no_git():
    """真库只读冒烟（不写）：两族群均有产出、计数与隔离区对账。

    口径（2026-09-24 定责修正）：对 = 可解析件产出（dual_track + embedding）；
    unparsed（detail 形态不可解析）只计数不产出对——故断言 len(pairs) == 两族群之和，
    并另以"三数之和 == pending"对账隔离区（清点时该 71 件须在隔离区报告可见）。
    旧断言 len(pairs) == pending 只在 unparsed==0 时成立（无解析缺口期）。
    """
    real = mp.DEFAULT_STORE
    if not real.exists():
        return  # 非本仓环境跳过
    store = cbb_store.ThreeStateStore(real)
    idx = mp.index_current_cands(mp.DEFAULT_CANDS)
    pairs, stats = mp.build_pairs(store, idx)
    n_pending_con = len([i for i in store.zone.pending()
                         if i.get("subclass") == "contradiction_pending"])
    assert len(pairs) == stats["dual_track"] + stats["embedding"], (len(pairs), stats)
    assert stats["dual_track"] + stats["embedding"] + stats["unparsed"] == n_pending_con


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted({k: v for k, v in globals().items()
                            if k.startswith("test_") and callable(v)}.items()):
        try:
            fn()
            print(f"PASS {name}")
        except AssertionError as e:
            fails += 1
            print(f"FAIL {name}: {e}")
    raise SystemExit(1 if fails else 0)
