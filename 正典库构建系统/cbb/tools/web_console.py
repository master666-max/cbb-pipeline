# -*- coding: utf-8 -*-
"""web_console.py — CBB 产出网页控制台（只读；标准库零依赖）。

把 CBB 全部产出搬上一个网页：六种检索模式 + 图谱可视化 + 决策账/隔离区/产出总览。
纪律：**对正典库与全部派生件只读**——本件只有 GET，无任何写入路径。
检索模式：关键词（正典库）/ 混合五路 / LightRAG 快速 / GraphRAG 完整（未建·哨兵A门控）/
骨架图（未建）/ LLM wiki（未建·规划中）；图谱页含链构造器（深度2）。

用法：py -X utf8 web_console.py [--port 8090] [--store <本体库>]
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "cbb-store"))
sys.path.insert(0, str(HERE.parent / "cbb-anchor"))
sys.path.insert(0, str(HERE.parent / "cbb-quarantine"))

import os
STORE = Path(os.environ.get("CBB_STORE") or (HERE.parent.parent / "迷深实战-本体库"))
INDEX = STORE.parent / "迷深实战-工作区" / "索引" / "lancedb"

import 检索层 as jl  # noqa: E402


def _graph_snapshot():
    from neo4j_export import collect_graph
    g = collect_graph(STORE)
    return {"nodes": [{"name": n["name"], "type": n["entity_type"], "lib": n["lib"]} for n in g["nodes"]],
            "edges": [{"s": e["subject"], "r": e["rel_type"], "t": e["object"],
                       "fact": (e["fact"] or "")[:80]} for e in g["edges"]]}


def api_search(mode: str, q: str, top_k: int = 10):
    if not q.strip():
        return {"error": "空查询"}
    if mode == "keyword":
        return {"mode": "关键词（正典库）", "hits": jl.keyword_recall(q, STORE, limit=top_k)}
    if mode == "hybrid":
        rep = jl.hybrid_search(q, STORE, INDEX, top_k=top_k, rerank=True,
                               graph_expand=None)
        return {"mode": "混合五路+重排", "top": rep["top"], "backend": rep["backend"],
                "口径": rep["口径"]}
    if mode == "lightrag":
        import lightrag_bridge as lb
        rep = lb.fifth_recall(q, STORE, top_k)
        return {"mode": "LightRAG 快速（第五路）", "names": rep["names"],
                "实体数": rep["entities"], "关系数": rep["relationships"]}
    if mode == "graphrag":
        return {"mode": "GraphRAG 完整检索", "status": "未建",
                "口径": "哨兵A 门控未解锁（全局归纳型查询<3）——解锁后走社区报告 map-reduce"}
    if mode == "skeleton":
        return {"mode": "骨架图检索", "status": "未建",
                "口径": "骨架图索引未构建（KET-RAG 式关键chunk骨架）"}
    if mode == "wiki":
        return {"mode": "LLM wiki", "status": "未建",
                "口径": "wiki 派生视图规划中（人物册/设定页，从正典库生成）"}
    return {"error": f"未知模式 {mode}"}


def api_chain(seed: str, depth: int = 2):
    import graph_chain as gc
    return {"seed": seed, "depth": depth, "chains": gc.chains([seed], depth=depth, max_chains=12)}


def api_decisions(limit: int = 50):
    p = STORE.parent / "决策账.jsonl"
    if not p.exists():
        p = HERE.parent.parent / "决策账.jsonl"
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    return {"total": len(rows), "tail": rows[-limit:]}


def api_quarantine():
    import cbb_quarantine as cq  # noqa: E402
    q = STORE / "quarantine-zone"
    items = [json.loads(x) for x in (q / "items.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    adjud = [json.loads(x) for x in (q / "adjudications.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    pend = [i for i in items if not any(a.get("item_id") == i.get("item_id") for a in adjud)]
    from collections import Counter
    return {"total": len(items), "pending": len(pend),
            "by_subclass": dict(__import__("collections").Counter(i.get("subclass") for i in items)),
            "pending样例": [{"item_id": i.get("item_id"), "subclass": i.get("subclass"),
                              "detail": (i.get("detail") or "")[:100]} for i in pend[:10]]}


def api_outputs():
    import lightrag_live  # noqa: F401  仅确认哨件可导入
    inv = {"正典库": {"libraries": str(STORE / "libraries"),
                      "侧车": sorted(f.name for f in STORE.glob("*.json*"))},
           "派生件": {"正典图": "Neo4j 7695（682节点/1645边）",
                      "Graphiti双时序": "Neo4j 7693（随章摄入）",
                      "向量库": "records+evidence（LanceDB）",
                      "LightRAG副本": "lightrag-exp（live哨 1s 同步）",
                      "查询日志": "logs/query-log.jsonl"},
           "账与哨": {"决策账": "append-only 裁定账",
                      "账本哈希链": "ledger.jsonl（verify 门）",
                      "隔离区": "quarantine-zone（pending/裁决）",
                      "实时哨心跳": "_live-heartbeat"}}
    return {"outputs": inv, "口径": "全部派生件可随时全量重建；正典库+决策账是唯一真源"}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: str, ctype: str = "application/json; charset=utf-8"):
        raw = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):  # noqa: N802
        try:
            u = urllib.parse.urlparse(self.path)
            q = dict(urllib.parse.parse_qsl(u.query))
            if u.path == "/":
                html = (HERE / "web_console.html").read_text(encoding="utf-8")
                return self._send(200, html, "text/html; charset=utf-8")
            if u.path == "/api/search":
                return self._send(200, json.dumps(api_search(q.get("mode", "keyword"), q.get("q", ""),
                                                              int(q.get("k", 10))), ensure_ascii=False))
            if u.path == "/api/graph":
                return self._send(200, json.dumps(_graph_snapshot(), ensure_ascii=False))
            if u.path == "/api/chain":
                return self._send(200, json.dumps(api_chain(q.get("seed", ""), int(q.get("depth", 2))),
                                                  ensure_ascii=False))
            if u.path == "/api/decisions":
                return self._send(200, json.dumps(api_decisions(int(q.get("limit", 50))), ensure_ascii=False))
            if u.path == "/api/quarantine":
                return self._send(200, json.dumps(api_quarantine(), ensure_ascii=False))
            if u.path == "/api/debug":
                import urllib.request as _u
                import graph_chain as _gc
                try:
                    with _u.urlopen("http://localhost:7695/", timeout=5) as r:
                        neo = "ok " + str(r.status)
                except Exception as _e:
                    neo = f"{type(_e).__name__}: {str(_e)[:80]}"
                return self._send(200, json.dumps({"proxies": _u.getproxies(),
                    "neo4j_http_direct": neo, "gc_BASE": _gc.BASE,
                    "proxy_env": sorted(k for k in os.environ if "proxy" in k.lower())},
                    ensure_ascii=False))
            if u.path == "/api/outputs":
                return self._send(200, json.dumps(api_outputs(), ensure_ascii=False))
            self._send(404, json.dumps({"error": "not found"}))
        except Exception as e:  # noqa: BLE001
            self._send(500, json.dumps({"error": f"{type(e).__name__}: {str(e)[:200]}"}))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8090)
    ns = ap.parse_args(argv)
    print(json.dumps({"web_console": True, "url": f"http://127.0.0.1:{ns.port}",
                      "store": str(STORE), "纪律": "只读"}, ensure_ascii=False))
    ThreadingHTTPServer(("127.0.0.1", ns.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
