# -*- coding: utf-8 -*-
"""graph_audit.py — 图谱↔正典库对账（段收口常态断言；不干扰图谱：只读+披露，不改写任何一侧）。

断言面：
  A 节点集：图 :Entity 名集 vs 库实体名集——图多出（库外节点）与图缺少（导出缺口）双侧披露；
  B 边集：(src, rel_type, tgt) 三元组双侧对比；
  C 时序一致性：抽样边的 valid_at/invalid_at 与库内记录重算值对比；
  D D2 侧车：evidence-graph-edges.jsonl 的 edge_id 与图边 edge_id 键级对账。
出口=报告（差异计数+样例）；差异不是失败，是隔离区/导出账的输入（T-5 每数带口径）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "cbb-store"))
sys.path.insert(0, str(HERE.parent / "contracts"))

from neo4j_export import collect_graph  # noqa: E402


def audit(store_root: Path, base: str | None = None) -> dict:
    import os
    base = base or os.environ.get("NEO4J_HTTP", "http://localhost:7695")
    import graph_chain as gc  # 复用鉴权与 _cypher
    gc.BASE = base
    store_root = Path(store_root)
    graph = collect_graph(store_root)
    lib_nodes = {n["name"] for n in graph["nodes"]}
    lib_edges = {(e["subject"], e["rel_type"], e["object"]) for e in graph["edges"]}

    g_nodes = {d["row"][0] for d in gc._cypher("MATCH (a:Entity) RETURN a.name AS n", {})}
    g_edges = {(d["row"][0], d["row"][1], d["row"][2]) for d in gc._cypher(
        "MATCH (a:Entity)-[r:REL]->(b:Entity) RETURN a.name, r.rel_type, b.name", {})}

    extra_nodes = sorted(g_nodes - lib_nodes)
    missing_nodes = sorted(lib_nodes - g_nodes)
    extra_edges = sorted(g_edges - lib_edges)
    missing_edges = sorted(lib_edges - g_edges)

    # C 时序一致性（全量边对比，机械可复算）
    lib_temporal = {}
    for e in graph["edges"]:
        lib_temporal[(e["subject"], e["rel_type"], e["object"])] = (
            e.get("valid_at"), e.get("invalid_at"))
    temporal_mismatch = []
    for d in gc._cypher("MATCH (a:Entity)-[r:REL]->(b:Entity) "
                        "RETURN a.name, r.rel_type, b.name, r.valid_at, r.invalid_at LIMIT 5000", {}):
        row = d["row"]
        key = (row[0], row[1], row[2])
        if key in lib_temporal and lib_temporal[key] != (row[3], row[4]):
            temporal_mismatch.append({"edge": key, "graph": (row[3], row[4]),
                                      "library": lib_temporal[key]})

    # D D2 侧车对账
    sidecar = store_root / "evidence-graph-edges.jsonl"
    sidecar_ids, unknown_edge_ids = set(), []
    if sidecar.exists():
        for ln in sidecar.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            eid = (json.loads(ln).get("graph_edge") or {}).get("edge_id")
            if eid:
                sidecar_ids.add(eid)
    if sidecar_ids:
        graph_edge_ids = {d["row"][0] for d in gc._cypher(
            "MATCH ()-[r:REL]->() RETURN r.edge_id AS e", {})}
        unknown_edge_ids = sorted(sidecar_ids - graph_edge_ids)[:20]

    report = {
        "节点": {"图": len(g_nodes), "库": len(lib_nodes),
                 "图外节点": extra_nodes[:20], "图外节点数": len(extra_nodes),
                 "未导出实体": missing_nodes[:20], "未导出实体数": len(missing_nodes)},
        "边": {"图": len(g_edges), "库": len(lib_edges),
               "图外边数": len(extra_edges), "未导出边数": len(missing_edges),
               "样例": {"图外": [list(x) for x in extra_edges[:5]],
                        "未导出": [list(x) for x in missing_edges[:5]]}},
        "时序不一致数": len(temporal_mismatch), "时序不一致样例": temporal_mismatch[:5],
        "D2侧车": {"edge_id 数": len(sidecar_ids), "图上无此 edge_id 数": len(unknown_edge_ids),
                   "样例": unknown_edge_ids},
        "口径": "图=neo4j_export 派生（章收口增量）；差异披露不改写——导出缺口走重导，库外节点走隔离区裁决",
    }
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True)
    ap.add_argument("--base", default="http://localhost:7695",
                    help="派生图 HTTP 端点（与实例解耦——通用件，无实例默认值）")
    ap.add_argument("--out", default="")
    ns = ap.parse_args(argv)
    rep = audit(Path(ns.store), base=ns.base)
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    if ns.out:
        Path(ns.out).write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
