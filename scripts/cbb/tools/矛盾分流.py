# -*- coding: utf-8 -*-
"""矛盾分流.py — 四分类分流＋机械档处置（2026-09-22 用户裁决 ⑤：新项目 auto／存量 batch_confirm）

四分类（Kontrast 语义落地，裁定采纳）：
  identical        同值                ——非冲突
  orthographic     规范化后同值        ——机械可修（繁简/全半角/空白/括号差异）
  granularity      粒度差异（包含关系）——机械可修，对齐方向=**库内值**（存量一致性优先）
  incomplete       单侧缺失            ——"知识库不完整"，非冲突（自动关闭类）
  direct_conflict  其余                ——真冲突，**只进人工**（值互斥且两边都有证据）

处置双模式（裁决 ⑤）：
  auto            新项目：机械档建议直接执行（写处置台账）
  batch_confirm   存量库：机器只出建议清单；人工产出**确认件**（item_id 列表）后仅执行确认子集
  本件产出＝处置台账（append-only）；**记录级改写由管线按台账重抽后经 gate→store 落地**
  （旧件字节不动纪律）；候选级快速对齐用 `align_candidate()`（纯函数，重入库前调用）。

数据源：隔离区 contradiction_pending 件中 detail 形如 `字段: 入库='X' vs 库内='Y'` 的双轨冲突
（cbb_store.dual_track 的 contradiction 轨产出格式）。
"""
from __future__ import annotations

import json
import re
from datetime import date as _date
from pathlib import Path

from 词表 import normalize  # 规范化形共用一份（一词一职）

MECHANICAL = ("orthographic", "granularity")
CLASSES = ("identical", "orthographic", "granularity", "incomplete", "direct_conflict")
_DUAL = re.compile(r"^(.*?):\s*入库='(.*)'\s*vs\s*库内='(.*)'$")


def _today() -> str:
    return _date.today().isoformat()


def classify_pair(field: str, val_in: str, val_stored: str) -> dict:
    """对一对值四分类。返回 {cls, mechanical, align_to(机械档时), why}。"""
    if val_in == val_stored:
        return {"cls": "identical", "mechanical": True, "align_to": None, "why": "同值"}
    if val_in is None or val_stored is None or (isinstance(val_in, str) and not val_in.strip()) \
            or (isinstance(val_stored, str) and not val_stored.strip()):
        return {"cls": "incomplete", "mechanical": False, "align_to": None,
                "why": "单侧缺失——知识库不完整，非冲突"}
    if normalize(val_in) == normalize(val_stored):
        return {"cls": "orthographic", "mechanical": True, "align_to": val_stored,
                "why": "规范化后同值（繁简/全半角/空白/括号差异）"}
    ni, ns = normalize(val_in), normalize(val_stored)
    if ni and ns and (ni in ns or ns in ni):
        return {"cls": "granularity", "mechanical": True, "align_to": val_stored,
                "why": "粒度差异（包含关系）；对齐方向=库内值（存量一致性优先）"}
    return {"cls": "direct_conflict", "mechanical": False, "align_to": None,
            "why": "值互斥且非粒度/书写差异——真冲突，进人工"}


def parse_dual_track_detail(detail: str) -> tuple[str, str, str] | None:
    m = _DUAL.match(detail.strip())
    return (m.group(1).strip(), m.group(2), m.group(3)) if m else None


