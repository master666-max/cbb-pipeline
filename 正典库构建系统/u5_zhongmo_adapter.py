# -*- coding: utf-8 -*-
"""u5_zhongmo_adapter.py — U5 换书试点：终末停滞委员会第一卷 → 判卷产线记录/植株清单。

数据源：D:\qoder专用!!!\终末停滞委员会-本典库（qoder 外部实现建的库，read-only）。
过滤：evidence 含 vol==1（第一卷）的记录；判定面 conclusion=canonical JSON、
evidence=第一卷引文"；"连接。植株 4 株：2 正（原样）+2 负（张冠李戴：甲断言×乙证据）。
产出：records_zhongmo.jsonl + plants_zhongmo.jsonl（供 judge_assemble --records/--plants）。
"""
import json
import random
from pathlib import Path

STORE = Path(r"D:\qoder专用！！！\终末停滞委员会-正典库\本体库")
OUT = Path(__file__).resolve().parent / "终末试点"
OUT.mkdir(exist_ok=True)

records = []
for f in sorted(STORE.glob("libraries/*/*/*.json")):
    rec = json.loads(f.read_text(encoding="utf-8"))
    ev_all = rec.get("evidence") or []
    ev1 = [e for e in ev_all if isinstance(e, dict) and e.get("vol") == 1]
    if not ev1:
        continue
    records.append({
        "record_id": rec["record_id"],
        "library": rec.get("library") or f.parts[-3],
        "conclusion": json.dumps(rec.get("canonical") or {}, ensure_ascii=False, sort_keys=True),
        "evidence": "；".join(e.get("quote", "") for e in ev1),
    })
print(f"第一卷记录: {len(records)} 件 | 类型分布: ", end="")
from collections import Counter
print(dict(Counter(r["library"] for r in records)))

rng = random.Random(20260929)
rng.shuffle(records)

# 分层抽 46：每类型尽量均匀
by_lib = {}
for r in records:
    by_lib.setdefault(r["library"], []).append(r)
libs = sorted(by_lib)
sample, i = [], 0
while len(sample) < 46:
    for lib in libs:
        if by_lib[lib]:
            sample.append(by_lib[lib].pop(0))
            if len(sample) >= 46:
                break
    i += 1
    if i > 100:
        break
print("抽样 46 件分布:", dict(Counter(r["library"] for r in sample)))

with (OUT / "records_zhongmo.jsonl").open("w", encoding="utf-8") as f:
    for r in sample:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

# 植株：2 正（抽样件原样）+ 2 负（张冠李戴：结论×无关证据）
pos = sample[:2]
neg_a, neg_b = sample[20], sample[41]
plants = [
    {"record_id": "zplant-pos-0", "expected": "promote",
     "rec": {"conclusion": pos[0]["conclusion"], "evidence": pos[0]["evidence"]}},
    {"record_id": "zplant-pos-1", "expected": "promote",
     "rec": {"conclusion": pos[1]["conclusion"], "evidence": pos[1]["evidence"]}},
    {"record_id": "zplant-neg-0", "expected": "not_promote",
     "rec": {"conclusion": neg_a["conclusion"], "evidence": neg_b["evidence"]}},
    {"record_id": "zplant-neg-1", "expected": "not_promote",
     "rec": {"conclusion": neg_b["conclusion"], "evidence": neg_a["evidence"]}},
]
with (OUT / "plants_zhongmo.jsonl").open("w", encoding="utf-8") as f:
    for p in plants:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")
print(f"植株 4 株写入（pos 2 + neg 张冠李戴 2）→ {OUT}")
