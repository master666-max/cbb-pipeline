# -*- coding: utf-8 -*-
"""graph_chain.py — 图检索链构造器（深度参数化；读 Neo4j 真源，零 LLM）。

设计：
  · **深度=推断步长**：depth=1 取"实体—关系→实体"单步；depth=2 允许两步传递链
    （A—r1→B—r2→C），供"经由谁间接…"类推断；链是有序结构化上下文，不进 RRF 摊平。
  · **与流程深度同步**：图由 run_chapter 的 aux 段逐章增量导出——本件每次查询都读
    当前图状态，链天然反映"已啃到的进度"，无需独立索引维护。
  · 只读；凭据走 derive_password（docker inspect，D-004 不落文件）。
"""
from __future__ import annotations

import base64
import json
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
import os
BASE = os.environ.get("NEO4J_HTTP", "http://localhost:7695")  # 跨机：env 覆盖
_PW = None


def _pw() -> str:
    global _PW
    if _PW is None:
        import sys
        sys.path.insert(0, str(HERE))
        from neo4j_export import derive_password
        _PW = derive_password(None)
        if not _PW:
            raise RuntimeError("Neo4j 凭据不可得（docker inspect/env）")
    return _PW


def _cypher(statement: str, params: dict) -> list[dict]:
    body = json.dumps({"statements": [{"statement": statement, "parameters": params}]}).encode("utf-8")
    req = urllib.request.Request(BASE + "/db/neo4j/tx/commit", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Basic " + base64.b64encode(
                                              f"neo4j:{_pw()}".encode()).decode()})
    with urllib.request.urlopen(req, timeout=20) as r:
        out = json.loads(r.read().decode("utf-8"))
    if out.get("errors"):
        raise RuntimeError(f"Cypher 错误: {out['errors'][:1]}")
    return out["results"][0]["data"]


def _hop(nodes: list[str], limit_per_node: int) -> dict[str, list[dict]]:
    """一跳邻接：{起点名: [{to, rel, fact, edge_id, valid_at, invalid_at}]}（双向）。"""
    adj: dict[str, list[dict]] = {n: [] for n in nodes}
    for n in nodes:
        rows = _cypher("MATCH (a:Entity {name:$n})-[r:REL]-(b:Entity) "
                       "WHERE b.name <> $n RETURN b.name AS to, r.rel_type AS rel, r.fact AS fact, "
                       "r.edge_id AS edge_id, r.valid_at AS valid_at, r.invalid_at AS invalid_at "
                       "LIMIT $lim", {"n": n, "lim": limit_per_node})
        for d in rows:
            row = d["row"]
            adj[n].append({"to": row[0], "rel": row[1], "fact": row[2],
                           "edge_id": row[3], "valid_at": row[4], "invalid_at": row[5]})
    return adj


def chains(seeds: list[str], depth: int = 1, max_chains: int = 8,
           limit_per_node: int = 8) -> list[dict]:
    """从种子实体出发构造证据链。输出有序链：
    depth=1 → [{"nodes": [A, B], "hops": [{from, rel, fact, edge_id, to}]}]
    depth=2 → 三节点传递链（B 作第二跳起点，不回访已访节点）。
    链不进 RRF（结构化上下文与 top-k 并列交付——推理的原料形态）。"""
    if depth not in (1, 2):
        raise ValueError("depth 仅支持 1|2")
    seeds = [s for s in seeds if s][:5]
    if not seeds:
        return []
    adj1 = _hop(seeds, limit_per_node)
    out: list[dict] = []
    seen_edges: set[tuple] = set()
    for a in seeds:
        for h1 in adj1[a]:
            key = (a, h1["edge_id"], h1["to"])
            if key in seen_edges:
                continue
            seen_edges.add(key)
            out.append({"nodes": [a, h1["to"]],
                        "hops": [{"from": a, "rel": h1["rel"], "fact": h1["fact"],
                                  "edge_id": h1["edge_id"], "to": h1["to"],
                                  "valid_at": h1["valid_at"], "invalid_at": h1["invalid_at"]}]})
    if depth == 2:
        frontier = sorted({h["to"] for a in seeds for h in adj1[a]})
        adj2 = _hop(frontier, limit_per_node)
        for a in seeds:
            for h1 in adj1[a]:
                for h2 in adj2.get(h1["to"], []):
                    if h2["to"] in (a, h1["to"]) or h2["edge_id"] == h1["edge_id"]:
                        continue
                    key2 = (h1["to"], h2["edge_id"], h2["to"])
                    if key2 in seen_edges:
                        continue
                    seen_edges.add(key2)
                    out.append({"nodes": [a, h1["to"], h2["to"]],
                                "hops": [{"from": a, "rel": h1["rel"], "fact": h1["fact"],
                                          "edge_id": h1["edge_id"], "to": h1["to"],
                                          "valid_at": h1["valid_at"], "invalid_at": h1["invalid_at"]},
                                         {"from": h1["to"], "rel": h2["rel"], "fact": h2["fact"],
                                          "edge_id": h2["edge_id"], "to": h2["to"],
                                          "valid_at": h2["valid_at"], "invalid_at": h2["invalid_at"]}]})
    return out[:max_chains]
