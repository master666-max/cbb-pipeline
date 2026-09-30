# -*- coding: utf-8 -*-
"""wiki_export.py — 批次 3·X2 交付形态导出器（快照范式 runner）。

用法：py -X utf8 wiki_export.py --store 迷深实战-本体库 --out 快照-迷深实战 [--sample-n 30]

流程：载入 store → 锚（ledger_head+计数）→ 渲染记录页/隔离页/索引/图谱 → 对账 → SNAPSHOT。
对账 FAIL ⇒ 退出码 1（快照已生成但标记 FAIL，不发布）。
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from cbb2 import export, notary  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--store", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--sample-n", type=int, default=30)
ns = ap.parse_args()

store = Path(ns.store).resolve()
out = Path(ns.out).resolve()

# 1 载入 store（只读）
records = []
for f in sorted((store / "libraries").glob("*/*/*.json")):
    records.append(json.loads(f.read_text(encoding="utf-8")))
recs_by_id = {r["record_id"]: r for r in records}

quarantine = []
qf = store / "quarantine-zone" / "items.jsonl"
if qf.exists():
    for l in qf.read_text(encoding="utf-8").splitlines():
        if l.strip():
            quarantine.append(json.loads(l))

comps = []
cf = store / "complementary-statements.jsonl"
if cf.exists():
    for l in cf.read_text(encoding="utf-8").splitlines():
        if l.strip():
            comps.append(json.loads(l))

sup = []
sf = store / "supersede-index.jsonl"
if sf.exists():
    for l in sf.read_text(encoding="utf-8").splitlines():
        if l.strip():
            sup.append(json.loads(l))

# 2 锚（计数前置，渲染可携带）
nodes, edges = export.project_graph(records)
head = notary.ledger_head(store)
anchor = export.build_anchor(store_root=store, ledger_head=head, record_count=len(records),
                             page_count=len(records), edge_count=len(edges))

# 3 渲染
pages = {}
for r in records:
    lib = r.get("library") or "misc"
    d = out / "wiki" / "records" / lib
    d.mkdir(parents=True, exist_ok=True)
    md = export.render_record_page(r, anchor)
    (d / f"{r['record_id']}.md").write_text(md, encoding="utf-8")
    pages[r["record_id"]] = md

qdir = out / "wiki" / "quarantine"
qdir.mkdir(parents=True, exist_ok=True)
for item in quarantine:
    md = export.render_record_page(
        {"record_id": item.get("item_id") or item.get("record_id"),
         "library": "quarantine", "status": item.get("status", "quarantine"),
         "canonical": {"item": item.get("item_id"), "group": item.get("group"),
                       "subclass": item.get("subclass"), "disposition": item.get("disposition"),
                       "detail": item.get("detail")},
         "evidence": [], "_aliases": []}, anchor)
    (qdir / f"{item.get('item_id') or item.get('record_id')}.md").write_text(md, encoding="utf-8")

# 索引页
idx = out / "wiki" / "indexes"
(idx / "by-type").mkdir(parents=True, exist_ok=True)
by_lib = {}
for r in records:
    by_lib.setdefault(r.get("library") or "misc", []).append(r)
for lib, rs in sorted(by_lib.items()):
    lines = [f"# {lib} 索引（{len(rs)} 件）", ""]
    for r in sorted(rs, key=lambda x: x["record_id"]):
        name = (r.get("canonical") or {}).get("name") or r["record_id"]
        st = r.get("status", "")
        lines.append(f"- [{name}](../records/{lib}/{r['record_id']}.md) `{st}` `{r['record_id']}`")
    (idx / "by-type" / f"{lib}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

sup_lines = ["# 失效链索引（supersede-index）", ""]
for r in sup:
    sup_lines.append(f"- seq{r.get('seq')} `{r.get('op')}` → {r.get('target')}（sha_after `{str(r.get('sha_after'))[:12]}`）")
(idx / "superseded.md").write_text("\n".join(sup_lines) + "\n", encoding="utf-8")

comp_lines = ["# 互补陈述索引（complementary-statements）", ""]
for c in comps:
    ev = (c.get("evidence") or [{}])
    q = ev[0].get("quote", "") if isinstance(ev[0], dict) else ""
    comp_lines.append(f"- `{c.get('event_id')}` about={c.get('about')} @ {c.get('at')}：{q[:80]}")
(idx / "complementary.md").write_text("\n".join(comp_lines) + "\n", encoding="utf-8")

# 4 图谱投影
gdir = out / "graph"
gdir.mkdir(parents=True, exist_ok=True)
(gdir / "nodes.jsonl").write_text(
    "".join(json.dumps(n, ensure_ascii=False) + "\n" for n in nodes), encoding="utf-8")
(gdir / "edges.jsonl").write_text(
    "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in edges), encoding="utf-8")

# 5 对账 + SNAPSHOT
rec = export.reconcile(pages=pages, store_records=recs_by_id, sample_n=ns.sample_n)
snapshot = dict(anchor)
snapshot["隔离页数"] = len(quarantine)
snapshot["索引页"] = ["_index.md", "indexes/by-type/*.md", "indexes/superseded.md", "indexes/complementary.md"]
snapshot["对账结果"] = rec
snapshot["状态"] = "PASS" if (rec["页数对账"] and rec["引文抽查"]["ok"]) else "FAIL——不发布"
(out / "SNAPSHOT.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")

# 全局索引（含对账结果）
idx_md = [
    f"# 快照索引（{store.name}）",
    "",
    f"- 快照状态：**{snapshot['状态']}**",
    f"- 检查点：rows={head.get('rows')} chain_head=`{str(head.get('chain_head'))[:12]}`",
    f"- 规模：{len(records)} 记录页 + {len(quarantine)} 隔离页；图谱 {len(nodes)} 节点/{len(edges)} 边",
    "- 导航：[by-type](indexes/by-type/) · [失效链](indexes/superseded.md) · [互补陈述](indexes/complementary.md) · [隔离区](../wiki/quarantine/)",
]
(out / "wiki" / "_index.md").write_text("\n".join(idx_md) + "\n", encoding="utf-8")

print(json.dumps({"状态": snapshot["状态"], "记录页": len(pages), "隔离页": len(quarantine),
                  "节点": len(nodes), "边": len(edges), "对账": rec,
                  "SNAPSHOT": str(out / "SNAPSHOT.json")}, ensure_ascii=False))
sys.exit(0 if snapshot["状态"].startswith("PASS") else 1)
