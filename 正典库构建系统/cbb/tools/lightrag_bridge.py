# -*- coding: utf-8 -*-
"""lightrag_bridge.py — 实验件：LightRAG 第五路召回（读副本，零查询期 LLM）。

纪律：
  · 关键词全部外部传入（hl/ll_keywords）→ 查询期 LLM 调用必须为 0（llm_calls() 断言）；
  · 只取结构化上下文（aquery_data），不生成、不裁决——产物并回主检索 RRF；
  · 副本只读（本件对正典库与 LightRAG 库均无写入）。
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
WORK = ROOT / "迷深实战-工作区" / "索引" / "lightrag-exp"

_rag = None
_initialized = False
CNT = {"llm_calls": 0, "emb_calls": 0, "emb_texts": 0}


def llm_calls() -> int:
    return CNT["llm_calls"]


async def _llm_stub(prompt, system_prompt=None, history_messages=[], **kwargs):  # noqa: ANN001
    CNT["llm_calls"] += 1
    return ""


async def _embed_batch(texts: list[str]) -> list[list[float]]:
    # 同导出件：1.5.7 队列 await 用户函数 → 协程 + to_thread（防堵看门狗）
    import urllib.request

    def _http(b):
        payload = json.dumps({"model": "text-embedding-qwen3-embedding-8b@q4_k_m", "input": b},
                             ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8080/v1/embeddings", data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            d = json.loads(r.read().decode("utf-8"))
        return [x["embedding"] for x in sorted(d["data"], key=lambda x: x["index"])]

    out: list[list[float]] = []
    B = 16
    for i in range(0, len(texts), B):
        b = texts[i:i + B]
        out.extend(await asyncio.to_thread(_http, b))
        CNT["emb_calls"] += 1
    CNT["emb_texts"] += len(texts)
    import numpy as np
    return np.asarray(out, dtype=np.float32)  # 1.5.7 契约：EmbeddingFunc.__call__ 取 result.size


LEX_CACHE: dict[str, tuple[set, dict]] = {}


def _canon_lexicon(store_root: Path):
    """canon 词表 = 全库实体名 ∪ 别名（跨库全集）。
    注：master 路①的 id2name 只扫 character 库，别名指向其他库实体时回退记录号——
    既有缺口在此不复制，本表全集扫。"""
    key = str(Path(store_root).resolve())
    if key in LEX_CACHE:
        return LEX_CACHE[key]
    store = Path(store_root)
    rid2name: dict[str, str] = {}
    names: set[str] = set()
    for f in sorted(store.glob("libraries/*/*/*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        nm = (rec.get("canonical") or {}).get("name")
        rid = rec.get("record_id")
        if nm and rid:
            rid2name[rid] = nm
            names.add(nm)
    alias2name: dict[str, str] = {}
    for row in (lambda p: [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
                if p.exists() else [])(store / "aliases.jsonl"):
        al, rid = row.get("alias"), row.get("entity_id")
        nm = rid2name.get(rid)
        if isinstance(al, str) and al and nm:
            alias2name[al] = nm
    LEX_CACHE[key] = (names, alias2name)
    return LEX_CACHE[key]


_IDISH = re.compile(r"cand-|rec-|[0-9a-f]{12}", re.I)


def mechanical_keywords(query: str, store_root: Path) -> tuple[list[str], list[str], dict]:
    """ll=实体级关键词——**只收词表内词，自造词零准入**：
    ① 别名/实体名在 query 中的精确命中（引号变体归一到 canon 原形）；
    ② 分词项仅当含 canon 词才收，且以 canon 原形入列；
       记录号形态（cand-*）与查询套语（"之间有什么关系"等非词表碎句）一律丢弃并计数。
    hl=主题级（本实验为空——主题词表未建，如实留空）。"""
    names, alias2name = _canon_lexicon(store_root)
    ll: list[str] = []
    dropped = {"record_id": 0, "非词表碎句": 0}

    def push(s: str):
        s = s.strip("『』「」···")
        if len(s) < 2:
            return
        if _IDISH.search(s):
            dropped["record_id"] += 1
            return
        if s not in names:  # 非 canon 原形 → 归一到含它的 canon 词
            canon = next((nm for nm in names if nm and (nm in s or s in nm)), None)
            if not canon:
                dropped["非词表碎句"] += 1
                return
            s = canon
        if s not in ll:
            ll.append(s)

    for al, nm in alias2name.items():
        if al in query:
            push(nm)
    for nm in names:
        if len(nm) >= 2 and nm in query:
            push(nm)
    for t in re.split(r"[\s，。？！、「」『』·]+", query):
        if len(t.strip("『』「」···")) >= 2:
            push(t)
    if not ll:
        # 非空兜底（v3）：纯描述式查询词表准入全空 → 碎句降级准入并披露口径，
        # **绝不落查询期 LLM**（v2 实测：空表会让 LightRAG 回退调 LLM 抽关键词，违零-LLM 判据）
        for t in re.split(r"[\s，。？！、「」『』·]+", query):
            tt = t.strip("『』「」···")
            if len(tt) >= 2 and not _IDISH.search(tt) and tt not in ll:
                ll.append(tt)
        dropped["空表碎句兜底"] = len(ll[:20])
    return [], ll[:20], dropped


def get_rag():
    global _rag
    if _rag is None:
        from lightrag import LightRAG
        from lightrag.utils import EmbeddingFunc
        WORK.mkdir(parents=True, exist_ok=True)
        _rag = LightRAG(working_dir=str(WORK),
                        embedding_func=EmbeddingFunc(embedding_dim=4096, func=_embed_batch),
                        llm_model_func=_llm_stub, llm_model_name="stub-no-llm")
    return _rag


_rid2name_cache: dict[Path, dict[str, str]] = {}


def _rid2name(store_root: Path) -> dict[str, str]:
    key = Path(store_root).resolve()
    if key not in _rid2name_cache:
        m: dict[str, str] = {}
        for f in Path(store_root).glob("libraries/*/*/*.json"):
            try:
                rec = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            nm = (rec.get("canonical") or {}).get("name")
            if nm:
                m[rec.get("record_id")] = nm
        _rid2name_cache[key] = m
    return _rid2name_cache[key]


async def fifth_recall_async(query: str, store_root: Path, top_k: int = 10, mode: str = "local") -> dict:
    """第五路（协程版）：调用方须在**同一个事件循环**内连续调用（跨 loop 会撞存储锁）。"""
    global _initialized
    rag = get_rag()
    if not _initialized:
        # 1.5.7 实测：存储不自动初始化（_storage_lock=None 崩）——显式 initialize
        await rag.initialize_storages()
        _initialized = True
    hl, ll, kw_dropped = mechanical_keywords(query, store_root)
    from lightrag import QueryParam
    param = QueryParam(mode=mode, only_need_context=True, top_k=top_k,
                       ll_keywords=ll, hl_keywords=hl, enable_rerank=False)
    data = await rag.aquery_data(query, param=param)
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        data = data["data"]  # aquery_data 外层是 {status,message,data,metadata}
    ents, rels, chunks = [], [], []
    if isinstance(data, dict):
        ents = data.get("entities") or []
        rels = data.get("relationships") or []
        chunks = data.get("chunks") or []
    names: list[str] = []
    for e in ents:
        n = e.get("entity_id") or e.get("entity_name") if isinstance(e, dict) else str(e)
        if n and n not in names:
            names.append(n)
    for r in rels:  # 关系端点并入（类2 需两端名齐）
        if isinstance(r, dict):
            for k in ("src_id", "tgt_id"):
                n = r.get(k)
                if n and n not in names:
                    names.append(n)
    m = _rid2name(store_root)
    for c in chunks:
        rid = (c.get("source_id") or c.get("id") or "") if isinstance(c, dict) else ""
        for piece in str(rid).split("<SEP>"):
            nm = m.get(piece.strip())
            if nm and nm not in names:
                names.append(nm)
    return {"names": names[:top_k], "entities": len(ents), "relationships": len(rels),
            "chunks": len(chunks), "mode": mode, "ll_keywords": ll, "kw_dropped": kw_dropped}


def fifth_recall(query: str, store_root: Path, top_k: int = 10, mode: str = "local") -> dict:
    """第五路（单发便捷版）：自带事件循环；批量请用 fifth_recall_async。"""
    return asyncio.run(fifth_recall_async(query, store_root, top_k, mode))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "迷深实战-本体库"))
    ap.add_argument("--q", required=True)
    ns = ap.parse_args()
    rep = fifth_recall(ns.q, Path(ns.store))
    rep["llm_calls"] = CNT["llm_calls"]
    print(json.dumps(rep, ensure_ascii=False, indent=1))
