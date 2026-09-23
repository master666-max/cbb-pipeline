# -*- coding: utf-8 -*-
"""检索层.py — L6 混合检索（U-F07 · 引擎=LanceDB 已裁 · 2026-09-23）

四路召回 → RRF 融合（纯公式）→ 本地重排精排（岗位④）→ **引文核验**。
纪律：
  · **对正典库只读**——全流程零写本体库（EXPLAIN 拒写同源）；
  · **向量只做召回、绝不裁决**——最终结果必须过引文核验，落不回就拒答/标"未核实"；
  · **缺席即降级**：向量路（索引/嵌入端点缺席）→退化为"别名＋关键词"两路；重排缺席→RRF 序；
    图路（Neo4j 缺席）→跳过。每级降级都在结果的"口径"里注明（T-5）。
  · 按查询计费（不触"×单元数"乘法线）；单次 token 记入返回值。

索引件（由 build_index 生成，属派生件、可随时重建）：
    <索引目录>/records.lance —— {record_id, name, text, vector(4096), library, status}
    <索引目录>/evidence.lance —— {record_id, chapter, line, quote, vector(4096)}
嵌入：本地 OpenAI 兼容端点（LM Studio /v1/embeddings，q4_k_m 常驻档）。
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.request
from pathlib import Path

import 重排器 as rr


# ---------- 嵌入（本地端点） ----------

def embed(texts: list[str], base: str | None = None, model: str = "text-embedding-qwen3-embedding-8b",
          timeout: float = 60.0, transport=None) -> list[list[float]] | None:
    base = base or os_env("EMBED_HTTP", "http://127.0.0.1:8080/v1/embeddings")
    payload = json.dumps({"model": model, "input": texts}, ensure_ascii=False).encode("utf-8")
    try:
        raw = (transport or _http_post)(base, payload, timeout)
        data = json.loads(raw)
        arr = sorted(data["data"], key=lambda x: x["index"])
        return [d["embedding"] for d in arr]
    except Exception:
        return None


def _http_post(url: str, payload: bytes, timeout: float) -> str:
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


def os_env(k: str, d: str) -> str:  # 便于测试注入
    import os
    return os.environ.get(k, d)


# ---------- 别名/专名精确召回（路①，机械） ----------

def alias_recall(query: str, store_root: Path) -> list[dict]:
    """专名/别名**精确命中**：query 中出现的实体名或别名 → 其记录。确定性，零模型。"""
    q = query
    hits: dict[str, dict] = {}
    id2name: dict[str, str] = {}
    store = Path(store_root)
    for f in sorted(store.glob("libraries/character/*/*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        nm = (rec.get("canonical") or {}).get("name")
        if nm:
            id2name[rec.get("record_id")] = nm
    for row in _jsonl(store / "aliases.jsonl"):
        al = row.get("alias")
        if isinstance(al, str) and al and al in q:
            rid = row.get("entity_id")
            nm = id2name.get(rid, rid)
            if nm:
                hits[nm] = {"name": nm, "record_id": rid, "via": "alias"}
    for nm in id2name.values():
        if len(nm) >= 2 and nm in q:
            hits[nm] = {"name": nm, "record_id": None, "via": "exact"}
    return list(hits.values())


def _jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


# ---------- RRF 融合（纯公式，可复算） ----------

def rrf(rank_lists: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """多路名次融合：score(item) = Σ 1/(k+rank_i)。输入=各路的 item 名次序。"""
    acc: dict[str, float] = {}
    for lst in rank_lists:
        for rank, item in enumerate(lst):
            acc[item] = acc.get(item, 0.0) + 1.0 / (k + rank + 1)
    return sorted(acc.items(), key=lambda x: -x[1])


# ---------- 引文核验 ----------

def verify_citations(citations: list[dict], store_root: Path) -> dict:
    """答案里的引文必须能回落到**库内既有证据**（record_id + quote 逐字匹配）。
    落不回 → 该引文标记 unverified（调用方据此拒答或标注）。只读。"""
    pool: set[tuple[str, str]] = set()
    store = Path(store_root)
    for f in sorted(store.glob("libraries/relation/*/*.json")) + sorted(
            store.glob("libraries/character/*/*.json")) + sorted(
            store.glob("libraries/setting/*/*.json")) + sorted(
            store.glob("libraries/event/*/*.json")) + sorted(
            store.glob("libraries/foreshadow/*/*.json")) + sorted(
            store.glob("libraries/timeline/*/*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        rid = rec.get("record_id")
        for ev in rec.get("evidence") or []:
            pool.add((rid, ev.get("quote")))
    ok, bad = [], []
    for c in citations:
        key = (c.get("record_id"), c.get("quote"))
        (ok if key in pool else bad).append(c)
    return {"verified": ok, "unverified": bad,
            "口径": "核验=record_id+quote 在库内证据集中逐字存在"}


# ---------- 混合检索主入口 ----------

def hybrid_search(query: str, store_root: Path, index_dir: Path | None = None,
                  top_k: int = 10, rerank: bool = True,
                  graph_expand=None, embed_fn=embed, rerank_transport=None) -> dict:
    """四路召回→RRF→（可选）重排→核验占位。
    graph_expand: callable(seed_names) -> list[name]（由调用方接 Neo4j；缺席=None 跳过）。
    向量路需要 index_dir 且 lancedb 可用且嵌入端点在线——任一缺席→该路跳过并在口径注明。"""
    notes: list[str] = []
    paths: list[list[str]] = []

    # 路①别名/专名（机械，恒可用）
    p1 = [h["name"] for h in alias_recall(query, store_root)]
    paths.append(p1)
    if p1:
        notes.append(f"别名精确命中 {len(p1)}")

    # 路②关键词（LanceDB FTS；索引缺席→退化为 query 分词对 record 文本的包含匹配，仍机械可用）
    kw = keyword_recall(query, store_root)
    paths.append([x["name"] for x in kw])
    if index_dir is None or not Path(index_dir).exists():
        notes.append("向量路缺席：索引未建（本查询退化为 别名+关键词+图 三路）")

    # 路③向量（需索引＋嵌入端点）
    if index_dir and Path(index_dir).exists():
        try:
            import lancedb  # noqa: F401
            qv = embed_fn([query])
            if qv:
                db = _db(index_dir)
                tbl = _open_table(db, "records")
                if tbl is not None:
                    res = tbl.search(qv[0]).limit(top_k).to_list()
                    paths.append([r.get("name") for r in res])
                    notes.append("向量路命中")
        except Exception as e:
            notes.append(f"向量路缺席（{str(e)[:40]}）")
    else:
        notes.append("向量路缺席：索引未建")

    # 路④图扩展（可选）
    if graph_expand:
        seeds = [h["name"] for h in alias_recall(query, store_root)][:5]
        ext = graph_expand(seeds)
        paths.append(ext)
        if ext:
            notes.append(f"图扩展 {len(ext)} 项")

    fused = rrf([p for p in paths if p])
    ranked = [(n, s) for n, s in fused]

    # 岗位④重排精排（缺席→RRF 序）
    backend = "rrf"
    if rerank and ranked:
        names = [n for n, _ in ranked]
        mech = list(range(len(names)))
        o, bk = rr.rerank_order_or_mechanical(query, names, mech)
        ranked = [(names[i], ranked[i][1] if i < len(ranked) else 0.0) for i in o]
        backend = bk

    top = [{"name": n, "rrf": round(s, 6)} for n, s in ranked[:top_k]]
    return {"top": top, "backend": backend, "paths": len([p for p in paths if p]),
            "口径": "；".join(notes) or "无降级"}


def keyword_recall(query: str, store_root: Path, limit: int = 10) -> list[dict]:
    """路②关键词：确定性包含匹配（索引缺席时的机械降级；FTS 建成后由 LanceDB 接管）。
    中文无空格 → 标点切分＋二元切分（bigram）取词，均为机械规则。"""
    terms = {t for t in re.split(r"[\s，。？！、]+", query) if len(t) >= 2}
    for t in list(terms):
        for i in range(len(t) - 1):
            terms.add(t[i:i + 2])
    hits: list[dict] = []
    seen: set[str] = set()
    store = Path(store_root)
    for f in sorted(store.glob("libraries/character/*/*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        nm = (rec.get("canonical") or {}).get("name") or ""
        if nm in seen:
            continue
        text = nm + json.dumps(rec.get("observations", []), ensure_ascii=False)
        score = sum(1 for t in terms if t in text)
        if score:
            hits.append({"name": nm, "score": score})
            seen.add(nm)
    hits.sort(key=lambda x: -x["score"])
    return hits[:limit]


def _db(index_dir: Path):
    import lancedb
    return lancedb.connect(str(index_dir))


def _open_table(db, name: str):
    try:
        return db.open_table(name)
    except Exception:
        return None


def main(argv=None) -> int:  # pragma: no cover
    ap = argparse.ArgumentParser(description="L6 混合检索（U-F07）")
    ap.add_argument("--store", required=True)
    ap.add_argument("--q", required=True)
    ap.add_argument("--index")
    ap.add_argument("--top-k", type=int, default=10)
    ns = ap.parse_args(argv)
    rep = hybrid_search(ns.q, Path(ns.store), Path(ns.index) if ns.index else None, ns.top_k)
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
