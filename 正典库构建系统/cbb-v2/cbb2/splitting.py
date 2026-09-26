# -*- coding: utf-8 -*-
"""cbb2.splitting — 门控动态切分 + 场景软标签（Phase C·U-C01；流程设计 P1）。

证据口径：语义切分全面替代被证伪（NAACL 2025）而大块掉实体召回（GraphRAG 实证）
→ 本模块只做**门控二次切分**：默认整章，重章信号触发章内逻辑分段（归并交抽取侧）。
场景边界=廉价机械信号的**软标签**（学术 SOTA 仅 ~51% 召回，不追硬切精度）。
θ 全部 env 可调；旗标 CBB_DYNAMIC_SPLIT 默认 off——实验不阻塞主线。
"""
from __future__ import annotations

import os
import re

SEPARATOR_RE = re.compile(r"^\s*(\*{3,}|—{3,}|■+|={3,}|◇+|※+)\s*$")
TIME_JUMP_WORDS = ("次日", "翌日", "当晚", "第二天", "数日后", "与此同时", "另一边",
                   "半小时后", "片刻后", "翌日清晨", "三天后", "一周后")

DEFAULT_THETA = {"theta_len": 12000, "theta_scenes": 3, "theta_newent": 15}


def enabled() -> bool:
    return os.environ.get("CBB_DYNAMIC_SPLIT", "off").lower() in ("on", "1", "true")


def theta() -> dict:
    t = dict(DEFAULT_THETA)
    for k in t:
        v = os.environ.get(f"CBB_{k.upper()}")
        if v and v.isdigit():
            t[k] = int(v)
    return t


def scene_tags(blocks: list[dict]) -> dict:
    """机械场景软标签：分隔符行/空段跳变/时间跳变词/对话密度 → 边界估计（不硬切）。"""
    boundaries: list[int] = []
    time_jumps = 0
    dialogue_paras = 0
    for b in blocks:
        if SEPARATOR_RE.match(b["text"]):
            boundaries.append(b["block_id"])
            continue
        head = b["text"][:24]
        if any(w in head for w in TIME_JUMP_WORDS):
            time_jumps += 1
            boundaries.append(b["block_id"])
        if "「" in b["text"] or "」" in b["text"]:
            dialogue_paras += 1
    n_blocks = max(1, len(blocks))
    scene_count = min(len(boundaries) + 1, n_blocks)
    return {"scene_count": scene_count, "boundaries": boundaries,
            "dialogue_ratio": round(dialogue_paras / n_blocks, 3),
            "time_jumps": time_jumps,
            "口径": "软标签——分段的归并语义在抽取侧，不做硬边界切割"}


def split_decision(chapter_text: str, tags: dict,
                   new_entity_hint: int | None = None) -> dict:
    """升级抽取 = (字数>θ_len) ∨ (场景边界数>θ_s) ∨ (新实体率>θ_e)。θ=env 可调。"""
    t = theta()
    reasons = []
    if len(chapter_text) > t["theta_len"]:
        reasons.append(f"字数{len(chapter_text)}>θ_len={t['theta_len']}")
    scenes = tags.get("scene_count", 1) - 1
    if scenes > t["theta_scenes"]:
        reasons.append(f"场景边界{scenes}>θ_scenes={t['theta_scenes']}")
    if new_entity_hint is not None and new_entity_hint > t["theta_newent"]:
        reasons.append(f"新实体{new_entity_hint}>θ_newent={t['theta_newent']}")
    return {"split": bool(reasons), "reasons": reasons, "theta": t}


def segment_blocks(blocks: list[dict], boundaries: list[int],
                   target_chars: int = 1200) -> list[list[dict]]:
    """边界处分组；无边界时按段落就近切到 target_chars（保段完整性，不劈段）。"""
    if boundaries:
        bset = set(boundaries)
        segs, cur = [], []
        for b in blocks:
            if b["block_id"] in bset and cur:
                segs.append(cur)
                cur = []
            cur.append(b)
        if cur:
            segs.append(cur)
        return segs
    segs, cur, size = [], [], 0
    for b in blocks:
        cur.append(b)
        size += len(b["text"])
        if size >= target_chars:
            segs.append(cur)
            cur, size = [], 0
    if cur:
        segs[-1].extend(cur) if segs else segs.append(cur)
    return segs
