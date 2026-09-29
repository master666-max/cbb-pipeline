# -*- coding: utf-8 -*-
"""build_v22_round.py — 迷深 v2.2 五十件验证轮组装（42 正件分层 + 8 株）。

产出：迷深实战-工作区/判卷/{records.jsonl, plants.jsonl}（供 judge_assemble）。
分层：本体库五类型 × 按比例；植株=g16c_rejudge.build_plants(4, 20260928) 同源同种。
"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from g16c_rejudge import build_plants  # noqa: E402

store = HERE / "迷深实战-本体库"
out = HERE / "迷深实战-工作区" / "判卷"
out.mkdir(parents=True, exist_ok=True)

rng = random.Random(20260929)
by_lib = {}
for f in sorted(store.glob("libraries/*/*/*.json")):
    rec = json.loads(f.read_text(encoding="utf-8"))
    if rec.get("status") != "provisional":
        continue
    ev = rec.get("evidence") or []
    if not ev:
        continue
    by_lib.setdefault(rec.get("library") or "misc", []).append({
        "record_id": rec["record_id"],
        "conclusion": json.dumps(rec.get("canonical") or {}, ensure_ascii=False, sort_keys=True),
        "evidence": "；".join(e.get("quote", "") for e in ev),
    })
print("类型池:", {k: len(v) for k, v in sorted(by_lib.items())})

sample, per = [], 8
for lib in sorted(by_lib):
    pool = by_lib[lib][:]
    rng.shuffle(pool)
    take = pool[:per]
    sample.extend(take)
sampled_per_lib = {lib: sum(1 for s in sample if s["record_id"] in {x["record_id"] for x in by_lib[lib]}) for lib in by_lib}
print("抽样:", sampled_per_lib)

with (out / "records.jsonl").open("w", encoding="utf-8") as f:
    for r in sample:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

plants = build_plants(4, 20260928)
with (out / "plants.jsonl").open("w", encoding="utf-8") as f:
    for p in plants:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")
print(f"植株 {len(plants)} 株写入")
print(json.dumps({"正件": len(sample), "株": len(plants)}, ensure_ascii=False))
