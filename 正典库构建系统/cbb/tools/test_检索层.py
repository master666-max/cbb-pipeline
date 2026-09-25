# -*- coding: utf-8 -*-
"""test_检索层.py — U-F07：别名召回/RRF/关键词/降级/引文核验（零网络；LanceDB 用例条件跳过）"""
import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
检索 = importlib.import_module("检索层")


def mk_store(tmp: Path) -> Path:
    store = tmp / "store"
    for lib in ("character", "relation"):
        (store / "libraries" / lib / "provisional").mkdir(parents=True, exist_ok=True)
    (store / "libraries" / "character" / "provisional" / "cand-entity-涡波.json").write_text(
        json.dumps({"record_id": "e-wb", "record_type": "entity", "library": "character",
                    "canonical": {"name": "相川涡波", "entity_type": "人物"},
                    "observations": [{"category": "summary", "text": "手持创世手环的少年"}],
                    "evidence": [{"vol": 1, "chapter": 41, "line": 1, "quote": "斯诺用眼神交流"}]},
                   ensure_ascii=False), encoding="utf-8")
    (store / "libraries" / "relation" / "provisional" / "r-1.json").write_text(
        json.dumps({"record_id": "r-1", "record_type": "relation", "library": "relation",
                    "canonical": {"subject": "斯诺·沃克", "rel_type": "情报传递", "object": "相川涡波"},
                    "evidence": [{"vol": 1, "chapter": 41, "line": 2, "quote": "用眼神交流告诉过我了"}]},
                   ensure_ascii=False), encoding="utf-8")
    (store / "aliases.jsonl").write_text(
        json.dumps({"alias": "涡波", "entity_id": "e-wb", "entity_type": "人物", "key": "涡波|e-wb"},
                   ensure_ascii=False), encoding="utf-8")
    return store


def test_alias_recall_hits_exact_and_alias(tmp_path):
    store = mk_store(tmp_path)
    hits = {h["name"] for h in 检索.alias_recall("涡波用手环做了什么", store)}
    assert "相川涡波" in hits  # 别名"涡波"命中
    hits2 = {h["name"] for h in 检索.alias_recall("相川涡波的表情", store)}
    assert "相川涡波" in hits2  # 本名精确命中


def test_rrf_fusion_known_order():
    """手算 RRF（k=60）：甲在两路都第 1 → 2/(60+1)；乙路一第 2、丙路二第 1 → 同分并列其后。"""
    fused = 检索.rrf([["甲", "乙"], ["甲", "丙"]])
    assert fused[0][0] == "甲"
    assert abs(fused[0][1] - 2 / 61) < 1e-9


def test_keyword_recall_scores(tmp_path):
    store = mk_store(tmp_path)
    hits = 检索.keyword_recall("手环的少年", store)
    assert hits and hits[0]["name"] == "相川涡波"  # 观察文本含"手环""少年"


def test_hybrid_search_degrades_without_index(tmp_path):
    """判据：索引缺席 → 向量路缺席口径注明，别名＋关键词两路照跑，backend=rrf（重排关）。"""
    store = mk_store(tmp_path)
    rep = 检索.hybrid_search("涡波用手环", store, index_dir=tmp_path / "no-index",
                             top_k=5, rerank=False)
    assert rep["paths"] >= 2
    assert "向量路缺席" in rep["口径"]
    assert rep["backend"] == "rrf"
    assert rep["top"] and rep["top"][0]["name"] == "相川涡波"


def test_verify_citations_split(tmp_path):
    store = mk_store(tmp_path)
    rep = 检索.verify_citations([
        {"record_id": "r-1", "quote": "用眼神交流告诉过我了"},      # 库内真证据
        {"record_id": "r-1", "quote": "这句话库里根本没有。"},      # 落不回
    ], store)
    assert len(rep["verified"]) == 1 and len(rep["unverified"]) == 1
    assert rep["unverified"][0]["quote"] == "这句话库里根本没有。"


def test_lancedb_roundtrip_if_available(tmp_path):
    """LanceDB 装好后：建表→写入→向量查询 回环（嵌入用注入桩，零网络）。"""
    try:
        import lancedb  # noqa: F401
    except ImportError:
        import unittest
        raise unittest.SkipTest("lancedb 未安装（后台安装中）")
    import pyarrow as pa
    db = 检索._db(tmp_path / "idx")
    tbl = db.create_table("records", pa.table({
        "record_id": ["e-wb"], "name": ["相川涡波"], "text": ["手持创世手环的少年"],
        "vector": [[0.1] * 8], "library": ["character"]}))
    tbl.add(pa.table({"record_id": ["r-1"], "name": ["斯诺·沃克"], "text": ["情报传递"],
                      "vector": [[0.9] * 8], "library": ["relation"]}))
    res = tbl.search([0.9] * 8).limit(1).to_list()
    assert res[0]["name"] == "斯诺·沃克"


