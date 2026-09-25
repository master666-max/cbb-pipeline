# -*- coding: utf-8 -*-
"""graphiti_dump.py — 按 group 导出 graphiti 图的实体/关系清单 + canon 命中率（质量评估件）。

用法：py -X utf8 graphiti_dump.py --group <group_id> [--out <json>]
命中率口径：实体名 ∈ 正典库实体名∪别名（canon 全集）→ hit；否则列出人工研判。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from neo4j_export import derive_password  # noqa: E402

BOLT = "bolt://localhost:7693"
STORE = HERE.parent.parent / "迷深实战-本体库"


def canon_set() -> set[str]:
    names = set()
    for f in STORE.glob("libraries/*/*/*.json"):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        nm = (rec.get("canonical") or {}).get("name")
        if nm:
            names.add(nm)
    aliases = STORE / "aliases.jsonl"
    if aliases.exists():
        for ln in aliases.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                al = json.loads(ln).get("alias")
                if isinstance(al, str):
                    names.add(al)
    return names


async def dump(group: str | None) -> dict:
    from neo4j import AsyncGraphDatabase
    pw = derive_password(None)
    driver = AsyncGraphDatabase.driver(BOLT, auth=("neo4j", pw))
    out: dict = {"group": group or "(全部)"}
    async with driver.session(database="neo4j") as s:
        ents = await (await s.run("MATCH (n:Entity) WHERE ($g IS NULL OR n.group_id = $g) "
                                  "RETURN n.name AS n, n.summary AS s", {"g": group})).data()
        rels = await (await s.run("MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity) "
                                  "WHERE ($g IS NULL OR (a.group_id = $g AND b.group_id = $g)) "
                                  "RETURN a.name AS f, r.fact AS fact, b.name AS t",
                                  {"g": group})).data()
    await driver.close()
    canon = canon_set()
    hit = [e["n"] for e in ents if e["n"] in canon]
    out.update({"entities": [{"name": e["n"], "canon_hit": e["n"] in canon,
                              "summary_head": (e["s"] or "")[:60]} for e in ents],
                "relations": [{"from": r["f"], "fact": (r["fact"] or "")[:80], "to": r["t"]}
                              for r in rels],
                "canon命中率": f"{len(hit)}/{len(ents)}"})
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default=None)
    ap.add_argument("--out", default="")
    ns = ap.parse_args()
    rep = asyncio.run(dump(ns.group))
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    if ns.out:
        Path(ns.out).write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
