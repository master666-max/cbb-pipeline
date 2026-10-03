# -*- coding: utf-8 -*-
"""batch6_export.py — 批次 6·聚合人物页 + lorebook 转换器（ST/RAG 双格式选项）。

用法：py -X utf8 batch6_export.py --store 迷深实战-本体库 --aliases 迷深实战-本体库/aliases.jsonl
        --snapshot 快照-迷深实战/SNAPSHOT.json --out 快照-迷深实战 [--format all] [--status all|confirmed]

状态口径：effective（文件 status + transitions.jsonl 旁车叠加）——R13 文件不动设计下
文件 status 恒为历史值，物料化/降级的真值在 transitions。
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from cbb2 import aggregate, export  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--store", required=True)
ap.add_argument("--aliases", required=True)
ap.add_argument("--snapshot", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--format", choices=["st", "rag", "all"], default="all")
ap.add_argument("--status", choices=["all", "confirmed"], default="all")
ns = ap.parse_args()

store = Path(ns.store).resolve()
out = Path(ns.out).resolve()
snapshot = json.loads(Path(ns.snapshot).read_text(encoding="utf-8"))
anchor = {"检查点": snapshot.get("检查点"), "store_root": snapshot.get("store_root")}

records = []
for f in sorted((store / "libraries").glob("*/*/*.json")):
    r = json.loads(f.read_text(encoding="utf-8"))
    records.append(r)
alias_rows = [json.loads(l) for l in Path(ns.aliases).read_text(encoding="utf-8").splitlines() if l.strip()]

# effective status：文件 status + transitions 叠加（末条胜出）
trans = {}
tf = store / "transitions.jsonl"
if tf.exists():
    for l in tf.read_text(encoding="utf-8").splitlines():
        s = l.strip()
        if not s:
            continue
        try:
            e = json.loads(s)
        except Exception:
            continue
        trans[e.get("record_id")] = e.get("to") or trans.get(e.get("record_id"))
eff = {r["record_id"]: trans.get(r["record_id"]) or r.get("status", "provisional") for r in records}

# --status confirmed：按 effective status 真过滤（文件 status + transitions 叠加，末条胜出）。
# 审计修复：原实现 --status 只是写进摘要的假开关（零过滤），未定（provisional）记录
# 会以「已确认」名义外流。零命中=如实输出 0 条（cluster/lorebook/rag 全为 0）。
if ns.status == "confirmed":
    records = [r for r in records if eff.get(r["record_id"]) == "confirmed"]

clusters = aggregate.build_clusters(records=records, alias_rows=alias_rows)


def safe_slug(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip() or "unnamed"


# ---- 聚合页 ----
agg_dir = out / "wiki" / "aggregates"
agg_dir.mkdir(parents=True, exist_ok=True)
slug_of = {}
for c in clusters:
    slug = safe_slug(c["main_name"])
    members = []
    for rid in c["members"]:
        rec = next((r for r in records if r["record_id"] == rid), None)
        if rec is None:
            continue
        canon = rec.get("canonical") or {}
        ev0 = (rec.get("evidence") or [{}])[0]
        members.append({"record_id": rid, "status": eff.get(rid, rec.get("status")),
                        "chapter": ev0.get("chapter") if isinstance(ev0, dict) else None,
                        "name": canon.get("name") or rid,
                        "quote": ev0.get("quote", "") if isinstance(ev0, dict) else "",
                        "canonical": canon, "evidence": rec.get("evidence") or []})
    md = aggregate.render_aggregate_page(main_name=c["main_name"], aliases=c["aliases"],
                                         members=members, anchor=anchor)
    (agg_dir / f"{slug}.md").write_text(md, encoding="utf-8")
    slug_of[c["main_name"]] = slug

# ---- lorebook：ST World Info + RAG 分块（双格式） ----
lore_dir = out / "lorebook"
lore_dir.mkdir(parents=True, exist_ok=True)
rec_by_id = {r["record_id"]: r for r in records}
entries = {}
rag_parts = []
uid = 0
order = 100
for c in sorted(clusters, key=lambda x: (-len(x["members"]), x["main_name"])):
    keys = [k for k in ([c["main_name"]] + sorted(c["aliases"])) if k]
    if not keys:
        continue
    body_lines = [f"【{c['main_name']}】聚合档案（{len(c['members'])} 条断言，三态随行）", ""]
    uid += 1
    for rid in c["members"]:
        rec = rec_by_id.get(rid)
        if rec is None:
            continue
        st = eff.get(rid, "provisional")
        canon = rec.get("canonical") or {}
        fact = canon.get("fact") or canon.get("rel_type") or canon.get("title") or ""
        if fact:
            body_lines.append(f"- 断言：{fact}（{st}）")
        for e in rec.get("evidence") or []:
            if isinstance(e, dict) and e.get("quote"):
                body_lines.append(f"- [卷{e.get('vol','?')}章{e.get('chapter','?')}] {e['quote']}"
                                  f"（源 {rid}）")
                break
    content = "\n".join(body_lines)
    entries[str(uid)] = {"uid": uid, "key": keys, "comment": c["main_name"],
                         "content": content, "constant": False, "selective": True,
                         "order": order - uid, "position": 0, "disable": False,
                         "probability": 100, "useProbability": True}
    rag_parts.append(f"## {c['main_name']}\n\nkeys: {', '.join(keys)}\n\n" + content + "\n")

st_book = {"entries": entries,
           "name": f"迷深实战-正典-lorebook（{ns.status}·批次 6）",
           "description": "批次 6 聚合导出：keys=正名+别名；content=聚合断言+引文回链（状态=effective）",
           "protocol": "https://github.com/SillyTavern/SillyTavern"}
if ns.format in ("st", "all"):
    (lore_dir / "sillytavern-v1.json").write_text(json.dumps(st_book, ensure_ascii=False, indent=1),
                                                  encoding="utf-8")
if ns.format in ("rag", "all"):
    (lore_dir / "rag-chunks.md").write_text("\n".join(rag_parts), encoding="utf-8")

summary = {"cluster 总数": len(clusters), "lorebook 条目": len(entries),
           "rag 块": len(rag_parts), "format": ns.format, "status_filter": ns.status,
           "聚合页目录": str(agg_dir), "状态口径": "effective（文件+transitions 叠加）"}
(out / "批次6摘要.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=1))