def test_rerank_uses_rich_text_not_name(tmp_path):
    """v3 修正断言：精排收到的是富文本 text 列，不是 name 串。"""
    import pyarrow as pa
    db = 检索._db(tmp_path / "idx")
    db.create_table("records", pa.table({
        "record_id": ["e-1"], "name": ["『注视』"],
        "text": ["诺文获得的神秘眼睛，能发动『注视』直接洞穿魔法。"],
        "vector": [[0.5] * 8], "library": ["setting"]}))
    seen = {}
    def t(endpoint, payload, timeout):
        seen["docs"] = json.loads(payload.decode("utf-8"))["documents"]
        return json.dumps({"results": [{"index": 0, "relevance_score": 0.7}]}).encode("utf-8")
    store = mk_store(tmp_path)
    检索.hybrid_search("注视", store, index_dir=tmp_path / "idx", top_k=3,
                       rerank=True, embed_fn=lambda ts: [[0.5] * 8], rerank_transport=t)
    assert any("神秘眼睛" in d for d in seen["docs"]), f"精排打分对象不是富文本: {seen['docs']}"


def test_第五路状态必落口径(tmp_path):
    """启用/关闭/副本缺席/调用失败四种情形必须能分开——旧实现只在命中时才落一行。"""
    import os
    store = mk_store(tmp_path)
    原 = os.environ.pop("CBB_FIFTH", None)
    try:
        r = 检索.hybrid_search("涡波", store, index_dir=None, top_k=3, rerank=False,
                               embed_fn=lambda ts: [[0.5] * 8])
        assert "第五路：" in r["口径"], r["口径"]
        assert ("未启用" in r["口径"]) or ("缺席" in r["口径"]), r["口径"]
        os.environ["CBB_FIFTH"] = "0"
        r2 = 检索.hybrid_search("涡波", store, index_dir=tmp_path / "idx", top_k=3, rerank=False,
                                embed_fn=lambda ts: [[0.5] * 8])
        assert "关闭" in r2["口径"], r2["口径"]
        os.environ.pop("CBB_FIFTH", None)
        r3 = 检索.hybrid_search("涡波", store, index_dir=tmp_path / "idx", top_k=3, rerank=False,
                                embed_fn=lambda ts: [[0.5] * 8])
        assert "副本缺席" in r3["口径"], r3["口径"]   # 副本/桥件不在 ⇒ 明说，不静默
    finally:
        os.environ.pop("CBB_FIFTH", None)
        if 原 is not None:
            os.environ["CBB_FIFTH"] = 原


def test_查询日志默认不写显式才写(tmp_path):
    """默认零写入；给路径才写（旧版：默认开＋落点写死成别的项目的实例名＋失败静默）。"""
    import os
    store = mk_store(tmp_path)
    os.environ.pop("CBB_QUERY_LOG", None)
    检索.hybrid_search("涡波", store, index_dir=None, top_k=3, rerank=False,
                       embed_fn=lambda ts: [[0.5] * 8])
    assert list(tmp_path.rglob("query-log.jsonl")) == [], "默认不该写盘，却写出了文件"
    out = tmp_path / "工作区" / "logs" / "query-log.jsonl"
    r = 检索.hybrid_search("涡波", store, index_dir=None, top_k=3, rerank=False,
                           embed_fn=lambda ts: [[0.5] * 8], query_log=out)
    assert out.exists() and len(out.read_text(encoding="utf-8").splitlines()) == 1
    assert "查询日志已写" in r["口径"], r["口径"]
    os.environ["CBB_QUERY_LOG"] = str(tmp_path / "via-env" / "q.jsonl")
    try:
        检索.hybrid_search("涡波", store, index_dir=None, top_k=3, rerank=False,
                           embed_fn=lambda ts: [[0.5] * 8])
        assert (tmp_path / "via-env" / "q.jsonl").exists(), "env 形态没生效"
    finally:
        os.environ.pop("CBB_QUERY_LOG", None)


def test_富文本投影要报原因(tmp_path):
    """投影失败/缺席不再静默退回 name——降级本身必须是可读的一句话。"""
    got, note = 检索._text_lookup(tmp_path / "没有这个目录", ["甲", "乙"])
    assert got == ["甲", "乙"] and "缺席" in note, note
    assert "name 串" in note, note


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        try:
            if fn.__code__.co_argcount:
                with tempfile.TemporaryDirectory() as td:
                    fn(Path(td))
            else:
                fn()
            print(f"OK {fn.__name__}")
        except unittest.SkipTest as e:
            print(f"SKIP {fn.__name__}: {e}")
    print(f"{len(fns)} tests PASS")
