# -*- coding: utf-8 -*-
"""test_图链与增量与网络补充.py — R4 分支三新件的单测（活依赖缺席→如实跳过）。"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "cbb-store"))
sys.path.insert(0, str(HERE.parent / "contracts"))


def _neo4j_up() -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:7695/", timeout=3):
            return True
    except Exception:
        return False


def test_graph_chain_depth_and_dedup():
    if not _neo4j_up():
        print("SKIP graph_chain：Neo4j 缺席（如实跳过，不算过）")
        return
    import graph_chain as gc
    rows = gc._cypher("MATCH (a:Entity)-[r:REL]-(b:Entity) WITH a, count(r) AS d "
                      "RETURN a.name AS n ORDER BY d DESC LIMIT 1", {})
    seed = rows[0]["row"][0]
    c1 = gc.chains([seed], depth=1, max_chains=5)
    assert c1, "depth=1 应有链"
    for c in c1:
        assert len(c["nodes"]) == 2 and len(c["hops"]) == 1
        assert c["hops"][0]["rel"] and c["hops"][0]["edge_id"]
    c2 = gc.chains([seed], depth=2, max_chains=10)
    for c in c2:
        assert len(c["nodes"]) in (2, 3)
        if len(c["nodes"]) == 3:
            assert c["nodes"][0] != c["nodes"][2], "两跳不得原地打转"
            assert c["hops"][0]["to"] == c["nodes"][1] == c["hops"][1]["from"]
    assert len(c1) <= 5 and len(c2) <= 10
    try:
        gc.chains([seed], depth=3)
        raise AssertionError("depth=3 应拒")
    except ValueError:
        pass
    print(f"OK graph_chain（seed={seed}，d1={len(c1)} 链 / d2={len(c2)} 链）")


def test_web_supplement_discipline():
    import web_supplement as ws
    # 结构纪律：硬标记
    live = ws.search("迷深 小说 设定", n=3)
    assert live["admissible"] is False and live["confidence"] == "low"
    if live["errors"] and not live["results"]:
        print(f"SKIP 网络实测：{live['errors'][:1]}（结构纪律已验）")
    else:
        assert live["results"] and all(r.get("url", "").startswith("http") for r in live["results"])
        print(f"OK web_supplement 实测 {len(live['results'])} 条（低置信标记+URL 溯源）")
    # 准入闸：低置信材料试图入正典必须炸
    try:
        ws.guard_block_admission({"admissible": False, "confidence": "low"})
        raise AssertionError("准入闸未拦")
    except PermissionError:
        pass
    # 引文核验面：web snippet 永远落不回库内证据池
    import 检索层 as jl
    with tempfile.TemporaryDirectory() as td:
        store = Path(td)
        d = store / "libraries" / "character" / "provisional"
        d.mkdir(parents=True)
        (d / "x.json").write_text(json.dumps(
            {"record_id": "x", "evidence": [{"vol": 1, "chapter": 1, "line": 1, "quote": "库内原句"}]},
            ensure_ascii=False), encoding="utf-8")
        web_quote = (live["results"][0]["snippet"][:50] if live["results"] else "网络句子的转述")
        rep = jl.verify_citations([{"record_id": "x", "quote": web_quote}], store)
        assert rep["unverified"] and not rep["verified"], "网络句不得过引文核验"
    print("OK 引文核验面：网络材料必判 unverified")


def test_delta_sync_idempotent():
    import lightrag_delta_sync as ds
    import lightrag_export as le

    def mk_rec(rid, name, etype="人物"):
        return {"record_id": rid, "record_type": "entity", "library": "character",
                "status": "provisional", "version": 1,
                "canonical": {"name": name, "entity_type": etype},
                "evidence": [{"vol": 1, "chapter": 1, "line": 1, "quote": f"{name}出场"}],
                "observations": [{"text": f"{name}的设定文本，用于链与增量验证。"}]}

    with tempfile.TemporaryDirectory() as td:
        store = Path(td) / "store"
        d = store / "libraries" / "character" / "provisional"
        d.mkdir(parents=True)
        (d / "e1.json").write_text(json.dumps(mk_rec("e1", "甲"), ensure_ascii=False), encoding="utf-8")
        (d / "e2.json").write_text(json.dumps(mk_rec("e2", "乙"), ensure_ascii=False), encoding="utf-8")
        work = Path(td) / "work"
        r1 = ds.sync(store, work, feed=True)
        assert r1["delta_entities"] == 2 and r1["fed"] and r1["llm_calls"] == 0, r1
        emb_after_first = r1["emb_calls"]
        r2 = ds.sync(store, work, feed=True)          # 幂等：零 delta 零嵌入
        assert r2["delta_entities"] == 0 and r2["delta_relationships"] == 0
        assert r2["emb_calls"] == emb_after_first and "无 delta" in r2.get("口径", ""), r2
        (d / "e3.json").write_text(json.dumps(mk_rec("e3", "丙"), ensure_ascii=False), encoding="utf-8")
        r3 = ds.sync(store, work, feed=True)          # 新章增量：只喂 1
        assert r3["delta_entities"] == 1 and r3["delta_relationships"] == 0, r3
        assert r3["llm_calls"] == 0
        print(f"OK delta_sync（首次 {r1['delta_entities']}E / 幂等 0 / 增量 {r3['delta_entities']}E，"
              f"嵌入调用 {r1['emb_calls']}→{r2['emb_calls']}→{r3['emb_calls']}）")


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted({k: v for k, v in globals().items()
                            if k.startswith("test_") and callable(v)}.items()):
        try:
            fn()
        except AssertionError as e:
            fails += 1
            print(f"FAIL {name}: {e}")
        except Exception as e:
            fails += 1
            print(f"ERROR {name}: {type(e).__name__}: {str(e)[:150]}")
    raise SystemExit(1 if fails else 0)
