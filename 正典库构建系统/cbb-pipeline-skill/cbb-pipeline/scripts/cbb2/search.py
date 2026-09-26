# -*- coding: utf-8 -*-
"""cbb2.search — 机械检索面：别名精确 + 关键词 + RRF + 引文核验（R11；端点相关路不在核心包）。"""
from __future__ import annotations

import json
import re
from pathlib import Path


def alias_recall(query: str, store_root: Path) -> list[dict]:
    q = query
    hits: dict[str, dict] = {}
    id2name: dict[str, str] = {}
    store = Path(store_root)
    for f in sorted(store.glob("libraries/character/*/*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        nm = (rec.get("canonical") or {}).get("name")
        if nm:
            id2name[rec.get("record_id")] = nm
    aliases = store / "aliases.jsonl"
    if aliases.exists():
        for row in [json.loads(x) for x in aliases.read_text(encoding="utf-8").splitlines() if x.strip()]:
            al = row.get("alias")
            if isinstance(al, str) and al and al in q:
                rid = row.get("entity_id")
                nm = id2name.get(rid)
                if nm:
                    hits[nm] = {"name": nm, "record_id": rid, "via": "alias"}
    for nm in id2name.values():
        if len(nm) >= 2 and nm in q:
            hits[nm] = {"name": nm, "record_id": None, "via": "exact"}
    return list(hits.values())


def rrf(rank_lists: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    acc: dict[str, float] = {}
    for lst in rank_lists:
        for rank, item in enumerate(lst):
            acc[item] = acc.get(item, 0.0) + 1.0 / (k + rank + 1)
    return sorted(acc.items(), key=lambda x: -x[1])


def verify_citations(citations: list[dict], store_root: Path) -> dict:
    pool: set[tuple[str, str]] = set()
    store = Path(store_root)
    for f in sorted(store.glob("libraries/*/*/*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        rid = rec.get("record_id")
        for ev in rec.get("evidence") or []:
            pool.add((rid, ev.get("quote")))
    ok, bad = [], []
    for c in citations:
        (ok if (c.get("record_id"), c.get("quote")) in pool else bad).append(c)
    return {"verified": ok, "unverified": bad,
            "口径": "核验=record_id+quote 在库内证据集中逐字存在"}
