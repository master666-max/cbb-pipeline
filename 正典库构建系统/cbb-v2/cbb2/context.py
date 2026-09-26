# -*- coding: utf-8 -*-
"""cbb2.context — 承接摘要 + 三层上下文包（Phase C·U-C02；流程设计 P2·⑤.1）。

三层（Context by Distinct Information 实证：混合省一半 token 保效果）：
  实体卡（内容寻址+新颖性门控）⊕ 滚动摘要（递归状态）⊕ 近窗（上一章尾）。
时间性激活（lorebook 移植）：sticky 激活后粘滞 N 章 / cooldown 冷却——防重复挤占预算。
指代显式化：包内一律用规范名，别名仅注记。先验非事实源（v1.6 铁律不动）。
"""
from __future__ import annotations

import json
from pathlib import Path

CARRY_MAX = 200
STATE_FILE = "上下文激活状态.json"


def _records(store_root: Path):
    for f in sorted(Path(store_root).glob("libraries/*/*/*.json")):
        try:
            yield json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue


def _max_chapter(rec: dict) -> int:
    chs = [e.get("chapter") for e in (rec.get("evidence") or []) if isinstance(e.get("chapter"), int)]
    return max(chs) if chs else 0


def carry_summary(store_root: Path, prev_chapter: int) -> str:
    """上一章在场实体+最新事件尾部——机械生成 ≤200 字（边界信息损失对策）。"""
    ents, events = [], []
    for rec in _records(store_root):
        if _max_chapter(rec) != prev_chapter:
            continue
        c = rec.get("canonical") or {}
        if rec.get("record_type") == "entity" and c.get("name"):
            ents.append(c["name"])
        elif rec.get("record_type") == "event":
            tail = (rec.get("observations") or [{}])[-1].get("text", "")
            if tail:
                events.append(tail)
    names = "、".join(dict.fromkeys(ents))[:80]
    ev = (events[-1] if events else "")[:80]
    s = f"承接第{prev_chapter}章：在场={names or '（无新记录）'}；{('最近事件=' + ev) if ev else ''}".strip()
    return s[:CARRY_MAX]


def _load_state(store_root: Path) -> dict:
    p = Path(store_root) / STATE_FILE
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def save_state(store_root: Path, state: dict):
    (Path(store_root) / STATE_FILE).write_text(
        json.dumps(state, ensure_ascii=False, sort_keys=True, indent=1), encoding="utf-8")


def activation_filter(store_root: Path, chapter: int, entity_names: list[str]) -> list[str]:
    """sticky/cooldown：激活过的实体粘滞到 sticky_until；冷却中（cooldown_until≥chapter）剔除。"""
    st = _load_state(store_root)
    out = []
    for nm in entity_names:
        e = st.get(nm, {})
        if e.get("cooldown_until", 0) >= chapter:
            continue
        out.append(nm)
        if chapter > e.get("sticky_until", 0):
            sticky = int(st.get("_sticky_n", 2))
            e["sticky_until"] = chapter + sticky
            st[nm] = e
    save_state(store_root, st)
    return out


def build_context_pack(store_root: Path, chapter: int, prev_slice_tail: str = "",
                       budget: int = 2000, sticky_n: int = 2) -> dict:
    """三层包：实体卡+滚动摘要+近窗；预算硬顶（字符）；先验非事实源标注。"""
    st = _load_state(store_root)
    st["_sticky_n"] = sticky_n
    save_state(store_root, st)
    by_ent: dict[str, dict] = {}
    rolling: list[str] = []
    for rec in _records(store_root):
        ch = _max_chapter(rec)
        if ch >= chapter:
            continue
        c = rec.get("canonical") or {}
        if rec.get("record_type") == "entity" and c.get("name"):
            g = by_ent.setdefault(c["name"], {"name": c["name"], "chapters": set()})
            g["chapters"].add(ch)
            for k in ("status", "entity_type"):
                if c.get(k):
                    g[k] = c[k]
        if ch >= chapter - 3:
            line = f"第{ch}章:{len([1]) and (c.get('name') or c.get('subject') or '')}"
            rolling.append(line)
    names = sorted(by_ent, key=lambda n: -max(by_ent[n]["chapters"]))
    picked = activation_filter(store_root, chapter, names[:12])
    cards = []
    used = 0
    for nm in picked:
        g = by_ent[nm]
        card = f"{nm}({g.get('entity_type', '')},{g.get('status', '')}) chapters={sorted(g['chapters'])[-3:]}"
        if used + len(card) > budget:
            break
        cards.append(card)
        used += len(card)
    roll = "｜".join(rolling[-3:])[:budget // 3]
    tail = (prev_slice_tail or "")[-budget // 3:]
    used += len(roll) + len(tail)
    return {"实体卡": cards, "滚动摘要": roll, "近窗": tail,
            "budget_used": used, "budget": budget,
            "口径": "先验非事实源——与原文冲突以原文为准（指代已显式化为规范名）"}
