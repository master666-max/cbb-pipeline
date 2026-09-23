# -*- coding: utf-8 -*-
"""抽样排序.py — 审查抽样的"最可疑优先"排序（岗位②·U-F05；2026-09-23）

场景：G2 证据门/人工抽检要看的样本很多，人先看最值得看的。
原理：重排器打"**引文对断言的支撑度**"分——支撑度**越低越可疑**，升序排列＝最可疑最先。
纪律（深融条款）：
  · **只定顺序，不定结论**：不改样本集合、不判对错、不进任何红区；
  · **缺席即降级**：重排器不可用 → 保持原序（机械），backend 如实标注；
  · 分数只作内部排序，不外报（judge 红线同源）。
"""
from __future__ import annotations

import 重排器 as rr


def rank_for_review(items: list[dict], endpoint: str | None = None,
                    transport=None) -> dict:
    """items: [{"record_id":…, "claim": 断言文本, "quote": 引文文本}, …]（顺序=原抽样序）。
    返回 {"order": [下标序列·最可疑最先], "backend": "rerank|mechanical", "supports": {record_id: 分}}。
    断言/引文缺文本的条目按机械原序处理（不虚构分数）。"""
    supports: dict[int, float] = {}
    backend = "rerank"
    for i, it in enumerate(items):
        claim = (it.get("claim") or "").strip()
        quote = (it.get("quote") or "").strip()
        if not claim or not quote:
            backend = "mechanical"  # 有缺文本项 → 整体转机械（同形、口径注明）
            break
        s = rr.score(claim, [quote], endpoint, transport=transport)
        if s is None:
            backend = "mechanical"
            break
        supports[i] = s[0]
    if backend == "rerank":
        order = sorted(range(len(items)), key=lambda i: supports.get(i, 0.0))
    else:
        order = list(range(len(items)))
    sup_out = {items[i].get("record_id"): round(supports[i], 6) for i in supports}
    return {"order": order, "backend": backend, "supports": sup_out,
            "口径": "支撑度升序＝最可疑最先；重排只定顺序不定结论；缺席降级保持原序"}
