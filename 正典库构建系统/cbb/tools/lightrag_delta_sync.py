# -*- coding: utf-8 -*-
"""lightrag_delta_sync.py — 增量同步：章收口把新增/变化的图谱元素喂给 LightRAG 副本。

机制：
  · sidecar 记账（<work>/_fed-sources.json）：每个实体名/关系三元组记录**已喂的 source 集**；
  · delta = 当前库状态 vs sidecar——source 集有增变即整条重喂（upsert 语义），
    全新条目正常喂；sidecar 没有的一律视为新；
  · **幂等**：无变化 → delta=0 → 零嵌入调用（可反复跑）；
  · 挂点：章收口/段收口的 aux 段调用（与 Neo4j 导出同批）。
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys_dir = str(HERE)
if sys_dir not in __import__("sys").path:
    __import__("sys").path.insert(0, sys_dir)

import lightrag_export as le  # noqa: E402  复用 build_kg/嵌入/桩


def _load_sidecar(work: Path) -> dict:
    p = work / "_fed-sources.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"entities": {}, "relationships": {}, "chunks": []}


def _diff(kg: dict, fed: dict) -> tuple[dict, dict]:
    """当前 vs 已喂 → (delta_kg, 统计)。实体/关系按 source 集变化判定；chunk 按 record_id 新增判定。"""
    d_ent, d_rel, d_chunk = [], [], []
    for e in kg["entities"]:
        key = e["entity_name"]
        srcs = sorted(str(e["source_id"]).split("<SEP>"))
        if fed["entities"].get(key) != srcs:
            d_ent.append(e)
    for r in kg["relationships"]:
        key = f"{r['src_id']}\u0001{r['keywords']}\u0001{r['tgt_id']}"
        srcs = sorted(str(r["source_id"]).split("<SEP>"))
        if fed["relationships"].get(key) != srcs:
            d_rel.append(r)
    fed_chunks = set(fed["chunks"])
    for c in kg["chunks"]:
        if c["source_id"] not in fed_chunks:
            d_chunk.append(c)
    stats = {"delta_entities": len(d_ent), "delta_relationships": len(d_rel),
             "delta_chunks": len(d_chunk)}
    delta = {"entities": d_ent, "relationships": d_rel, "chunks": d_chunk}
    return delta, stats


def _merge_sidecar(fed: dict, kg: dict) -> dict:
    for e in kg["entities"]:
        fed["entities"][e["entity_name"]] = sorted(str(e["source_id"]).split("<SEP>"))
    for r in kg["relationships"]:
        fed["relationships"][f"{r['src_id']}\u0001{r['keywords']}\u0001{r['tgt_id']}"] = \
            sorted(str(r["source_id"]).split("<SEP>"))
    fed["chunks"] = sorted({c["source_id"] for c in kg["chunks"]} | set(fed["chunks"]))
    return fed


def sync(store_root: Path, work: Path, feed: bool = True) -> dict:
    import time as _t
    hb = Path(work) / "_live-heartbeat"
    if feed and hb.exists() and (_t.time() - hb.stat().st_mtime) < 120:
        return {"fed": False, "llm_calls": 0, "emb_calls": 0,
                "口径": "live 哨在岗（心跳 120s 内）——章收口同步让位，避免双进程写副本"}
    le.STORE = Path(store_root)
    kg, stats = le.build_kg(Path(store_root))
    fed = _load_sidecar(Path(work))
    delta, dstats = _diff(kg, fed)
    report = {"stats": stats, **dstats, "fed": False, "llm_calls": le.CNT["llm_calls"],
              "emb_calls": le.CNT["emb_calls"]}
    if feed and (dstats["delta_entities"] or dstats["delta_relationships"] or dstats["delta_chunks"]):
        Path(work).mkdir(parents=True, exist_ok=True)
        from lightrag import LightRAG
        from lightrag.utils import EmbeddingFunc
        rag = LightRAG(working_dir=str(work),
                       embedding_func=EmbeddingFunc(embedding_dim=4096, func=le._embed_batch),
                       llm_model_func=le._llm_stub, llm_model_name="stub-no-llm")

        async def _feed():
            await rag.initialize_storages()
            try:
                await rag.ainsert_custom_kg(delta)
            finally:
                await rag.finalize_storages()

        asyncio.run(_feed())
        _merge_sidecar(fed, kg)
        Path(work).mkdir(parents=True, exist_ok=True)
        (Path(work) / "_fed-sources.json").write_text(
            json.dumps(fed, ensure_ascii=False, indent=1), encoding="utf-8")
        report.update({"fed": True, "llm_calls": le.CNT["llm_calls"],
                       "emb_calls": le.CNT["emb_calls"]})
    elif feed:
        report["口径"] = "无 delta（幂等：零嵌入调用）"
    return report


def main(argv=None) -> int:  # pragma: no cover
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(le.STORE))
    ap.add_argument("--work", default=str(le.WORK))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--bootstrap", action="store_true",
                    help="副本已含当前全量时使用：只把现状写入 sidecar 记账，不喂（防首章全量重嵌）")
    ns = ap.parse_args(argv)
    if ns.bootstrap:
        le.STORE = Path(ns.store)
        kg, stats = le.build_kg(Path(ns.store))
        fed = _merge_sidecar(_load_sidecar(Path(ns.work)), kg)
        Path(ns.work).mkdir(parents=True, exist_ok=True)
        (Path(ns.work) / "_fed-sources.json").write_text(
            json.dumps(fed, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({"bootstrapped": True, **stats}, ensure_ascii=False))
        return 0
    rep = sync(Path(ns.store), Path(ns.work), feed=not ns.dry_run)
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
