# -*- coding: utf-8 -*-
"""lightrag_export.py — 实验件：把 CBB 知识图谱喂给 LightRAG（insert_custom_kg 路径，零 LLM）。

真源=正典库（collect_graph 与 Neo4j 导出同源）；LightRAG working_dir=派生索引副本，
与 LanceDB 索引同级（派生件、可重建、位于 gitignore 的 索引/ 下）。
纪律：
  · 零查询期/写入期 LLM——llm_model_func 为计数桩，任何调用都会被记录并暴露；
  · 自环/缺字段行跳过并计数（T-5 不静默）；
  · weight=去重 source 数（LightRAG 语义下界）。
用法：
  py -X utf8 lightrag_export.py --dry-run     # 只导出计数，不写
  py -X utf8 lightrag_export.py --feed        # 导出并喂入（含嵌入，分钟级）
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "cbb-store"))
sys.path.insert(0, str(HERE.parent / "contracts"))

from neo4j_export import collect_graph  # noqa: E402

ROOT = HERE.parent.parent                    # 正典库构建系统/
STORE = ROOT / "迷深实战-本体库"
WORK = ROOT / "迷深实战-工作区" / "索引" / "lightrag-exp"
EMB = "http://127.0.0.1:8080/v1/embeddings"
MODEL = "text-embedding-qwen3-embedding-8b@q4_k_m"
BATCH = 16

CNT = {"emb_calls": 0, "emb_texts": 0, "llm_calls": 0}


async def _embed_batch(texts: list[str]) -> list[list[float]]:
    # LightRAG 1.5.7 的任务队列 await 用户函数——嵌入函数必须是协程；
    # 阻塞 HTTP 放 to_thread，防堵队列看门狗
    def _http(b):
        payload = json.dumps({"model": MODEL, "input": b}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(EMB, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            d = json.loads(r.read().decode("utf-8"))
        return [x["embedding"] for x in sorted(d["data"], key=lambda x: x["index"])]

    out: list[list[float]] = []
    for i in range(0, len(texts), BATCH):
        b = texts[i:i + BATCH]
        out.extend(await asyncio.to_thread(_http, b))
        CNT["emb_calls"] += 1
        print(f"  embed {i + len(b)}/{len(texts)}", flush=True)
    CNT["emb_texts"] += len(texts)
    import numpy as np
    return np.asarray(out, dtype=np.float32)  # 1.5.7 契约：EmbeddingFunc.__call__ 取 result.size


async def _llm_stub(prompt, system_prompt=None, history_messages=[], **kwargs):  # noqa: ANN001
    CNT["llm_calls"] += 1
    return ""


def _record_text(rec: dict) -> str:
    obs = [o.get("text", "") for o in (rec.get("observations") or []) if o.get("text")]
    return "；".join(obs) if obs else ""


def build_kg(store_root: Path) -> tuple[dict, dict]:
    """库 → ({entities,relationships,chunks}, 统计)。同名实体/同三元组关系做 <SEP> 合并。"""
    graph = collect_graph(store_root)
    rid2rec: dict[str, dict] = {}

    def rec_of(rid):
        if rid in rid2rec:
            return rid2rec[rid]
        hits = list(store_root.glob(f"libraries/*/*/{rid}.json"))
        rec = {}
        if hits:
            try:
                rec = json.loads(hits[0].read_text(encoding="utf-8"))
            except Exception:
                rec = {}
        rid2rec[rid] = rec
        return rec

    stats = {"nodes": len(graph["nodes"]), "edges": len(graph["edges"]),
             "skipped_selfloop": 0, "merged_entity": 0, "merged_rel": 0}
    ents: dict[str, dict] = {}
    for n in graph["nodes"]:
        e = ents.setdefault(n["name"], {"entity_name": n["name"], "entity_type": n["entity_type"] or "unknown",
                                        "description": [], "source_id": []})
        if e["entity_type"] == "unknown":
            e["entity_type"] = n["entity_type"] or "unknown"
        txt = _record_text(rec_of(n["record_id"])) or n["name"]
        e["description"].append(txt)
        e["source_id"].append(n["record_id"])
    rels: dict[tuple, dict] = {}
    for e in graph["edges"]:
        if e["subject"] == e["object"]:
            stats["skipped_selfloop"] += 1
            continue
        if e["subject"] not in ents or e["object"] not in ents:
            stats["skipped_selfloop"] += 1  # 端点实体不在库（悬挂边）——同槽披露
            continue
        key = (e["subject"], e["rel_type"], e["object"])
        r = rels.setdefault(key, {"src_id": e["subject"], "tgt_id": e["object"], "keywords": e["rel_type"],
                                  "description": [], "source_id": [], "weight": 0})
        txt = e["fact"] or e["rel_type"]
        r["description"].append(txt)
        r["source_id"].append(e["record_id"])
    SEP = "\u0001"  # 占位，下面统一换成 LightRAG 的 <SEP>
    kg_entities, kg_rels, kg_chunks = [], [], []
    for e in ents.values():
        descs, srcs = _dedup(e["description"]), _dedup(e["source_id"])
        stats["merged_entity"] += len(e["description"]) - len(descs)
        kg_entities.append({"entity_name": e["entity_name"], "entity_type": e["entity_type"],
                            "description": SEP_TXT.join(descs), "source_id": SEP_TXT.join(srcs)})
    for r in rels.values():
        descs, srcs = _dedup(r["description"]), _dedup(r["source_id"])
        stats["merged_rel"] += len(r["description"]) - len(descs)
        kg_rels.append({"src_id": r["src_id"], "tgt_id": r["tgt_id"], "keywords": r["keywords"],
                        "description": SEP_TXT.join(descs), "source_id": SEP_TXT.join(srcs),
                        "weight": float(len(set(srcs)))})
    for rid in sorted({s for e in ents.values() for s in e["source_id"]}
                      | {s for r in rels.values() for s in r["source_id"]}):
        rec = rec_of(rid)
        txt = _record_text(rec)
        if txt:
            kg_chunks.append({"content": txt, "source_id": rid})
    stats.update({"entities": len(kg_entities), "relationships": len(kg_rels), "chunks": len(kg_chunks)})
    return {"entities": kg_entities, "relationships": kg_rels, "chunks": kg_chunks}, stats


SEP_TXT = "<SEP>"


def _dedup(seq: list[str]) -> list[str]:
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--feed", action="store_true")
    ns = ap.parse_args(argv)
    kg, stats = build_kg(STORE)
    print(json.dumps(stats, ensure_ascii=False))
    if ns.dry_run or not ns.feed:
        return 0
    WORK.mkdir(parents=True, exist_ok=True)
    from lightrag import LightRAG
    from lightrag.utils import EmbeddingFunc
    rag = LightRAG(working_dir=str(WORK),
                   embedding_func=EmbeddingFunc(embedding_dim=4096, func=_embed_batch),
                   llm_model_func=_llm_stub, llm_model_name="stub-no-llm")

    async def _feed():
        # 1.5.7 实测：custom-KG 路径不会自动初始化存储（JsonKVStorage._storage_lock=None
        # → index_done_callback 崩 NoneType async CM）。必须显式 initialize。
        await rag.initialize_storages()
        try:
            await rag.ainsert_custom_kg(kg)
        finally:
            await rag.finalize_storages()

    asyncio.run(_feed())
    print(json.dumps({"fed": True, **CNT, **stats}, ensure_ascii=False))
    (WORK / "_feed-report.json").write_text(
        json.dumps({"cnt": CNT, "stats": stats}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
