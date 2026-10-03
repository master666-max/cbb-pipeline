# -*- coding: utf-8 -*-
"""cbb2.export — 交付形态层引擎（批次 3·X1）：快照锚 / 记录页渲染 / 对账 / 图谱投影。

快照范式公理（批次 3 工单）：
  store=活体（唯一事实源）；导出=不可变快照（生成即冻结）；快照自锚定（检查点+对账随包）；
  对账失败 ⇒ 快照标 FAIL 不发布。渲染器责任=忠实性（对账纪律），内容质量归判卷战役。
"""
from __future__ import annotations

import hashlib
import json
import random
import time
from pathlib import Path

EXPORTER_VERSION = "1.0"
VALID = ("provisional", "confirmed", "quarantine")


def build_anchor(store_root: Path, ledger_head: dict, record_count: int, page_count: int,
                 edge_count: int, exporter_version: str = EXPORTER_VERSION) -> dict:
    """快照锚：账本检查点 + 记录数/页数/边数对账 + 导出器版本。不可变语义由消费方保证。"""
    return {"检查点": {"rows": ledger_head.get("rows"), "chain_head": ledger_head.get("chain_head")},
            "store_root": str(store_root),
            "对账": {"store记录数": record_count, "记录页数": page_count, "边数": edge_count},
            "导出器版本": exporter_version,
            "生成时间": time.strftime("%Y-%m-%dT%H:%M:%S")}


def render_record_page(record: dict, snapshot_anchor: dict) -> str:
    """记录页（1:1 忠实渲染）：YAML front-matter + 断言 + 逐字引文块引 + 观察 + 状态标注。
    一页=一自然 RAG 块。快照锚写入 front-matter（自锚定）。"""
    rid = record["record_id"]
    canonical = record.get("canonical") or {}
    name = canonical.get("name") or rid
    status = record.get("status") or "provisional"
    aliases = record.get("_aliases") or []
    ev = record.get("evidence") or []
    chapters = sorted({e.get("chapter") for e in ev if isinstance(e, dict) and e.get("chapter") is not None})
    sup = record.get("supersedes")
    lines = [
        "---",
        f"record_id: {rid}",
        f"type: {record.get('library') or record.get('record_type') or 'unknown'}",
        f"status: {status}",
        f"aliases: {json.dumps(aliases, ensure_ascii=False)}",
        f"chapters: {json.dumps(chapters)}",
        f"evidence_count: {len(ev)}",
        f"supersedes: {json.dumps(sup, ensure_ascii=False)}",
        f"快照锚: {json.dumps(snapshot_anchor, ensure_ascii=False, sort_keys=True)}",
        "---",
        "",
        f"# {name}",
        "",
        "## 断言（canonical）",
        "",
        "```json",
        json.dumps(canonical, ensure_ascii=False, sort_keys=True, indent=1),
        "```",
        "",
        "## 证据引文（逐字，可回链）",
        "",
    ]
    for e in ev:
        if not isinstance(e, dict):
            continue
        loc = f"[卷{e.get('vol', '?')} 章{e.get('chapter', '?')} 行{e.get('line', '?')}]"
        lines.append(f"> {loc} {e.get('quote', '')}")
    lines.append("")
    obs = record.get("observations") or []
    if obs:
        lines.append("## 观察")
        lines.append("")
        for o in obs:
            text = o.get("text") if isinstance(o, dict) else str(o)
            cat = o.get("category", "") if isinstance(o, dict) else ""
            lines.append(f"- {'[' + cat + '] ' if cat else ''}{text}")
        lines.append("")
    lines.append("## 状态标注")
    lines.append("")
    lines.append(f"`{status}`" + ("（隔离区，勿混入正式区）" if status == "quarantine" else ""))
    return "\n".join(lines) + "\n"


def reconcile(pages: dict[str, str], store_records: dict[str, dict], sample_n: int = 30) -> dict:
    """对账（全机械）：①页数/集合对账（缺页+多页）；②引文抽查（随机 N 页，页内块引
    必须逐字出现在 store evidence quote 中——快照手改/渲染不忠实即 FAIL）。"""
    page_ids = set(pages)
    store_ids = set(store_records)
    missing = sorted(store_ids - page_ids)
    extra = sorted(page_ids - store_ids)
    page_ok = (not missing) and (not extra)

    rng = random.Random(20260929)
    sample_ids = sorted(page_ids & store_ids)
    rng.shuffle(sample_ids)
    sample_ids = sample_ids[:sample_n]
    quote_fail = []
    for rid in sample_ids:
        quotes = [e.get("quote", "") for e in (store_records[rid].get("evidence") or [])
                  if isinstance(e, dict)]
        page = pages[rid]
        for q in quotes:
            if q and q not in page:
                quote_fail.append({"record_id": rid, "quote": q[:60]})
    return {"页数对账": page_ok, "缺失页": missing, "多出页": extra,
            "引文抽查": {"ok": not quote_fail, "样本": len(sample_ids), "失败": quote_fail[:5]}}


def project_graph(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """图谱投影：节点=带 name 的记录（实体面）；边=relation 记录的 canonical
    {subject, predicate, object} 投影（不可投影的 relation 跳过，不造边）。"""
    nodes, edges = [], []
    seen = set()
    for r in records:
        canon = r.get("canonical") or {}
        name = canon.get("name")
        if name and name not in seen:
            seen.add(name)
            nodes.append({"name": name, "type": r.get("library") or r.get("record_type"),
                          "status": r.get("status"), "record_id": r["record_id"],
                          "aliases": r.get("_aliases") or []})
    for r in records:
        if (r.get("library") or r.get("record_type")) != "relation":
            continue
        canon = r.get("canonical") or {}
        # 2026-10-01 审计修正：库内契约是 rel_type（store.identity_key 口径），predicate 是旧投影方言；
        # 只读 predicate 使正规写入链的关系边标签全部退化成"关联"
        s, p, o = canon.get("subject"), canon.get("rel_type") or canon.get("predicate"), canon.get("object")
        if s and o:
            edges.append({"source": s, "predicate": p or "关联", "target": o,
                          "status": r.get("status"), "record_id": r["record_id"]})
    return nodes, edges
