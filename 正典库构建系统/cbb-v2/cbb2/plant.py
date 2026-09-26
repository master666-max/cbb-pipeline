# -*- coding: utf-8 -*-
"""cbb2.plant — 植物捕获金标（Phase D·U-D06；plant capture，arXiv:2403.04058 思路）。

向待抽域注入已知答案的合成记录（"植物"），抽取完成后测捕获率——
绕开 capture-recapture 的独立性假设，是对 Chapman 估计的硬交叉验证。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

STATE = "植物捕获-金标.jsonl"


def plant(store_root: Path, seeds: list[dict], at: str) -> list[dict]:
    """登记金标植物：每株 {plant_id, expect(字段断言), source_chapter, at}。返回带 id 的清单。"""
    p = Path(store_root) / STATE
    out = []
    for s in seeds:
        pid = "plant-" + hashlib.sha256(json.dumps(s, sort_keys=True, ensure_ascii=False)
                                        .encode()).hexdigest()[:12]
        row = {"plant_id": pid, "expect": s.get("expect") or {}, "name": s.get("name", ""),
               "source_chapter": s.get("source_chapter"), "at": at, "captured": False}
        out.append(row)
    with p.open("a", encoding="utf-8") as f:
        for row in out:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return out


def capture_rate(store_root: Path, harvested_records: list[dict],
                 chapter: int | None = None) -> dict:
    """捕获率=被抽中(身份键命中 expect.name)且断言符合 expect 的株数 / 总株数。"""
    p = Path(store_root) / STATE
    plants = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] \
        if p.exists() else []
    idx = {}
    for r in harvested_records:
        c = r.get("canonical") or {}
        if c.get("name"):
            idx[c["name"]] = c
    hit = 0
    results = []
    for pl in plants:
        if chapter is not None and pl.get("source_chapter") not in (None, chapter):
            continue
        c = idx.get(pl["name"])
        ok = bool(c)
        if ok:
            for k, v in (pl.get("expect") or {}).items():
                if c.get(k) != v:
                    ok = False
                    break
        hit += ok
        pl["captured"] = ok
        results.append({"plant_id": pl["plant_id"], "name": pl["name"], "captured": ok})
    p.write_text("\n".join(json.dumps(x, ensure_ascii=False, sort_keys=True) for x in plants) + "\n",
                 encoding="utf-8")
    n = len(results)
    return {"plants": n, "captured": hit,
            "rate": round(hit / n, 4) if n else None,
            "miss": [r for r in results if not r["captured"]]}
