# -*- coding: utf-8 -*-
"""匹配建议.py — 入库/隔离处置的"最可能对应既有记录"排序（岗位③·U-F06·仅建议位）

场景：候选实体/关系进 store 时，既有记录里可能有同指/近指——给人工一个**建议排序**。
红线（结构性保证，不是口头约定）：
  · 本模块**零写库**：返回值只能由调用方放进记录的 `_meta.match_suggestions`（人工复核位）；
  · **admit 前必须 `strip_suggestions()` 剥离**——store 会原样保留 _meta，不剥=建议混进正典记录；
  · store 的判定路径（identity_key / 0.85 门槛 / UNIQUE / 双轨合并 / 裁决）**不消费**该字段；
  · 建议可关闭且不影响主链（不调用即不存在）。
降级：重排器不可用 → 机械序（原序），backend 如实标注。
"""
from __future__ import annotations

import json

import 重排器 as rr


def strip_suggestions(record: dict) -> dict:
    """admit 前剥离建议位（纯函数：入参不动）。建议只属于人工复核，不得进入正典记录。"""
    out = json.loads(json.dumps(record, ensure_ascii=False))
    meta = out.get("_meta")
    if isinstance(meta, dict):
        meta.pop("match_suggestions", None)
        if not meta:
            out.pop("_meta", None)
    return out


def suggest_matches(candidate: dict, existing: list[dict], top_k: int = 5,
                    endpoint: str | None = None, transport=None) -> dict:
    """candidate: {"record_id":…, "canonical": {"name":…, "entity_type":…}}（待入库候选）
    existing:   [{"record_id":…, "name":…}, …]（既有实体名单，调用方自行圈定范围）
    返回 {"suggestions": [{record_id, name, rank}…≤top_k], "backend": "rerank|mechanical"}"""
    cname = (candidate.get("canonical") or {}).get("name") or ""
    docs = [(e.get("name") or "") for e in existing]
    mech = list(range(len(existing)))
    if not cname or not docs:
        return {"suggestions": [], "backend": "mechanical",
                "口径": "候选名或既有名单为空——无可建议"}
    o, backend = rr.rerank_order_or_mechanical(cname, docs, mech, endpoint, transport)
    sugg = [{"record_id": existing[i].get("record_id"), "name": existing[i].get("name"),
             "rank": r} for r, i in enumerate(o[:top_k])]
    return {"suggestions": sugg, "backend": backend,
            "口径": "仅建议位：供人工复核；不进 store 判定路径（结构性隔离由调用点保证）"}