def propose(store_root: Path | str, limit: int | None = None) -> dict:
    """从隔离区产建议清单（只读干跑）。返回按类计数＋逐条建议。"""
    iq = Path(store_root) / "quarantine-zone" / "items.jsonl"
    items = [json.loads(x) for x in iq.read_text(encoding="utf-8").splitlines() if x.strip()] \
        if iq.exists() else []
    # A5 修复（审计 R4）：pending 判定按 adjudications 差集——items.status 写死后永不回写，
    # 静态过滤会让已裁件重入机械档（违反终态不可再动）
    aq = Path(store_root) / "quarantine-zone" / "adjudications.jsonl"
    adjudicated = {json.loads(x)["item_id"] for x in aq.read_text(encoding="utf-8").splitlines() if x.strip()} \
        if aq.exists() else set()
    by_cls: dict[str, int] = {c: 0 for c in CLASSES}
    proposals: list[dict] = []
    for it in items:
        if it.get("item_id") in adjudicated:
            continue
        if it.get("subclass") != "contradiction_pending":
            continue
        parsed = parse_dual_track_detail(it.get("detail", ""))
        if not parsed:
            continue  # 非双轨形态（嵌入存疑等）→ 不入本件口径，另见词表域
        field, vi, vs = parsed
        c = classify_pair(field, vi, vs)
        by_cls[c["cls"]] += 1
        proposals.append({"item_id": it["item_id"], "record_id": it.get("record_id"),
                          "field": field, "val_in": vi, "val_stored": vs,
                          "cls": c["cls"], "mechanical": c["mechanical"],
                          "align_to": c["align_to"], "why": c["why"]})
        if limit and len(proposals) >= limit:
            break
    return {"scanned_items": len(items), "proposals": proposals, "by_cls": by_cls,
            "口径": "分母=隔离区 contradiction_pending 且 detail 为双轨形态；其余形态不计入"}


def align_candidate(record: dict, field: str, align_to: str) -> dict:
    """候选级快速对齐（纯函数）：改 canonical 字段＋留痕；重入库走既有 gate→store。"""
    canon = dict(record.get("canonical") or {})
    canon[f"{field}"] = align_to
    out = dict(record, canonical=canon)
    out.setdefault("_meta", {})["alignment"] = {"field": field, "aligned_to": align_to,
                                                "at": _today()}
    return out


def apply(proposals: list[dict], mode: str, confirmations: list[str] | None = None,
          store_root: Path | str | None = None, at: str | None = None,
          by: str = "pipeline") -> dict:
    """执行机械档建议。auto=全执行（新项目）；batch_confirm=仅执行确认件内的 item_id（存量库）。
    直接冲突类**永不执行**（只进人工）。台账 append-only。"""
    if mode not in ("auto", "batch_confirm"):
        raise ValueError(f"非法 mode={mode!r}，合法=auto | batch_confirm")
    conf = set(confirmations or [])
    ledger_path = (Path(store_root) / "处置台账.jsonl") if store_root else None
    # A5b 修复：台账 item_id 幂等——重放不重复落账
    done_ids = set()
    if ledger_path is not None and ledger_path.exists():
        done_ids = {json.loads(x).get("item_id")
                    for x in ledger_path.read_text(encoding="utf-8").splitlines() if x.strip()}
    executed = skipped_cls = skipped_not_confirmed = skipped_dup = 0
    rows: list[dict] = []
    for p in proposals:
        if not p.get("mechanical"):
            skipped_cls += 1
            continue
        if p["item_id"] in done_ids:
            skipped_dup += 1
            continue
        if mode == "batch_confirm" and p["item_id"] not in conf:
            skipped_not_confirmed += 1
            continue
        row = {"item_id": p["item_id"], "record_id": p.get("record_id"),
               "action": "align_field", "field": p["field"],
               "from": p["val_in"], "to": p["align_to"],
               "cls": p["cls"], "basis": p["why"], "mode": mode, "by": by,
               "at": at or _today()}
        rows.append(row)
        executed += 1
    if ledger_path is not None and rows:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with ledger_path.open("a", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"executed": executed, "skipped_direct_conflict": skipped_cls,
            "skipped_already_in_ledger": skipped_dup,
            "skipped_not_confirmed": skipped_not_confirmed,
            "ledger": str(ledger_path) if ledger_path else None,
            "口径": f"mode={mode}；direct_conflict 永不机械执行；记录级改写由管线按台账重抽落地"}


def main(argv=None) -> int:  # pragma: no cover
    import argparse
    ap = argparse.ArgumentParser(description="矛盾分流（裁决⑤）")
    ap.add_argument("--store", required=True)
    ap.add_argument("--limit", type=int)
    ns = ap.parse_args(argv)
    rep = propose(ns.store, ns.limit)
    print(json.dumps(rep["by_cls"], ensure_ascii=False))
    for p in rep["proposals"][:20]:
        print(f"  [{p['cls']}] {p['item_id']} {p['field']}: {p['val_in']!r} → {p['align_to']!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
