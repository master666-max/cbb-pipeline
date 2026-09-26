# -*- coding: utf-8 -*-
"""词表类型映射构建.py — U-A07：从隔离区 604 件双轨 detail 提取 entity_type 映射表。

规则：
  granularity（一侧值含另一侧/括注超集）→ 规范值=更全一侧（机械，无争议）；
  direct_conflict → 规范值=库内值（改入库侧不动现役库）；
  同一入库值映射到多个不同库内值 → 冲突 → 人工桶（不进映射表）。
产出：迷深实战-工作区/词表类型映射-20260926.json + 覆盖率报告（stdout）。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
Q = ROOT / "迷深实战-本体库" / "quarantine-zone" / "items.jsonl"
OUT = ROOT / "迷深实战-工作区" / "词表类型映射-20260926.json"
PAT = re.compile(r"entity_type: 入库='(.*)' vs 库内='(.*)'")

gran, direct = {}, {}   # variant -> {canonical: count}
unparsed = []
for line in Q.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    it = json.loads(line)
    if it.get("subclass") != "contradiction_pending" or it.get("status") != "pending":
        continue
    m = PAT.search(it.get("detail", ""))
    if not m:
        unparsed.append(it.get("item_id"))
        continue
    vin, vst = m.group(1), m.group(2)
    if vin == vst:
        continue
    # granularity 判定：一侧去括注/去空白后包含另一侧
    core_in = re.sub(r"（.*?）|\(.*?\)|\s", "", vin)
    core_st = re.sub(r"（.*?）|\(.*?\)|\s", "", vst)
    if core_in and core_st and (core_in in core_st or core_st in core_in):
        canon = vin if len(vin) >= len(vst) else vst
        variant = vst if canon == vin else vin
        gran.setdefault(variant, {})
        gran[variant][canon] = gran[variant].get(canon, 0) + 1
    else:
        direct.setdefault(vin, {})
        direct[vin][vst] = direct[vin].get(vst, 0) + 1

mapping, conflicts = {}, {}
for table in (gran, direct):
    for variant, targets in table.items():
        if len(targets) == 1:
            mapping[variant] = next(iter(targets))
        else:
            conflicts[variant] = targets

report = {
    "granularity_variants": sum(1 for t in gran.items()),
    "direct_variants": len(direct),
    "mapping_entries": len(mapping),
    "conflict_variants_manual": conflicts,
    "unparsed_items": len(unparsed),
}
OUT.write_text(json.dumps(
    {"_review": "U-A07 产物；mapping=variant→canonical（规范值）；conflicts 需人工裁定",
     "mapping": dict(sorted(mapping.items())), "conflicts": conflicts,
     "unparsed_items": unparsed}, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in report.items() if k != "conflict_variants_manual"},
                 ensure_ascii=False, indent=1))
print("冲突变体（人工桶）:", json.dumps(conflicts, ensure_ascii=False)[:600])
print("落盘:", OUT.name)
