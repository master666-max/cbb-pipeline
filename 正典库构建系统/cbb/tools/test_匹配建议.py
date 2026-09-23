# -*- coding: utf-8 -*-
"""test_匹配建议.py — 岗位③测试：建议排序＋**红区隔离**（结构性证明建议不进判定路径）"""
import importlib
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "cbb-store"))
sys.path.insert(0, str(HERE))
建议 = importlib.import_module("匹配建议")
import cbb_store  # noqa: E402


def test_suggestion_order_rerank_and_fallback():
    cand = {"record_id": "new-1", "canonical": {"name": "缇达", "entity_type": "人物"}}
    existing = [{"record_id": "e-1", "name": "完全无关的角色"},
                {"record_id": "e-2", "name": "缇迖"},
                {"record_id": "e-3", "name": "缇达"}]
    body = json.dumps({"results": [{"index": 2, "relevance_score": 0.99},
                                   {"index": 1, "relevance_score": 0.6},
                                   {"index": 0, "relevance_score": 0.01}]}).encode("utf-8")
    建议 = 建议mod = __import__("匹配建议")
    rep = 建议.suggest_matches(cand, existing, top_k=2,
                              transport=lambda e, p, t: body.decode("utf-8"))
    assert [x["record_id"] for x in rep["suggestions"]] == ["e-3", "e-2"]
    assert rep["backend"] == "rerank"

    rep2 = 建议mod.suggest_matches(cand, existing, top_k=2,
                                   transport=lambda e, p, t: (_ for _ in ()).throw(OSError("x")))
    assert rep2["backend"] == "mechanical" and rep2["suggestions"][0]["record_id"] == "e-1"  # 机械=原序


def test_red_zone_isolation_structural(tmp_path):
    """判据（红区隔离）：带建议的记录与不带建议的记录，**store 判定结果逐字段一致**——
    建议字段挂在 _meta 上，store 的 identity/路由/合并不读它（结构性隔离的实证）。"""
    tmp = tempfile.TemporaryDirectory()
    s1 = cbb_store.ThreeStateStore(Path(tmp.name) / "a")
    s2 = cbb_store.ThreeStateStore(Path(tmp.name) / "b")

    def mk(name):
        return {"record_id": f"cand-entity-{name}", "record_type": "entity", "library": "character",
                "status": "candidate",
                "canonical": {"name": name, "entity_type": "人物"},
                "evidence": [{"vol": 1, "chapter": 1, "line": 1, "quote": f"{name}登场"}],
                "verified_against": {"path": "t", "sha": "0" * 7, "verified_at": "1970-01-01"},
                "provenance": {"extractor_confidence": 0.9, "extractor": "t", "gate_trace": [],
                               "precedent_refs": [], "status_history": []},
                "version": 1, "supersedes": None}

    clean = mk("缇达")
    dirty = mk("缇达")
    dirty["_meta"] = {"match_suggestions": [{"record_id": "whatever", "rank": 0}]}  # 现实形态：仅建议位
    r1 = s1.admit_or_merge(clean)
    r2 = s2.admit_or_merge(dirty)
    # 只比语义字段（created/track）；path 因临时目录不同必然不同
    for k in ("created", "track"):
        assert r1.get(k) == r2.get(k), f"判定路径受建议字段影响：{k}: {r1.get(k)} vs {r2.get(k)}"
    # store 会原样保留 _meta（实测）→ 契约＝admit 前必须 strip_suggestions
    stripped = 建议.strip_suggestions(dirty)
    assert json.dumps(stripped, ensure_ascii=False, sort_keys=True) ==            json.dumps(clean, ensure_ascii=False, sort_keys=True), "剥离后应与干净记录逐字节同构"
    s3 = cbb_store.ThreeStateStore(Path(tmp.name) / "c")
    s3.admit_or_merge(建议.strip_suggestions(dirty))
    rec = json.loads((Path(tmp.name) / "c" / "libraries" / "character" / "provisional" /
                      "cand-entity-缇达.json").read_text(encoding="utf-8"))
    assert "match_suggestions" not in (rec.get("_meta") or {}), "剥离后落盘不得带建议位"
    tmp.cleanup()


if __name__ == "__main__":
    import tempfile
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        if fn.__code__.co_argcount:
            with tempfile.TemporaryDirectory() as td:
                fn(Path(td))
        else:
            fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
