# -*- coding: utf-8 -*-
"""派生层对账.py — 图谱与向量库与正典库三方计数对账（半途写不留痕这件事必须有个哨）

为什么需要（2026-09-25 本机实测，LightRAG 1.5.7 直灌）：
  嵌入端点中途挂掉时，`acreate_entity` 已经把节点写进了图（graphml 里能看到
  entity_id/entity_type/description/source_id 全在），向量库却没写——
  **半途写、非事务**。后果不是报错而是静默不一致：图里查得到、向量召回不到，
  用 local/hybrid 模式检索时会以为"这本书没有这条"，与真没有完全同形。
  所以灌完必须双查，不许拿"跑成功了"当对账。

四道检查（有任一不过 ⇒ 退出码 1，可当闸门）：
  C1 图节点数 == 实体向量库记录数（并列出两侧差集）
  C2 图边数   == 关系向量库记录数
  C3 每个节点必须带来源位（source_id / file_path / _id 之外的任一坐标字段）⇒ 缺坐标清单
  C4 与正典库对账：派生层名字在正典名单里的字面命中率（**只报数不判通过**，
     命中率高不等于对得上，见 实体名归因.py 的分类处置）

用法：
  py -X utf8 派生层对账.py --graph lightrag/graph_chunk_entity_relation.graphml \
      --vdb lightrag/vdb_entities.json lightrag/vdb_relationships.json \
      [--canon 本体库/records.jsonl] [--name-field canonical_name]
输入兼容：LightRAG 的 graphml+vdb json，与 GraphRAG 的 entities.parquet→jsonl 导出（jsonl 亦可）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

COORD_KEYS = ("source_id", "file_path", "coordinates", "coord", "text_unit_ids")
NAME_KEYS = ("name", "title", "canonical_name", "entity_name", "entity_id")
SEP_RE = re.compile(r"[\s\u3000·・‧⋅•.。_－—–\-/、,，:：;；]")


def canon(s: str) -> str:
    return SEP_RE.sub("", unicodedata.normalize("NFKC", str(s))).lower()


def graphml_nodes(path: Path) -> tuple[list[dict], int]:
    """读 graphml：返回 (节点属性表, 边数)。只用正则，不引第三方图库。"""
    txt = path.read_text(encoding="utf-8")
    keys = dict(re.findall(r'<key\s+id="(d\d+)"[^>]*attr\.name="([^"]+)"', txt))
    nodes: list[dict] = []
    for body in re.findall(r'<node\s+id="[^"]*">(.*?)</node>', txt, re.DOTALL):
        d = {keys.get(k, k): v for k, v in
             re.findall(r'<data\s+key="(d\d+)"[^>]*>(.*?)</data>', body, re.DOTALL)}
        nodes.append(d)
    n_edge = len(re.findall(r"<edge\s", txt))
    return nodes, n_edge


def jsonl_rows(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out.append(r if isinstance(r, dict) else {"name": str(r)})
    return out


def load_graph(path: Path) -> tuple[list[dict], int]:
    if path.suffix in {".jsonl", ".json"}:
        rows = jsonl_rows(path) if path.suffix == ".jsonl" else json.loads(
            path.read_text(encoding="utf-8"))
        return (rows if isinstance(rows, list) else rows.get("entities", [])), 0
    return graphml_nodes(path)


def vdb_count(path: Path) -> tuple[int, list[str]]:
    """LightRAG 的 nano-vectordb json：{"data":[{...}]} 或直接 list；返回 (条数, 名字列表)。"""
    d = json.loads(path.read_text(encoding="utf-8"))
    rows = d.get("data", d) if isinstance(d, dict) else d
    if isinstance(rows, dict):
        rows = list(rows.values())
    names = []
    for r in rows if isinstance(rows, list) else []:
        if isinstance(r, dict):
            nm = next((str(r[k]) for k in NAME_KEYS if r.get(k)), "")
            names.append(nm)
    return len(names), names


def name_of(row: dict) -> str:
    return next((str(row[k]) for k in NAME_KEYS if row.get(k)), "")


def main() -> int:
    ap = argparse.ArgumentParser(description="派生层三方计数对账（半途写的哨）")
    ap.add_argument("--graph", required=True, type=Path, help="graphml 或 entities jsonl")
    ap.add_argument("--vdb", nargs="*", type=Path, default=[],
                    help="实体向量库与关系向量库 json（按顺序：实体在前、关系在后）")
    ap.add_argument("--canon", type=Path, default=None, help="正典库记录 jsonl（可选）")
    ap.add_argument("--out", type=Path, default=None)
    ns = ap.parse_args()

    nodes, n_edge = load_graph(ns.graph)
    ent_vdb = vdb_count(ns.vdb[0])[0] if ns.vdb else None
    rel_vdb = vdb_count(ns.vdb[1])[0] if len(ns.vdb) > 1 else None

    缺坐标 = [name_of(r) for r in nodes
              if not any(r.get(k) for k in COORD_KEYS)]
    图名 = {canon(name_of(r)) for r in nodes if name_of(r)}
    v名 = {canon(n) for n in (vdb_count(ns.vdb[0])[1] if ns.vdb else []) if n}
    canon_names: set[str] = set()
    if ns.canon:
        canon_names = {canon(name_of(r)) for r in jsonl_rows(ns.canon) if name_of(r)}
    报告: dict = {
        "口径": {"图文件": str(ns.graph), "向量库文件": [str(p) for p in ns.vdb],
                 "坐标字段": list(COORD_KEYS), "名字归一口径": "去分隔符+NFKC+小写"},
        "计数": {"图节点": len(nodes), "图边": n_edge,
                 "实体向量": ent_vdb, "关系向量": rel_vdb,
                 "缺坐标节点": len(缺坐标)},
        "差集": {"图有向量无": sorted(图名 - v名) if ns.vdb else "未给向量库",
                 "向量有图无": sorted(v名 - 图名) if ns.vdb else "未给向量库"},
        "缺坐标清单": 缺坐标[:50],
    }

    if ns.canon:
        命中 = sorted(n for n in 图名 if n in canon_names)
        报告["与正典对账"] = {
            "正典名单规模": len(canon_names),
            "派生层名字命中正典": f"{len(命中)}/{len(图名)}",
            "口径上界": "命中率高≠对得上：字面相同可能异义，未命中也可能是自造标签"
                        "（分类处置走 实体名归因.py）。本栏只报数，不作通过判据。",
        }

    fail = []
    if ent_vdb is not None and ent_vdb != len(nodes):
        fail.append(f"C1 图节点 {len(nodes)} ≠ 实体向量 {ent_vdb} ⇒ 半途写，向量召回会漏")
    if rel_vdb is not None and n_edge and rel_vdb != n_edge:
        fail.append(f"C2 图边 {n_edge} ≠ 关系向量 {rel_vdb}")
    if 缺坐标:
        fail.append(f"C3 {len(缺坐标)} 个节点无来源位（不可回落原文）")
    if ns.canon and not canon_names:
        fail.append("C4 正典名单为空 ⇒ 判定面为空，不许读成『都对得上』（判定面非空纪律）")
    报告["结论"] = "PASS" if not fail else "FAIL"
    报告["未过项"] = fail

    s = json.dumps(报告, ensure_ascii=False, indent=1)
    if ns.out:
        ns.out.write_text(s, encoding="utf-8")
    print(s)
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
