# -*- coding: utf-8 -*-
"""kg_export.py — 批次 6·知识图谱导出（LightRAG / GraphML / 三元组 CSV）。

从正典库产出三种图谱格式，供 RAG/图分析管线消费：
  1. LightRAG entities.jsonl + relationships.jsonl
  2. GraphML（NetworkX / Gephi 通用）
  3. 三元组 CSV（subject,predicate,object — triplestore 直用）

用法：py -X utf8 kg_export.py --store 迷深实战-本体库 --out kg-export/
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "cbb-v2"))


def load_store(store_root: str):
    store = Path(store_root)
    entities = []
    relations = []
    for f in sorted((store / "libraries").glob("*/*/*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        lib = r.get("library", "")
        canon = r.get("canonical") or {}
        if lib == "relation":
            relations.append(r)
        else:
            nm = canon.get("name") or r["record_id"]
            etype = canon.get("entity_type") or canon.get("category") or lib
            desc_parts = []
            if canon.get("fact"):
                desc_parts.append(canon["fact"])
            if canon.get("description"):
                desc_parts.append(canon["description"])
            if canon.get("title"):
                desc_parts.append(canon["title"])
            for e in (r.get("evidence") or [])[:3]:
                if isinstance(e, dict) and e.get("quote"):
                    desc_parts.append(e["quote"])
            entities.append({
                "record_id": r["record_id"],
                "entity_name": nm,
                "entity_type": etype,
                "description": "；".join(desc_parts)[:2000],
                "status": r.get("status", "provisional"),
                "aliases": r.get("_aliases") or [],
                "chapters": sorted({e.get("chapter") for e in (r.get("evidence") or []) if isinstance(e, dict) and e.get("chapter")}),
            })
    return entities, relations


def _xml_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def export_lightrag(entities, relations, out: Path):
    """LightRAG 格式：entities.jsonl + relationships.jsonl"""
    ent_out = out / "lightrag_entities.jsonl"
    with ent_out.open("w", encoding="utf-8") as f:
        for e in entities:
            f.write(json.dumps({
                "entity_name": e["entity_name"],
                "entity_type": e["entity_type"],
                "description": e["description"],
                "source_id": e["record_id"],
            }, ensure_ascii=False) + "\n")

    rel_out = out / "lightrag_relationships.jsonl"
    with rel_out.open("w", encoding="utf-8") as f:
        for r in relations:
            canon = r.get("canonical") or {}
            sub, pred, obj = canon.get("subject"), canon.get("rel_type") or canon.get("predicate"), canon.get("object")
            if sub and obj:
                f.write(json.dumps({
                    "source": sub,
                    "target": obj,
                    "description": f"{sub} —{pred or '关联'}→ {obj}",
                    "keywords": pred or "关联",
                    "weight": 1.0,
                    "source_id": r["record_id"],
                    "status": r.get("status", "provisional"),
                }, ensure_ascii=False) + "\n")
    return ent_out, rel_out


def export_graphml(entities, relations, out: Path):
    """GraphML（NetworkX/Gephi 通用格式）"""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
        '  <key id="name" for="node" attr.name="name" attr.type="string"/>',
        '  <key id="type" for="node" attr.name="type" attr.type="string"/>',
        '  <key id="status" for="node" attr.name="status" attr.type="string"/>',
        '  <key id="desc" for="node" attr.name="description" attr.type="string"/>',
        '  <key id="label" for="edge" attr.name="label" attr.type="string"/>',
        '  <key id="status" for="edge" attr.name="status" attr.type="string"/>',
        '  <graph id="G" edgedefault="directed">',
    ]
    node_ids = set()
    for e in entities:
        nid = e["entity_name"]
        if nid in node_ids:
            continue
        node_ids.add(nid)
        desc = (e.get("description") or "")[:300].replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")
        lines.append(f'    <node id="{_xml_escape(nid)}">'
                     f'<data key="name">{_xml_escape(nid)}</data>'
                     f'<data key="type">{_xml_escape(e["entity_type"])}</data>'
                     f'<data key="status">{e["status"]}</data>'
                     f'<data key="desc">{desc}</data></node>')
    for r in relations:
        canon = r.get("canonical") or {}
        sub, pred, obj = canon.get("subject"), canon.get("rel_type") or canon.get("predicate"), canon.get("object")
        if sub and obj and sub in node_ids and obj in node_ids:
            lines.append(f'    <edge source="{_xml_escape(sub)}" target="{_xml_escape(obj)}">'
                         f'<data key="label">{_xml_escape(pred or "关联")}</data></edge>')
    lines.append("  </graph>")
    lines.append("</graphml>")
    out.joinpath("knowledge-graph.graphml").write_text("\n".join(lines), encoding="utf-8")


def export_triples(entities, relations, out: Path):
    """三元组 CSV：subject,predicate,object,status,source_record_id"""
    lines = ["subject,predicate,object,status,source_record_id"]
    for r in relations:
        canon = r.get("canonical") or {}
        sub, pred, obj = canon.get("subject"), canon.get("rel_type") or canon.get("predicate"), canon.get("object")
        st = r.get("status", "provisional")
        if sub and obj:
            lines.append(f'"{sub}","{pred or "关联"}","{obj}","{st}"')
    for e in entities:
        lines.append(f'"{e["entity_name"]}","是类型","{e["entity_type"]}","{e["status"]}","{e["record_id"]}"')
    out.joinpath("triples.csv").write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True)
    ap.add_argument("--out", default="kg-export")
    ns = ap.parse_args()

    out = Path(ns.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    entities, relations = load_store(ns.store)
    print(f"实体 {len(entities)} | 关系 {len(relations)}")

    export_lightrag(entities, relations, out)
    export_graphml(entities, relations, out)
    export_triples(entities, relations, out)

    for f in sorted(out.iterdir()):
        print(f"  {f.name}: {f.stat().st_size / 1024:.0f}KB")


if __name__ == "__main__":
    main()
